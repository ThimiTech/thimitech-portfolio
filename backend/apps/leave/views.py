import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.notifications.services import push
from apps.permissions.permissions import IsEmployee, IsHRAdmin
from . import services
from .models import LeaveRequest, LeaveType
from .serializers import (
    BalanceSerializer, DecisionSerializer, LeaveCalendarSerializer, LeaveRequestCreateSerializer,
    LeaveRequestSerializer, LeaveTypeSerializer, RejectSerializer,
)

TAGS = ['Leave']
REQUEST_SELECT = ('user__profile__department__manager', 'leave_type', 'approver')
YEAR_PARAM = OpenApiParameter('year', int, description='Calendar year (default: current year)')


def _int_param(request, name, default=None):
    raw = request.query_params.get(name)
    if raw in (None, ''):
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValidationError({name: f'{name} must be an integer.'})


def _year_param(request):
    year = _int_param(request, 'year', timezone.localdate().year)
    if not 1900 <= year <= 2200:
        raise ValidationError({'year': 'year must be between 1900 and 2200.'})
    return year


def _date_param(request, name):
    raw = request.query_params.get(name)
    if not raw:
        raise ValidationError({name: f'{name} is required (YYYY-MM-DD).'})
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({name: f'{name} must be a date (YYYY-MM-DD).'})


@extend_schema_view(
    list=extend_schema(tags=TAGS, summary='Leave types (non-HR see active only)'),
    retrieve=extend_schema(tags=TAGS),
    create=extend_schema(tags=TAGS, summary='Create leave type (hr_admin+)'),
    update=extend_schema(tags=TAGS),
    partial_update=extend_schema(tags=TAGS),
    destroy=extend_schema(tags=TAGS, summary='Delete; a type with requests is deactivated instead (200)'),
)
class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveTypeSerializer

    def get_permissions(self):
        return [IsEmployee()] if self.action in ('list', 'retrieve') else [IsHRAdmin()]

    def get_queryset(self):
        qs = LeaveType.objects.all()
        if getattr(self, 'swagger_fake_view', False):
            return qs
        return qs if self.request.user.has_role('hr_admin') else qs.filter(is_active=True)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.requests.exists():
            obj.is_active = False
            obj.save(update_fields=['is_active'])
            return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=TAGS, summary='Leave requests', parameters=[
        OpenApiParameter('scope', str, enum=['mine', 'team'], description='mine (default) or team (manager: team; hr_admin+: everyone)'),
        OpenApiParameter('status', str, enum=[s for s, _ in LeaveRequest.Status.choices]),
        YEAR_PARAM,
        OpenApiParameter('user', int, description='scope=team only: one person'),
    ]),
    retrieve=extend_schema(tags=TAGS),
    create=extend_schema(tags=TAGS, request=LeaveRequestCreateSerializer, responses={201: LeaveRequestSerializer}),
)
class LeaveRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          viewsets.GenericViewSet):
    permission_classes = [IsEmployee]

    def get_serializer_class(self):
        return LeaveRequestCreateSerializer if self.action == 'create' else LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        qs = LeaveRequest.objects.select_related(*REQUEST_SELECT)
        if getattr(self, 'swagger_fake_view', False):
            return qs
        if self.action in ('approve', 'reject', 'cancel'):
            return qs  # authorisation is checked per object so outsiders get 403, not 404
        if self.action == 'list':
            return self._list_queryset(qs)
        if user.has_role('hr_admin'):
            return qs
        return qs.filter(Q(user=user) | services.team_q(user))

    def _list_queryset(self, qs):
        user, params = self.request.user, self.request.query_params
        scope = params.get('scope', 'mine')
        if scope == 'mine':
            qs = qs.filter(user=user)
        elif scope == 'team':
            if user.has_role('hr_admin'):
                pass
            elif user.has_role('manager'):
                qs = qs.filter(services.team_q(user))
            else:
                raise PermissionDenied('Team scope requires role: manager or higher.')
            if (uid := _int_param(self.request, 'user')) is not None:
                qs = qs.filter(user_id=uid)
        else:
            raise ValidationError({'scope': 'scope must be "mine" or "team".'})

        if st := params.get('status'):
            if st not in LeaveRequest.Status.values:
                raise ValidationError({'status': f'status must be one of {", ".join(LeaveRequest.Status.values)}.'})
            qs = qs.filter(status=st)
        year = _year_param(self.request)
        return qs.filter(start_date__year__lte=year, end_date__year__gte=year)

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            # Per-user lock: serialises this user's creates so the overlap/balance checks can't race.
            get_user_model().objects.select_for_update().filter(pk=request.user.pk).first()
            ser = self.get_serializer(data=request.data)
            ser.is_valid(raise_exception=True)
            req = ser.save(user=request.user)
        services.notify(
            f'Leave request from {request.user.full_name}',
            f'{request.user.full_name} requested {services.describe(req)}.\n\n'
            f'Reason: {req.reason}\n\nReview it in Thimi Tech OS > Leave > Approvals.',
            services.eligible_approvers(request.user),
        )
        push(services.eligible_approvers(request.user), 'leave_requested',
             f'{request.user.full_name} requested leave', services.describe(req), '/app/leave?tab=approvals')
        req = LeaveRequest.objects.select_related(*REQUEST_SELECT).get(pk=req.pk)
        return Response(LeaveRequestSerializer(req, context=self.get_serializer_context()).data,
                        status=status.HTTP_201_CREATED)

    def _decide(self, request, new_status):
        body = (RejectSerializer if new_status == LeaveRequest.Status.REJECTED else DecisionSerializer)(data=request.data)
        with transaction.atomic():
            req = self.get_object()
            req = LeaveRequest.objects.select_for_update().select_related('leave_type', 'user').get(pk=req.pk)
            if req.user_id == request.user.pk:
                raise PermissionDenied('You cannot decide your own leave request.')
            if not services.can_decide(request.user, req):
                raise PermissionDenied("Only the requester's department manager or HR can decide this request.")
            if req.status != LeaveRequest.Status.PENDING:
                raise ValidationError({'status': f'Only pending requests can be decided (this one is {req.status}).'})
            body.is_valid(raise_exception=True)  # after the 403/status checks so outsiders learn nothing
            if new_status == LeaveRequest.Status.APPROVED:
                short = services.balance_shortfall(
                    req.user, req.leave_type, req.start_date, req.end_date, req.half_day, req.days,
                    count_pending=False, exclude_pk=req.pk,
                )
                if short:
                    raise ValidationError({'non_field_errors': [short]})
            req.status = new_status
            req.approver = request.user
            req.decision_note = body.validated_data['decision_note']
            req.decided_at = timezone.now()
            req.save(update_fields=['status', 'approver', 'decision_note', 'decided_at'])
            if new_status == LeaveRequest.Status.APPROVED:
                services.mark_attendance_on_leave(req)

        note = f'\n\nNote from {request.user.full_name}: {req.decision_note}' if req.decision_note else ''
        services.notify(
            f'Your leave request was {new_status}',
            f'Your {services.describe(req)} was {new_status} by {request.user.full_name}.{note}',
            [req.user],
        )
        push([req.user], 'leave_decided', f'Your leave request was {new_status}',
             f'{services.describe(req)}, by {request.user.full_name}.{note}', '/app/leave', exclude=request.user)
        req = LeaveRequest.objects.select_related(*REQUEST_SELECT).get(pk=req.pk)
        return Response(LeaveRequestSerializer(req, context=self.get_serializer_context()).data)

    @extend_schema(tags=TAGS, request=DecisionSerializer, responses=LeaveRequestSerializer,
                   summary='Approve a pending request (dept manager of requester, or hr_admin+)')
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, LeaveRequest.Status.APPROVED)

    @extend_schema(tags=TAGS, request=RejectSerializer, responses=LeaveRequestSerializer,
                   summary='Reject a pending request (decision_note required)')
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, LeaveRequest.Status.REJECTED)

    @extend_schema(tags=TAGS, request=None, responses=LeaveRequestSerializer,
                   summary='Cancel: owner (pending, or approved & not yet started) or hr_admin+')
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        actor = request.user
        with transaction.atomic():
            req = self.get_object()
            req = LeaveRequest.objects.select_for_update().get(pk=req.pk)
            if actor.pk != req.user_id and not actor.has_role('hr_admin'):
                raise PermissionDenied('You can only cancel your own leave requests.')
            if not services.can_cancel(actor, req, timezone.localdate()):
                if req.status not in (LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED):
                    raise ValidationError({'status': f'This request is already {req.status}.'})
                raise ValidationError({'status': 'Approved leave that has already started can only be cancelled by HR.'})
            if req.status == LeaveRequest.Status.APPROVED:
                services.revert_attendance_on_leave(req)
            req.status = LeaveRequest.Status.CANCELLED
            req.save(update_fields=['status'])
        req = LeaveRequest.objects.select_related(*REQUEST_SELECT).get(pk=req.pk)
        return Response(LeaveRequestSerializer(req, context=self.get_serializer_context()).data)


@extend_schema(tags=TAGS, summary='Leave balances for a year', parameters=[
    YEAR_PARAM, OpenApiParameter('user', int, description='Someone else (hr_admin+, or their department manager)'),
], responses=inline_serializer('LeaveBalances', {
    'year': serializers.IntegerField(),
    'user': inline_serializer('LeaveBalanceUser', {'id': serializers.IntegerField(), 'full_name': serializers.CharField()}),
    'balances': BalanceSerializer(many=True),
}))
class LeaveBalanceViewSet(viewsets.ViewSet):
    permission_classes = [IsEmployee]

    def list(self, request):
        year = _year_param(request)
        target = request.user
        uid = _int_param(request, 'user')
        if uid is not None and uid != request.user.pk:
            target = get_user_model().objects.select_related('profile__department').filter(pk=uid).first()
            if not target:
                raise NotFound('User not found.')
            if not (request.user.has_role('hr_admin') or services.is_manager_of(request.user, target)):
                raise PermissionDenied("You can only view your own or your team's balances.")
        return Response({
            'year': year,
            'user': {'id': target.pk, 'full_name': target.full_name},
            'balances': BalanceSerializer(services.balances(target, year), many=True).data,
        })


@extend_schema(tags=TAGS, summary='Pending requests the current user may decide', responses=LeaveRequestSerializer(many=True))
class LeaveApprovalViewSet(viewsets.GenericViewSet):
    permission_classes = [IsEmployee]
    serializer_class = LeaveRequestSerializer

    def list(self, request):
        qs = (LeaveRequest.objects.select_related(*REQUEST_SELECT)
              .filter(services.decidable_q(request.user), status=LeaveRequest.Status.PENDING)
              .order_by('start_date'))
        return Response(self.get_serializer(qs, many=True).data)


@extend_schema(tags=TAGS, summary='Approved leave in a date range (who is away)', parameters=[
    OpenApiParameter('start', OpenApiTypes.DATE, required=True),
    OpenApiParameter('end', OpenApiTypes.DATE, required=True, description='Inclusive; span at most 366 days'),
], responses=LeaveCalendarSerializer(many=True))
class LeaveCalendarViewSet(viewsets.GenericViewSet):
    permission_classes = [IsEmployee]
    serializer_class = LeaveCalendarSerializer

    def list(self, request):
        start, end = _date_param(request, 'start'), _date_param(request, 'end')
        if end < start:
            raise ValidationError({'end': 'end cannot be before start.'})
        if (end - start).days > 366:
            raise ValidationError({'end': 'Range can span at most 366 days.'})
        user = request.user
        qs = LeaveRequest.objects.select_related('user', 'leave_type').filter(
            status=LeaveRequest.Status.APPROVED, start_date__lte=end, end_date__gte=start,
        )
        if not user.has_role('hr_admin'):
            dept_id = getattr(getattr(user, 'profile', None), 'department_id', None)
            visible = Q(user=user) | Q(user__profile__department__manager=user)
            if dept_id:
                visible |= Q(user__profile__department_id=dept_id)
            qs = qs.filter(visible)
        return Response(self.get_serializer(qs.order_by('start_date', 'user__first_name'), many=True).data)
