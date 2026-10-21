import datetime
from decimal import Decimal

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.leave.models import LeaveRequest, LeaveType
from apps.org.models import Department, EmployeeProfile, Organization
from apps.users.models import User

from .models import Notification
from .services import push

MON = datetime.date(2030, 6, 3)


def mk(email, role, dept=None):
    u = User.objects.create_user(username=email.split('@')[0], email=email, password='x', role=role,
                                 first_name=email.split('@')[0].title())
    if dept:
        EmployeeProfile.objects.update_or_create(user=u, defaults={'department': dept})
    return User.objects.get(pk=u.pk)


class InboxApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = mk('a@n.test', 'employee')
        cls.b = mk('b@n.test', 'employee')
        cls.guest = mk('g@n.test', 'guest')
        push([cls.a], 'notice', 'For A 1')
        push([cls.a], 'notice', 'For A 2')
        push([cls.b], 'notice', 'For B')

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client

    def test_anonymous_rejected(self):
        self.assertEqual(self.client.get('/api/notifications/').status_code, 401)

    def test_list_and_count_are_own_only(self):
        r = self.as_(self.a).get('/api/notifications/')
        self.assertEqual([n['title'] for n in r.data], ['For A 2', 'For A 1'])
        self.assertEqual(self.client.get('/api/notifications/unread-count/').data, {'unread': 2})
        self.assertEqual(self.as_(self.guest).get('/api/notifications/').data, [])

    def test_mark_read_scoped_and_idempotent(self):
        b_note = Notification.objects.get(recipient=self.b)
        self.assertEqual(self.as_(self.a).post(f'/api/notifications/{b_note.pk}/read/').status_code, 404)
        b_note.refresh_from_db()
        self.assertIsNone(b_note.read_at)

        mine = Notification.objects.filter(recipient=self.a).first()
        first = self.client.post(f'/api/notifications/{mine.pk}/read/').data['read_at']
        self.assertIsNotNone(first)
        self.assertEqual(self.client.post(f'/api/notifications/{mine.pk}/read/').data['read_at'], first)
        self.assertEqual(len(self.client.get('/api/notifications/?unread=1').data), 1)

    def test_mark_all_read_only_touches_mine(self):
        self.assertEqual(self.as_(self.a).post('/api/notifications/read-all/').data, {'marked': 2})
        self.assertEqual(self.client.get('/api/notifications/unread-count/').data, {'unread': 0})
        self.assertTrue(Notification.objects.filter(recipient=self.b, read_at__isnull=True).exists())

    def test_push_skips_inactive_duplicates_and_excluded(self):
        off = mk('off@n.test', 'employee')
        off.is_active = False
        off.save()
        self.assertEqual(push([self.a, self.a, off, None, self.b], 'notice', 't', exclude=self.b), 1)

    def test_nav_counts(self):
        self.assertEqual(self.as_(self.guest).get('/api/nav-counts/').status_code, 403)
        r = self.as_(self.a).get('/api/nav-counts/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {'leave_approvals': 0, 'unread_notices': 0, 'overdue_tasks': 0, 'unread_notifications': 2,
                                  'attendance_corrections': 0})


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EventHookTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        org = Organization.load()
        org.weekend_days = [5]
        org.save()
        cls.eng = Department.objects.create(name='Engineering')
        cls.ops = Department.objects.create(name='Operations')
        cls.mgr = mk('mgr@h.test', 'manager', cls.eng)
        cls.emp = mk('emp@h.test', 'employee', cls.eng)
        cls.outsider = mk('out@h.test', 'employee', cls.ops)
        cls.hr = mk('hr@h.test', 'hr_admin', cls.ops)
        cls.hr2 = mk('hr2@h.test', 'hr_admin', cls.ops)
        cls.eng.manager = cls.mgr
        cls.eng.save()
        cls.annual = LeaveType.objects.create(name='Annual', code='annual', annual_quota=5, is_paid=True)

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client

    def inbox(self, user, kind):
        return list(Notification.objects.filter(recipient=user, kind=kind).values_list('title', flat=True))

    def test_leave_request_and_decision(self):
        r = self.as_(self.emp).post('/api/leave/requests/', {
            'leave_type': self.annual.pk, 'start_date': MON.isoformat(), 'end_date': MON.isoformat(), 'reason': 'Trip',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.inbox(self.mgr, 'leave_requested'), ['Emp requested leave'])
        self.assertEqual(self.inbox(self.hr, 'leave_requested'), [])  # the department manager decides, not HR
        self.assertEqual(Notification.objects.get(recipient=self.mgr).link, '/app/leave?tab=approvals')

        self.assertEqual(self.as_(self.mgr).post(f"/api/leave/requests/{r.data['id']}/approve/", {}, format='json').status_code, 200)
        self.assertEqual(self.inbox(self.emp, 'leave_decided'), ['Your leave request was approved'])
        self.assertEqual(self.inbox(self.outsider, 'leave_decided'), [])

    def test_leave_without_manager_goes_to_hr(self):
        r = self.as_(self.outsider).post('/api/leave/requests/', {
            'leave_type': self.annual.pk, 'start_date': MON.isoformat(), 'end_date': MON.isoformat(), 'reason': 'x',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Notification.objects.filter(kind='leave_requested').count(), 2)  # hr + hr2
        self.assertTrue(LeaveRequest.objects.filter(pk=r.data['id']).exists())

    def test_task_assignment(self):
        project = self.as_(self.mgr).post('/api/pm/projects/', {'name': 'P', 'key': 'PRJ', 'members': [self.emp.pk]}, format='json').data
        col = project['boards'][0]['columns'][0]['id']
        t = self.client.post('/api/pm/tasks/', {'title': 'Survey', 'column': col, 'assignee': self.emp.pk}, format='json')
        self.assertEqual(t.status_code, 201, t.data)
        n = Notification.objects.get(recipient=self.emp, kind='task_assigned')
        self.assertEqual((n.title, n.body, n.link), (f"Mgr assigned you PRJ-{t.data['id']}", 'Survey', f"/app/projects/{project['id']}"))
        # a non-assignment edit does not re-notify; self-assignment never notifies
        self.client.patch(f"/api/pm/tasks/{t.data['id']}/", {'title': 'Survey 2'}, format='json')
        self.client.patch(f"/api/pm/tasks/{t.data['id']}/", {'assignee': self.mgr.pk}, format='json')
        self.assertEqual(Notification.objects.filter(kind='task_assigned').count(), 1)

    def test_urgent_and_department_notices(self):
        self.as_(self.hr).post('/api/notices/', {'title': 'Fire drill', 'body': 'b', 'category': 'urgent'}, format='json')
        for u in (self.mgr, self.emp, self.outsider, self.hr2):
            self.assertEqual(self.inbox(u, 'notice'), ['Urgent: Fire drill'])
        self.assertEqual(self.inbox(self.hr, 'notice'), [])  # not the author

        r = self.client.post('/api/notices/', {'title': 'Standup moved', 'body': 'b', 'audience': 'department',
                                               'department_id': self.eng.id}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn('New notice for Engineering: Standup moved', self.inbox(self.emp, 'notice'))
        self.assertEqual(self.inbox(self.outsider, 'notice'), ['Urgent: Fire drill'])

        self.client.post('/api/notices/', {'title': 'General', 'body': 'b'}, format='json')  # org-wide, normal: board only
        self.assertEqual(Notification.objects.filter(kind='notice', title__contains='General').count(), 0)

    def test_payslip_issue_and_asset_assignment(self):
        hr = self.as_(self.hr)
        salary = hr.post('/api/finance/salaries/', {'employee': self.emp.pk, 'basic': '50000.00', 'allowances': '0.00',
                                                    'deductions': '0.00', 'effective_from': '2026-01-01'}, format='json').data
        slip = hr.post('/api/finance/payslips/generate/', {'salary': salary['id'], 'period': '2026-10-01'}, format='json').data
        self.assertEqual(self.inbox(self.emp, 'payslip_issued'), [])  # draft: nothing yet
        self.assertEqual(hr.post(f"/api/finance/payslips/{slip['id']}/issue/").status_code, 200)
        self.assertEqual(self.inbox(self.emp, 'payslip_issued'), ['Your payslip for October 2026 was issued'])

        cat = hr.post('/api/inventory/categories/', {'name': 'Laptops'}, format='json').data
        asset = hr.post('/api/inventory/assets/', {'tag': 'LT-1', 'name': 'ThinkPad', 'category': cat['id']}, format='json').data
        self.assertEqual(hr.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.emp.pk}, format='json').status_code, 201)
        self.assertEqual(self.inbox(self.emp, 'asset_assigned'), ['ThinkPad (LT-1) was assigned to you'])
        self.assertEqual(Decimal(slip['net']), Decimal('50000.00'))
