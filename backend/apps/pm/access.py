from django.db.models import Case, F, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .models import Project, Task


def visible_projects(user):
    if not user.is_authenticated or not user.has_role('employee'):
        return Project.objects.none()
    if user.has_role('hr_admin'):
        return Project.objects.all()
    return Project.objects.filter(Q(lead=user) | Q(members=user)).distinct()


def can_manage(user, project):
    return user.has_role('hr_admin') or (user.has_role('manager') and project.lead_id == user.pk)


def require_manager(user, project):
    if not can_manage(user, project):
        raise PermissionDenied('Only the project lead or HR/admin can manage this project.')


PRIORITY_ORDER = Case(*(When(priority=p, then=Value(i)) for i, p in enumerate(('urgent', 'high', 'medium', 'low'))),
                      default=Value(9), output_field=IntegerField())


def open_tasks_for(user):
    """Unfinished tasks assigned to `user` on active projects they can see, soonest due (then most urgent) first."""
    return (Task.objects.filter(assignee=user, column__board__project__in=visible_projects(user).filter(archived=False))
            .exclude(column__status='done')
            .select_related('column__board__project', 'assignee', 'milestone')
            .order_by(F('due_date').asc(nulls_last=True), PRIORITY_ORDER, 'id'))


def my_tasks_summary(user, limit=5):
    """{open, overdue, items[<=limit]} for the dashboard."""
    from .serializers import TaskSerializer
    qs = open_tasks_for(user)
    return {
        'open': qs.count(),
        'overdue': qs.filter(due_date__lt=timezone.localdate()).count(),
        'items': TaskSerializer(qs[:limit], many=True).data,
    }
