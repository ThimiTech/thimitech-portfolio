"""Attendance rules: lateness, day classification, scoping. Pure-ish helpers so tests can hit them directly."""
import calendar
import datetime
import ipaddress

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.calendar_app.models import Holiday
from apps.calendar_app.utils import working_days
from apps.leave.models import LeaveRequest
from apps.org.models import Organization

from .models import AttendanceRecord

S = AttendanceRecord.Status
STAFF_ROLES = ['employee', 'manager', 'hr_admin', 'super_admin']


def _ip(value):
    try:
        return ipaddress.ip_address((value or '').strip())
    except ValueError:
        return None


def client_ip(request):
    """Best-effort client IP. X-Forwarded-For is only honoured when the direct peer is a private/loopback
    proxy, and is read right-to-left (proxies append; leftmost hops are whatever the client sent): the first
    public hop wins. Anything unparsable falls back to REMOTE_ADDR, so a junk header can never 500."""
    remote = _ip(request.META.get('REMOTE_ADDR'))
    if remote and (remote.is_private or remote.is_loopback):
        for hop in reversed(request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')):
            ip = _ip(hop)
            if ip is None:
                break
            if not (ip.is_private or ip.is_loopback):
                return str(ip)
    return str(remote) if remote else None


def late_after(org, day):
    """Aware datetime after which a check-in on `day` counts as late."""
    start = datetime.datetime.combine(day, org.work_start)
    return timezone.make_aware(start) + datetime.timedelta(minutes=org.late_grace_minutes)


def check_in_status(check_in, org=None):
    """present/late for an aware check-in datetime. Non-working days (overtime) are always present."""
    org = org or Organization.load()
    day = timezone.localtime(check_in).date()
    if day_kind(day, org)[0] != 'working':
        return S.PRESENT
    return S.LATE if check_in > late_after(org, day) else S.PRESENT


def day_kind(day, org=None):
    """('working'|'weekend'|'holiday', holiday_name|None)."""
    org = org or Organization.load()
    h = Holiday.objects.filter(date=day, is_optional=False).first()
    if h:
        return 'holiday', h.name
    if day.weekday() in set(org.weekend_days):
        return 'weekend', None
    return 'working', None


def month_kinds(start, end, org=None):
    """{date: ('working'|'weekend'|'holiday', name|None)} for [start, end] in two queries."""
    org = org or Organization.load()
    weekend = set(org.weekend_days)
    holidays = dict(Holiday.objects.filter(date__range=(start, end), is_optional=False).values_list('date', 'name'))
    out, d = {}, start
    while d <= end:
        out[d] = ('holiday', holidays[d]) if d in holidays else (('weekend', None) if d.weekday() in weekend else ('working', None))
        d += datetime.timedelta(days=1)
    return out


def approved_leaves(start, end, users=None):
    qs = LeaveRequest.objects.filter(
        status=LeaveRequest.Status.APPROVED, start_date__lte=end, end_date__gte=start,
    ).select_related('leave_type')
    if users is not None:
        qs = qs.filter(user__in=users)
    return qs


def leave_on(user, day):
    return approved_leaves(day, day, [user]).first()


def leave_days_map(start, end, users=None):
    """{user_id: set(dates)} of approved leave within [start, end]."""
    out = {}
    for lr in approved_leaves(start, end, users):
        d = max(lr.start_date, start)
        while d <= min(lr.end_date, end):
            out.setdefault(lr.user_id, set()).add(d)
            d += datetime.timedelta(days=1)
    return out


def parse_month(value):
    """'YYYY-MM' (default: current local month) -> (first_day, last_day)."""
    if not value:
        today = timezone.localdate()
        y, m = today.year, today.month
    else:
        try:
            y, m = (int(p) for p in value.split('-'))
            if not (1900 <= y <= 2999 and 1 <= m <= 12):
                raise ValueError
        except (ValueError, TypeError):
            raise ValidationError({'month': 'Use the format YYYY-MM, e.g. 2026-10.'})
    return datetime.date(y, m, 1), datetime.date(y, m, calendar.monthrange(y, m)[1])


def parse_date(value):
    if not value:
        return timezone.localdate()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValidationError({'date': 'Use the format YYYY-MM-DD.'})


def scoped_staff(user, department=None):
    """Active staff the user may see: hr_admin+ everyone, manager their departments' members."""
    qs = get_user_model().objects.filter(is_active=True, role__in=STAFF_ROLES).select_related(
        'profile', 'profile__department',
    ).order_by('first_name', 'email')
    if not user.has_role('hr_admin'):
        qs = qs.filter(profile__department__manager=user)
    if department:
        try:
            qs = qs.filter(profile__department_id=int(department))
        except ValueError:
            raise ValidationError({'department': 'Must be a department id.'})
    return qs


def join_date(user):
    p = getattr(user, 'profile', None)
    return p.join_date if p else None


def derive_status(day, today, kind, record, on_leave, joined=None):
    """Display status for one user-day.

    record status wins; then weekend/holiday (leave never covers non-working days, matching
    LeaveRequest.days); then approved leave; then absent (past) / not_checked_in (today);
    None for future days or before the join date.
    """
    if record:
        return record.status
    if joined and day < joined:
        return None
    if kind != 'working':
        return kind
    if on_leave:
        return S.ON_LEAVE
    if day < today:
        return S.ABSENT
    if day == today:
        return 'not_checked_in'
    return None


def month_days(records, start, end, leave_dates=(), joined=None):
    """[{date, kind, holiday_name, status}] for one user over [start, end] -- same cells as the register."""
    today = timezone.localdate()
    by_date = {r.date: r for r in records}
    return [
        {'date': d, 'kind': kind, 'holiday_name': name,
         'status': derive_status(d, today, kind, by_date.get(d), d in leave_dates, joined)}
        for d, (kind, name) in month_kinds(start, end).items()
    ]


def summarize(records, start, end, leave_dates=(), joined=None, days=None):
    """Monthly summary for one user. attendance_rate = attended / expected working days so far, where
    expected = past working days (not on leave, after joining) plus today only once it has a record."""
    days = days if days is not None else month_days(records, start, end, leave_dates, joined)
    counts = {'present': 0, 'late': 0, 'absent': 0, 'on_leave': 0}
    for day in days:
        if day['status'] in counts:
            counts[day['status']] += 1
    expected = [d for d in days if d['kind'] == 'working' and d['status'] in (S.PRESENT, S.LATE, S.ABSENT)]
    attended = sum(1 for d in expected if d['status'] in (S.PRESENT, S.LATE))
    return {
        **counts,
        'worked_minutes_total': sum(r.worked_minutes or 0 for r in records),
        'working_days_in_month': len(working_days(start, end)),
        'working_days_elapsed': len(expected),
        'attendance_rate': round(100 * attended / len(expected), 1) if expected else None,
    }


def day_statuses(members, day):
    """(kind, holiday_name, [(user, status, record)]) for `members` on `day`; users who join later are omitted.
    Shared by the team view and the dashboard so both derive statuses the same way."""
    records = {r.user_id: r for r in AttendanceRecord.objects.filter(date=day, user__in=members)}
    leave = leave_days_map(day, day, members)
    kind, holiday = day_kind(day)
    today = timezone.localdate()
    rows = []
    for u in members:
        joined = join_date(u)
        if joined and day < joined:
            continue
        rec = records.get(u.id)
        rows.append((u, derive_status(day, today, kind, rec, day in leave.get(u.id, ()), joined) or 'not_checked_in', rec))
    return kind, holiday, rows
