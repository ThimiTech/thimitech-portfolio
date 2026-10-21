from rest_framework.permissions import BasePermission


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
