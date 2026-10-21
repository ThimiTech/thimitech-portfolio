import datetime

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.notifications.models import Notification

from .models import AttendanceCorrection, AttendanceRecord
from .tests import NPT, Base

URL = '/api/attendance/corrections/'


class CorrectionTests(Base):
    def setUp(self):
        self.day = timezone.localdate() - datetime.timedelta(days=2)

    def login(self, user):
        # fresh instance: fixture users carry a stale cached profile from the auto-create signal
        self.client.force_authenticate(type(user).objects.get(pk=user.pk))

    def request(self, user, **extra):
        self.login(user)
        body = {'date': self.day.isoformat(), 'check_in': '09:30', 'check_out': '18:00', 'reason': 'Forgot to punch', **extra}
        return self.client.post(URL, body, format='json')

    def test_flow_routes_to_manager_updates_record_notifies_and_audits(self):
        r = self.request(self.emp)
        self.assertEqual(r.status_code, 201, r.data)
        cid = r.data['id']
        self.assertEqual(Notification.objects.get(kind='correction_requested').recipient, self.mgr)

        self.login(self.mgr)
        self.assertEqual(self.client.get('/api/nav-counts/').data['attendance_corrections'], 1)
        self.assertEqual([c['id'] for c in self.client.get(URL, {'scope': 'approvals'}).data], [cid])
        self.login(self.emp)
        self.assertEqual(self.client.get('/api/nav-counts/').data['attendance_corrections'], 0)
        self.assertEqual(self.client.post(f'{URL}{cid}/approve/').status_code, 403)  # own request
        self.login(self.gis_mgr)
        self.assertEqual(self.client.post(f'{URL}{cid}/approve/').status_code, 403)  # not their team

        self.login(self.mgr)
        r = self.client.post(f'{URL}{cid}/approve/', {}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'approved')
        rec = AttendanceRecord.objects.get(user=self.emp, date=self.day)
        self.assertEqual(rec.source, 'corrected')
        self.assertEqual(rec.check_in.astimezone(NPT).time(), datetime.time(9, 30))
        self.assertEqual(rec.check_out.astimezone(NPT).time(), datetime.time(18, 0))
        self.assertEqual(rec.status, 'present')
        self.assertEqual(Notification.objects.get(kind='correction_decided').recipient, self.emp)
        self.assertTrue(AuditLog.objects.filter(target_model='attendance.attendancerecord', target_id=str(rec.pk),
                                                actor_id=self.mgr.pk, diff__source__after='corrected').exists())
        self.assertTrue(AuditLog.objects.filter(target_model='attendance.attendancecorrection', target_id=str(cid),
                                                action='update').exists())
        self.assertEqual(self.client.post(f'{URL}{cid}/approve/').status_code, 400)  # already decided

    def test_approval_overwrites_existing_record(self):
        rec = AttendanceRecord.objects.create(user=self.emp, date=self.day, status='absent', note='Auto-marked', source='system')
        cid = self.request(self.emp, check_in='11:00', check_out=None).data['id']
        self.login(self.hr)
        self.assertEqual(self.client.post(f'{URL}{cid}/approve/').status_code, 200)
        rec.refresh_from_db()
        self.assertEqual((rec.source, rec.check_out), ('corrected', None))
        self.assertIn(rec.status, ('late', 'present'))  # late on a working day, present on a weekend/holiday
        self.assertEqual(AttendanceRecord.objects.filter(user=self.emp, date=self.day).count(), 1)

    def test_reject_needs_note_and_leaves_attendance_alone(self):
        cid = self.request(self.emp).data['id']
        self.login(self.hr)
        self.assertEqual(self.client.post(f'{URL}{cid}/reject/', {}, format='json').status_code, 400)
        r = self.client.post(f'{URL}{cid}/reject/', {'decision_note': 'Badge log shows 11:00'}, format='json')
        self.assertEqual(r.data['status'], 'rejected')
        self.assertFalse(AttendanceRecord.objects.filter(user=self.emp, date=self.day).exists())

    def test_validation(self):
        today = timezone.localdate()
        self.assertEqual(self.request(self.emp, date=today.isoformat()).status_code, 400)
        self.assertEqual(self.request(self.emp, date=(today - datetime.timedelta(days=31)).isoformat()).status_code, 400)
        self.assertEqual(self.request(self.emp, check_out='09:00').status_code, 400)
        self.assertEqual(self.request(self.emp, reason='').status_code, 400)
        self.assertEqual(self.request(self.emp).status_code, 201)
        self.assertEqual(self.request(self.emp).status_code, 400)  # one pending per day
        self.login(self.guest)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_visibility(self):
        cid = self.request(self.emp).data['id']
        self.request(self.maya)
        self.login(self.emp)
        self.assertEqual([c['id'] for c in self.client.get(URL).data], [cid])
        self.login(self.gis_mgr)
        self.assertEqual(self.client.get(f'{URL}{cid}/').status_code, 404)
        self.assertEqual(len(self.client.get(URL, {'scope': 'approvals'}).data), 1)  # maya only
        self.login(self.hr)
        self.assertEqual(len(self.client.get(URL, {'scope': 'approvals'}).data), 2)
        self.assertTrue(self.client.get(f'{URL}{cid}/').data['can_decide'])

    def test_hr_record_edits_are_marked_hr(self):
        self.login(self.hr)
        r = self.client.post('/api/attendance/records/', {'user': self.emp.pk, 'date': self.day.isoformat(), 'status': 'absent'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['source'], 'hr')
        self.assertEqual(AttendanceCorrection.objects.count(), 0)
