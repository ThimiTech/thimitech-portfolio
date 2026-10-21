import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Job, JobApplication


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ApplicationUploadTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='appl', email='appl@x.test', password='x')
        cls.job = Job.objects.create(title='Dev', employment_type='Full-time', description='d')
        cls.closed = Job.objects.create(title='Old', employment_type='Full-time', description='d', is_active=False)

    def apply(self, cv, job=None):
        self.client.force_authenticate(self.user)
        return self.client.post('/api/jobs/apply/', {
            'job': (job or self.job).pk, 'name': 'A', 'phone': '1', 'address': 'x', 'cv': cv,
        }, format='multipart')

    def test_cv_html_rejected(self):
        r = self.apply(SimpleUploadedFile('cv.html', b'<script>alert(1)</script>', content_type='application/pdf'))
        self.assertEqual(r.status_code, 400)
        self.assertIn('cv', r.data)

    def test_cv_size_limit(self):
        r = self.apply(SimpleUploadedFile('cv.pdf', b'0' * (5 * 1024 * 1024 + 1), content_type='application/pdf'))
        self.assertEqual(r.status_code, 400)

    def test_cv_stored_under_unguessable_dir(self):
        r = self.apply(SimpleUploadedFile('cv.pdf', b'%PDF-1.4', content_type='application/pdf'))
        self.assertEqual(r.status_code, 201, r.data)
        name = JobApplication.objects.get().cv.name
        self.assertRegex(name, r'^applications/cv/[0-9a-f]{32}/cv\.pdf$')

    def test_cannot_apply_to_inactive_job(self):
        r = self.apply(SimpleUploadedFile('cv.pdf', b'%PDF-1.4', content_type='application/pdf'), job=self.closed)
        self.assertEqual(r.status_code, 400)
