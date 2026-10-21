import logging
import os

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.permissions.permissions import IsEmployee, IsManager
from apps.notifications.services import push
from apps.users.tasks import send_email

from .models import Notice, NoticeRead
from .serializers import (
    AUDIENCE_READS, STAFF_ROLES, NoticeSerializer, ReadersResponseSerializer, notice_status, user_brief,
)

log = logging.getLogger(__name__)
User = get_user_model()

LIST_CAP = 200  # ponytail: hard cap instead of pagination; add pagination if boards outgrow it
TRUE = ('1', 'true', 'yes')
FALSE = ('0', 'false', 'no')

TAG = ['Notice board']


def _user_department_id(user):
    profile = getattr(user, 'profile', None)
    return profile.department_id if profile else None


def audience_users(notice):
    """Active staff (employee+) the notice is addressed to."""
    qs = User.objects.filter(is_active=True, role__in=STAFF_ROLES)
    if notice.audience == Notice.Audience.DEPARTMENT:
        qs = qs.filter(profile__department_id=notice.department_id)
    return qs.select_related('profile__department').order_by('first_name', 'email')


def email_urgent(notice):
    """Email an urgent notice to its audience exactly once (claimed via emailed_at, so the beat
    task and perform_create can't both send). Returns True when this call sent it."""
    if not Notice.objects.filter(pk=notice.pk, emailed_at__isnull=True).update(emailed_at=timezone.now()):
        return False
    push(audience_users(notice), 'notice', f'Urgent: {notice.title}', '', '/app/notices', exclude=notice.author)
    recipients = list(audience_users(notice).exclude(pk=notice.author_id).values_list('email', flat=True))
    if recipients:
        try:
            send_email.delay(f'[Urgent] {notice.title}', notice.body, recipients)
        except Exception:  # broker down must not turn a saved notice into a 500
            log.exception('Could not queue urgent notice email for notice %s', notice.pk)
    return True


list_params = [
    OpenApiParameter('manage', OpenApiTypes.BOOL, description='manager+: include scheduled/expired notices you can manage (hr_admin+: all)'),
    OpenApiParameter('category', OpenApiTypes.STR, enum=[c for c, _ in Notice.Category.choices]),
    OpenApiParameter('unread', OpenApiTypes.BOOL, description='1 = only notices I have not read'),
    OpenApiParameter('pinned', OpenApiTypes.BOOL),
    OpenApiParameter('search', OpenApiTypes.STR, description='Matches title or body'),
    OpenApiParameter('status', OpenApiTypes.STR, enum=['published', 'scheduled', 'expired'], description='Only meaningful with manage=1'),
]


@extend_schema_view(
    list=extend_schema(tags=TAG, parameters=list_params),
    retrieve=extend_schema(tags=TAG),
    create=extend_schema(tags=TAG),
    update=extend_schema(tags=TAG),
    partial_update=extend_schema(tags=TAG),
    destroy=extend_schema(tags=TAG),
)
class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    queryset = Notice.objects.none()  # schema hint only; real scoping in get_queryset

    def get_permissions(self):
        return [IsManager()] if self.action == 'create' else [IsEmployee()]

    def _flag(self, name):
        return self.request.query_params.get(name, '').lower() in TRUE

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()

        dept_id = _user_department_id(user)
        visible = Q(audience=Notice.Audience.ALL)
        if dept_id:
            visible |= Q(audience=Notice.Audience.DEPARTMENT, department_id=dept_id)
        live = Q(publish_at__lte=now) & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        if user.has_role('hr_admin'):
            manageable = Q(pk__isnull=False)  # everything (an empty Q() would vanish in an OR)
        elif user.has_role('manager'):
            manageable = Q(author=user) | Q(department__manager=user)
        else:
            manageable = Q(author=user)

        if self.action == 'list' and self._flag('manage') and user.has_role('manager'):
            scope = manageable
        elif self.action in ('list', 'read', 'read_all', 'unread_count'):
            # reads only count for notices addressed to you and live now
            scope = visible & live
        else:  # detail routes: anything you can see now, or manage
            scope = (visible & live) | manageable

        return (
            Notice.objects.filter(scope)
            .select_related('author__profile', 'department')
            .annotate(
                is_read=Exists(NoticeRead.objects.filter(notice=OuterRef('pk'), user=user)),
                read_count=Coalesce(Subquery(
                    NoticeRead.objects.filter(AUDIENCE_READS, notice=OuterRef('pk'))
                    .order_by().values('notice').annotate(c=Count('pk')).values('c'),
                    output_field=IntegerField(),
                ), 0),
            )
        )

    def filter_queryset(self, qs):
        if self.action != 'list':
            return qs
        p = self.request.query_params
        now = timezone.now()
        if p.get('category'):
            qs = qs.filter(category=p['category'])
        if self._flag('unread'):
            qs = qs.filter(is_read=False)
        pinned = p.get('pinned', '').lower()
        if pinned in TRUE:
            qs = qs.filter(pinned=True)
        elif pinned in FALSE and pinned:
            qs = qs.filter(pinned=False)
        if p.get('search'):
            term = p['search'].strip()
            qs = qs.filter(Q(title__icontains=term) | Q(body__icontains=term))
        st = p.get('status')
        if st == 'scheduled':
            qs = qs.filter(publish_at__gt=now)
        elif st == 'expired':
            qs = qs.filter(expires_at__lte=now)
        elif st == 'published':
            qs = qs.filter(publish_at__lte=now).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())[:LIST_CAP]
        return Response(self.get_serializer(qs, many=True).data)

    def get_object(self):
        notice = super().get_object()
        # checked before serializer validation so non-authors get 403, not 400
        if self.action in ('update', 'partial_update', 'destroy', 'readers'):
            user = self.request.user
            if not (user.has_role('hr_admin') or notice.author_id == user.id):
                raise PermissionDenied('Only the author or an HR admin can do this.')
        return notice

    def perform_create(self, serializer):
        notice = serializer.save(author=self.request.user)
        # the author has obviously read their own notice; keeps it out of their unread badge
        NoticeRead.objects.create(notice=notice, user=self.request.user)
        live = notice_status(notice) == 'published'
        if notice.category == Notice.Category.URGENT and live:
            email_urgent(notice)  # also pushes the in-app notification
        elif notice.audience == Notice.Audience.DEPARTMENT and live:
            # ponytail: only notices live at creation; scheduled department notices just appear on the board
            push(audience_users(notice), 'notice', f'New notice for {notice.department.name}: {notice.title}',
                 '', '/app/notices', exclude=notice.author)
        # scheduled urgent notices (and notices edited to urgent) are mailed by the
        # notices.tasks.email_due_urgent_notices beat task once live.

    def perform_destroy(self, instance):
        if instance.attachment:
            instance.attachment.delete(save=False)
        instance.delete()

    @extend_schema(
        tags=TAG, request=None,
        responses=inline_serializer('NoticeReadResult', {
            'id': serializers.IntegerField(), 'is_read': serializers.BooleanField(),
            'read_at': serializers.DateTimeField(),
        }),
    )
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notice = self.get_object()
        rec, _ = NoticeRead.objects.get_or_create(notice=notice, user=request.user)
        return Response({'id': notice.id, 'is_read': True, 'read_at': timezone.localtime(rec.read_at)})

    @extend_schema(
        tags=TAG, request=None,
        responses=inline_serializer('NoticeReadAllResult', {'marked': serializers.IntegerField()}),
    )
    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        unread = self.get_queryset().filter(is_read=False).values_list('pk', flat=True)
        created = NoticeRead.objects.bulk_create(
            [NoticeRead(notice_id=pk, user=request.user) for pk in unread], ignore_conflicts=True,
        )
        return Response({'marked': len(created)})

    @extend_schema(
        tags=TAG,
        responses=inline_serializer('NoticeUnreadCount', {'unread': serializers.IntegerField()}),
    )
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread': self.get_queryset().filter(is_read=False).count()})

    @extend_schema(tags=TAG, responses=ReadersResponseSerializer)
    @action(detail=True, methods=['get'])
    def readers(self, request, pk=None):
        notice = self.get_object()

        def row(user, read_at):
            p = getattr(user, 'profile', None)
            dept = p.department if p else None
            return {
                **user_brief(user, request),
                'department': {'id': dept.id, 'name': dept.name} if dept else None,
                'read_at': timezone.localtime(read_at) if read_at else None,
            }

        # only audience members count; a reader who left the department drops out of reach
        reads = notice.reads.filter(AUDIENCE_READS).select_related('user__profile__department').order_by('-read_at')
        read_rows = [row(r.user, r.read_at) for r in reads]
        read_ids = {r['id'] for r in read_rows}
        audience = list(audience_users(notice))
        unread_rows = [row(u, None) for u in audience if u.id not in read_ids]
        return Response({
            'audience_count': len(audience),
            'read_count': len(read_rows),
            'read': read_rows,
            'unread': unread_rows,
        }, status=status.HTTP_200_OK)

    @extend_schema(tags=TAG, responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'])
    def attachment(self, request, pk=None):
        notice = self.get_object()  # same scoping as retrieve: visible & live, or manageable
        if not notice.attachment:
            raise Http404
        try:
            fh = notice.attachment.open('rb')
        except FileNotFoundError:
            raise Http404
        return FileResponse(fh, as_attachment=True, filename=os.path.basename(notice.attachment.name))
