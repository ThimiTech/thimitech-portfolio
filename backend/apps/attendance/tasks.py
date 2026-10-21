import datetime

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.calendar_app.utils import is_working_day
from django.contrib.auth import get_user_model

from .models import AttendanceRecord
from .services import STAFF_ROLES, leave_days_map
from apps.audit.context import system_context


@shared_task
@system_context('attendance.mark_absentees')
@transaction.atomic
def mark_absentees(date_str=None):
    """For a working day (default: today, local), give every active staff member without a record
    an on_leave (approved leave) or absent record. Idempotent; skips users who joined after the date."""
    day = datetime.date.fromisoformat(date_str) if date_str else timezone.localdate()
    if not is_working_day(day):
        return {'date': str(day), 'skipped': 'not a working day', 'absent': 0, 'on_leave': 0}
    users = (
        get_user_model().objects.filter(is_active=True, role__in=STAFF_ROLES)
        .filter(Q(profile__isnull=True) | Q(profile__join_date__isnull=True) | Q(profile__join_date__lte=day))
        .exclude(attendance__date=day)
    )
    leave = leave_days_map(day, day, users)
    S = AttendanceRecord.Status
    # get_or_create retains per-row audit signals and avoids reporting racing check-ins as new absences.
    new = []
    for user in users:
        record, created = AttendanceRecord.objects.get_or_create(
            user=user, date=day, defaults={'status': S.ON_LEAVE if day in leave.get(user.id, ()) else S.ABSENT, 'note': 'Auto-marked', 'source': AttendanceRecord.Source.SYSTEM},
        )
        if created:
            new.append(record)
    on_leave = sum(r.status == S.ON_LEAVE for r in new)
    return {'date': str(day), 'absent': len(new) - on_leave, 'on_leave': on_leave}
