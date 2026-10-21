from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.org.models import Department
from .models import CalendarEvent, Holiday

User = get_user_model()


def user_mini(user):
    return {'id': user.pk, 'full_name': user.full_name} if user else None


class UserMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ['id', 'name', 'date', 'description', 'is_optional']


class HolidayBulkItemSerializer(serializers.Serializer):
    """One row of a bulk upload. No unique validator: duplicates are skipped, not rejected."""

    name = serializers.CharField(max_length=150)
    date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_optional = serializers.BooleanField(required=False, default=False)


class CalendarEventSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    attendees = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True).exclude(role='guest'), many=True, required=False
    )
    attendees_detail = UserMiniSerializer(source='attendees', many=True, read_only=True)
    created_by = UserMiniSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'start', 'end', 'all_day', 'location', 'audience',
            'department', 'department_name', 'attendees', 'attendees_detail',
            'created_by', 'can_edit', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_can_edit(self, obj) -> bool:
        return can_edit_event(self.context['request'].user, obj)

    def validate(self, attrs):
        get = lambda k: attrs[k] if k in attrs else getattr(self.instance, k, None)  # noqa: E731
        start, end = get('start'), get('end')
        audience = get('audience') or CalendarEvent.Audience.ORGANIZATION
        department = get('department')

        if start and end and end < start:
            raise serializers.ValidationError({'end': 'End must be the same as or after start.'})
        if audience == CalendarEvent.Audience.DEPARTMENT:
            if not department:
                raise serializers.ValidationError({'department': 'Department is required for a department event.'})
        elif department is not None:
            if 'department' in attrs:
                raise serializers.ValidationError(
                    {'department': 'Department is only allowed when audience is "department".'}
                )
            attrs['department'] = None  # audience changed away from department: drop the stale link

        user = self.context['request'].user
        # On update, the scope check applies only when the scope actually changes: a creator who has since
        # lost the department can still fix a typo (can_edit already gates who may edit at all).
        scope_unchanged = self.instance is not None and (
            audience == self.instance.audience and attrs.get('department', department) == self.instance.department
        )
        if not user.has_role('hr_admin') and not scope_unchanged:
            if audience == CalendarEvent.Audience.ORGANIZATION:
                raise PermissionDenied('Only HR/admin can create organization-wide events.')
            if audience == CalendarEvent.Audience.DEPARTMENT and (
                not user.has_role('manager') or department.manager_id != user.pk
            ):
                raise PermissionDenied('You can only create department events for departments you manage.')
        return attrs


def can_edit_event(user, event):
    return event.created_by_id == user.pk or user.has_role('hr_admin')
