import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Job, JobApplication

PDF = b'%PDF-1.4'


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HiringTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = User.objects.create_user(username='hr', email='hr@x.test', password='x', role='hr_admin')
        cls.staff = User.objects.create_user(username='st', email='st@x.test', password='x', role='employee')
        cls.guest = User.objects.create_user(username='g', email='g@x.test', password='x')
        cls.job = Job.objects.create(title='Dev', employment_type='Full-time', description='d')
        cls.closed = Job.objects.create(title='Old', employment_type='Full-time', description='d', is_active=False)
        cls.app = JobApplication.objects.create(
            job=cls.job, applicant=cls.guest, name='Gita Guest', phone='98', address='Thimi',
            cv=SimpleUploadedFile('cv.pdf', PDF), hr_notes='strong')

    def test_public_urls_keep_their_shape(self):
        r = self.client.get('/api/jobs/')
        self.assertEqual([j['id'] for j in r.data], [self.job.pk])
        self.assertNotIn('pending_count', r.data[0])
        self.assertEqual(self.client.get(f'/api/jobs/{self.closed.pk}/').status_code, 404)
        self.client.force_authenticate(self.guest)
        mine = self.client.get('/api/jobs/applications/')
        self.assertEqual(len(mine.data), 1)
        self.assertNotIn('hr_notes', mine.data[0])

    def test_only_hr_manages_postings(self):
        body = {'title': 'GIS analyst', 'employment_type': 'Contract', 'description': 'd',
                'requirement_texts': ['QGIS', ' ']}
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post('/api/jobs/', body, format='json').status_code, 403)
        self.assertEqual(self.client.get('/api/hiring/applications/').status_code, 403)
        self.client.force_authenticate(self.hr)
        r = self.client.post('/api/jobs/', body, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([q['text'] for q in r.data['requirements']], ['QGIS'])
        listed = self.client.get('/api/jobs/?manage=1').data
        self.assertEqual(len(listed), 3)  # includes the closed posting
        self.assertEqual(next(j for j in listed if j['id'] == self.job.pk)['pending_count'], 1)
        self.assertEqual(self.client.delete(f'/api/jobs/{self.job.pk}/').status_code, 400)  # has applications
        self.assertEqual(self.client.delete(f'/api/jobs/{r.data["id"]}/').status_code, 204)

    def test_pipeline_status_and_cv(self):
        self.client.force_authenticate(self.hr)
        url = f'/api/hiring/applications/{self.app.pk}/'
        r = self.client.patch(url, {'status': 'interview', 'name': 'Changed'}, format='json')
        self.assertEqual((r.data['status'], r.data['name']), ('interview', 'Gita Guest'))
        self.assertEqual(self.client.get('/api/hiring/applications/?status=interview').data[0]['id'], self.app.pk)
        cv = self.client.get(url + 'cv/')
        self.assertEqual(bytes().join(cv.streaming_content), PDF)
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.get(url + 'cv/').status_code, 403)

    def test_hire_promotes_and_starts_onboarding(self):
        self.client.force_authenticate(self.hr)
        r = self.client.post(f'/api/hiring/applications/{self.app.pk}/hire/', {'designation': 'Engineer'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.guest.refresh_from_db()
        self.assertEqual((self.guest.role, r.data['status']), ('employee', 'selected'))
        profile = self.guest.profile
        self.assertEqual((self.guest.first_name, profile.designation, profile.phone), ('Gita', 'Engineer', '98'))
        self.assertTrue(self.guest.onboarding_tasks.exists())
        self.client.force_authenticate(self.guest)
        self.assertGreater(self.client.get('/api/nav-counts/').data['onboarding_open'], 0)

    def test_hire_never_demotes_and_refuses_rejected(self):
        self.client.force_authenticate(self.hr)
        mine = JobApplication.objects.create(job=self.job, applicant=self.hr, name='HR', phone='1', address='x',
                                             cv=SimpleUploadedFile('cv.pdf', PDF), status='rejected')
        self.assertEqual(self.client.post(f'/api/hiring/applications/{mine.pk}/hire/').status_code, 400)
        mine.status = 'pending'
        mine.save()
        self.assertEqual(self.client.post(f'/api/hiring/applications/{mine.pk}/hire/').status_code, 200)
        self.hr.refresh_from_db()
        self.assertEqual(self.hr.role, 'hr_admin')
