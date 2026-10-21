import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.attendance.models import AttendanceRecord
from apps.leave.models import LeaveRequest, LeaveType
from apps.notices.models import Notice

from .models import Department, EmployeeProfile

User = get_user_model()
URL = '/api/dashboard/'


class DashboardTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        def mk(email, role):
            return User.objects.create_user(username=email.split('@')[0], email=email, password='x-Pass-123',
                                            role=role, first_name=email.split('@')[0].title())

        cls.hr = mk('hr@t.com', 'hr_admin')
        cls.mgr = mk('mgr@t.com', 'manager')
        cls.emp = mk('emp@t.com', 'employee')
        cls.other = mk('other@t.com', 'employee')
        cls.guest = mk('guest@t.com', 'guest')
        cls.eng = Department.objects.create(name='Engineering', manager=cls.mgr)
        cls.ops = Department.objects.create(name='Operations')
        cls.today = timezone.localdate()
        for u, d in ((cls.mgr, cls.eng), (cls.emp, cls.eng), (cls.other, cls.ops)):
            EmployeeProfile.objects.filter(user=u).update(department=d)
        # a birthday 2 days out shows in this week's celebrations
        EmployeeProfile.objects.filter(user=cls.other).update(
            date_of_birth=(cls.today + datetime.timedelta(days=2)).replace(year=1995))

        cls.annual = LeaveType.objects.create(name='Annual', code='annual', annual_quota=Decimal('18'))
        start = cls.today + datetime.timedelta(days=20)
        cls.req = LeaveRequest.objects.create(user=cls.emp, leave_type=cls.annual, start_date=start, end_date=start,
                                              days=Decimal('1'), reason='Trip')
        LeaveRequest.objects.create(user=cls.other, leave_type=cls.annual, start_date=start, end_date=start,
                                    days=Decimal('1'), reason='Trip')
        AttendanceRecord.objects.create(user=cls.emp, date=cls.today, check_in=timezone.now(), status='present')
        Notice.objects.create(title='Hello', body='b', author=cls.hr, publish_at=timezone.now())

    def get(self, user):
        self.client.force_authenticate(user)
        return self.client.get(URL)

    def test_anonymous_and_guest_blocked(self):
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.assertEqual(self.get(self.guest).status_code, 403)

    def test_employee_sees_own_sections_only(self):
        r = self.get(self.emp)
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['today']['record']['status'], 'present')
        self.assertTrue(d['today']['can_check_out'])
        self.assertEqual(d['leave']['my_pending'], 1)
        self.assertEqual(d['leave']['balances'][0]['remaining'], Decimal('18'))
        self.assertEqual(d['approvals']['count'], 0)
        self.assertEqual(d['notices']['unread'], 1)
        self.assertEqual(d['notices']['items'][0]['title'], 'Hello')
        self.assertIn('birthday', [i['kind'] for i in d['celebrations']])
        self.assertIsNone(d['team'])
        self.assertIsNone(d['org'])

    def test_manager_sees_team_approvals_and_pulse(self):
        d = self.get(self.mgr).data
        self.assertEqual(d['approvals']['count'], 1)  # emp only; 'other' is in a department mgr does not manage
        self.assertEqual(d['approvals']['items'][0]['id'], self.req.id)
        self.assertEqual(d['team']['counts']['present'], 1)
        self.assertEqual(d['team']['counts']['total'], 2)  # mgr + emp
        self.assertIsNone(d['org'])

    def test_hr_sees_org_pulse(self):
        d = self.get(self.hr).data
        self.assertEqual(d['approvals']['count'], 2)
        self.assertEqual(d['org']['pending_leave'], 2)
        self.assertEqual(d['org']['attendance']['present'], 1)
        self.assertEqual(d['org']['total_staff'], 4)
        self.assertEqual(d['org']['unassigned'], 1)  # hr has no department
        self.assertEqual({h['name']: h['count'] for h in d['org']['headcount']}, {'Engineering': 2, 'Operations': 1})
        self.assertEqual(d['team']['counts']['total'], 0)  # hr manages no department

    def test_query_count_does_not_grow_with_staff(self):
        self.client.force_authenticate(self.hr)
        self.client.get(URL)  # warm per-process caches
        with CaptureQueriesContext(connection) as before:
            self.client.get(URL)
        for i in range(5):
            u = User.objects.create_user(username=f'x{i}', email=f'x{i}@t.com', password='x-Pass-123', role='employee')
            EmployeeProfile.objects.filter(user=u).update(department=self.eng)
            AttendanceRecord.objects.create(user=u, date=self.today, check_in=timezone.now(), status='late')
        with CaptureQueriesContext(connection) as after:
            self.client.get(URL)
        self.assertEqual(len(after), len(before))


class DashboardAdditionsTests(APITestCase):
    """my_tasks, on_leave_today (team vs org scope) and team pending leave."""

    @classmethod
    def setUpTestData(cls):
        from apps.pm.models import Board, Column, Project, Task

        def mk(email, role, dept=None):
            u = User.objects.create_user(username=email.split('@')[0], email=email, password='x-Pass-123',
                                         role=role, first_name=email.split('@')[0].title())
            if dept:
                EmployeeProfile.objects.filter(user=u).update(department=dept)
            return User.objects.get(pk=u.pk)

        cls.today = timezone.localdate()
        cls.eng = Department.objects.create(name='Engineering')
        cls.ops = Department.objects.create(name='Operations')
        cls.mgr = mk('m@d.test', 'manager', cls.eng)
        cls.emp = mk('e@d.test', 'employee', cls.eng)
        cls.away_team = mk('awayteam@d.test', 'employee', cls.eng)
        cls.away_other = mk('awayother@d.test', 'employee', cls.ops)
        cls.hr = mk('h@d.test', 'hr_admin', cls.ops)
        cls.eng.manager = cls.mgr
        cls.eng.save()
        lt = LeaveType.objects.create(name='Annual', code='annual', annual_quota=Decimal('18'))
        for u in (cls.away_team, cls.away_other):
            AttendanceRecord.objects.create(user=u, date=cls.today, status='on_leave')
        future = cls.today + datetime.timedelta(days=30)
        LeaveRequest.objects.create(user=cls.emp, leave_type=lt, start_date=future, end_date=future, days=1, reason='r')
        LeaveRequest.objects.create(user=cls.away_other, leave_type=lt, start_date=future, end_date=future, days=1, reason='r')

        p = Project.objects.create(name='P', key='DSH', lead=cls.mgr)
        p.members.add(cls.emp)
        archived = Project.objects.create(name='Old', key='OLD', lead=cls.mgr, archived=True)
        archived.members.add(cls.emp)
        board = Board.objects.create(project=p, name='b')
        cols = {s: Column.objects.create(board=board, status=s, name=s) for s in ('backlog', 'done')}
        old_col = Column.objects.create(board=Board.objects.create(project=archived, name='b'), status='backlog', name='x')
        yesterday = cls.today - datetime.timedelta(days=1)
        for i in range(6):
            Task.objects.create(title=f'T{i}', column=cols['backlog'], assignee=cls.emp, created_by=cls.mgr,
                                due_date=yesterday if i < 2 else None, priority='urgent' if i == 5 else 'low')
        Task.objects.create(title='Done', column=cols['done'], assignee=cls.emp, created_by=cls.mgr, due_date=yesterday)
        Task.objects.create(title='Archived', column=old_col, assignee=cls.emp, created_by=cls.mgr)
        Task.objects.create(title='Not mine', column=cols['backlog'], assignee=cls.mgr, created_by=cls.mgr)

    def get(self, user):
        self.client.force_authenticate(user)
        return self.client.get(URL).data

    def test_my_tasks(self):
        t = self.get(self.emp)['my_tasks']
        self.assertEqual((t['open'], t['overdue'], len(t['items'])), (6, 2, 5))
        self.assertEqual([i['title'] for i in t['items'][:3]], ['T0', 'T1', 'T5'])  # overdue first, then urgent
        self.assertEqual(t['items'][0]['key'], f"DSH-{t['items'][0]['id']}")

    def test_on_leave_today_scope(self):
        self.assertIsNone(self.get(self.emp)['on_leave_today'])
        d = self.get(self.mgr)
        self.assertEqual([p['full_name'] for p in d['on_leave_today']], ['Awayteam'])
        self.assertEqual(d['team']['pending_leave'], 1)  # emp's, not the other department's
        self.assertEqual({p['full_name'] for p in self.get(self.hr)['on_leave_today']}, {'Awayteam', 'Awayother'})

    def test_nav_counts_match_dashboard(self):
        self.client.force_authenticate(self.mgr)
        self.assertEqual(self.client.get('/api/nav-counts/').data['leave_approvals'], 1)
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.get('/api/nav-counts/').data['overdue_tasks'], 2)
