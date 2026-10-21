import csv
import datetime
import io
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, APITestCase

from apps.calendar_app.models import Holiday
from apps.leave.models import LeaveRequest, LeaveType
from apps.org.models import Department, EmployeeProfile, Organization

from . import services as svc
from .models import AttendanceRecord
from .tasks import mark_absentees

User = get_user_model()
NPT = datetime.timezone(datetime.timedelta(hours=5, minutes=45))
# 2026-10-14 is a Wednesday; Saturday (5) is the weekend.
WED = datetime.date(2026, 10, 14)
SAT = datetime.date(2026, 10, 17)


def at(day, h, m, s=0):
    return datetime.datetime(day.year, day.month, day.day, h, m, s, tzinfo=NPT)


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        org = Organization.load()
        org.work_start, org.late_grace_minutes, org.weekend_days = datetime.time(10, 0), 15, [5]
        org.save()

        def mk(email, role, dept=None, join=None):
            u = User.objects.create_user(username=email.split('@')[0], email=email, password='pw', role=role,
                                         first_name=email.split('@')[0].title())
            EmployeeProfile.objects.update_or_create(user=u, defaults={'department': dept, 'join_date': join})
            return u

        cls.eng = Department.objects.create(name='Engineering')
        cls.gis = Department.objects.create(name='GIS')
        cls.mgr = mk('mgr@t.com', 'manager', cls.eng)
        cls.eng.manager = cls.mgr
        cls.eng.save()
        cls.emp = mk('emp@t.com', 'employee', cls.eng)
        cls.gis_mgr = mk('gmgr@t.com', 'manager', cls.gis)
        cls.gis.manager = cls.gis_mgr
        cls.gis.save()
        cls.maya = mk('maya@t.com', 'employee', cls.gis)
        cls.hr = mk('hr@t.com', 'hr_admin')
        cls.guest = User.objects.create_user(username='g', email='g@t.com', password='pw', role='guest')
        cls.lt = LeaveType.objects.create(name='Sick', code='sick', annual_quota=12)

    def login(self, user):
        self.client.force_authenticate(user)

    def leave(self, user, start, end, status='approved', half_day=False):
        return LeaveRequest.objects.create(user=user, leave_type=self.lt, start_date=start, end_date=end,
                                           reason='x', status=status, half_day=half_day)

    def now(self, dt):
        return mock.patch('django.utils.timezone.now', return_value=dt)


class CheckInTests(Base):
    def test_grace_boundary_exact_is_present(self):
        self.login(self.emp)
        with self.now(at(WED, 10, 15)):
            r = self.client.post('/api/attendance/check-in/', {'work_mode': 'remote'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['status'], 'present')
        self.assertEqual(r.data['work_mode'], 'remote')
        self.assertEqual(r.data['date'], '2026-10-14')

    def test_grace_plus_one_minute_is_late(self):
        self.login(self.emp)
        with self.now(at(WED, 10, 16)):
            r = self.client.post('/api/attendance/check-in/')
        self.assertEqual(r.data['status'], 'late')

    def test_non_working_day_is_present_even_if_late(self):
        self.login(self.emp)
        with self.now(at(SAT, 14, 0)):
            r = self.client.post('/api/attendance/check-in/')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['status'], 'present')

    def test_records_ip_from_forwarded_for(self):
        self.login(self.emp)
        with self.now(at(WED, 9, 0)):
            r = self.client.post('/api/attendance/check-in/', HTTP_X_FORWARDED_FOR='49.244.1.5, 10.0.0.1')
        self.assertEqual(r.data['check_in_ip'], '49.244.1.5')

    def test_double_check_in_rejected(self):
        self.login(self.emp)
        with self.now(at(WED, 9, 0)):
            self.client.post('/api/attendance/check-in/')
            r = self.client.post('/api/attendance/check-in/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('already checked in', r.data['detail'])
        self.assertEqual(AttendanceRecord.objects.filter(user=self.emp).count(), 1)

    def test_approved_leave_blocks_check_in(self):
        self.leave(self.emp, WED, WED)
        self.login(self.emp)
        with self.now(at(WED, 9, 0)):
            r = self.client.post('/api/attendance/check-in/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('approved', r.data['detail'])
        self.assertFalse(AttendanceRecord.objects.filter(user=self.emp).exists())

    def test_pending_or_half_day_leave_does_not_block(self):
        self.leave(self.emp, WED, WED, status='pending')
        self.leave(self.maya, WED, WED, half_day=True)
        with self.now(at(WED, 9, 0)):
            self.login(self.emp)
            self.assertEqual(self.client.post('/api/attendance/check-in/').status_code, 201)
            self.login(self.maya)
            self.assertEqual(self.client.post('/api/attendance/check-in/').status_code, 201)

    def test_guest_forbidden(self):
        self.login(self.guest)
        self.assertEqual(self.client.post('/api/attendance/check-in/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/attendance/today/').status_code, 401)


class CheckOutTests(Base):
    def test_check_out_without_check_in(self):
        self.login(self.emp)
        with self.now(at(WED, 17, 0)):
            r = self.client.post('/api/attendance/check-out/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('not checked in', r.data['detail'])

    def test_check_out_flow_and_double_check_out(self):
        self.login(self.emp)
        with self.now(at(WED, 9, 30)):
            self.client.post('/api/attendance/check-in/')
        with self.now(at(WED, 17, 45)):
            r = self.client.post('/api/attendance/check-out/', {'note': 'done'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data['worked_minutes'], 495)
            self.assertEqual(r.data['note'], 'done')
            r = self.client.post('/api/attendance/check-out/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('already checked out', r.data['detail'])


class TodayAndMeTests(Base):
    def test_today_payload(self):
        Holiday.objects.create(name='Dashain', date=WED)
        self.login(self.emp)
        with self.now(at(WED, 8, 0)):
            r = self.client.get('/api/attendance/today/')
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertIsNone(d['record'])
        self.assertFalse(d['is_working_day'])
        self.assertEqual(d['day_kind'], 'holiday')
        self.assertEqual(d['holiday_name'], 'Dashain')
        self.assertEqual(d['policy']['late_after'], '10:15')
        self.assertTrue(d['can_check_in'])
        self.assertFalse(d['can_check_out'])
        self.assertFalse(d['on_leave'])

    def test_me_month_summary(self):
        # Oct 2026: 31 days, 5 Saturdays -> 26 working days; plus one holiday -> 25.
        Holiday.objects.create(name='H', date=datetime.date(2026, 10, 1))
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 5), status='present',
                                        check_in=at(datetime.date(2026, 10, 5), 9, 0),
                                        check_out=at(datetime.date(2026, 10, 5), 17, 0))
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 6), status='late')
        self.leave(self.emp, datetime.date(2026, 10, 7), datetime.date(2026, 10, 7))
        AttendanceRecord.objects.create(user=self.maya, date=datetime.date(2026, 10, 5), status='present')
        self.login(self.emp)
        with self.now(at(datetime.date(2026, 10, 8), 9, 0)):
            r = self.client.get('/api/attendance/me/?month=2026-10')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['records']), 2)
        s = r.data['summary']
        self.assertEqual(s['working_days_in_month'], 25)
        self.assertEqual((s['present'], s['late'], s['on_leave']), (1, 1, 1))
        # Expected: 2,4,5,6 (7 is leave; today the 8th has no check-in yet so it is not counted).
        self.assertEqual(s['absent'], 2)
        self.assertEqual(s['working_days_elapsed'], 4)
        self.assertEqual(s['attendance_rate'], 50.0)
        self.assertEqual(s['worked_minutes_total'], 480)
        by_day = {d['date']: d for d in r.data['days']}
        self.assertEqual(len(r.data['days']), 31)
        self.assertEqual(by_day[datetime.date(2026, 10, 1)]['kind'], 'holiday')
        self.assertEqual(by_day[datetime.date(2026, 10, 7)]['status'], 'on_leave')  # leave, no stored record
        self.assertEqual(by_day[datetime.date(2026, 10, 2)]['status'], 'absent')
        self.assertEqual(by_day[datetime.date(2026, 10, 8)]['status'], 'not_checked_in')
        # Checking in today brings it into the denominator and the numerator.
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 8), status='present')
        with self.now(at(datetime.date(2026, 10, 8), 9, 5)):
            s = self.client.get('/api/attendance/me/?month=2026-10').data['summary']
        self.assertEqual((s['working_days_elapsed'], s['attendance_rate']), (5, 60.0))

    def test_leave_spanning_weekend_and_holiday(self):
        fri, sat, sun = datetime.date(2026, 10, 16), datetime.date(2026, 10, 17), datetime.date(2026, 10, 18)
        Holiday.objects.create(name='H', date=sun)
        self.leave(self.emp, fri, sun)
        with self.now(at(datetime.date(2026, 10, 20), 9, 0)):
            self.login(self.emp)
            me = self.client.get('/api/attendance/me/?month=2026-10').data
            self.login(self.hr)
            reg = self.client.get('/api/attendance/register/?month=2026-10').data
        by_day = {d['date']: d['status'] for d in me['days']}
        self.assertEqual([by_day[fri], by_day[sat], by_day[sun]], ['on_leave', 'weekend', 'holiday'])
        self.assertEqual(me['summary']['on_leave'], 1)
        row = next(r for r in reg['rows'] if r['user']['email'] == 'emp@t.com')
        self.assertEqual(row['cells'][15:18], ['on_leave', 'weekend', 'holiday'])
        self.assertEqual(row['totals']['on_leave'], 1)

    def test_me_query_count_constant(self):
        self.login(self.emp)
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 1), status='present')
        with self.now(at(datetime.date(2026, 10, 20), 9, 0)), CaptureQueriesContext(connection) as one:
            self.client.get('/api/attendance/me/?month=2026-10')
        for day in range(2, 10):
            AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, day), status='present')
        with self.now(at(datetime.date(2026, 10, 20), 9, 0)), CaptureQueriesContext(connection) as many:
            r = self.client.get('/api/attendance/me/?month=2026-10')
        self.assertEqual(len(r.data['records']), 9)
        self.assertEqual(len(many), len(one))

    def test_me_bad_month(self):
        self.login(self.emp)
        r = self.client.get('/api/attendance/me/?month=2026-13')
        self.assertEqual(r.status_code, 400)
        self.assertIn('month', r.data)
        for bad in ('9999-12', '0000-01', 'abc'):
            self.assertEqual(self.client.get(f'/api/attendance/me/?month={bad}').status_code, 400, bad)


class MarkAbsenteesTests(Base):
    def test_marks_absent_and_leave_idempotently(self):
        self.leave(self.maya, WED, WED)
        AttendanceRecord.objects.create(user=self.emp, date=WED, status='present')
        res = mark_absentees('2026-10-14')
        self.assertEqual(res['on_leave'], 1)
        recs = dict(AttendanceRecord.objects.filter(date=WED).values_list('user__email', 'status'))
        self.assertEqual(recs['emp@t.com'], 'present')  # untouched
        self.assertEqual(recs['maya@t.com'], 'on_leave')
        self.assertEqual(recs['mgr@t.com'], 'absent')
        self.assertNotIn('g@t.com', recs)  # guests are not staff
        count = AttendanceRecord.objects.count()
        self.assertEqual(mark_absentees('2026-10-14')['absent'], 0)
        self.assertEqual(AttendanceRecord.objects.count(), count)

    def test_skips_weekend_and_holiday(self):
        self.assertIn('skipped', mark_absentees(SAT.isoformat()))
        Holiday.objects.create(name='Dashain', date=WED)
        self.assertIn('skipped', mark_absentees(WED.isoformat()))
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_optional_holiday_is_working(self):
        Holiday.objects.create(name='Opt', date=WED, is_optional=True)
        mark_absentees(WED.isoformat())
        self.assertTrue(AttendanceRecord.objects.filter(date=WED).exists())

    def test_skips_users_not_yet_joined(self):
        self.maya.profile.join_date = WED + datetime.timedelta(days=1)
        self.maya.profile.save()
        mark_absentees(WED.isoformat())
        self.assertFalse(AttendanceRecord.objects.filter(user=self.maya).exists())
        self.assertTrue(AttendanceRecord.objects.filter(user=self.emp).exists())

    def test_defaults_to_local_today(self):
        with self.now(at(WED, 23, 30)):
            self.assertEqual(mark_absentees()['date'], '2026-10-14')


class TeamTests(Base):
    def test_employee_forbidden(self):
        self.login(self.emp)
        self.assertEqual(self.client.get('/api/attendance/team/').status_code, 403)
        self.assertEqual(self.client.get('/api/attendance/register/').status_code, 403)

    def test_manager_sees_only_own_team(self):
        AttendanceRecord.objects.create(user=self.emp, date=WED, status='late', check_in=at(WED, 10, 30))
        self.leave(self.mgr, WED, WED)
        self.login(self.mgr)
        with self.now(at(WED, 11, 0)):
            r = self.client.get('/api/attendance/team/')
            # Asking for another department yields nobody, not their data.
            other = self.client.get(f'/api/attendance/team/?department={self.gis.id}')
        self.assertEqual(r.status_code, 200)
        by = {m['user']['email']: m['status'] for m in r.data['members']}
        self.assertEqual(by, {'emp@t.com': 'late', 'mgr@t.com': 'on_leave'})
        self.assertEqual(r.data['counts'], {'late': 1, 'on_leave': 1})
        self.assertEqual(other.data['members'], [])

    def test_hr_sees_everyone_and_filters(self):
        self.login(self.hr)
        with self.now(at(WED, 11, 0)):
            r = self.client.get('/api/attendance/team/?date=2026-10-14')
            g = self.client.get(f'/api/attendance/team/?date=2026-10-14&department={self.gis.id}')
        emails = {m['user']['email'] for m in r.data['members']}
        self.assertEqual(emails, {'mgr@t.com', 'emp@t.com', 'gmgr@t.com', 'maya@t.com', 'hr@t.com'})
        self.assertEqual({m['status'] for m in r.data['members']}, {'not_checked_in'})
        self.assertEqual({m['user']['email'] for m in g.data['members']}, {'gmgr@t.com', 'maya@t.com'})

    def test_team_weekend_and_past_absent(self):
        self.login(self.hr)
        with self.now(at(datetime.date(2026, 10, 20), 9, 0)):
            sat = self.client.get('/api/attendance/team/?date=2026-10-17')
            wed = self.client.get('/api/attendance/team/?date=2026-10-14')
        self.assertEqual(sat.data['day_kind'], 'weekend')
        self.assertEqual({m['status'] for m in sat.data['members']}, {'weekend'})
        self.assertEqual({m['status'] for m in wed.data['members']}, {'absent'})


class RegisterTests(Base):
    def setUp(self):
        AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 5), status='present',
                                        check_in=at(datetime.date(2026, 10, 5), 9, 0),
                                        check_out=at(datetime.date(2026, 10, 5), 18, 0))
        AttendanceRecord.objects.create(user=self.maya, date=datetime.date(2026, 10, 5), status='late')

    def test_json_matrix_scoped_for_manager(self):
        self.login(self.mgr)
        with self.now(at(datetime.date(2026, 10, 6), 9, 0)):
            r = self.client.get('/api/attendance/register/?month=2026-10')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['days']), 31)
        self.assertEqual({row['user']['email'] for row in r.data['rows']}, {'mgr@t.com', 'emp@t.com'})
        emp = next(row for row in r.data['rows'] if row['user']['email'] == 'emp@t.com')
        self.assertEqual(len(emp['cells']), 31)
        self.assertEqual(emp['cells'][4], 'present')     # Oct 5
        self.assertEqual(emp['cells'][2], 'weekend')     # Oct 3 is Saturday
        self.assertEqual(emp['cells'][5], 'not_checked_in')  # today
        self.assertIsNone(emp['cells'][6])               # future
        self.assertEqual(emp['totals']['worked_minutes'], 540)

    def test_csv_export(self):
        self.login(self.hr)
        with self.now(at(datetime.date(2026, 10, 6), 9, 0)):
            r = self.client.get('/api/attendance/register/?month=2026-10&format=csv')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/csv'))
        self.assertIn('attendance-register-2026-10.csv', r['Content-Disposition'])
        lines = r.content.decode().splitlines()
        self.assertTrue(lines[0].startswith('Employee,Email,Department,01,02'))
        maya = next(line for line in lines if 'maya@t.com' in line).split(',')
        self.assertEqual(maya[3 + 4], 'L')
        self.assertEqual(maya[3 + 2], 'W')

    def test_csv_neutralises_formulas(self):
        self.emp.first_name = '=1+1'
        self.emp.save()
        self.login(self.hr)
        with self.now(at(datetime.date(2026, 10, 6), 9, 0)):
            r = self.client.get('/api/attendance/register/?month=2026-10&format=csv')
        row = next(row for row in csv.reader(io.StringIO(r.content.decode())) if 'emp@t.com' in row)
        self.assertTrue(row[0].startswith("'=1+1"), row[0])

    def test_csv_forbidden_for_employee(self):
        self.login(self.emp)
        self.assertEqual(self.client.get('/api/attendance/register/?format=csv').status_code, 403)


class HRCorrectionTests(Base):
    def test_employee_and_manager_cannot_edit(self):
        rec = AttendanceRecord.objects.create(user=self.emp, date=WED, status='late')
        for u in (self.emp, self.mgr):
            self.login(u)
            self.assertEqual(self.client.patch(f'/api/attendance/records/{rec.id}/', {'status': 'present'}).status_code, 403)
            self.assertEqual(self.client.get('/api/attendance/records/').status_code, 403)

    def test_hr_patch_and_create(self):
        rec = AttendanceRecord.objects.create(user=self.emp, date=WED, status='late', check_in=at(WED, 10, 40))
        self.login(self.hr)
        r = self.client.patch(f'/api/attendance/records/{rec.id}/',
                              {'status': 'present', 'note': 'Bus strike', 'check_out': at(WED, 18, 0).isoformat()})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['status'], r.data['worked_minutes']), ('present', 440))
        r = self.client.post('/api/attendance/records/', {
            'user': self.maya.id, 'date': '2026-10-13', 'status': 'present',
            'check_in': at(datetime.date(2026, 10, 13), 9, 0).isoformat()})
        self.assertEqual(r.status_code, 201, r.data)
        r = self.client.get('/api/attendance/records/?month=2026-10&user=%d' % self.maya.id)
        self.assertEqual(len(r.data), 1)

    def test_hr_validation(self):
        AttendanceRecord.objects.create(user=self.emp, date=WED)
        self.login(self.hr)
        dup = self.client.post('/api/attendance/records/', {'user': self.emp.id, 'date': '2026-10-14'})
        self.assertEqual(dup.status_code, 400)
        self.assertIn('already has a record', str(dup.data['date']))
        wrong_day = self.client.post('/api/attendance/records/', {
            'user': self.maya.id, 'date': '2026-10-14', 'check_in': at(WED + datetime.timedelta(days=1), 9, 0).isoformat()})
        self.assertEqual(wrong_day.status_code, 400)
        self.assertIn('check_in', wrong_day.data)
        backwards = self.client.post('/api/attendance/records/', {
            'user': self.maya.id, 'date': '2026-10-14',
            'check_in': at(WED, 10, 0).isoformat(), 'check_out': at(WED, 9, 0).isoformat()})
        self.assertIn('check_out', backwards.data)


    def test_hr_cannot_self_edit_or_future_date(self):
        own = AttendanceRecord.objects.create(user=self.hr, date=WED, status='late')
        other = AttendanceRecord.objects.create(user=self.emp, date=datetime.date(2026, 10, 13), status='late')
        self.login(self.hr)
        with self.now(at(WED, 12, 0)):
            r = self.client.patch(f'/api/attendance/records/{own.id}/', {'status': 'present'})
            self.assertEqual(r.status_code, 403)
            r = self.client.post('/api/attendance/records/', {'user': self.hr.id, 'date': '2026-10-13', 'status': 'present'})
            self.assertEqual(r.status_code, 403)
            # Re-assigning someone else's record to yourself is a self-edit too.
            r = self.client.patch(f'/api/attendance/records/{other.id}/', {'user': self.hr.id})
            self.assertEqual(r.status_code, 403)
            r = self.client.post('/api/attendance/records/', {'user': self.emp.id, 'date': '2026-10-15', 'status': 'present'})
            self.assertEqual(r.status_code, 400)
            self.assertIn('future', str(r.data['date']))
        own.refresh_from_db()
        self.assertEqual(own.status, 'late')

    def test_super_admin_may_self_edit(self):
        boss = User.objects.create_user(username='boss', email='boss@t.com', password='pw', role='super_admin')
        rec = AttendanceRecord.objects.create(user=boss, date=WED, status='late')
        self.login(boss)
        with self.now(at(WED, 12, 0)):
            r = self.client.patch(f'/api/attendance/records/{rec.id}/', {'status': 'present'})
        self.assertEqual(r.status_code, 200, r.data)


class ServiceTests(Base):
    def test_check_in_status_boundary(self):
        org = Organization.load()
        self.assertEqual(svc.check_in_status(at(WED, 10, 15, 0), org), 'present')
        self.assertEqual(svc.check_in_status(at(WED, 10, 15, 1), org), 'late')
        self.assertEqual(svc.check_in_status(at(SAT, 12, 0), org), 'present')

    def test_parse_month_december(self):
        self.assertEqual(svc.parse_month('2026-12'), (datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)))

    def test_parse_month_rejects_overflow(self):
        for bad in ('9999-12', '2026-0', '2026-13'):
            with self.assertRaises(ValidationError):
                svc.parse_month(bad)

    def test_client_ip(self):
        rf = APIRequestFactory()

        def ip(remote, fwd=None):
            extra = {'REMOTE_ADDR': remote, **({'HTTP_X_FORWARDED_FOR': fwd} if fwd else {})}
            return svc.client_ip(rf.get('/', **extra))

        self.assertEqual(ip('127.0.0.1', 'not-an-ip, 10.0.0.1'), '127.0.0.1')  # junk header never 500s
        self.assertEqual(ip('127.0.0.1', '1.2.3.4, 49.244.1.9'), '49.244.1.9')  # proxy-appended hop wins
        self.assertEqual(ip('49.244.9.9', '1.2.3.4'), '49.244.9.9')  # no proxy: header ignored
        self.assertEqual(ip('127.0.0.1'), '127.0.0.1')

    def test_check_in_with_junk_forwarded_for(self):
        self.login(self.emp)
        with self.now(at(WED, 9, 0)):
            r = self.client.post('/api/attendance/check-in/', HTTP_X_FORWARDED_FOR='not-an-ip, 10.0.0.1')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['check_in_ip'], '127.0.0.1')
