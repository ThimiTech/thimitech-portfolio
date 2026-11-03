from rest_framework import serializers
from rest_framework.permissions import BasePermission

from apps.users.models import Clearance


class IsAdminOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        return request.user.is_authenticated and request.user.is_staff


def min_role(role):
    """Permission class allowing authenticated users whose role rank >= `role`."""

    class MinRole(BasePermission):
        message = f'Requires role: {role} or higher.'

        def has_permission(self, request, view):
            return request.user.is_authenticated and request.user.has_role(role)

    MinRole.__name__ = f'MinRole_{role}'
    return MinRole


IsEmployee = min_role('employee')
IsManager = min_role('manager')
IsHRAdmin = min_role('hr_admin')
IsSuperAdmin = min_role('super_admin')


class IsFinance(BasePermission):
    """Finance books, payroll, reports and the finance drive: HR/admin+ or the accountant role."""
    message = 'Requires finance access (HR admin, super admin, or accountant).'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.can_finance()


class ClassifiedMixin:
    """Serializer mixin for models with `classification` (put it first in the bases).
    Nobody files something above their own clearance, and public items stay Internal."""

    def validate_classification(self, value):
        if value > self.context['request'].user.clearance:
            raise serializers.ValidationError('You cannot set an access level above your own clearance.')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        level = attrs.get('classification', getattr(self.instance, 'classification', Clearance.INTERNAL))
        if attrs.get('public', getattr(self.instance, 'public', False)) and level > Clearance.INTERNAL:
            raise serializers.ValidationError({'classification': 'Public items must be Internal.'})
        return attrs
