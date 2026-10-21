import datetime
from unittest.mock import patch
from django.db import DatabaseError, connection, transaction
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User
from apps.org.models import Department, EmployeeProfile, Organization
from apps.calendar_app.models import Holiday
from apps.attendance.models import AttendanceRecord


class AuditAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='auditowner', email='owner@audit.test', password='test', role='super_admin', first_name='Audit owner')
        cls.hr = User.objects.create_user(username='audithr', email='hr@audit.test', password='test', role='hr_admin')
        cls.employee = User.objects.create_user(username='auditemployee', email='staff@audit.test', password='test', role='employee')

    def test_oversight_is_super_admin_only(self):
        for user in [None, self.employee, self.hr]:
            self.client.force_authenticate(user)
            for url in ['/api/audit/events/', '/api/audit/options/', '/api/monitoring/overview/']:
                self.assertIn(self.client.get(url).status_code, [401, 403])
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get('/api/audit/events/').status_code, 200)

    def test_jwt_actor_redaction_and_request_correlation(self):
        from .models import AuditLog
        token = RefreshToken.for_user(self.owner)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        r = self.client.post('/api/org/departments/', {'name': 'Audit example', 'description': 'secret text'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        event = AuditLog.objects.filter(target_model='org.department', target_id=str(r.data['id']), action='create').latest('id')
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.actor_label, 'Audit owner')
        self.assertTrue(event.request_id)
        self.assertEqual(event.source, 'api')
        self.assertNotIn('secret text', str(event.diff))
        self.assertTrue(event.diff['description']['redacted'])
        self.assertNotIn(str(token.access_token), str(event.diff))
        self.assertEqual(r['X-Request-ID'], str(event.request_id))

    def test_read_only_api_filters_and_pagination(self):
        from .models import AuditLog
        self.client.force_authenticate(self.owner)
        r = self.client.post('/api/org/departments/', {'name': 'Filter target'}, format='json')
        result = self.client.get('/api/audit/events/?module=org&action=create&page_size=1')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data['results']), 1)
        event = result.data['results'][0]
        self.assertEqual(event['target_model'], 'org.department')
        self.assertEqual(self.client.post('/api/audit/events/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(f"/api/audit/events/{event['id']}/", {}, format='json').status_code, 405)
        self.assertEqual(self.client.delete(f"/api/audit/events/{event['id']}/").status_code, 405)
        for query in ['actor=not-an-id', 'start=invalid', 'action=unknown', 'module=unknown', 'request_id=invalid']:
            self.assertEqual(self.client.get('/api/audit/events/?' + query).status_code, 400)
        self.assertTrue(AuditLog.objects.filter(target_id=str(r.data['id'])).exists())

    def test_ordinary_save_noop_and_rollback(self):
        from .models import AuditLog
        department = Department.objects.create(name='Before')
        count = AuditLog.objects.count()
        department.save()
        self.assertEqual(AuditLog.objects.count(), count)
        try:
            with transaction.atomic():
                department.name = 'Rolled back'
                department.save()
                raise RuntimeError('abort')
        except RuntimeError:
            pass
        self.assertEqual(AuditLog.objects.count(), count)
        department.refresh_from_db()
        self.assertEqual(department.name, 'Before')

    def test_model_and_database_append_only_guards(self):
        from .models import AuditLog
        from django.core.exceptions import ValidationError
        Department.objects.create(name='Immutable test')
        event = AuditLog.objects.latest('id')
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=event.pk).update(action='delete')
        with self.assertRaises(ValidationError):
            AuditLog.objects.all().delete()
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('UPDATE audit_auditlog SET action = %s WHERE id = %s', ['delete', event.pk])
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM audit_auditlog WHERE id = %s', [event.pk])

    def test_membership_and_bulk_holidays_are_audited(self):
        from .models import AuditLog
        self.client.force_authenticate(self.owner)
        project = self.client.post('/api/pm/projects/', {'name': 'Audit workflow', 'key': 'AUDIT', 'members': [self.employee.pk]}, format='json')
        self.assertEqual(project.status_code, 201, project.data)
        memberships = AuditLog.objects.filter(target_model='pm.project', target_id=str(project.data['id']), action='membership')
        self.assertTrue(memberships.exists())
        bulk = self.client.post('/api/calendar/holidays/bulk/', [{'name': 'Audit holiday', 'date': '2031-01-02'}], format='json')
        self.assertEqual(bulk.status_code, 201, bulk.data)
        self.assertTrue(AuditLog.objects.filter(target_model='calendar_app.holiday', target_id=str(bulk.data['created'][0]['id']), action='create').exists())

    def test_failed_http_write_rolls_back_and_context_does_not_leak(self):
        from django.http import HttpResponse
        from .models import AuditLog
        from .middleware import AuditContextMiddleware
        from .context import current_context
        count = AuditLog.objects.count()
        def rejected(request):
            Department.objects.create(name='Should roll back')
            return HttpResponse(status=400)
        request = RequestFactory().post('/api/org/departments/?secret=never-record')
        request.user = self.owner
        response = AuditContextMiddleware(rejected)(request)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Department.objects.filter(name='Should roll back').exists())
        self.assertEqual(AuditLog.objects.count(), count)
        self.assertIsNone(current_context.get())
        department = Department.objects.create(name='System after request')
        event = AuditLog.objects.get(target_model='org.department', target_id=str(department.pk))
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.source, 'system')

    def test_partial_saves_redaction_and_deletion_snapshots(self):
        from .models import AuditLog
        department = Department.objects.create(name='Original', description='private before')
        department.name = 'Unsaved title'
        department.description = 'private after'
        department.save(update_fields=['description'])
        event = AuditLog.objects.filter(target_model='org.department', target_id=str(department.pk)).latest('id')
        self.assertEqual(set(event.diff), {'description'})
        self.assertTrue(event.diff['description']['redacted'])
        self.assertNotIn('private', str(event.diff))
        self.employee.set_password('secret-password')
        self.employee.save(update_fields=['password'])
        password_event = AuditLog.objects.filter(target_model='users.user', target_id=str(self.employee.pk)).latest('id')
        self.assertTrue(password_event.diff['password']['redacted'])
        self.assertNotIn(self.employee.password, str(password_event.diff))
        pk = department.pk
        department.delete()
        deletion = AuditLog.objects.get(target_model='org.department', target_id=str(pk), action='delete')
        self.assertEqual(deletion.diff['name']['before'], 'Original')

    def test_reverse_membership_removal_and_clear_are_recorded(self):
        from apps.pm.models import Project
        from .models import AuditLog
        project = Project.objects.create(name='Reverse membership', key='REVERSE', lead=self.owner)
        self.employee.work_projects.add(project)
        self.employee.work_projects.remove(project)
        project.members.add(self.employee)
        self.employee.work_projects.clear()
        events = AuditLog.objects.filter(target_model='pm.project', target_id=str(project.pk), action='membership')
        self.assertEqual(events.count(), 4)
        self.assertEqual(events.latest('id').diff['members']['after'], [])

    def test_invoice_bulk_lines_and_system_job_are_attributed(self):
        from apps.attendance.tasks import mark_absentees
        from .models import AuditLog
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/finance/invoices/', {'number': 'AUD-001', 'client_name': 'Private client', 'issue_date': '2030-06-01', 'due_date': '2030-06-30', 'items': [{'description': 'Private work', 'quantity': '2', 'unit_price': '120'}]}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        lines = AuditLog.objects.filter(target_model='finance.invoiceline', request_id=response['X-Request-ID'])
        self.assertEqual(lines.count(), 1)
        self.assertTrue(lines.get().diff['unit_price']['redacted'])
        self.assertEqual(lines.get().actor_id, self.owner.pk)
        result = mark_absentees('2030-06-03')
        jobs = AuditLog.objects.filter(target_model='attendance.attendancerecord', entry_point='attendance.mark_absentees')
        self.assertEqual(jobs.count(), result['absent'])
        self.assertTrue(all(e.source == 'system' and e.actor_id is None and e.request_id for e in jobs))
        count = jobs.count()
        mark_absentees('2030-06-03')
        self.assertEqual(jobs.count(), count)

    def test_leave_attendance_updates_are_recorded(self):
        from apps.leave.models import LeaveRequest, LeaveType
        from apps.leave.services import mark_attendance_on_leave, revert_attendance_on_leave
        from .models import AuditLog
        day = datetime.date(2030, 6, 3)
        record = AttendanceRecord.objects.create(user=self.employee, date=day, status='absent')
        leave_type = LeaveType.objects.create(name='Attendance audit', code='attendance-audit')
        request = LeaveRequest.objects.create(user=self.employee, leave_type=leave_type, start_date=day, end_date=day, days=1, reason='Private', status='approved')
        mark_attendance_on_leave(request)
        record.refresh_from_db()
        self.assertEqual(record.status, 'on_leave')
        event = AuditLog.objects.filter(target_model='attendance.attendancerecord', target_id=str(record.pk), action='update').latest('id')
        self.assertEqual(event.diff['status'], {'before': 'absent', 'after': 'on_leave'})
        request.status = 'cancelled'
        request.save()
        with patch('django.utils.timezone.localdate', return_value=day + datetime.timedelta(days=1)):
            revert_attendance_on_leave(request)
        record.refresh_from_db()
        self.assertEqual(record.status, 'absent')
        self.assertEqual(AuditLog.objects.filter(target_model='attendance.attendancerecord', target_id=str(record.pk), action='update').count(), 2)


class MonitoringTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='monitorowner', email='owner@monitor.test', password='x', role='super_admin')
        cls.emp = User.objects.create_user(username='monitoremp', email='emp@monitor.test', password='x', role='employee')
        cls.dept = Department.objects.create(name='Survey')
        EmployeeProfile.objects.filter(user=cls.emp).update(department=cls.dept, join_date=datetime.date(2030, 6, 4))
        Organization.load()

    def test_attendance_uses_join_dates_holidays_and_today_not_absent(self):
        self.client.force_authenticate(self.owner)
        Holiday.objects.create(name='Mandatory', date=datetime.date(2030, 6, 5))
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2030, 6, 4), status='late')
        with patch('django.utils.timezone.localdate', return_value=datetime.date(2030, 6, 6)):
            r = self.client.get('/api/monitoring/overview/?start=2030-06-03&end=2030-06-06')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['headcount']['total'], 2)
        days = {d['date']: d for d in r.data['attendance']['days']}
        self.assertEqual(days['2030-06-03']['absent'], 1)
        self.assertEqual(days['2030-06-04']['late'], 1)
        self.assertEqual(days['2030-06-05']['kind'], 'holiday')
        self.assertEqual(days['2030-06-05']['expected'], 0)
        self.assertEqual(days['2030-06-06']['not_checked_in'], 2)
        self.assertEqual(days['2030-06-06']['absent'], 0)

    def test_window_validation_and_reads_do_not_emit_audit(self):
        from .models import AuditLog
        self.client.force_authenticate(self.owner)
        count = AuditLog.objects.count()
        self.assertEqual(self.client.get('/api/monitoring/overview/').status_code, 200)
        self.assertEqual(AuditLog.objects.count(), count)
        for query in ['start=invalid', 'start=2025-01-01&end=2026-01-01', 'start=2026-10-17&end=2026-10-01', 'end=2099-01-01', 'end=0001-01-01']:
            self.assertEqual(self.client.get('/api/monitoring/overview/?' + query).status_code, 400)

    def test_project_health_counts_mixed_columns_and_excludes_archives(self):
        from apps.pm.models import Project, Board, Column, Task
        from .monitoring import project_payload
        today = datetime.date(2030, 6, 6)
        project = Project.objects.create(name='Mixed project', key='MIXED', lead=self.owner)
        board = Board.objects.create(project=project, name='Delivery')
        active = Column.objects.create(board=board, name='Active', status='active')
        done = Column.objects.create(board=board, name='Done', status='done')
        for column in [active, done]:
            Task.objects.create(title='Task', column=column, due_date=today - datetime.timedelta(days=1), created_by=self.owner)
        archived = Project.objects.create(name='Archived', key='ARCHIVED', lead=self.owner, archived=True)
        old_board = Board.objects.create(project=archived, name='Old')
        old_column = Column.objects.create(board=old_board, name='Old')
        Task.objects.create(title='Ignored', column=old_column, due_date=today - datetime.timedelta(days=1), created_by=self.owner)
        payload = project_payload(today)
        self.assertEqual(payload['active'], 1)
        self.assertEqual(payload['overdue_tasks'], 1)
        self.assertEqual(payload['total_tasks'], 2)
        self.assertEqual(payload['unassigned_tasks'], 1)
        self.assertEqual(payload['by_project'][0]['health'], 'at_risk')
        self.assertEqual(payload['by_project'][0]['percent'], 50)
        active.status = 'done'
        active.save()
        self.assertEqual(project_payload(today)['by_project'][0]['health'], 'complete')

    def test_leave_exposure_clamps_per_person_and_keeps_unlimited_separate(self):
        from decimal import Decimal
        from apps.leave.models import LeaveType, LeaveRequest
        from .monitoring import leave_payload
        capped = LeaveType.objects.create(name='Annual audit', code='annual-audit', annual_quota=5)
        unlimited = LeaveType.objects.create(name='Unlimited audit', code='unlimited-audit', annual_quota=0)
        LeaveRequest.objects.create(user=self.emp, leave_type=capped, start_date='2030-06-01', end_date='2030-06-30', days=7, reason='private', status='approved')
        LeaveRequest.objects.create(user=self.owner, leave_type=capped, start_date='2030-06-07', end_date='2030-06-07', days=Decimal('.5'), half_day=True, reason='private', status='pending')
        payload = leave_payload([self.owner, self.emp], 2030, Organization.load())
        self.assertEqual(Decimal(payload['remaining_paid_days']), 5)
        self.assertEqual(Decimal(payload['pending_paid_days']), Decimal('.5'))
        self.assertIsNone(next(t for t in payload['by_type'] if t['id'] == unlimited.pk)['remaining_days'])

    def test_finance_keeps_currencies_and_lifecycle_states_separate(self):
        from apps.finance.models import Expense, Payslip, Invoice, InvoiceLine
        from .monitoring import overview
        Payslip.objects.create(employee=self.emp, period='2030-06-01', basic=100, allowances=20, deductions=5, status='paid', created_by=self.owner)
        for currency in ['NPR', 'USD']:
            Expense.objects.create(employee=self.emp, description='Claim', amount=10, currency=currency, status='approved', created_by=self.owner)
        Expense.objects.create(employee=self.emp, description='Draft', amount=999, status='draft', created_by=self.owner)
        invoice = Invoice.objects.create(number='MON-1', client_name='Client', issue_date='2030-06-01', due_date='2030-06-30', currency='USD', status='issued', tax_amount=1, created_by=self.owner)
        InvoiceLine.objects.create(invoice=invoice, description='Work', quantity=2, unit_price=30)
        payload = overview(datetime.date(2030, 6, 3), datetime.date(2030, 6, 6))['finance']
        currencies = {c['currency']: c for c in payload['currencies']}
        self.assertEqual(currencies['NPR']['payroll_paid'], '115.00')
        self.assertEqual(currencies['NPR']['expenses_approved'], '10.00')
        self.assertEqual(currencies['USD']['invoice_outstanding'], '61.00')

    def test_monitoring_does_not_create_an_organization(self):
        from .models import AuditLog
        Organization.objects.all().delete()
        count = AuditLog.objects.count()
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/monitoring/overview/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Organization.objects.exists())
        self.assertEqual(AuditLog.objects.count(), count)
