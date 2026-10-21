import datetime
from collections import defaultdict
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from apps.attendance.models import AttendanceRecord
from apps.attendance.services import month_kinds, leave_days_map, derive_status, join_date, STAFF_ROLES
from apps.leave.models import LeaveType, LeaveRequest
from apps.leave.services import days_by_year
from apps.org.models import Department, Organization
from apps.pm.models import Project, Task
from apps.finance.services import summary_payload as finance_summary
from apps.inventory.services import summary_payload as inventory_summary
from .models import AuditLog
from .serializers import AuditLogSerializer

STATUSES = ['present', 'late', 'absent', 'on_leave', 'not_checked_in']


def attendance_payload(staff, start, end, today, org):
    kinds = month_kinds(start, end, org)
    records = {(r.user_id, r.date): r for r in AttendanceRecord.objects.filter(user__in=staff, date__range=(start, end))}
    leaves = leave_days_map(start, end, staff)
    totals = dict.fromkeys(STATUSES + ['expected', 'attended'], 0)
    rows = []
    for day, (kind, _) in kinds.items():
        counts = dict.fromkeys(STATUSES + ['expected', 'attended'], 0)
        for user in staff:
            joined = join_date(user)
            if joined and day < joined:
                continue
            status = derive_status(day, today, kind, records.get((user.pk, day)), day in leaves.get(user.pk, ()), joined)
            if status in STATUSES:
                counts[status] += 1
            if kind == 'working' and status in ['present', 'late', 'absent']:
                counts['expected'] += 1
                counts['attended'] += int(status in ['present', 'late'])
        for key in totals:
            totals[key] += counts[key]
        rows.append({'date': day.isoformat(), 'kind': kind, **counts})
    return {'days': rows, 'totals': totals, 'rate': round(totals['attended'] / totals['expected'] * 100, 1) if totals['expected'] else None, 'roster_basis': 'Current active staff; join dates respected'}


def leave_payload(staff, year, org):
    ids = [user.pk for user in staff]
    used, pending = defaultdict(Decimal), defaultdict(Decimal)
    requests = LeaveRequest.objects.filter(user_id__in=ids, leave_type__is_paid=True, start_date__year__lte=year, end_date__year__gte=year, status__in=['approved', 'pending'])
    for row in requests:
        days = days_by_year(row.start_date, row.end_date, row.half_day, row.days, org=org).get(year, Decimal('0'))
        (used if row.status == 'approved' else pending)[(row.user_id, row.leave_type_id)] += days
    rows = []
    for leave_type in LeaveType.objects.filter(is_active=True, is_paid=True):
        capped = leave_type.annual_quota > 0
        total_used = sum((used[(uid, leave_type.pk)] for uid in ids), Decimal('0'))
        total_pending = sum((pending[(uid, leave_type.pk)] for uid in ids), Decimal('0'))
        remaining = sum((max(leave_type.annual_quota - used[(uid, leave_type.pk)], Decimal('0')) for uid in ids), Decimal('0')) if capped else None
        rows.append({'id': leave_type.pk, 'name': leave_type.name, 'quota_days': str(leave_type.annual_quota * len(ids)) if capped else None, 'used_days': str(total_used), 'pending_days': str(total_pending), 'remaining_days': str(remaining) if remaining is not None else None})
    return {'year': year, 'remaining_paid_days': str(sum((Decimal(row['remaining_days']) for row in rows if row['remaining_days'] is not None), Decimal('0'))), 'pending_paid_days': str(sum((Decimal(row['pending_days']) for row in rows), Decimal('0'))), 'pending_requests': LeaveRequest.objects.filter(user_id__in=ids, status='pending').count(), 'by_type': rows}


def project_payload(today):
    projects = Project.objects.filter(archived=False).annotate(total=Count('boards__columns__tasks', distinct=True), done=Count('boards__columns__tasks', filter=Q(boards__columns__status='done'), distinct=True), overdue=Count('boards__columns__tasks', filter=Q(boards__columns__tasks__due_date__lt=today, boards__columns__status__in=['backlog', 'active', 'review']), distinct=True))
    rows = []
    for project in projects:
        complete = project.total > 0 and project.done == project.total
        at_risk = project.overdue > 0 or (project.due_date and project.due_date < today and not complete)
        health = 'complete' if complete else 'at_risk' if at_risk else 'unplanned' if not project.total else 'on_track'
        rows.append({'id': project.pk, 'key': project.key, 'name': project.name, 'due_date': project.due_date.isoformat() if project.due_date else None, 'total': project.total, 'done': project.done, 'overdue': project.overdue, 'percent': round(project.done / project.total * 100) if project.total else 0, 'health': health})
    tasks = Task.objects.filter(column__board__project__archived=False)
    return {'active': len(rows), 'archived': Project.objects.filter(archived=True).count(), 'total_tasks': tasks.count(), 'overdue_tasks': sum(row['overdue'] for row in rows), 'unassigned_tasks': tasks.filter(assignee__isnull=True).exclude(column__status='done').count(), 'by_project': rows}


def overview(start, end):
    today = timezone.localdate()
    staff = list(get_user_model().objects.filter(is_active=True, role__in=STAFF_ROLES).select_related('profile', 'profile__department'))
    departments = {d.pk: {'id': d.pk, 'name': d.name, 'count': 0} for d in Department.objects.all()}
    roles = defaultdict(int)
    unassigned = 0
    for user in staff:
        roles[user.role] += 1
        profile = getattr(user, 'profile', None)
        if profile and profile.department_id in departments:
            departments[profile.department_id]['count'] += 1
        else:
            unassigned += 1
    org = Organization.objects.first() or Organization()
    events = AuditLog.objects.all()
    return {
        'as_of': today.isoformat(), 'generated_at': timezone.now(), 'timezone': settings.TIME_ZONE,
        'attendance_window': {'start': start.isoformat(), 'end': end.isoformat()},
        'headcount': {'total': len(staff), 'unassigned': unassigned, 'by_department': sorted(departments.values(), key=lambda d: (-d['count'], d['name'])), 'by_role': [{'role': role, 'count': count} for role, count in sorted(roles.items())], 'joined_this_month': sum(bool(join_date(u) and join_date(u).year == today.year and join_date(u).month == today.month and join_date(u) <= today) for u in staff)},
        'attendance': attendance_payload(staff, start, end, today, org),
        'leave': leave_payload(staff, today.year, org),
        'projects': project_payload(today), 'finance': finance_summary(), 'inventory': inventory_summary(),
        'audit': {'capture_started_at': events.order_by('timestamp', 'id').values_list('timestamp', flat=True).first(), 'last_24h': events.filter(timestamp__gte=timezone.now() - datetime.timedelta(days=1)).count(), 'recent': AuditLogSerializer(events[:5], many=True).data},
    }
