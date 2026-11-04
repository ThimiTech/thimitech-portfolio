"""Clearance vs classification across project content, the drive and the people API."""
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.drive.models import File, Folder, ShareLink
from apps.users.models import Clearance, User

MEDIA = tempfile.mkdtemp()


def make(name, role, clearance=Clearance.INTERNAL):
    return User.objects.create_user(username=name, email=f'{name}@cl.test', password='x', role=role, clearance=clearance)


@override_settings(MEDIA_ROOT=MEDIA)
class ClearanceTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.lead = make('lead', 'manager', Clearance.RESTRICTED)
        self.dev = make('dev', 'employee')
        self.boss = make('boss', 'super_admin')
        self.client.force_authenticate(self.lead)
        self.project = self.client.post('/api/pm/projects/', {'name': 'Atlas', 'key': 'ATL', 'members': [self.dev.pk]},
                                        format='json').data

    def as_(self, u):
        self.client.force_authenticate(u)
        return self.client

    def test_project_document_hidden_below_clearance(self):
        r = self.as_(self.lead).post('/api/pm/documents/', {
            'project': self.project['id'], 'title': 'Contract', 'classification': Clearance.RESTRICTED,
            'file': SimpleUploadedFile('c.pdf', b'%PDF-1.4')}, format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        doc = r.data['id']
        dev = self.as_(self.dev)
        self.assertEqual(dev.get(f'/api/pm/documents/?project={self.project["id"]}').data, [])
        self.assertEqual(dev.get(f'/api/pm/documents/{doc}/file/').status_code, 404)
        self.assertEqual(self.as_(self.lead).get(f'/api/pm/documents/{doc}/file/').status_code, 200)
        # nobody classifies above their own clearance; public items stay Internal
        r = self.as_(self.lead).patch(f'/api/pm/documents/{doc}/', {'classification': Clearance.SECRET}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.as_(self.lead).patch(f'/api/pm/documents/{doc}/', {'public': True}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_meeting_attendees_must_be_cleared(self):
        r = self.as_(self.lead).post('/api/pm/meetings/', {
            'project': self.project['id'], 'title': 'Pricing', 'start': '2026-11-04T10:00:00Z', 'end': '2026-11-04T11:00:00Z',
            'attendees': [self.dev.pk], 'classification': Clearance.CONFIDENTIAL}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('attendees', r.data)

    def test_drive_folder_floor_cascades_and_limits_share_links(self):
        folder = Folder.objects.create(space='company', name='Contracts')
        f = File.objects.create(space='company', folder=folder, name='nda.pdf', file=SimpleUploadedFile('nda.pdf', b'x'))
        r = self.as_(self.boss).patch(f'/api/drive/folders/{folder.pk}/', {'classification': Clearance.RESTRICTED}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        f.refresh_from_db()
        self.assertEqual(f.classification, Clearance.RESTRICTED)
        # a new file in that folder can't sit below it
        later = File.objects.create(space='company', folder=folder, name='b.pdf', file=SimpleUploadedFile('b.pdf', b'x'))
        self.assertEqual(later.classification, Clearance.RESTRICTED)
        dev = self.as_(self.dev)
        self.assertNotIn('Contracts', [x['name'] for x in dev.get('/api/drive/browse/?space=company').data['folders']])
        self.assertEqual(dev.get(f'/api/drive/files/{f.pk}/content/').status_code, 404)
        # ...unless the file is linked to them (their own contract)
        File.objects.filter(pk=f.pk).update(employee=self.dev)
        self.assertEqual(dev.get(f'/api/drive/files/{f.pk}/content/').status_code, 200)
        # a share link never exposes more than its creator may see now
        link = ShareLink.objects.create(folder=folder, created_by=self.lead, expires_at='2099-01-01T00:00:00Z')
        self.assertEqual(len(self.client.get(f'/api/drive/shared/{link.token}/').data['files']), 2)
        User.objects.filter(pk=self.lead.pk).update(clearance=Clearance.INTERNAL)
        self.assertEqual(len(self.client.get(f'/api/drive/shared/{link.token}/').data['files']), 0)

    def test_only_super_admin_sets_clearance(self):
        hr = make('hr', 'hr_admin', Clearance.RESTRICTED)
        r = self.as_(hr).patch(f'/api/org/people/{self.dev.pk}/', {'clearance': Clearance.CONFIDENTIAL}, format='json')
        self.assertEqual(r.status_code, 403)
        r = self.as_(self.boss).patch(f'/api/org/people/{self.dev.pk}/', {'clearance': Clearance.CONFIDENTIAL}, format='json')
        self.assertEqual((r.status_code, r.data['clearance']), (200, Clearance.CONFIDENTIAL))
        self.assertEqual(self.boss.clearance, Clearance.SECRET)  # super admins always hold the top level
