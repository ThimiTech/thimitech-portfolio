import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class WorkspaceTests(APITestCase):
    """Sprints, documents, notes, meetings, whiteboards and the public case-study API."""

    @classmethod
    def setUpTestData(cls):
        def user(name, role):
            return User.objects.create_user(username=name, email=f'{name}@ws.test', password='test', role=role)
        cls.lead = user('lead', 'manager')
        cls.member = user('member', 'employee')
        cls.outsider = user('outsider', 'employee')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.client.force_authenticate(self.lead)
        r = self.client.post('/api/pm/projects/', {'name': 'Atlas', 'key': 'ATL', 'members': [self.member.pk]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.project = r.data
        self.columns = r.data['boards'][0]['columns']

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def upload(self, name, content=b'hello', public=False, user=None):
        return self.as_user(user or self.lead).post('/api/pm/documents/', {
            'project': self.project['id'], 'title': name, 'file': SimpleUploadedFile(name, content), 'public': public,
        }, format='multipart')

    def test_sprint_lifecycle_and_completion_tracking(self):
        today = timezone.localdate()
        sprint = lambda n: self.client.post('/api/pm/sprints/', {'project': self.project['id'], 'name': n,  # noqa: E731
                                                                 'start_date': today, 'end_date': today + timedelta(days=13)}, format='json').data
        s1, s2 = sprint('S1'), sprint('S2')
        done = self.client.post('/api/pm/tasks/', {'title': 'A', 'column': self.columns[0]['id'], 'sprint': s1['id']}, format='json').data
        open_ = self.client.post('/api/pm/tasks/', {'title': 'B', 'column': self.columns[0]['id'], 'sprint': s1['id']}, format='json').data
        self.assertEqual(self.client.post(f"/api/pm/sprints/{s1['id']}/start/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/pm/sprints/{s2['id']}/start/").status_code, 400)  # one active at a time
        moved = self.client.patch(f"/api/pm/tasks/{done['id']}/", {'column': self.columns[-1]['id']}, format='json').data
        self.assertIsNotNone(moved['completed_at'])
        back = self.client.patch(f"/api/pm/tasks/{done['id']}/", {'column': self.columns[0]['id']}, format='json').data
        self.assertIsNone(back['completed_at'])
        self.client.patch(f"/api/pm/tasks/{done['id']}/", {'column': self.columns[-1]['id']}, format='json')
        r = self.client.post(f"/api/pm/sprints/{s1['id']}/complete/", {'carry_to': s2['id']}, format='json')
        self.assertEqual((r.status_code, r.data['carried']), (200, 1))
        self.assertEqual(self.client.get(f"/api/pm/tasks/{open_['id']}/").data['sprint'], s2['id'])
        self.assertEqual(self.client.get(f"/api/pm/tasks/{done['id']}/").data['sprint'], s1['id'])
        self.assertEqual(self.as_user(self.member).post(f"/api/pm/sprints/{s2['id']}/start/").status_code, 403)

    def test_documents_are_scoped_and_only_leads_publish(self):
        r = self.upload('spec.md', b'# Spec\n<script>x</script>', user=self.member)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['file'], 'spec.md')  # no /media path leaks
        url = f"/api/pm/documents/{r.data['id']}/file/"
        resp = self.as_user(self.member).get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain; charset=utf-8')  # never rendered as HTML
        self.assertEqual(resp['Content-Security-Policy'], 'sandbox')
        self.assertEqual(self.as_user(self.outsider).get(url).status_code, 404)
        self.assertEqual(self.upload('evil.html', user=self.member).status_code, 400)
        self.assertEqual(self.upload('pub.pdf', public=True, user=self.member).status_code, 400)
        denied = self.as_user(self.member).patch(f"/api/pm/documents/{r.data['id']}/", {'public': True}, format='json')
        self.assertEqual(denied.status_code, 400)

    def test_notes_titles_unique_and_member_editable(self):
        note = lambda t: self.as_user(self.member).post('/api/pm/notes/', {'project': self.project['id'], 'title': t, 'body': '[[Other]]'}, format='json')  # noqa: E731
        self.assertEqual(note('Ideas').status_code, 201)
        self.assertEqual(note('ideas').status_code, 400)
        self.assertEqual(self.as_user(self.outsider).post('/api/pm/notes/', {'project': self.project['id'], 'title': 'x'}, format='json').status_code, 400)

    def test_meeting_invites_calendar_and_ics(self):
        start = timezone.now() + timedelta(days=1)
        r = self.client.post('/api/pm/meetings/', {
            'project': self.project['id'], 'title': 'Sprint planning', 'start': start.isoformat(),
            'end': (start + timedelta(hours=1)).isoformat(), 'attendees': [self.member.pk],
            'action_items': [{'text': 'Draft scope', 'assignee': self.member.pk}],
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Notification.objects.filter(recipient=self.member, kind='meeting').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.lead, kind='meeting').exists())
        bad = self.client.post('/api/pm/meetings/', {'project': self.project['id'], 'title': 'x', 'start': start.isoformat(),
                                                    'end': (start + timedelta(hours=1)).isoformat(), 'attendees': [self.outsider.pk]}, format='json')
        self.assertIn('attendees', bad.data)
        same = self.client.post('/api/pm/meetings/', {'project': self.project['id'], 'title': 'x', 'start': start.isoformat(),
                                                     'end': start.isoformat()}, format='json')
        self.assertIn('end', same.data)
        day = timezone.localtime(start).date().isoformat()
        feed = self.as_user(self.member).get('/api/calendar/feed/', {'start': day, 'end': day}).data
        self.assertIn('meeting', [i['kind'] for i in feed['items']])
        ics = self.client.get(f"/api/pm/meetings/{r.data['id']}/ics/")
        self.assertIn(b'SUMMARY:ATL \xc2\xb7 Sprint planning', ics.content)

    def test_whiteboard_rejects_stale_saves(self):
        wb = self.as_user(self.member).post('/api/pm/whiteboards/', {'project': self.project['id'], 'title': 'Ideas'}, format='json').data
        url = f"/api/pm/whiteboards/{wb['id']}/"
        ok = self.client.patch(url, {'data': {'elements': [{'id': 'a'}]}, 'version': 1}, format='json')
        self.assertEqual((ok.status_code, ok.data['version']), (200, 2))
        stale = self.as_user(self.lead).patch(url, {'data': {'elements': []}, 'version': 1}, format='json')
        self.assertEqual(stale.status_code, 409)

    def test_public_profile_exposes_only_chosen_sections(self):
        pid = self.project['id']
        self.assertEqual(self.client.patch(f'/api/pm/projects/{pid}/', {'visibility': 'public'}, format='json').status_code, 400)
        r = self.client.patch(f'/api/pm/projects/{pid}/', {'visibility': 'public', 'slug': 'Atlas', 'story': '# Hi',
                                                          'public_sections': ['story', 'gallery']}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIsNotNone(r.data['published_at'])
        image = self.upload('shot.png', b'\x89PNG', public=True).data
        private = self.upload('private.png').data
        pdf = self.upload('deck.pdf', b'%PDF', public=True).data
        self.client.force_authenticate(None)
        detail = self.client.get('/api/pm/public/atlas/').data
        self.assertEqual(detail['story'], '# Hi')
        self.assertNotIn('team', detail)
        self.assertNotIn('documents', detail)
        self.assertEqual([g['id'] for g in detail['gallery']], [image['id']])
        self.assertEqual(self.client.get(f"/api/pm/public/atlas/files/{image['id']}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/pm/public/atlas/files/{private['id']}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/pm/public/atlas/files/{pdf['id']}/").status_code, 404)  # documents section off
        self.as_user(self.lead).patch(f'/api/pm/projects/{pid}/', {'visibility': 'private'}, format='json')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/pm/public/atlas/').status_code, 404)
        self.assertEqual(self.client.get('/api/pm/public/').data, [])
