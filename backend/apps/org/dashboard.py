"""GET /api/dashboard/ — one round trip for the /app home page. Every section reuses its module's own logic."""
import datetime

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance import services as attendance
from apps.attendance.views import today_payload
from apps.calendar_app.views import feed_items
from apps.leave import services as leave
from apps.leave.models import LeaveRequest
from apps.leave.serializers import BalanceSerializer, LeaveRequestSerializer
from apps.leave.views import REQUEST_SELECT
from apps.notices.serializers import NoticeSerializer, user_brief
from apps.notices.views import NoticeViewSet
from apps.permissions.permissions import IsEmployee
from apps.pm.access import my_tasks_summary, open_tasks_for

from .models import Department
from .views import STAFF_ROLES

UPCOMING_DAYS = 14
WEEK_DAYS = 7
STATUSES = ('present', 'late', 'absent', 'on_leave', 'not_checked_in')


def _dept(u):
    profile = getattr(u, 'profile', None)
    return profile.department if profile else None


def _counts(rows):
    out = dict.fromkeys(STATUSES, 0)
    for _, st, _ in rows:
        if st in out:  # weekend/holiday statuses carry no signal for a pulse
            out[st] += 1
    out['total'] = len(rows)
    return out


class DashboardView(APIView):
    permission_classes = [IsEmployee]

    @extend_schema(tags=['Dashboard'], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user, today = request.user, timezone.localdate()
        ctx = {'request': request}
        pending = LeaveRequest.Status.PENDING

        approvals = (LeaveRequest.objects.select_related(*REQUEST_SELECT)
                     .filter(leave.decidable_q(user), status=pending).order_by('start_date'))
        notices = NoticeViewSet(request=request, action='list', format_kwarg=None).get_queryset()

        upcoming = feed_items(user, today, today + datetime.timedelta(days=UPCOMING_DAYS - 1))
        week_end = (today + datetime.timedelta(days=WEEK_DAYS - 1)).isoformat()

        data = {
            'today': today_payload(user, ctx),
            'leave': {
                'year': today.year,
                'balances': BalanceSerializer(leave.balances(user, today.year), many=True).data,
                'my_pending': LeaveRequest.objects.filter(user=user, status=pending).count(),
            },
            'approvals': {
                'count': approvals.count(),
                'items': LeaveRequestSerializer(approvals[:5], many=True, context=ctx).data,
            },
            'notices': {
                'unread': notices.filter(is_read=False).count(),
                'items': NoticeSerializer(notices.order_by('-publish_at')[:5], many=True, context=ctx).data,
            },
            'my_tasks': my_tasks_summary(user),
            'upcoming': {'days': UPCOMING_DAYS, 'items': upcoming},
            'celebrations': [i for i in upcoming
                             if i['kind'] in ('birthday', 'work_anniversary') and i['start'] <= week_end],
            'team': None,
            'org': None,
            'on_leave_today': None,  # manager: their team; hr_admin+: everyone
        }

        if user.has_role('manager'):
            # hr_admin+: everyone in one pass; the team is the subset whose department this user manages
            scoped = list(attendance.scoped_staff(user))
            kind, _, rows = attendance.day_statuses(scoped, today)
            team = [r for r in rows if (d := _dept(r[0])) and d.manager_id == user.id]
            data['team'] = {
                'day_kind': kind,
                'counts': _counts(team),
                'pending_leave': LeaveRequest.objects.filter(leave.team_q(user), status=pending).count(),
            }
            away = rows if user.has_role('hr_admin') else team
            data['on_leave_today'] = [user_brief(u, request) for u, st, _ in away if st == 'on_leave']
            if user.has_role('hr_admin'):
                data['org'] = {
                    'day_kind': kind,
                    'attendance': _counts(rows),
                    'pending_leave': LeaveRequest.objects.filter(status=pending).count(),
                    'headcount': list(Department.objects.annotate(count=Count(
                        'members', filter=Q(members__user__is_active=True, members__user__role__in=STAFF_ROLES),
                    )).order_by('-count', 'name').values('id', 'name', 'count')),
                    'unassigned': sum(1 for u in scoped if not _dept(u)),
                    'total_staff': len(scoped),
                }
        return Response(data)


def unread_notices_count(request):
    return NoticeViewSet(request=request, action='list', format_kwarg=None).get_queryset().filter(is_read=False).count()


class NavCountsView(APIView):
    """GET /api/nav-counts/ -- sidebar/top-bar badges in one cheap call (the layout polls it)."""
    permission_classes = [IsEmployee]

    @extend_schema(tags=['Dashboard'], summary='Badge counts for the app shell', responses=inline_serializer('NavCounts', {
        'leave_approvals': serializers.IntegerField(help_text='Pending leave requests I may decide'),
        'unread_notices': serializers.IntegerField(),
        'overdue_tasks': serializers.IntegerField(help_text='My open tasks past their due date'),
        'unread_notifications': serializers.IntegerField(),
        'attendance_corrections': serializers.IntegerField(help_text='Pending attendance corrections I may decide'),
    }))
    def get(self, request):
        from apps.attendance.models import AttendanceCorrection
        from apps.notifications.models import Notification
        user = request.user
        return Response({
            'leave_approvals': LeaveRequest.objects.filter(
                leave.decidable_q(user), status=LeaveRequest.Status.PENDING).count(),
            'unread_notices': unread_notices_count(request),
            'overdue_tasks': open_tasks_for(user).filter(due_date__lt=timezone.localdate()).count(),
            'unread_notifications': Notification.objects.filter(recipient=user, read_at__isnull=True).count(),
            'attendance_corrections': AttendanceCorrection.objects.filter(
                leave.decidable_q(user), status=AttendanceCorrection.Status.PENDING).count(),
        })
