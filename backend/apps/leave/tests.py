import datetime
from decimal import Decimal

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.attendance.models import AttendanceRecord
from apps.calendar_app.models import Holiday
from apps.org.models import Department, EmployeeProfile, Organization
from apps.users.models import User
from . import services
from .models import LeaveRequest, LeaveType

D = datetime.date
MON = D(2030, 6, 3)          # Monday; Sat 2030-06-08 is the weekend
HOLIDAY = D(2030, 6, 5)      # mandatory holiday (Wednesday)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True,
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LeaveTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        org = Organization.load()
        org.weekend_days = [5]
        org.save()
        Holiday.objects.create(name='Test holiday', date=HOLIDAY)
        Holiday.objects.create(name='Optional', date=D(2030, 6, 6), is_optional=True)

        def mk(email, role, dept=None):
            u = User.objects.create_user(username=email.split('@')[0], email=email, password='x',
                                         role=role, first_name=email.split('@')[0].title())
            if dept is not ...:
                # org may auto-create the profile via a post_save signal
                EmployeeProfile.objects.update_or_create(user=u, defaults={'department': dept})
            return User.objects.get(pk=u.pk)  # drop the stale cached profile

        cls.eng = Department.objects.create(name='Engineering')
        cls.gis = Department.objects.create(name='GIS')
        cls.ops = Department.objects.create(name='Operations')
        cls.mgr = mk('mgr@t.com', 'manager', cls.eng)
        cls.gis_mgr = mk('gismgr@t.com', 'manager', cls.gis)
        cls.emp = mk('emp@t.com', 'employee', cls.eng)
        cls.emp2 = mk('emp2@t.com', 'employee', cls.eng)
        cls.maya = mk('maya@t.com', 'employee', cls.gis)
        cls.hr = mk('hr@t.com', 'hr_admin', cls.ops)
        cls.boss = mk('boss@t.com', 'super_admin', cls.ops)
        cls.guest = mk('guest@t.com', 'guest', ...)
        cls.eng.manager = cls.mgr
        cls.eng.save()
        cls.gis.manager = cls.gis_mgr
        cls.gis.save()

        cls.annual = LeaveType.objects.create(name='Annual', code='annual', annual_quota=5, is_paid=True)
        cls.unpaid = LeaveType.objects.create(name='Unpaid', code='unpaid', annual_quota=0, is_paid=False)
        cls.old = LeaveType.objects.create(name='Old', code='old', annual_quota=3, is_active=False)

    # helpers
    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client

    def create(self, user, start, end=None, lt=None, half=False, reason='Family'):
        return self.as_(user).post('/api/leave/requests/', {
            'leave_type': (lt or self.annual).pk, 'start_date': start.isoformat(),
            'end_date': (end or start).isoformat(), 'half_day': half, 'reason': reason,
        }, format='json')

    def make(self, user, start, end=None, status='pending', lt=None, half=False):
        end = end or start
        return LeaveRequest.objects.create(
            user=user, leave_type=lt or self.annual, start_date=start, end_date=end, half_day=half,
            days=services.compute_days(start, end, half), reason='r', status=status)

    # ---- day computation ----
    def test_days_skip_weekend_and_mandatory_holiday(self):
        # Mon..Sun: minus Sat (weekend) and Wed (holiday); optional holiday Thu still counts
        self.assertEqual(services.compute_days(MON, MON + datetime.timedelta(days=6)), 5)
        r = self.create(self.emp, MON, MON + datetime.timedelta(days=6), lt=self.unpaid)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['days'], 5)
        self.assertEqual(r.data['status'], 'pending')
        self.assertEqual(r.data['designated_approver']['id'], self.mgr.pk)

    def test_half_day(self):
        r = self.create(self.emp, MON, half=True)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['days'], 0.5)

    def test_half_day_rules(self):
        r = self.create(self.emp, MON, MON + datetime.timedelta(days=1), half=True)
        self.assertEqual(r.status_code, 400)
        self.assertIn('half_day', r.data)
        r = self.create(self.emp, HOLIDAY, half=True)  # not a working day
        self.assertEqual(r.status_code, 400)

    def test_no_working_days_and_bad_range(self):
        self.assertEqual(self.create(self.emp, D(2030, 6, 8)).status_code, 400)  # Saturday only
        r = self.create(self.emp, MON, MON - datetime.timedelta(days=1))
        self.assertEqual(r.status_code, 400)
        self.assertIn('end_date', r.data)

    def test_backdate_limit(self):
        old = timezone.localdate() - datetime.timedelta(days=40)
        r = self.create(self.emp, old, old + datetime.timedelta(days=3), lt=self.unpaid)
        self.assertEqual(r.status_code, 400)
        self.assertIn('start_date', r.data)

    def test_inactive_type_rejected(self):
        self.assertEqual(self.create(self.emp, MON, lt=self.old).status_code, 400)

    def test_overlap(self):
        self.make(self.emp, MON, MON + datetime.timedelta(days=2))
        r = self.create(self.emp, MON + datetime.timedelta(days=1), MON + datetime.timedelta(days=4))
        self.assertEqual(r.status_code, 400)
        self.assertIn('overlap', str(r.data))
        # rejected/cancelled requests don't block; other people don't block
        LeaveRequest.objects.update(status='rejected')
        self.assertEqual(self.create(self.emp, MON + datetime.timedelta(days=1)).status_code, 201)
        self.assertEqual(self.create(self.emp2, MON + datetime.timedelta(days=1)).status_code, 201)

    # ---- balances ----
    def test_balance_insufficient(self):
        self.make(self.emp, D(2030, 3, 4), D(2030, 3, 6), status='approved')  # 3 days used of 5
        r = self.create(self.emp, MON, MON + datetime.timedelta(days=3))     # Mon,Tue,Thu = 3 > 2
        self.assertEqual(r.status_code, 400)
        self.assertIn('Insufficient', str(r.data))
        # pending counts toward availability on create
        self.assertEqual(self.create(self.emp, MON, MON + datetime.timedelta(days=1)).status_code, 201)
        self.assertEqual(self.create(self.emp, D(2030, 7, 1)).status_code, 400)
        # unpaid types are never limited
        self.assertEqual(self.create(self.emp, D(2030, 7, 1), D(2030, 7, 12), lt=self.unpaid).status_code, 201)

    def test_approve_rechecks_balance(self):
        self.make(self.emp, D(2030, 3, 4), D(2030, 3, 7), status='approved')  # 4 used
        req = self.make(self.emp, MON, MON + datetime.timedelta(days=1))     # 2 pending
        r = self.as_(self.mgr).post(f'/api/leave/requests/{req.pk}/approve/')
        self.assertEqual(r.status_code, 400)
        req.refresh_from_db()
        self.assertEqual(req.status, 'pending')

    def test_balances_cross_year(self):
        req = self.make(self.emp, D(2030, 12, 30), D(2031, 1, 2), status='approved')
        self.assertEqual(req.days, 4)
        self.make(self.emp, D(2031, 2, 3), status='pending')
        r = self.as_(self.emp).get('/api/leave/balances/?year=2030')
        row = next(b for b in r.data['balances'] if b['leave_type']['code'] == 'annual')
        self.assertEqual((row['quota'], row['used'], row['pending'], row['remaining']), (5, 2, 0, 3))
        r = self.as_(self.emp).get('/api/leave/balances/?year=2031')
        row = next(b for b in r.data['balances'] if b['leave_type']['code'] == 'annual')
        self.assertEqual((row['used'], row['pending'], row['remaining']), (2, 1, 3))
        unpaid = next(b for b in r.data['balances'] if b['leave_type']['code'] == 'unpaid')
        self.assertIsNone(unpaid['remaining'])
        self.assertNotIn('old', [b['leave_type']['code'] for b in r.data['balances']])

    def test_cross_year_balance_check_per_year(self):
        self.make(self.emp, D(2031, 1, 6), D(2031, 1, 9), status='approved')  # 4 used in 2031
        r = self.create(self.emp, D(2030, 12, 30), D(2031, 1, 2))           # needs 2 in 2031, 1 left
        self.assertEqual(r.status_code, 400)
        self.assertIn('2031', str(r.data))

    def test_balances_other_user_permissions(self):
        self.assertEqual(self.as_(self.mgr).get(f'/api/leave/balances/?user={self.emp.pk}').status_code, 200)
        self.assertEqual(self.as_(self.hr).get(f'/api/leave/balances/?user={self.maya.pk}').status_code, 200)
        self.assertEqual(self.as_(self.gis_mgr).get(f'/api/leave/balances/?user={self.emp.pk}').status_code, 403)
        self.assertEqual(self.as_(self.emp2).get(f'/api/leave/balances/?user={self.emp.pk}').status_code, 403)
        self.assertEqual(self.as_(self.guest).get('/api/leave/balances/').status_code, 403)

    # ---- approval eligibility ----
    def test_manager_approves_team_member(self):
        req = self.make(self.emp, MON, MON + datetime.timedelta(days=1))
        AttendanceRecord.objects.create(user=self.emp, date=MON, status='absent')
        AttendanceRecord.objects.create(user=self.emp, date=MON + datetime.timedelta(days=1), status='present')
        r = self.as_(self.mgr).post(f'/api/leave/requests/{req.pk}/approve/', {'decision_note': 'Enjoy'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'approved')
        self.assertEqual(r.data['approver']['id'], self.mgr.pk)
        self.assertIsNotNone(r.data['decided_at'])
        self.assertEqual(AttendanceRecord.objects.get(user=self.emp, date=MON).status, 'on_leave')
        self.assertEqual(AttendanceRecord.objects.get(user=self.emp, date=MON + datetime.timedelta(days=1)).status, 'present')
        # already decided
        self.assertEqual(self.as_(self.hr).post(f'/api/leave/requests/{req.pk}/reject/').status_code, 400)

    def test_manager_of_other_department_forbidden(self):
        req = self.make(self.emp, MON)
        self.assertEqual(self.as_(self.gis_mgr).post(f'/api/leave/requests/{req.pk}/approve/').status_code, 403)
        self.assertEqual(self.as_(self.emp2).post(f'/api/leave/requests/{req.pk}/approve/').status_code, 403)

    def test_self_approve_forbidden(self):
        for user in (self.mgr, self.hr, self.boss):
            req = self.make(user, MON)
            self.assertEqual(self.as_(user).post(f'/api/leave/requests/{req.pk}/approve/').status_code, 403)
            req.delete()

    def test_hr_can_approve_managers_request(self):
        req = self.make(self.mgr, MON)
        self.assertEqual(self.as_(self.emp).post(f'/api/leave/requests/{req.pk}/approve/').status_code, 403)
        r = self.as_(self.hr).post(f'/api/leave/requests/{req.pk}/approve/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'approved')

    def test_hr_request_needs_admin(self):
        req = self.make(self.hr, MON)
        self.assertEqual(self.as_(self.hr).post(f'/api/leave/requests/{req.pk}/reject/').status_code, 403)
        r = self.as_(self.boss).post(f'/api/leave/requests/{req.pk}/reject/', {'decision_note': 'Busy week'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'rejected')
        self.assertEqual(r.data['decision_note'], 'Busy week')

    def test_approvals_list(self):
        a = self.make(self.emp, MON)
        b = self.make(self.maya, MON)
        c = self.make(self.mgr, MON)
        self.make(self.emp2, MON, status='approved')
        ids = lambda u: {x['id'] for x in self.as_(u).get('/api/leave/approvals/').data}
        self.assertEqual(ids(self.mgr), {a.pk})
        self.assertEqual(ids(self.gis_mgr), {b.pk})
        self.assertEqual(ids(self.hr), {a.pk, b.pk, c.pk})
        self.assertEqual(ids(self.emp), set())
        self.assertTrue(self.as_(self.mgr).get('/api/leave/approvals/').data[0]['can_decide'])

    # ---- cancel ----
    def test_cancel_rules(self):
        today = timezone.localdate()
        pending = self.make(self.emp, MON)
        self.assertEqual(self.as_(self.emp2).post(f'/api/leave/requests/{pending.pk}/cancel/').status_code, 403)
        self.assertEqual(self.as_(self.mgr).post(f'/api/leave/requests/{pending.pk}/cancel/').status_code, 403)
        r = self.as_(self.emp).post(f'/api/leave/requests/{pending.pk}/cancel/')
        self.assertEqual((r.status_code, r.data['status']), (200, 'cancelled'))
        self.assertEqual(self.as_(self.emp).post(f'/api/leave/requests/{pending.pk}/cancel/').status_code, 400)

        future = self.make(self.emp, D(2030, 7, 1), status='approved')
        self.assertEqual(self.as_(self.emp).post(f'/api/leave/requests/{future.pk}/cancel/').status_code, 200)

        started = self.make(self.emp, today - datetime.timedelta(days=1), today + datetime.timedelta(days=1),
                            status='approved', lt=self.unpaid)
        self.assertEqual(self.as_(self.emp).post(f'/api/leave/requests/{started.pk}/cancel/').status_code, 400)
        self.assertEqual(self.as_(self.hr).post(f'/api/leave/requests/{started.pk}/cancel/').status_code, 200)

    # ---- list / retrieve scoping ----
    def test_list_scopes(self):
        mine = self.make(self.emp, MON)
        team = self.make(self.emp2, MON)
        other = self.make(self.maya, MON)
        ids = lambda u, q='': {x['id'] for x in self.as_(u).get(f'/api/leave/requests/?year=2030{q}').data}
        self.assertEqual(ids(self.emp), {mine.pk})
        self.assertEqual(ids(self.mgr, '&scope=team'), {mine.pk, team.pk})
        self.assertEqual(ids(self.hr, '&scope=team'), {mine.pk, team.pk, other.pk})
        self.assertEqual(ids(self.hr, '&scope=team&status=approved'), set())
        self.assertEqual(ids(self.emp, '&year=2029'), set())
        self.assertEqual(self.as_(self.emp).get('/api/leave/requests/?scope=team').status_code, 403)
        self.assertEqual(self.as_(self.emp).get('/api/leave/requests/?status=bogus').status_code, 400)
        # retrieve: owner, manager of owner, HR; not peers or other managers
        self.assertEqual(self.as_(self.emp).get(f'/api/leave/requests/{mine.pk}/').status_code, 200)
        self.assertEqual(self.as_(self.mgr).get(f'/api/leave/requests/{mine.pk}/').status_code, 200)
        self.assertEqual(self.as_(self.hr).get(f'/api/leave/requests/{mine.pk}/').status_code, 200)
        self.assertEqual(self.as_(self.emp2).get(f'/api/leave/requests/{mine.pk}/').status_code, 404)
        self.assertEqual(self.as_(self.gis_mgr).get(f'/api/leave/requests/{mine.pk}/').status_code, 404)

    def test_guest_blocked(self):
        self.assertEqual(self.create(self.guest, MON).status_code, 403)
        self.assertEqual(self.as_(self.guest).get('/api/leave/types/').status_code, 403)

    # ---- calendar ----
    def test_calendar_visibility(self):
        self.make(self.emp, MON, status='approved')
        self.make(self.maya, MON, status='approved')
        self.make(self.emp2, MON, status='pending')
        url = '/api/leave/calendar/?start=2030-06-01&end=2030-06-30'
        names = lambda u: sorted(x['user']['full_name'] for x in self.as_(u).get(url).data)
        self.assertEqual(names(self.emp2), ['Emp'])
        self.assertEqual(names(self.gis_mgr), ['Maya'])
        self.assertEqual(names(self.hr), ['Emp', 'Maya'])
        row = self.as_(self.emp2).get(url).data[0]
        self.assertEqual(set(row), {'id', 'user', 'leave_type', 'start_date', 'end_date', 'half_day', 'days'})
        self.assertEqual(self.as_(self.emp).get('/api/leave/calendar/?start=2030-06-01').status_code, 400)

    # ---- types ----
    def test_types(self):
        codes = lambda u: {t['code'] for t in self.as_(u).get('/api/leave/types/').data}
        self.assertEqual(codes(self.emp), {'annual', 'unpaid'})
        self.assertEqual(codes(self.hr), {'annual', 'unpaid', 'old'})
        body = {'name': 'Study', 'code': 'study', 'annual_quota': 2, 'is_paid': True, 'color': '#123456'}
        self.assertEqual(self.as_(self.mgr).post('/api/leave/types/', body, format='json').status_code, 403)
        r = self.as_(self.hr).post('/api/leave/types/', body, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.as_(self.hr).delete(f"/api/leave/types/{r.data['id']}/").status_code, 204)
        # in use -> deactivated instead
        self.make(self.emp, MON)
        r = self.as_(self.hr).delete(f'/api/leave/types/{self.annual.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['is_active'])
        self.assertTrue(LeaveType.objects.filter(pk=self.annual.pk).exists())

    # ---- email ----
    def test_emails_on_create_and_decision(self):
        r = self.create(self.emp, MON)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.mgr.email])
        self.as_(self.mgr).post(f"/api/leave/requests/{r.data['id']}/approve/")
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [self.emp.email])
        self.assertIn('approved', mail.outbox[1].subject)

    # ---- review fixes ----
    def test_year_out_of_range_is_400(self):
        for url in ('/api/leave/requests/', '/api/leave/balances/'):
            for y in ('99999', '-5', '0'):
                r = self.as_(self.emp).get(f'{url}?year={y}')
                self.assertEqual(r.status_code, 400, (url, y))
                self.assertIn('year', r.data)

    def test_span_capped_at_one_year(self):
        r = self.create(self.emp, MON, D(2031, 6, 10), lt=self.unpaid)
        self.assertEqual(r.status_code, 400)
        self.assertIn('end_date', r.data)
        self.assertEqual(self.create(self.emp, MON, D(2031, 6, 3), lt=self.unpaid).status_code, 201)  # 365 days ok

    def test_color_must_be_hex(self):
        body = {'name': 'Study', 'code': 'study', 'annual_quota': 2, 'is_paid': True}
        for bad in ('#zzzzzz', '#;}a{b}'):
            r = self.as_(self.hr).post('/api/leave/types/', {**body, 'color': bad}, format='json')
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn('color', r.data)

    def test_reject_requires_note(self):
        req = self.make(self.emp, MON)
        for data in ({}, {'decision_note': '   '}):
            r = self.as_(self.mgr).post(f'/api/leave/requests/{req.pk}/reject/', data, format='json')
            self.assertEqual(r.status_code, 400)
            self.assertIn('decision_note', r.data)
        req.refresh_from_db()
        self.assertEqual(req.status, 'pending')
        # outsiders still get 403, not a validation hint
        self.assertEqual(self.as_(self.gis_mgr).post(f'/api/leave/requests/{req.pk}/reject/').status_code, 403)
        # approve still allows an empty note
        self.assertEqual(self.as_(self.mgr).post(f'/api/leave/requests/{req.pk}/approve/').status_code, 200)

    def test_cancel_approved_reverts_attendance(self):
        today = timezone.localdate()
        day = datetime.timedelta(days=1)
        req = self.make(self.emp, today - 2 * day, today + day, status='approved', lt=self.unpaid)
        A = AttendanceRecord
        A.objects.create(user=self.emp, date=today - 2 * day, status='on_leave')
        A.objects.create(user=self.emp, date=today - day, status='present', check_in=timezone.now())
        A.objects.create(user=self.emp, date=today, status='on_leave')
        A.objects.create(user=self.maya, date=today - 2 * day, status='on_leave')
        r = self.as_(self.hr).post(f'/api/leave/requests/{req.pk}/cancel/')
        self.assertEqual((r.status_code, r.data['status']), (200, 'cancelled'))
        self.assertEqual(A.objects.get(user=self.emp, date=today - 2 * day).status, 'absent')
        self.assertEqual(A.objects.get(user=self.emp, date=today - day).status, 'present')
        self.assertFalse(A.objects.filter(user=self.emp, date=today).exists())
        self.assertEqual(A.objects.get(user=self.maya).status, 'on_leave')

    def test_manager_request_emails_hr(self):
        r = self.create(self.mgr, MON)
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data['designated_approver'])
        self.assertEqual(sorted(mail.outbox[0].to), sorted([self.hr.email, self.boss.email]))
