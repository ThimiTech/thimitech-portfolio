import mimetypes
import os
from datetime import timezone as dt_timezone

from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.notifications.services import push
from apps.permissions.permissions import IsEmployee, IsManager
from .access import visible_projects, can_manage, require_manager
from .models import Project, Board, Column, Task, Comment, Milestone, ProjectLink, Sprint, Document, Note, Meeting, Whiteboard
from .serializers import (ProjectSerializer, BoardSerializer, ColumnSerializer, TaskSerializer, CommentSerializer, MilestoneSerializer,
                          LinkSerializer, ProjectSummarySerializer, SprintSerializer, DocumentSerializer, NoteSerializer,
                          MeetingSerializer, WhiteboardSerializer, name_of)

INLINE_TYPES = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
TEXT_TYPES = {'txt', 'md', 'csv'}
IMAGE_TYPES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
PARSERS = [JSONParser, MultiPartParser, FormParser]


def serve_document(doc, download=False):
    """Stream a stored document. Previewable types go inline in a sandbox; text is always text/plain (never HTML)."""
    ext = doc.extension
    try:
        fh = doc.file.open('rb')
    except FileNotFoundError:
        raise Http404
    inline = not download and (ext in INLINE_TYPES or ext in TEXT_TYPES)
    resp = FileResponse(fh, as_attachment=not inline, filename=os.path.basename(doc.file.name))
    if ext in TEXT_TYPES:
        resp['Content-Type'] = 'text/plain; charset=utf-8'
    elif ext in INLINE_TYPES:
        resp['Content-Type'] = mimetypes.types_map.get(f'.{ext}', 'application/octet-stream')
    resp['Content-Security-Policy'] = 'sandbox'
    resp['X-Content-Type-Options'] = 'nosniff'
    return resp


@extend_schema(tags=['Project management'])
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    parser_classes = PARSERS

    def get_permissions(self):
        return [IsManager()] if self.action == 'create' else [IsEmployee()]

    def get_queryset(self):
        return visible_projects(self.request.user).select_related('lead').prefetch_related('members', 'boards__columns').annotate(
            total_tasks=Count('boards__columns__tasks', distinct=True),
            done_tasks=Count('boards__columns__tasks', filter=Q(boards__columns__status='done'), distinct=True),
        )

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.save(lead=self.request.user)
        project.members.add(self.request.user)
        create_board(project, 'Main board')

    @transaction.atomic
    def perform_update(self, serializer):
        require_manager(self.request.user, serializer.instance)
        going_public = serializer.validated_data.get('visibility') == 'public' and serializer.instance.visibility != 'public'
        serializer.save(**({'published_at': timezone.now()} if going_public else {}))

    def perform_destroy(self, instance):
        require_manager(self.request.user, instance)
        raise ValidationError('Archive projects to preserve their task history.')


def create_board(project, name):
    board = Board.objects.create(project=project, name=name)
    for index, (status, label) in enumerate(Column.Status.choices):
        Column.objects.create(board=board, name=label, status=status, position=index)
    return board


class ScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsEmployee]
    project_path = 'project'

    def get_queryset(self):
        queryset = self.queryset.filter(**{f'{self.project_path}__in': visible_projects(self.request.user)})
        project = self.request.query_params.get('project')
        if project:
            if not project.isdigit():
                raise ValidationError({'project': 'Use a project id.'})
            queryset = queryset.filter(**{f'{self.project_path}_id': project})
        return queryset

    def project_of(self, instance):
        for attr in self.project_path.split('__'):
            instance = getattr(instance, attr)
        return instance

    def perform_destroy(self, instance):
        require_manager(self.request.user, self.project_of(instance))
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('Move the tasks out before deleting this column or board.')


@extend_schema(tags=['Project management'])
class BoardViewSet(ScopedViewSet):
    queryset = Board.objects.select_related('project').prefetch_related('columns')
    serializer_class = BoardSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        serializer.instance = create_board(project, serializer.validated_data['name'])


@extend_schema(tags=['Project management'])
class ColumnViewSet(ScopedViewSet):
    queryset = Column.objects.select_related('board__project')
    serializer_class = ColumnSerializer
    project_path = 'board__project'


@extend_schema(tags=['Project management'])
class TaskViewSet(ScopedViewSet):
    queryset = Task.objects.select_related('column__board__project', 'assignee', 'milestone')
    serializer_class = TaskSerializer
    project_path = 'column__board__project'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('mine') == '1':
            qs = qs.filter(assignee=self.request.user)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data['column'].board.project
        require_manager(self.request.user, project)
        notify_assignee(serializer.save(created_by=self.request.user), None, self.request.user)

    def perform_update(self, serializer):
        before = serializer.instance.assignee_id
        notify_assignee(serializer.save(), before, self.request.user)

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_manage(request.user, self.project_of(task)):
            if task.assignee_id != request.user.pk or set(request.data) - {'column', 'position'}:
                raise PermissionDenied('Employees can move only their assigned tasks. Ask the project lead to edit task details.')
        return super().update(request, *args, **kwargs)


def notify_assignee(task, previous_assignee_id, actor):
    """In-app notice to a task's new assignee (not when you assign yourself)."""
    if task.assignee_id and task.assignee_id != previous_assignee_id:
        project = task.column.board.project
        push([task.assignee], 'task_assigned', f'{actor.full_name} assigned you {project.key}-{task.pk}',
             task.title, f'/app/projects/{project.pk}', exclude=actor)


@extend_schema(tags=['Project management'])
class MilestoneViewSet(ScopedViewSet):
    queryset = Milestone.objects.select_related('project')
    serializer_class = MilestoneSerializer


@extend_schema(tags=['Project management'])
class LinkViewSet(ScopedViewSet):
    queryset = ProjectLink.objects.select_related('project')
    serializer_class = LinkSerializer


@extend_schema(tags=['Project management'])
class SprintViewSet(ScopedViewSet):
    queryset = Sprint.objects.select_related('project')
    serializer_class = SprintSerializer

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def start(self, request, pk=None):
        sprint = self.get_object()
        require_manager(request.user, sprint.project)
        if sprint.status != 'planned':
            raise ValidationError('Only a planned sprint can be started.')
        if Sprint.objects.filter(project=sprint.project, status='active').exists():
            raise ValidationError('Complete the active sprint before starting another.')
        sprint.status = 'active'
        sprint.save(update_fields=['status'])
        return Response(SprintSerializer(sprint, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def complete(self, request, pk=None):
        """Close the sprint; unfinished tasks move to `carry_to` (a planned sprint id) or back to the backlog."""
        sprint = self.get_object()
        require_manager(request.user, sprint.project)
        if sprint.status != 'active':
            raise ValidationError('Only the active sprint can be completed.')
        target = request.data.get('carry_to')
        if target:
            target = Sprint.objects.filter(pk=target, project=sprint.project, status='planned').first()
            if not target:
                raise ValidationError({'carry_to': 'Choose a planned sprint in this project.'})
        carried = Task.objects.filter(sprint=sprint).exclude(column__status='done').update(sprint=target)
        sprint.status, sprint.completed_at = 'completed', timezone.now()
        sprint.save(update_fields=['status', 'completed_at'])
        return Response({**SprintSerializer(sprint, context={'request': request}).data, 'carried': carried})


class MemberScopedViewSet(ScopedViewSet):
    """Members create and edit; only the owner or a project manager deletes."""
    owner_field = 'created_by'

    def perform_destroy(self, instance):
        if getattr(instance, f'{self.owner_field}_id') != self.request.user.pk:
            require_manager(self.request.user, instance.project)
        instance.delete()


@extend_schema(tags=['Project management'])
class DocumentViewSet(MemberScopedViewSet):
    queryset = Document.objects.select_related('project', 'uploaded_by')
    serializer_class = DocumentSerializer
    parser_classes = PARSERS
    owner_field = 'uploaded_by'

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user, size=serializer.validated_data['file'].size)

    def perform_update(self, serializer):
        if serializer.instance.uploaded_by_id != self.request.user.pk:
            require_manager(self.request.user, serializer.instance.project)
        serializer.save()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        instance.file.delete(save=False)

    @action(detail=True, methods=['get'], url_name='file')
    def file(self, request, pk=None):
        return serve_document(self.get_object(), download=request.query_params.get('download') == '1')


@extend_schema(tags=['Project management'])
class NoteViewSet(MemberScopedViewSet):
    queryset = Note.objects.select_related('project', 'author', 'updated_by')
    serializer_class = NoteSerializer
    owner_field = 'author'

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


@extend_schema(tags=['Project management'])
class MeetingViewSet(MemberScopedViewSet):
    queryset = Meeting.objects.select_related('project', 'created_by').prefetch_related('attendees')
    serializer_class = MeetingSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        meeting = serializer.save(created_by=self.request.user)
        notify_attendees(meeting, meeting.attendees.all(), self.request.user)

    @transaction.atomic
    def perform_update(self, serializer):
        before = set(serializer.instance.attendees.values_list('pk', flat=True))
        meeting = serializer.save()
        notify_attendees(meeting, meeting.attendees.exclude(pk__in=before), self.request.user)

    @action(detail=True, methods=['get'])
    def ics(self, request, pk=None):
        m = self.get_object()
        stamp = lambda dt: dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')  # noqa: E731
        esc = lambda s: s.replace('\\', '\\\\').replace(';', r'\;').replace(',', r'\,').replace('\n', r'\n')  # noqa: E731
        body = '\r\n'.join([
            'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Thimi Tech OS//PM//EN', 'BEGIN:VEVENT',
            f'UID:pm-meeting-{m.pk}@thimitech', f'DTSTAMP:{stamp(m.updated_at)}', f'DTSTART:{stamp(m.start)}',
            f'DTEND:{stamp(m.end)}', f'SUMMARY:{esc(f"{m.project.key} · {m.title}")}', f'LOCATION:{esc(m.location)}',
            f'DESCRIPTION:{esc(m.agenda)}', 'END:VEVENT', 'END:VCALENDAR', ''])
        resp = HttpResponse(body, content_type='text/calendar; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="meeting-{m.pk}.ics"'
        return resp


def notify_attendees(meeting, users, actor):
    when = timezone.localtime(meeting.start).strftime('%d %b %H:%M')
    push(users, 'meeting', f'{name_of(actor)} invited you: {meeting.title}', f'{meeting.project.name} · {when}',
         f'/app/projects/{meeting.project_id}?tab=Meetings', exclude=actor)


@extend_schema(tags=['Project management'])
class WhiteboardViewSet(MemberScopedViewSet):
    queryset = Whiteboard.objects.select_related('project', 'updated_by')
    serializer_class = WhiteboardSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        board = self.get_object()
        board = Whiteboard.objects.select_for_update().get(pk=board.pk)
        if 'data' in request.data and str(request.data.get('version')) != str(board.version):
            return Response({'detail': 'Someone else saved this whiteboard. Reload to see their changes.',
                             'version': board.version}, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(board, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user, version=board.version + 1)
        return Response(serializer.data)


@extend_schema(tags=['Public projects'])
class PublicProjectViewSet(viewsets.GenericViewSet):
    """Projects published as case studies. Only the sections the lead chose leave the building."""
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = 'slug'

    def get_queryset(self):
        return Project.objects.filter(visibility='public', archived=False).exclude(slug=None).order_by('-published_at', '-id')

    def card(self, p):
        request = self.request
        cover = request.build_absolute_uri(p.cover.url) if p.cover else None
        return {'slug': p.slug, 'name': p.name, 'key': p.key, 'tagline': p.tagline, 'cover': cover, 'tech': p.tech,
                'health': p.health, 'start_date': p.start_date, 'due_date': p.due_date, 'published_at': p.published_at}

    @extend_schema(responses=dict)
    def list(self, request):
        return Response([self.card(p) for p in self.get_queryset()])

    @extend_schema(responses=dict)
    def retrieve(self, request, slug=None):
        p = get_object_or_404(self.get_queryset(), slug=slug)
        sections = set(p.public_sections)
        data = {**self.card(p), 'sections': p.public_sections}
        if 'story' in sections:
            data['story'] = p.story
        if 'progress' in sections:
            tasks = Task.objects.filter(column__board__project=p)
            total, done = tasks.count(), tasks.filter(column__status='done').count()
            data['progress'] = {'total': total, 'done': done, 'percent': round(done / total * 100) if total else 0}
        if 'milestones' in sections:
            data['milestones'] = list(p.milestones.values('title', 'due_date', 'completed'))
        if 'team' in sections:
            people = {u.pk: u for u in p.members.select_related('profile')} | {p.lead_id: p.lead}
            data['team'] = [{'name': name_of(u), 'role': getattr(getattr(u, 'profile', None), 'designation', ''),
                             'lead': u.pk == p.lead_id} for u in people.values()]
        if 'links' in sections:
            data['links'] = list(p.links.filter(public=True).values('title', 'kind', 'url'))
        docs = p.documents.filter(public=True)
        file_url = lambda d: request.build_absolute_uri(f'/api/pm/public/{p.slug}/files/{d.pk}/')  # noqa: E731
        if 'gallery' in sections:
            data['gallery'] = [{'id': d.pk, 'title': d.title, 'description': d.description, 'url': file_url(d)}
                               for d in docs if d.extension in IMAGE_TYPES]
        if 'documents' in sections:
            data['documents'] = [{'id': d.pk, 'title': d.title, 'extension': d.extension, 'size': d.size, 'url': file_url(d)}
                                 for d in docs if d.extension not in IMAGE_TYPES]
        return Response(data)

    @extend_schema(responses={(200, 'application/octet-stream'): bytes})
    @action(detail=True, methods=['get'], url_path=r'files/(?P<doc>\d+)')
    def files(self, request, slug=None, doc=None):
        p = get_object_or_404(self.get_queryset(), slug=slug)
        d = get_object_or_404(p.documents.filter(public=True), pk=doc)
        section = 'gallery' if d.extension in IMAGE_TYPES else 'documents'
        if section not in p.public_sections:
            raise Http404
        return serve_document(d, download=request.query_params.get('download') == '1')


@extend_schema(tags=['Project management'])
class CommentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        qs = Comment.objects.filter(task__column__board__project__in=visible_projects(self.request.user)).select_related('author', 'task__column__board__project')
        task = self.request.query_params.get('task')
        if task:
            if not task.isdigit():
                raise ValidationError({'task': 'Use a task id.'})
            qs = qs.filter(task_id=task)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        if instance.author_id != self.request.user.pk:
            require_manager(self.request.user, instance.task.column.board.project)
        instance.delete()


@extend_schema(tags=['Project management'])
class SummaryView(APIView):
    permission_classes = [IsEmployee]

    @extend_schema(responses=ProjectSummarySerializer)
    def get(self, request):
        projects = visible_projects(request.user).filter(archived=False)
        tasks = Task.objects.filter(column__board__project__in=projects)
        counts = tasks.aggregate(tasks=Count('id'), done=Count('id', filter=Q(column__status='done')), active=Count('id', filter=Q(column__status='active')), overdue=Count('id', filter=Q(due_date__lt=timezone.localdate()) & ~Q(column__status='done')))
        return Response({'projects': projects.count(), **counts, 'assigned_to_me': tasks.filter(assignee=request.user).exclude(column__status='done').count()})
