import datetime
from django.utils import timezone
from rest_framework import serializers
from .models import AuditLog
from .policy import TRACKED_APPS


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ['id', 'timestamp', 'actor_id', 'actor_label', 'actor_role', 'action', 'target_model', 'target_id', 'diff', 'source', 'entry_point', 'request_id']
        read_only_fields = fields


class AuditFiltersSerializer(serializers.Serializer):
    module = serializers.ChoiceField(choices=sorted(TRACKED_APPS), required=False)
    action = serializers.ChoiceField(choices=AuditLog.Action.choices, required=False)
    source = serializers.ChoiceField(choices=['api', 'admin', 'system'], required=False)
    actor = serializers.IntegerField(min_value=1, required=False)
    request_id = serializers.UUIDField(required=False)
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        for field in ['start', 'end']:
            if field in attrs and not 1900 <= attrs[field].year <= 2999:
                raise serializers.ValidationError({field: 'Use a year between 1900 and 2999.'})
        if attrs.get('start') and attrs.get('end') and attrs['start'] > attrs['end']:
            raise serializers.ValidationError({'end': 'End date must be on or after the start date.'})
        return attrs


class MonitoringWindowSerializer(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        end = attrs.get('end', today)
        if end.year < 1900:
            raise serializers.ValidationError('Use a year of 1900 or later.')
        start = attrs.get('start', end - datetime.timedelta(days=29))
        if start.year < 1900 or end > today or end < start or (end - start).days >= 93:
            raise serializers.ValidationError('Choose a past attendance window of 1 to 93 days, ending no later than today.')
        return {'start': start, 'end': end}


class AuditOptionsSerializer(serializers.Serializer):
    modules = serializers.ListField(child=serializers.CharField())
    actions = serializers.ListField(child=serializers.CharField())
    sources = serializers.ListField(child=serializers.CharField())
    tracked_models = serializers.ListField(child=serializers.CharField())
    capture_started_at = serializers.DateTimeField(allow_null=True)


