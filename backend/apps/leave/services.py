"""Leave rules: day computation, balances, and who may decide a request."""
import datetime
import logging
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.calendar_app.utils import working_days
from apps.users.tasks import send_email
from .models import LeaveRequest, LeaveType

log = logging.getLogger(__name__)
HALF = Decimal('0.5')
HR_ROLES = ('hr_admin', 'super_admin')


# ---- days ------------------------------------------------------------------

def compute_days(start, end, half_day=False):
    """Requested working days: 0.5 for a half day, else the count of working days in [start, end]."""
    if half_day:
        return HALF if start == end and working_days(start, end) else Decimal(0)
    return Decimal(len(working_days(start, end)))


def days_by_year(start, end, half_day, days, *, org=None):
    """{year: days} — a request that crosses Dec 31 is split by its working days in each year."""
    if start.year == end.year:
        return {start.year: Decimal(days)}
    split = defaultdict(Decimal)
    for d in working_days(start, end, org=org):
        split[d.year] += 1
    return dict(split)


# ---- people ----------------------------------------------------------------

def department_manager(user):
    """The requester's department manager (never the requester), or None."""
    profile = getattr(user, 'profile', None)
    return profile.manager if profile else None


def hr_users():
    return get_user_model().objects.filter(is_active=True, role__in=HR_ROLES)


def team_q(actor, prefix='user__'):
    """Q matching people in departments `actor` manages (excluding the actor)."""
    return Q(**{f'{prefix}profile__department__manager': actor}) & ~Q(**{f'{prefix}pk': actor.pk})


def is_manager_of(actor, user):
    m = department_manager(user)
    return bool(m and m.pk == actor.pk)


def can_decide(actor, req):
    """Department manager of the requester, or hr_admin+; never the requester."""
    if actor.pk == req.user_id:
        return False
    return actor.has_role('hr_admin') or is_manager_of(actor, req.user)


def eligible_approvers(user):
    """Who gets the 'new request' email: the department manager, else every hr_admin+."""
    m = department_manager(user)
    return [m] if m else list(hr_users().exclude(pk=user.pk))


def decidable_q(actor):
    """Q over LeaveRequest for requests `actor` may decide."""
    q = Q() if actor.has_role('hr_admin') else team_q(actor)
    return q & ~Q(user=actor)


def can_cancel(actor, req, today):
    if req.status not in (LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED):
        return False
    if actor.has_role('hr_admin'):
        return True
    if actor.pk != req.user_id:
        return False
    return req.status == LeaveRequest.Status.PENDING or req.start_date > today


# ---- balances --------------------------------------------------------------

def _usage(user, year, statuses, exclude_pk=None):
    """{leave_type_id: days in `year`} over the user's requests with the given statuses."""
    qs = LeaveRequest.objects.filter(
        user=user, status__in=statuses, start_date__year__lte=year, end_date__year__gte=year,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    out = defaultdict(Decimal)
    for r in qs:
        out[r.leave_type_id] += days_by_year(r.start_date, r.end_date, r.half_day, r.days).get(year, 0)
    return out


def balances(user, year):
    used = _usage(user, year, [LeaveRequest.Status.APPROVED])
    pending = _usage(user, year, [LeaveRequest.Status.PENDING])
    rows = []
    for lt in LeaveType.objects.filter(is_active=True):
        u, p = used.get(lt.pk, Decimal(0)), pending.get(lt.pk, Decimal(0))
        rows.append({
            'leave_type': lt,
            'quota': lt.annual_quota,
            'used': u,
            'pending': p,
            # quota 0 = no fixed allowance (unpaid / case-by-case)
            'remaining': lt.annual_quota - u if lt.annual_quota > 0 else None,
        })
    return rows


def balance_shortfall(user, leave_type, start, end, half_day, days, *, count_pending, exclude_pk=None):
    """Error message if the request would exceed the yearly quota, else None.

    Only paid types with a quota are limited. On create, pending requests also count
    (count_pending=True) so several pending requests can't overbook the quota.
    """
    if not leave_type.is_paid or leave_type.annual_quota <= 0:
        return None
    statuses = [LeaveRequest.Status.APPROVED] + ([LeaveRequest.Status.PENDING] if count_pending else [])
    for year, need in days_by_year(start, end, half_day, days).items():
        taken = _usage(user, year, statuses, exclude_pk).get(leave_type.pk, Decimal(0))
        left = leave_type.annual_quota - taken
        if need > left:
            return (f'Insufficient {leave_type.name} balance for {year}: '
                    f'{_fmt(need)} day(s) requested, {_fmt(max(left, 0))} available'
                    f'{" (including pending requests)" if count_pending else ""}.')
    return None


def _fmt(d):
    return f'{d.normalize():f}'


# ---- side effects ----------------------------------------------------------

def notify(subject, body, users):
    """Queue an email; a broker outage must never fail the request that triggered it."""
    emails = [u.email for u in users if u and u.email]
    if not emails:
        return
    try:
        send_email.delay(subject, body, emails)
    except Exception:  # noqa: BLE001
        log.exception('Could not queue leave email: %s', subject)


def describe(req):
    span = f'{req.start_date:%Y-%m-%d}' + ('' if req.start_date == req.end_date else f' to {req.end_date:%Y-%m-%d}')
    return f'{req.leave_type.name} leave, {span} ({_fmt(req.days)} day(s){", half day" if req.half_day else ""})'


def mark_attendance_on_leave(req):
    """Absent attendance records inside an approved leave become on_leave."""
    from apps.attendance.models import AttendanceRecord
    from apps.audit.services import audited_update
    return audited_update(AttendanceRecord.objects.filter(
        user=req.user, date__range=(req.start_date, req.end_date), status=AttendanceRecord.Status.ABSENT,
    ), status=AttendanceRecord.Status.ON_LEAVE)


def revert_attendance_on_leave(req):
    """Undo mark_attendance_on_leave for a cancelled approved leave: leave rows without a check-in
    become absent for past days; today/future rows are dropped so check-in and mark_absentees work again."""
    from apps.attendance.models import AttendanceRecord
    today = timezone.localdate()
    qs = AttendanceRecord.objects.filter(
        user_id=req.user_id, date__range=(req.start_date, req.end_date),
        status=AttendanceRecord.Status.ON_LEAVE, check_in__isnull=True,
    )
    qs.filter(date__gte=today).delete()
    from apps.audit.services import audited_update
    audited_update(qs.filter(date__lt=today), status=AttendanceRecord.Status.ABSENT)


def max_backdate(today):
    return today - datetime.timedelta(days=30)
