import shutil
import tempfile
from datetime import timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.org.models import Department, EmployeeProfile
from apps.users.models import User

from .models import Notice, NoticeRead

URL = '/api/notices/'
MEDIA = tempfile.mkdtemp(prefix='notices_test_media_')


def make_user(email, role, dept=None):
    u = User.objects.create_user(username=email.split('@')[0], email=email, password='x', role=role,
                                 first_name=email.split('@')[0].title())
    if role != 'guest':
        # org may auto-create the profile via a post_save signal
        EmployeeProfile.objects.update_or_create(user=u, defaults={'department': dept})
    return User.objects.get(pk=u.pk)  # drop the stale cached profile


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   MEDIA_ROOT=MEDIA)
class NoticeTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.eng = Department.objects.create(name='Engineering')
        cls.gis = Department.objects.create(name='GIS')
        cls.hr = make_user('hr@t.com', 'hr_admin')
        cls.mgr = make_user('mgr@t.com', 'manager', cls.eng)
        cls.eng.manager = cls.mgr
        cls.eng.save()
        cls.gis_mgr = make_user('gismgr@t.com', 'manager', cls.gis)
        cls.gis.manager = cls.gis_mgr
        cls.gis.save()
        cls.sita = make_user('sita@t.com', 'employee', cls.eng)
        cls.maya = make_user('maya@t.com', 'employee', cls.gis)
        cls.guest = make_user('guest@t.com', 'guest')

    def notice(self, **kw):
        kw.setdefault('title', 'N')
        kw.setdefault('body', 'B')
        kw.setdefault('author', self.hr)
        return Notice.objects.create(**kw)

    def ids(self, user, query=''):
        self.client.force_authenticate(user)
        r = self.client.get(URL + query)
        self.assertEqual(r.status_code, 200, r.data)
        return {n['id'] for n in r.data}

    # ---- visibility ------------------------------------------------------
    def test_visibility_rules(self):
        now = timezone.now()
        everyone = self.notice()
        eng_only = self.notice(audience='department', department=self.eng)
        scheduled = self.notice(publish_at=now + timedelta(days=1))
        expired = self.notice(publish_at=now - timedelta(days=3), expires_at=now - timedelta(days=1))

        self.assertEqual(self.ids(self.sita), {everyone.id, eng_only.id})
        self.assertEqual(self.ids(self.maya), {everyone.id})
        # employees can't use manage mode to peek at scheduled notices
        self.assertEqual(self.ids(self.maya, '?manage=1'), {everyone.id})
        # hr manage mode sees all
        self.assertEqual(self.ids(self.hr, '?manage=1'), {everyone.id, eng_only.id, scheduled.id, expired.id})
        # detail of hidden notice is 404 for maya
        self.client.force_authenticate(self.maya)
        self.assertEqual(self.client.get(f'{URL}{eng_only.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'{URL}{scheduled.id}/').status_code, 404)

    def test_status_and_shape(self):
        now = timezone.now()
        n = self.notice(publish_at=now + timedelta(hours=1))
        self.client.force_authenticate(self.hr)
        r = self.client.get(URL + '?manage=1&status=scheduled')
        self.assertEqual([x['id'] for x in r.data], [n.id])
        item = r.data[0]
        self.assertEqual(item['status'], 'scheduled')
        self.assertEqual(item['author'], {'id': self.hr.id, 'full_name': self.hr.full_name, 'photo': None})
        self.assertIsNone(item['department'])
        self.assertEqual(item['read_count'], 0)
        self.assertFalse(item['is_read'])
        self.assertTrue(item['can_edit'])

    def test_guest_forbidden(self):
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_filters(self):
        a = self.notice(title='Server outage', category='urgent', pinned=True)
        b = self.notice(title='Picnic', category='event')
        NoticeRead.objects.create(notice=b, user=self.sita)
        self.assertEqual(self.ids(self.sita, '?category=event'), {b.id})
        self.assertEqual(self.ids(self.sita, '?unread=1'), {a.id})
        self.assertEqual(self.ids(self.sita, '?pinned=1'), {a.id})
        self.assertEqual(self.ids(self.sita, '?pinned=0'), {b.id})
        self.assertEqual(self.ids(self.sita, '?search=outage'), {a.id})

    # ---- create / edit permissions --------------------------------------
    def test_manager_department_only(self):
        self.client.force_authenticate(self.mgr)
        ok = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department', 'department_id': self.eng.id})
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(ok.data['department'], {'id': self.eng.id, 'name': 'Engineering'})
        self.assertEqual(ok.data['author']['id'], self.mgr.id)

        other = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department', 'department_id': self.gis.id})
        self.assertEqual(other.status_code, 400)
        self.assertIn('department_id', other.data)

        everyone = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'all'})
        self.assertEqual(everyone.status_code, 400)
        self.assertIn('audience', everyone.data)

        no_dept = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department'})
        self.assertEqual(no_dept.status_code, 400)

    def test_employee_cannot_create(self):
        self.client.force_authenticate(self.sita)
        r = self.client.post(URL, {'title': 'T', 'body': 'B'})
        self.assertEqual(r.status_code, 403)

    def test_pinned_restricted(self):
        self.client.force_authenticate(self.mgr)
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department',
                                   'department_id': self.eng.id, 'pinned': True})
        self.assertEqual(r.status_code, 400)
        self.assertIn('pinned', r.data)
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department',
                                   'department_id': self.eng.id, 'pinned': False})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.patch(f"{URL}{r.data['id']}/", {'pinned': True}).status_code, 400)

        self.client.force_authenticate(self.hr)
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'pinned': True})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data['pinned'])

    def test_edit_delete_author_or_hr(self):
        n = self.notice(author=self.mgr, audience='department', department=self.eng)
        self.client.force_authenticate(self.sita)
        self.assertEqual(self.client.patch(f'{URL}{n.id}/', {'title': 'X'}).status_code, 403)
        self.assertEqual(self.client.delete(f'{URL}{n.id}/').status_code, 403)
        self.client.force_authenticate(self.mgr)
        self.assertEqual(self.client.patch(f'{URL}{n.id}/', {'title': 'X'}).status_code, 200)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.delete(f'{URL}{n.id}/').status_code, 204)
        self.assertFalse(Notice.objects.filter(pk=n.id).exists())

    def test_manager_sees_own_scheduled_in_manage_mode(self):
        n = self.notice(author=self.mgr, audience='department', department=self.eng,
                        publish_at=timezone.now() + timedelta(days=2))
        self.assertEqual(self.ids(self.mgr), set())
        self.assertEqual(self.ids(self.mgr, '?manage=1'), {n.id})

    def test_expiry_validation(self):
        self.client.force_authenticate(self.hr)
        now = timezone.now()
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'publish_at': now.isoformat(),
                                   'expires_at': (now - timedelta(hours=1)).isoformat()}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('expires_at', r.data)

    def test_attachment_rules(self):
        self.client.force_authenticate(self.hr)
        bad = SimpleUploadedFile('x.exe', b'MZ', content_type='application/octet-stream')
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'attachment': bad}, format='multipart')
        self.assertEqual(r.status_code, 400)
        self.assertIn('attachment', r.data)
        big = SimpleUploadedFile('big.pdf', b'0' * (10 * 1024 * 1024 + 1), content_type='application/pdf')
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'attachment': big}, format='multipart')
        self.assertEqual(r.status_code, 400)
        ok = SimpleUploadedFile('policy.pdf', b'%PDF-1.4', content_type='application/pdf')
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'attachment': ok}, format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        nid = r.data['id']
        self.assertTrue(r.data['attachment'].endswith(f'{URL}{nid}/attachment/'))
        self.assertEqual(r.data['attachment_name'], 'policy.pdf')
        r = self.client.patch(f'{URL}{nid}/', {'remove_attachment': True}, format='multipart')
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data['attachment'])
        self.client.delete(f'{URL}{nid}/')

    # ---- reads -----------------------------------------------------------
    def test_read_idempotent_and_unread_count(self):
        a, b = self.notice(), self.notice()
        self.notice(audience='department', department=self.gis)  # invisible to sita
        self.client.force_authenticate(self.sita)
        self.assertEqual(self.client.get(URL + 'unread-count/').data, {'unread': 2})
        r1 = self.client.post(f'{URL}{a.id}/read/')
        r2 = self.client.post(f'{URL}{a.id}/read/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data['read_at'], r2.data['read_at'])
        self.assertEqual(NoticeRead.objects.filter(notice=a, user=self.sita).count(), 1)
        self.assertEqual(self.client.get(URL + 'unread-count/').data, {'unread': 1})
        self.assertTrue(self.client.get(f'{URL}{a.id}/').data['is_read'])
        r = self.client.post(URL + 'read-all/')
        self.assertEqual(r.data, {'marked': 1})
        self.assertEqual(self.client.post(URL + 'read-all/').data, {'marked': 0})
        self.assertEqual(self.client.get(URL + 'unread-count/').data, {'unread': 0})
        # read_count hidden from non-authors
        self.assertIsNone(self.client.get(f'{URL}{b.id}/').data['read_count'])

    def test_readers_permission_and_content(self):
        n = self.notice(author=self.mgr, audience='department', department=self.eng)
        NoticeRead.objects.create(notice=n, user=self.sita)
        self.client.force_authenticate(self.sita)
        self.assertEqual(self.client.get(f'{URL}{n.id}/readers/').status_code, 403)
        self.client.force_authenticate(self.gis_mgr)  # cannot even see it
        self.assertEqual(self.client.get(f'{URL}{n.id}/readers/').status_code, 404)
        for user in (self.mgr, self.hr):
            self.client.force_authenticate(user)
            r = self.client.get(f'{URL}{n.id}/readers/')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data['audience_count'], 2)  # mgr + sita
            self.assertEqual([x['id'] for x in r.data['read']], [self.sita.id])
            self.assertEqual([x['id'] for x in r.data['unread']], [self.mgr.id])
            self.assertEqual(r.data['read'][0]['department'], {'id': self.eng.id, 'name': 'Engineering'})
        self.client.force_authenticate(self.mgr)
        self.assertEqual(self.client.get(f'{URL}{n.id}/').data['read_count'], 1)

    # ---- urgent email ----------------------------------------------------
    def test_urgent_email_sent_once_to_audience(self):
        self.client.force_authenticate(self.mgr)
        r = self.client.post(URL, {'title': 'Server down', 'body': 'Use VPN B', 'category': 'urgent',
                                   'audience': 'department', 'department_id': self.eng.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['sita@t.com'])  # author excluded, other depts excluded
        self.assertIn('Server down', mail.outbox[0].subject)

    def test_urgent_to_all_skips_guests(self):
        self.client.force_authenticate(self.hr)
        self.client.post(URL, {'title': 'Fire drill', 'body': 'Now', 'category': 'urgent'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(set(mail.outbox[0].to), {'mgr@t.com', 'gismgr@t.com', 'sita@t.com', 'maya@t.com'})

    def test_scheduled_urgent_and_normal_not_emailed(self):
        self.client.force_authenticate(self.hr)
        later = (timezone.now() + timedelta(days=1)).isoformat()
        self.client.post(URL, {'title': 'Later', 'body': 'x', 'category': 'urgent', 'publish_at': later}, format='json')
        self.client.post(URL, {'title': 'Plain', 'body': 'x'})
        self.assertEqual(len(mail.outbox), 0)

    def test_expired_urgent_not_emailed(self):
        self.client.force_authenticate(self.hr)
        now = timezone.now()
        r = self.client.post(URL, {'title': 'Old', 'body': 'x', 'category': 'urgent',
                                   'publish_at': (now - timedelta(days=3)).isoformat(),
                                   'expires_at': (now - timedelta(days=1)).isoformat()}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['status'], 'expired')
        self.assertEqual(len(mail.outbox), 0)

    def test_beat_emails_scheduled_urgent_once_live(self):
        from .tasks import email_due_urgent_notices
        self.client.force_authenticate(self.hr)
        now = timezone.now()
        self.client.post(URL, {'title': 'Live now', 'body': 'x', 'category': 'urgent'})  # mailed at create
        r = self.client.post(URL, {'title': 'Soon', 'body': 'x', 'category': 'urgent',
                                   'publish_at': (now + timedelta(hours=1)).isoformat()}, format='json')
        self.assertEqual(len(mail.outbox), 1)
        email_due_urgent_notices()
        self.assertEqual(len(mail.outbox), 1)  # not live yet; the create-time one isn't re-sent
        Notice.objects.filter(pk=r.data['id']).update(publish_at=now - timedelta(minutes=1))
        self.assertEqual(email_due_urgent_notices()['emailed'], [r.data['id']])
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('Soon', mail.outbox[1].subject)
        email_due_urgent_notices()
        self.assertEqual(len(mail.outbox), 2)

    # ---- attachments are served through the scoped API -------------------
    def upload(self, user, name='secret.pdf', **data):
        self.client.force_authenticate(user)
        f = SimpleUploadedFile(name, b'%PDF-1.4 secret', content_type='application/pdf')
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'attachment': f, **data}, format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        return Notice.objects.get(pk=r.data['id'])

    def test_attachment_scoped_and_unguessable(self):
        n = self.upload(self.mgr, audience='department', department_id=self.eng.id)
        # stored under a random directory, not notices/<original name>
        self.assertRegex(n.attachment.name, r'^notices/[0-9a-f]{32}/secret\.pdf$')
        url = f'{URL}{n.id}/attachment/'

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.client.force_authenticate(self.maya)  # other department
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.sita)  # audience
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 secret')
        self.assertIn('attachment; filename="secret.pdf"', r['Content-Disposition'])

    def test_scheduled_attachment_hidden_until_live(self):
        later = (timezone.now() + timedelta(days=1)).isoformat()
        n = self.upload(self.hr, publish_at=later)
        self.client.force_authenticate(self.sita)
        self.assertEqual(self.client.get(f'{URL}{n.id}/attachment/').status_code, 404)
        self.client.force_authenticate(self.hr)  # whoever manages it can preview
        self.assertEqual(self.client.get(f'{URL}{n.id}/attachment/').status_code, 200)

    def test_replacing_attachment_deletes_old_file(self):
        n = self.upload(self.hr)
        storage, old = n.attachment.storage, n.attachment.name
        self.assertTrue(storage.exists(old))
        new = SimpleUploadedFile('v2.pdf', b'%PDF-1.4 v2', content_type='application/pdf')
        r = self.client.patch(f'{URL}{n.id}/', {'attachment': new}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['attachment_name'], 'v2.pdf')
        self.assertFalse(storage.exists(old))

    def test_multipart_put_without_pinned_keeps_pin(self):
        n = self.notice(pinned=True)
        self.client.force_authenticate(self.hr)
        r = self.client.put(f'{URL}{n.id}/', {'title': 'New', 'body': 'B'}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['pinned'])
        # a non-HR author is not tripped up by HR's pin either
        m = self.notice(author=self.mgr, audience='department', department=self.eng, pinned=True)
        self.client.force_authenticate(self.mgr)
        r = self.client.put(f'{URL}{m.id}/', {'title': 'New', 'body': 'B', 'audience': 'department',
                                             'department_id': self.eng.id}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['pinned'])

    # ---- reads only count inside the audience ---------------------------
    def test_read_requires_audience_and_live(self):
        eng = self.notice(author=self.mgr, audience='department', department=self.eng)
        scheduled = self.notice(publish_at=timezone.now() + timedelta(days=2))
        self.client.force_authenticate(self.hr)  # hr has no department: can manage, but is not the audience
        self.assertEqual(self.client.get(f'{URL}{eng.id}/').status_code, 200)
        self.assertEqual(self.client.post(f'{URL}{eng.id}/read/').status_code, 404)
        self.assertEqual(self.client.post(f'{URL}{scheduled.id}/read/').status_code, 404)
        self.assertFalse(NoticeRead.objects.filter(user=self.hr).exists())

    def test_reach_excludes_non_audience_reads(self):
        n = self.notice(author=self.mgr, audience='department', department=self.eng)
        NoticeRead.objects.create(notice=n, user=self.sita)
        NoticeRead.objects.create(notice=n, user=self.maya)  # e.g. moved out of Engineering since
        self.client.force_authenticate(self.mgr)
        r = self.client.get(f'{URL}{n.id}/readers/')
        self.assertEqual((r.data['audience_count'], r.data['read_count']), (2, 1))
        self.assertEqual([x['id'] for x in r.data['read']], [self.sita.id])
        self.assertEqual(self.client.get(f'{URL}{n.id}/').data['read_count'], 1)
        listed = {x['id']: x for x in self.client.get(URL + '?manage=1').data}
        self.assertEqual(listed[n.id]['read_count'], 1)

    def test_author_does_not_see_own_notice_unread(self):
        self.client.force_authenticate(self.mgr)
        r = self.client.post(URL, {'title': 'T', 'body': 'B', 'audience': 'department', 'department_id': self.eng.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data['is_read'])
        self.assertEqual(self.client.get(URL + 'unread-count/').data, {'unread': 0})
        self.client.force_authenticate(self.sita)
        self.assertEqual(self.client.get(URL + 'unread-count/').data, {'unread': 1})
