"""GET /api/search/?q= — one box for people, projects, tasks, project notes and documents, and notices.
Every source reuses its module's own visibility rule, so search never shows what the page itself would hide."""
import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notices.views import NoticeViewSet
from apps.permissions.permissions import IsEmployee
from apps.pm.access import visible_projects
from apps.pm.models import Document, Note, Task

from .views import STAFF_ROLES

PER_KIND = 5
TASK_KEY = re.compile(r'^([a-z0-9]+)-(\d+)$', re.I)


def _all_terms(terms, *fields):
    """Every term must appear in at least one of `fields`."""
    q = Q()
    for term in terms:
        any_field = Q()
        for f in fields:
            any_field |= Q(**{f'{f}__icontains': term})
        q &= any_field
    return q


def _hit(kind, label, sub, to):
    return {'kind': kind, 'label': label, 'sub': sub or '', 'to': to}


class SearchView(APIView):
    permission_classes = [IsEmployee]

    @extend_schema(tags=['Dashboard'], summary='Search across the workspace',
                   parameters=[OpenApiParameter('q', str, description='At least 2 characters')],
                   responses=inline_serializer('SearchHit', {
                       'kind': serializers.ChoiceField(choices=['person', 'project', 'task', 'note', 'document', 'notice']),
                       'label': serializers.CharField(), 'sub': serializers.CharField(), 'to': serializers.CharField(),
                   }, many=True))
    def get(self, request):
        text = request.query_params.get('q', '').strip()[:80]
        terms = text.split()
        if len(text) < 2:
            return Response([])
        user, hits = request.user, []
        projects = visible_projects(user).filter(archived=False)

        people = (get_user_model().objects.filter(is_active=True, role__in=STAFF_ROLES)
                  .filter(_all_terms(terms, 'first_name', 'last_name', 'email', 'profile__designation'))
                  .select_related('profile').order_by('first_name', 'last_name')[:PER_KIND])
        hits += [_hit('person', p.full_name, getattr(getattr(p, 'profile', None), 'designation', ''),
                      f'/app/people/{p.pk}') for p in people]

        hits += [_hit('project', p.name, p.key.upper(), f'/app/projects/{p.pk}')
                 for p in projects.filter(_all_terms(terms, 'name', 'key', 'description')).order_by('name')[:PER_KIND]]

        tasks = Task.objects.filter(column__board__project__in=projects).select_related('column__board__project')
        key = TASK_KEY.match(text)  # "WALK-12" finds that task directly
        tasks = (tasks.filter(pk=key.group(2), column__board__project__key__iexact=key.group(1)) if key
                 else tasks.filter(_all_terms(terms, 'title')))
        for t in tasks.order_by('-updated_at')[:PER_KIND]:
            project = t.column.board.project
            hits.append(_hit('task', t.title, f'{project.key.upper()}-{t.pk} · {project.name}',
                             f'/app/projects/{project.pk}?tab=Board'))

        for kind, model, tab in (('note', Note, 'Notes'), ('document', Document, 'Docs')):
            rows = (model.objects.filter(project__in=projects, classification__lte=user.clearance)
                    .filter(_all_terms(terms, 'title')).select_related('project').order_by('-id')[:PER_KIND])
            hits += [_hit(kind, r.title, r.project.name, f'/app/projects/{r.project_id}?tab={tab}') for r in rows]

        notices = NoticeViewSet(request=request, action='list', format_kwarg=None).get_queryset()
        hits += [_hit('notice', n.title, 'Notice board', '/app/notices')
                 for n in notices.filter(_all_terms(terms, 'title')).order_by('-publish_at')[:PER_KIND]]
        return Response(hits)
