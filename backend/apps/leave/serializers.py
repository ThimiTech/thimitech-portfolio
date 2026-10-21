import re

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from . import services
from .models import LeaveRequest, LeaveType


class LeaveUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class LeavePersonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class LeaveTypeSerializer(serializers.ModelSerializer):
    annual_quota = serializers.DecimalField(max_digits=5, decimal_places=1, min_value=0, coerce_to_string=False)

    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'code', 'annual_quota', 'is_paid', 'color', 'is_active']

    def validate_color(self, v):
        if v and not re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            raise serializers.ValidationError('Use a hex colour like #7a6a52.')
        return v


class LeaveTypeBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'code', 'color', 'is_paid']


class LeaveRequestSerializer(serializers.ModelSerializer):
    user = LeaveUserSerializer(read_only=True)
    leave_type = LeaveTypeBriefSerializer(read_only=True)
    approver = LeaveUserSerializer(read_only=True, allow_null=True)
    days = serializers.DecimalField(max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True)
    designated_approver = serializers.SerializerMethodField()
    can_decide = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'leave_type', 'start_date', 'end_date', 'half_day', 'days', 'reason', 'status',
            'approver', 'decision_note', 'decided_at', 'created_at',
            'designated_approver', 'can_decide', 'can_cancel',
        ]
        read_only_fields = fields

    @extend_schema_field(LeavePersonSerializer(allow_null=True))
    def get_designated_approver(self, obj):
        """The requester's department manager; null means HR (hr_admin+) decides."""
        m = services.department_manager(obj.user)
        return {'id': m.pk, 'full_name': m.full_name} if m else None

    def get_can_decide(self, obj) -> bool:
        return obj.status == LeaveRequest.Status.PENDING and services.can_decide(self.context['request'].user, obj)

    def get_can_cancel(self, obj) -> bool:
        return services.can_cancel(self.context['request'].user, obj, timezone.localdate())


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    leave_type = serializers.PrimaryKeyRelatedField(
        queryset=LeaveType.objects.filter(is_active=True),
        error_messages={'does_not_exist': 'Unknown or inactive leave type.'},
    )
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'half_day', 'reason']

    def validate(self, data):
        user = self.context['request'].user
        start, end, half = data['start_date'], data['end_date'], data.get('half_day', False)
        today = timezone.localdate()

        if end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before the start date.'})
        if start < services.max_backdate(today):
            raise serializers.ValidationError({'start_date': 'Leave cannot start more than 30 days in the past.'})
        if (end - start).days > 366:
            raise serializers.ValidationError({'end_date': 'Leave can span at most one year; split longer leave.'})
        if half and start != end:
            raise serializers.ValidationError({'half_day': 'A half day must start and end on the same date.'})

        days = services.compute_days(start, end, half)
        if not days:
            raise serializers.ValidationError(
                {'non_field_errors': ['The selected dates contain no working days (weekends and holidays are excluded).']}
            )

        clash = LeaveRequest.objects.filter(
            Q(start_date__lte=end) & Q(end_date__gte=start),
            user=user, status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
        ).first()
        if clash:
            raise serializers.ValidationError({'non_field_errors': [
                f'These dates overlap your {clash.status} request for '
                f'{clash.start_date:%Y-%m-%d} to {clash.end_date:%Y-%m-%d}.'
            ]})

        short = services.balance_shortfall(user, data['leave_type'], start, end, half, days, count_pending=True)
        if short:
            raise serializers.ValidationError({'non_field_errors': [short]})

        data['days'] = days
        return data


class DecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class RejectSerializer(serializers.Serializer):
    decision_note = serializers.CharField(max_length=2000, trim_whitespace=True,
                                          error_messages={'blank': 'Give a reason for rejecting.',
                                                          'required': 'Give a reason for rejecting.'})


class BalanceSerializer(serializers.Serializer):
    leave_type = LeaveTypeBriefSerializer()
    quota = serializers.DecimalField(max_digits=6, decimal_places=1, coerce_to_string=False)
    used = serializers.DecimalField(max_digits=6, decimal_places=1, coerce_to_string=False)
    pending = serializers.DecimalField(max_digits=6, decimal_places=1, coerce_to_string=False)
    remaining = serializers.DecimalField(max_digits=6, decimal_places=1, coerce_to_string=False, allow_null=True)


class LeaveCalendarSerializer(serializers.ModelSerializer):
    user = LeavePersonSerializer(read_only=True)
    leave_type = LeaveTypeBriefSerializer(read_only=True)
    days = serializers.DecimalField(max_digits=5, decimal_places=1, coerce_to_string=False, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'user', 'leave_type', 'start_date', 'end_date', 'half_day', 'days']
