import datetime

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leave.models import LeaveRequest
from apps.org.models import EmployeeProfile, Organization
from apps.permissions.permissions import IsEmployee, IsHRAdmin
from .models import CalendarEvent, Holiday
from .serializers import (
    CalendarEventSerializer, HolidayBulkItemSerializer, HolidaySerializer, can_edit_event, user_mini,
)

TAG = ['Calendar & holidays']
MAX_RANGE_DAYS = 100

RANGE_PARAMS = [
    OpenApiParameter('start', OpenApiTypes.DATE, required=True, description='YYYY-MM-DD (inclusive)'),
    OpenApiParameter('end', OpenApiTypes.DATE, required=True, description=f'YYYY-MM-DD (inclusive, ≤ {MAX_RANGE_DAYS} days after start)'),
]


def parse_range(params):
    """Required, bounded ?start=&end= date range. Raises a 400 with a clear message."""
    out = {}
    for key in ('start', 'end'):
        raw = params.get(key)
        if not raw:
            raise ValidationError({key: f'"{key}" is required (YYYY-MM-DD).'})
        try:
            out[key] = datetime.date.fromisoformat(raw)
        except ValueError:
            raise ValidationError({key: f'"{raw}" is not a valid date (YYYY-MM-DD).'})
    start, end = out['start'], out['end']
    if end < start:
        raise ValidationError({'end': 'end must be on or after start.'})
    if (end - start).days > MAX_RANGE_DAYS:
        raise ValidationError({'end': f'Range too large: at most {MAX_RANGE_DAYS} days between start and end.'})
    return start, end


def day_bounds(start, end):
    """Aware datetimes covering local dates [start, end]."""
    tz = timezone.get_current_timezone()
    return (
        datetime.datetime.combine(start, datetime.time.min, tz),
        datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min, tz),
    )


def department_id(user):
    profile = getattr(user, 'profile', None)  # guests / admins may have no profile
    return profile.department_id if profile else None


def visible_events(user):
    qs = CalendarEvent.objects.select_related('department', 'created_by').prefetch_related('attendees')
    if user.has_role('hr_admin'):
        return qs
    A = CalendarEvent.Audience
    q = (
        Q(audience=A.ORGANIZATION)
        | Q(audience=A.DEPARTMENT, department__manager=user)
        | Q(created_by=user)
        | Q(attendees=user)
    )
    dept = department_id(user)
    if dept:
        q |= Q(audience=A.DEPARTMENT, department_id=dept)
    return qs.filter(q).distinct()


def visible_leaves(user):
    qs = LeaveRequest.objects.filter(status=LeaveRequest.Status.APPROVED).select_related(
        'user', 'leave_type'
    )
    if user.has_role('hr_admin'):
        return qs
    q = Q(user=user) | Q(user__profile__department__manager=user)
    dept = department_id(user)
    if dept:
        q |= Q(user__profile__department_id=dept)
    return qs.filter(q)


class IsCreatorOrHRForWrites(BasePermission):
    message = 'Only the creator or HR/admin can change this event.'

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or can_edit_event(request.user, obj)


class BulkHolidayResultSerializer(serializers.Serializer):
    created = HolidaySerializer(many=True)
    skipped = serializers.ListField(child=serializers.DictField())


@extend_schema_view(
    list=extend_schema(tags=TAG, parameters=[OpenApiParameter('year', OpenApiTypes.INT, description='Defaults to the current year')]),
    retrieve=extend_schema(tags=TAG), create=extend_schema(tags=TAG), update=extend_schema(tags=TAG),
    partial_update=extend_schema(tags=TAG), destroy=extend_schema(tags=TAG),
)
class HolidayViewSet(viewsets.ModelViewSet):
    serializer_class = HolidaySerializer
    queryset = Holiday.objects.all()

    def get_permissions(self):
        return [IsEmployee()] if self.action in ('list', 'retrieve') else [IsHRAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action != 'list':
            return qs
        raw = self.request.query_params.get('year') or timezone.localdate().year
        try:
            year = int(raw)
            if not 1900 <= year <= 2200:
                raise ValueError
        except ValueError:
            raise ValidationError({'year': f'"{raw}" is not a valid year.'})
        return qs.filter(date__year=year)

    @extend_schema(tags=TAG, request=HolidayBulkItemSerializer(many=True), responses={201: BulkHolidayResultSerializer})
    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Create many holidays at once (e.g. a year's Nepali list). Existing dates are skipped and reported."""
        rows = request.data.get('holidays') if isinstance(request.data, dict) else request.data
        if not isinstance(rows, list) or not rows:
            raise ValidationError({'detail': 'Send a non-empty JSON list of {name, date, description?, is_optional?}.'})
        if len(rows) > 366:
            raise ValidationError({'detail': 'At most 366 holidays per request.'})
        ser = HolidayBulkItemSerializer(data=rows, many=True)
        ser.is_valid(raise_exception=True)

        existing = set(Holiday.objects.filter(
            date__in=[r['date'] for r in ser.validated_data]
        ).values_list('date', flat=True))
        to_create, skipped = [], []
        for row in ser.validated_data:
            if row['date'] in existing:
                skipped.append({'date': row['date'].isoformat(), 'name': row['name'],
                                'reason': 'A holiday already exists on this date.'})
                continue
            existing.add(row['date'])  # also dedupes repeats inside the payload
            to_create.append(Holiday(**row))
        created = Holiday.objects.bulk_create(to_create)
        from apps.audit.services import record_created
        for holiday in created:
            record_created(holiday)
        return Response(
            {'created': HolidaySerializer(created, many=True).data, 'skipped': skipped},
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(tags=TAG, parameters=RANGE_PARAMS),
    retrieve=extend_schema(tags=TAG), create=extend_schema(tags=TAG), update=extend_schema(tags=TAG),
    partial_update=extend_schema(tags=TAG), destroy=extend_schema(tags=TAG),
)
class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    queryset = CalendarEvent.objects.none()  # schema hint only; real scoping in get_queryset
    permission_classes = [IsEmployee, IsCreatorOrHRForWrites]

    def get_queryset(self):
        qs = visible_events(self.request.user)
        if self.action == 'list':
            lo, hi = day_bounds(*parse_range(self.request.query_params))
            qs = qs.filter(start__lt=hi, end__gte=lo)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


def _anniversary(d, year):
    try:
        return d.replace(year=year)
    except ValueError:  # Feb 29 in a non-leap year
        return datetime.date(year, 2, 28)


class FeedView(APIView):
    permission_classes = [IsEmployee]

    @extend_schema(tags=TAG, parameters=RANGE_PARAMS, responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        """Unified calendar: holidays, visible events, approved leaves, birthdays, work anniversaries."""
        start, end = parse_range(request.query_params)
        return Response({
            'start': start.isoformat(), 'end': end.isoformat(),
            'weekend_days': Organization.load().weekend_days,
            'items': feed_items(request.user, start, end),
        })


def feed_items(user, start, end):
    """Sorted feed items visible to `user` for local dates [start, end]. Shared with the dashboard."""
    items = []

    for h in Holiday.objects.filter(date__range=(start, end)):
        items.append(item('holiday', h.pk, h.name, h.date, h.date, True, 'rust',
                          {'is_optional': h.is_optional, 'description': h.description}))

    lo, hi = day_bounds(start, end)
    dt = serializers.DateTimeField()
    for e in visible_events(user).filter(start__lt=hi, end__gte=lo):
        items.append(item('event', e.pk, e.title, dt.to_representation(e.start), dt.to_representation(e.end),
                          e.all_day, 'sky', {
                              'audience': e.audience, 'location': e.location, 'description': e.description,
                              'department': {'id': e.department_id, 'name': e.department.name} if e.department else None,
                              'created_by': user_mini(e.created_by), 'can_edit': can_edit_event(user, e),
                          }))

    from apps.pm.models import Meeting
    meetings = Meeting.objects.filter(Q(attendees=user) | Q(created_by=user), start__lt=hi, end__gte=lo).exclude(
        status='cancelled').select_related('project').distinct()
    for m in meetings:
        items.append(item('meeting', m.pk, f'{m.project.key} · {m.title}', dt.to_representation(m.start),
                          dt.to_representation(m.end), False, 'flag', {
                              'project': {'id': m.project_id, 'name': m.project.name}, 'location': m.location,
                              'kind': m.kind,
                          }))

    for lv in visible_leaves(user).filter(start_date__lte=end, end_date__gte=start):
        t = lv.leave_type
        items.append(item('leave', lv.pk, f'{lv.user.full_name} · {t.name}', lv.start_date, lv.end_date, True,
                          'moss', {
                              'user': user_mini(lv.user), 'half_day': lv.half_day, 'days': str(lv.days),
                              'leave_type': {'id': t.pk, 'name': t.name, 'code': t.code, 'color': t.color},
                          }))

    # ponytail: scans every active profile in Python; fine for a small org, move to a month/day DB filter past ~5k staff
    profiles = EmployeeProfile.objects.select_related('user').filter(
        user__is_active=True
    ).exclude(user__role='guest').filter(Q(date_of_birth__isnull=False) | Q(join_date__isnull=False))
    for p in profiles:
        who = user_mini(p.user)
        for year in range(start.year, end.year + 1):
            if p.date_of_birth:
                occ = _anniversary(p.date_of_birth, year)
                if start <= occ <= end:  # only month/day leave the server, never the birth year
                    items.append(item('birthday', p.user_id, f'{who["full_name"]}’s birthday', occ, occ, True,
                                      'contour', {'user': who, 'month': occ.month, 'day': occ.day}))
            if p.join_date:
                occ = _anniversary(p.join_date, year)
                years = year - p.join_date.year
                if years >= 1 and start <= occ <= end:
                    items.append(item('work_anniversary', p.user_id,
                                      f'{who["full_name"]} · {years} yr{"s" if years > 1 else ""} at Thimi Tech',
                                      occ, occ, True, 'river',
                                      {'user': who, 'years': years, 'month': occ.month, 'day': occ.day}))

    items.sort(key=lambda i: (i['start'][:10], KIND_ORDER[i['kind']], i['start'], i['title']))
    return items


KIND_ORDER = {'holiday': 0, 'event': 1, 'meeting': 1, 'leave': 2, 'birthday': 3, 'work_anniversary': 4}


def item(kind, pk, title, start, end, all_day, color, meta):
    iso = lambda v: v if isinstance(v, str) else v.isoformat()  # noqa: E731
    return {'kind': kind, 'id': pk, 'title': title, 'start': iso(start), 'end': iso(end),
            'all_day': all_day, 'color': color, 'meta': meta}
