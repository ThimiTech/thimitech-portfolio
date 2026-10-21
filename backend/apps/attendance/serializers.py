from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.leave.services import can_decide, max_backdate

from .models import AttendanceCorrection, AttendanceRecord
from .services import STAFF_ROLES


class StaffSerializer(serializers.Serializer):
    """Compact person card used in team/register rows."""
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    def get_department(self, user):
        p = getattr(user, 'profile', None)
        return {'id': p.department_id, 'name': p.department.name} if p and p.department else None

    def get_designation(self, user):
        p = getattr(user, 'profile', None)
        return p.designation if p else ''

    def get_photo(self, user):
        p = getattr(user, 'profile', None)
        if not (p and p.photo):
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(p.photo.url) if request else p.photo.url


class AttendanceRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    worked_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'user', 'user_name', 'date', 'check_in', 'check_out', 'status', 'work_mode',
            'note', 'source', 'check_in_ip', 'check_out_ip', 'worked_minutes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'source', 'check_in_ip', 'check_out_ip', 'created_at', 'updated_at']
        extra_kwargs = {'user': {'queryset': get_user_model().objects.filter(role__in=STAFF_ROLES)}}

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        day, cin, cout = get('date'), get('check_in'), get('check_out')
        for name, ts in (('check_in', cin), ('check_out', cout)):
            if ts and day and timezone.localtime(ts).date() != day:
                raise serializers.ValidationError({name: f'Must fall on {day} (Asia/Kathmandu time).'})
        if cin and cout and cout < cin:
            raise serializers.ValidationError({'check_out': 'Check-out cannot be before check-in.'})
        if cout and not cin:
            raise serializers.ValidationError({'check_in': 'Set a check-in time before a check-out time.'})
        user = get('user')
        if user and day:
            clash = AttendanceRecord.objects.filter(user=user, date=day)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({'date': f'{user.full_name} already has a record for {day}.'})
        return attrs

    def get_validators(self):
        return []  # unique (user, date) is checked in validate() with a readable message


class CheckInSerializer(serializers.Serializer):
    work_mode = serializers.ChoiceField(choices=AttendanceRecord.WorkMode.choices, default='office')
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class CheckOutSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class CorrectionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    approver_name = serializers.CharField(source='approver.full_name', read_only=True, default=None)
    can_decide = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceCorrection
        fields = ['id', 'user', 'user_name', 'date', 'check_in', 'check_out', 'reason', 'status', 'approver',
                  'approver_name', 'decision_note', 'decided_at', 'created_at', 'can_decide']
        read_only_fields = ['user', 'status', 'approver', 'decision_note', 'decided_at', 'created_at']
        extra_kwargs = {'check_out': {'required': True, 'allow_null': True}}

    def get_can_decide(self, obj) -> bool:
        request = self.context.get('request')
        return bool(request and obj.status == AttendanceCorrection.Status.PENDING and can_decide(request.user, obj))

    def validate(self, attrs):
        day, today, user = attrs['date'], timezone.localdate(), self.context['request'].user
        if day >= today:
            raise serializers.ValidationError({'date': 'Corrections are for past days; use check-in/out for today.'})
        if day < max_backdate(today):
            raise serializers.ValidationError({'date': f'Corrections can go back at most 30 days (to {max_backdate(today)}).'})
        if attrs.get('check_out') and attrs['check_out'] <= attrs['check_in']:
            raise serializers.ValidationError({'check_out': 'Check-out must be after check-in.'})
        if AttendanceCorrection.objects.filter(user=user, date=day, status=AttendanceCorrection.Status.PENDING).exists():
            raise serializers.ValidationError({'date': f'You already have a pending correction for {day}.'})
        return attrs


class CorrectionDecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class CorrectionRejectSerializer(serializers.Serializer):
    decision_note = serializers.CharField(max_length=2000)
