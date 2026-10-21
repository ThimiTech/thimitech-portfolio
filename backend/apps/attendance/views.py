import csv
import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, renderers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.leave import services as leave_svc
from apps.notifications.services import push
from apps.org.models import Organization
from apps.permissions.permissions import IsEmployee, IsHRAdmin, IsManager

from . import services as svc
from .models import AttendanceCorrection, AttendanceRecord
from .serializers import (
    AttendanceRecordSerializer, CheckInSerializer, CheckOutSerializer, CorrectionDecisionSerializer,
    CorrectionRejectSerializer, CorrectionSerializer, StaffSerializer,
)

TAGS = ['Attendance']
MONTH = OpenApiParameter('month', OpenApiTypes.STR, description='YYYY-MM (default: current month)')
DEPT = OpenApiParameter('department', OpenApiTypes.INT, description='Department id filter')
CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(value):
    """Neutralise spreadsheet formula injection (names/emails are user-editable via /api/me/)."""
    s = str(value)
    return "'" + s if s[:1] in CSV_FORMULA_PREFIXES else s


CSV_CODES = {'present': 'P', 'late': 'L', 'absent': 'A', 'on_leave': 'LV', 'weekend': 'W', 'holiday': 'H',
             'not_checked_in': '-', None: ''}


class CSVRenderer(renderers.BaseRenderer):
    """Only lets ?format=csv pass content negotiation; the view builds the CSV body itself."""
    media_type = 'text/csv'
    format = 'csv'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Only reached for error responses (403/400) on a CSV request: emit the message as text.
        return str(data.get('detail', data) if isinstance(data, dict) else data).encode() if data else b''


def _policy(org):
    return {
        'work_start': org.work_start.strftime('%H:%M'),
        'work_end': org.work_end.strftime('%H:%M'),
        'late_grace_minutes': org.late_grace_minutes,
        'weekend_days': org.weekend_days,
    }


def today_payload(user, context):
    """GET /attendance/today/ body; also embedded in the dashboard."""
    org, today = Organization.load(), timezone.localdate()
    rec = AttendanceRecord.objects.filter(user=user, date=today).select_related('user').first()
    kind, holiday = svc.day_kind(today, org)
    leave = svc.leave_on(user, today)
    full_leave = bool(leave and not leave.half_day)
    return {
        'date': today,
        'server_time': timezone.localtime(),
        'record': AttendanceRecordSerializer(rec, context=context).data if rec else None,
        'policy': {**_policy(org), 'late_after': timezone.localtime(svc.late_after(org, today)).strftime('%H:%M')},
        'is_working_day': kind == 'working',
        'day_kind': kind,
        'holiday_name': holiday,
        'on_leave': full_leave,
        'leave': {
            'id': leave.id, 'leave_type': leave.leave_type.name, 'start_date': leave.start_date,
            'end_date': leave.end_date, 'half_day': leave.half_day,
        } if leave else None,
        'can_check_in': not full_leave and not (rec and (rec.check_in or rec.status == 'on_leave')),
        'can_check_out': bool(rec and rec.check_in and not rec.check_out),
    }


@extend_schema(tags=TAGS)
class AttendanceViewSet(viewsets.GenericViewSet):
    """Self-service (employee+) and team views (manager+). All routes are list-level actions."""
    permission_classes = [IsEmployee]
    serializer_class = AttendanceRecordSerializer

    def get_queryset(self):
        return AttendanceRecord.objects.filter(user=self.request.user).select_related('user')

    def _rec(self, rec):
        return AttendanceRecordSerializer(rec, context=self.get_serializer_context()).data if rec else None

    # ---- self-service -------------------------------------------------------------------------

    @extend_schema(request=CheckInSerializer, responses={201: AttendanceRecordSerializer})
    @action(detail=False, methods=['post'], url_path='check-in')
    def check_in(self, request):
        s = CheckInSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user, today, now = request.user, timezone.localdate(), timezone.now()
        leave = svc.leave_on(user, today)
        if leave and not leave.half_day:
            raise ValidationError({'detail': f'You are on approved {leave.leave_type.name} today '
                                             f'({leave.start_date} to {leave.end_date}); check-in is not needed.'})
        rec = AttendanceRecord.objects.filter(user=user, date=today).first()
        if rec and rec.check_in:
            local = timezone.localtime(rec.check_in).strftime('%H:%M')
            raise ValidationError({'detail': f'You already checked in today at {local}.'})
        if rec and rec.status == AttendanceRecord.Status.ON_LEAVE:
            raise ValidationError({'detail': 'Today is recorded as leave; ask HR to correct it if you are working.'})
        rec = rec or AttendanceRecord(user=user, date=today)
        rec.check_in, rec.check_in_ip = now, svc.client_ip(request)
        rec.status = svc.check_in_status(now)
        rec.work_mode = s.validated_data['work_mode']
        if s.validated_data['note']:
            rec.note = s.validated_data['note']
        try:
            with transaction.atomic():
                rec.save()
        except IntegrityError:  # concurrent double-click
            raise ValidationError({'detail': 'You already checked in today.'})
        return Response(self._rec(rec), status=201)

    @extend_schema(request=CheckOutSerializer, responses={200: AttendanceRecordSerializer})
    @action(detail=False, methods=['post'], url_path='check-out')
    def check_out(self, request):
        s = CheckOutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        with transaction.atomic():
            rec = AttendanceRecord.objects.select_for_update().filter(
                user=request.user, date=timezone.localdate()).first()
            if not rec or not rec.check_in:
                raise ValidationError({'detail': 'You have not checked in today.'})
            if rec.check_out:
                local = timezone.localtime(rec.check_out).strftime('%H:%M')
                raise ValidationError({'detail': f'You already checked out today at {local}.'})
            rec.check_out, rec.check_out_ip = timezone.now(), svc.client_ip(request)
            if s.validated_data['note']:
                rec.note = s.validated_data['note']
            rec.save()
        return Response(self._rec(rec))

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def today(self, request):
        return Response(today_payload(request.user, self.get_serializer_context()))

    @extend_schema(parameters=[MONTH], responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'])
    def me(self, request):
        start, end = svc.parse_month(request.query_params.get('month'))
        records = list(self.get_queryset().filter(date__range=(start, end)).order_by('date'))
        leave = svc.leave_days_map(start, end, [request.user]).get(request.user.id, set())
        days = svc.month_days(records, start, end, leave, svc.join_date(request.user))
        return Response({
            'month': start.strftime('%Y-%m'), 'start': start, 'end': end,
            'days': days,
            'records': AttendanceRecordSerializer(records, many=True).data,
            'summary': svc.summarize(records, start, end, days=days),
        })

    # ---- team / HR ----------------------------------------------------------------------------

    @extend_schema(parameters=[OpenApiParameter('date', OpenApiTypes.DATE), DEPT],
                   responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'], permission_classes=[IsManager])
    def team(self, request):
        day = svc.parse_date(request.query_params.get('date'))
        members = list(svc.scoped_staff(request.user, request.query_params.get('department')))
        kind, holiday, statuses = svc.day_statuses(members, day)
        rows, counts = [], {}
        for u, st, rec in statuses:
            counts[st] = counts.get(st, 0) + 1
            rows.append({
                'user': StaffSerializer(u, context={'request': request}).data,
                'status': st,
                'record': {
                    'id': rec.id, 'check_in': rec.check_in and timezone.localtime(rec.check_in),
                    'check_out': rec.check_out and timezone.localtime(rec.check_out), 'work_mode': rec.work_mode,
                    'worked_minutes': rec.worked_minutes, 'note': rec.note,
                } if rec else None,
            })
        return Response({'date': day, 'day_kind': kind, 'holiday_name': holiday, 'counts': counts, 'members': rows})

    @extend_schema(parameters=[MONTH, DEPT, OpenApiParameter('format', OpenApiTypes.STR, enum=['json', 'csv'])],
                   responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=['get'], permission_classes=[IsManager],
            renderer_classes=[renderers.JSONRenderer, renderers.BrowsableAPIRenderer, CSVRenderer])
    def register(self, request):
        start, end = svc.parse_month(request.query_params.get('month'))
        members = list(svc.scoped_staff(request.user, request.query_params.get('department')))
        kinds = svc.month_kinds(start, end)
        days = sorted(kinds)
        leave = svc.leave_days_map(start, end, members)
        recs = {}
        for r in AttendanceRecord.objects.filter(date__range=(start, end), user__in=members):
            recs.setdefault(r.user_id, []).append(r)
        today = timezone.localdate()
        rows = []
        for u in members:
            joined, mine = svc.join_date(u), recs.get(u.id, [])
            by_date, lv = {r.date: r for r in mine}, leave.get(u.id, set())
            cells = [svc.derive_status(d, today, kinds[d][0], by_date.get(d), d in lv, joined) for d in days]
            totals = {k: cells.count(k) for k in ('present', 'late', 'absent', 'on_leave')}
            totals['worked_minutes'] = sum(r.worked_minutes or 0 for r in mine)
            rows.append({'user': StaffSerializer(u, context={'request': request}).data, 'cells': cells, 'totals': totals})

        if request.accepted_renderer.format == 'csv':
            month = start.strftime('%Y-%m')
            resp = HttpResponse(content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="attendance-register-{month}.csv"'
            w = csv.writer(resp)
            w.writerow(['Employee', 'Email', 'Department', *[d.strftime('%d') for d in days],
                        'Present', 'Late', 'Absent', 'On leave', 'Worked hours'])
            for row in rows:
                u, t = row['user'], row['totals']
                w.writerow([csv_safe(u['full_name']), csv_safe(u['email']),
                            csv_safe((u['department'] or {}).get('name', '')),
                            *[CSV_CODES.get(c, c) for c in row['cells']],
                            t['present'], t['late'], t['absent'], t['on_leave'], round(t['worked_minutes'] / 60, 1)])
            w.writerow([])
            w.writerow(['Legend: P present, L late, A absent, LV on leave, W weekend, H holiday, - not checked in'])
            return resp

        return Response({
            'month': start.strftime('%Y-%m'),
            'days': [{'date': d, 'weekday': d.weekday(), 'kind': kinds[d][0], 'holiday_name': kinds[d][1]} for d in days],
            'rows': rows,
        })


@extend_schema_view(
    list=extend_schema(tags=TAGS, parameters=[
        MONTH, DEPT, OpenApiParameter('user', OpenApiTypes.INT), OpenApiParameter('status', OpenApiTypes.STR)]),
    retrieve=extend_schema(tags=TAGS), create=extend_schema(tags=TAGS),
    update=extend_schema(tags=TAGS), partial_update=extend_schema(tags=TAGS),
)
class AttendanceRecordViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                              mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """HR corrections: list/fix/create records (hr_admin+). Employees never edit records."""
    permission_classes = [IsHRAdmin]
    serializer_class = AttendanceRecordSerializer

    def get_queryset(self):
        qs = AttendanceRecord.objects.select_related('user').order_by('-date', 'user__first_name')
        if self.action != 'list':
            return qs
        p = self.request.query_params
        start, end = svc.parse_month(p.get('month'))
        qs = qs.filter(date__range=(start, end))
        if p.get('department'):
            qs = qs.filter(user__in=svc.scoped_staff(self.request.user, p['department']))
        if p.get('user'):
            if not p['user'].isdigit():
                raise ValidationError({'user': 'Must be a user id.'})
            qs = qs.filter(user_id=p['user'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        return qs

    def _guard(self, users, day):
        """No self-corrections (super_admin excepted) and no records for days that have not happened."""
        me = self.request.user
        if me in users and not me.has_role('super_admin'):
            raise PermissionDenied('You cannot create or correct your own attendance; ask another HR admin.')
        if day and day > timezone.localdate():
            raise ValidationError({'date': 'Cannot record attendance for a future date.'})

    def perform_create(self, serializer):
        d = serializer.validated_data
        self._guard({d.get('user')}, d.get('date'))
        serializer.save(source=AttendanceRecord.Source.HR)

    def perform_update(self, serializer):
        d, inst = serializer.validated_data, serializer.instance
        self._guard({inst.user, d.get('user', inst.user)}, d.get('date', inst.date))
        serializer.save(source=AttendanceRecord.Source.HR)


CORRECTIONS_LINK = '/app/attendance?tab=corrections'


def apply_correction(c):
    """Write an approved correction onto that day's record (created if missing). Plain save() so audit signals see it."""
    tz = timezone.get_current_timezone()
    cin = timezone.make_aware(datetime.datetime.combine(c.date, c.check_in), tz)
    rec = (AttendanceRecord.objects.select_for_update().filter(user_id=c.user_id, date=c.date).first()
           or AttendanceRecord(user_id=c.user_id, date=c.date))
    rec.check_in = cin
    rec.check_out = timezone.make_aware(datetime.datetime.combine(c.date, c.check_out), tz) if c.check_out else None
    rec.status = svc.check_in_status(cin)
    rec.source = AttendanceRecord.Source.CORRECTED
    rec.save()
    return rec


@extend_schema_view(
    list=extend_schema(tags=TAGS, summary='Attendance correction requests', parameters=[
        OpenApiParameter('scope', str, enum=['mine', 'approvals'],
                         description='mine (default) or approvals (pending requests I may decide)'),
    ]),
    retrieve=extend_schema(tags=TAGS),
    create=extend_schema(tags=TAGS, summary='Request a correction for a past day (up to 30 days back)'),
)
class AttendanceCorrectionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                                  viewsets.GenericViewSet):
    """Approval routing is the leave module's: the requester's department manager, or hr_admin+; never yourself."""
    permission_classes = [IsEmployee]
    serializer_class = CorrectionSerializer

    def get_queryset(self):
        qs = AttendanceCorrection.objects.select_related('user__profile__department__manager', 'approver')
        if getattr(self, 'swagger_fake_view', False):
            return qs
        user = self.request.user
        if self.action in ('approve', 'reject'):
            return qs  # authorisation per object, so outsiders get 403 rather than 404
        if self.action == 'list':
            scope = self.request.query_params.get('scope', 'mine')
            if scope == 'approvals':
                return qs.filter(leave_svc.decidable_q(user), status=AttendanceCorrection.Status.PENDING).order_by('date')
            if scope != 'mine':
                raise ValidationError({'scope': 'scope must be "mine" or "approvals".'})
            return qs.filter(user=user)
        return qs.filter(Q(user=user) | leave_svc.decidable_q(user))

    def perform_create(self, serializer):
        c = serializer.save(user=self.request.user)
        out = f' to {c.check_out:%H:%M}' if c.check_out else ''
        push(leave_svc.eligible_approvers(c.user), 'correction_requested',
             f'{c.user.full_name} requested an attendance correction',
             f'{c.date:%d %b %Y}: {c.check_in:%H:%M}{out}. Reason: {c.reason}', CORRECTIONS_LINK, exclude=c.user)

    def _decide(self, request, new_status):
        body = (CorrectionRejectSerializer if new_status == AttendanceCorrection.Status.REJECTED
                else CorrectionDecisionSerializer)(data=request.data)
        with transaction.atomic():
            c = AttendanceCorrection.objects.select_for_update().select_related('user').get(pk=self.get_object().pk)
            if c.user_id == request.user.pk:
                raise PermissionDenied('You cannot decide your own correction request.')
            if not leave_svc.can_decide(request.user, c):
                raise PermissionDenied("Only the requester's department manager or HR can decide this request.")
            if c.status != AttendanceCorrection.Status.PENDING:
                raise ValidationError({'status': f'Only pending requests can be decided (this one is {c.status}).'})
            body.is_valid(raise_exception=True)
            c.status, c.approver, c.decided_at = new_status, request.user, timezone.now()
            c.decision_note = body.validated_data['decision_note']
            c.save(update_fields=['status', 'approver', 'decision_note', 'decided_at'])
            if new_status == AttendanceCorrection.Status.APPROVED:
                apply_correction(c)
            note = f' Note: {c.decision_note}' if c.decision_note else ''
            push([c.user], 'correction_decided', f'Your attendance correction for {c.date:%d %b} was {new_status}',
                 f'Decided by {request.user.full_name}.{note}', CORRECTIONS_LINK, exclude=request.user)
        return Response(self.get_serializer(c).data)

    @extend_schema(tags=TAGS, request=CorrectionDecisionSerializer, responses=CorrectionSerializer,
                   summary="Approve: rewrites that day's record with source=corrected")
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, AttendanceCorrection.Status.APPROVED)

    @extend_schema(tags=TAGS, request=CorrectionRejectSerializer, responses=CorrectionSerializer,
                   summary='Reject (decision_note required)')
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, AttendanceCorrection.Status.REJECTED)
