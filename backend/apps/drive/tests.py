import io
import shutil
import tempfile
import zipfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.finance.models import Account, Transaction
from apps.users.models import User
from .models import File, Folder, ShareLink

MEDIA = tempfile.mkdtemp()


def user(email, role):
    return User.objects.create_user(username=email, email=email, password='x', role=role)


@override_settings(MEDIA_ROOT=MEDIA)
class DriveTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.emp = user('emp@x.com', 'employee')
        self.other = user('other@x.com', 'employee')
        self.ca = user('ca@x.com', 'accountant')
        self.hr = user('hr@x.com', 'hr_admin')

    def upload(self, who, name='a.pdf', **data):
        self.client.force_authenticate(who)
        return self.client.post('/api/drive/files/', {'file': SimpleUploadedFile(name, b'%PDF-1.4 x'), **data}, format='multipart')

    def test_spaces_by_role(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual([s['id'] for s in self.client.get('/api/drive/spaces/').data['spaces']], ['company'])
        self.assertEqual(self.client.get('/api/drive/browse/', {'space': 'finance'}).status_code, 403)
        self.client.force_authenticate(self.ca)
        self.assertEqual([s['id'] for s in self.client.get('/api/drive/spaces/').data['spaces']], ['company', 'finance'])

    def test_company_drive_shared_but_only_uploader_or_hr_deletes(self):
        r = self.upload(self.emp, 'Letterhead.pdf', space='company')
        self.assertEqual(r.status_code, 201, r.data)
        self.client.force_authenticate(self.other)
        self.assertEqual(len(self.client.get('/api/drive/browse/', {'space': 'company'}).data['files']), 1)
        self.assertEqual(self.client.delete(f"/api/drive/files/{r.data['id']}/").status_code, 403)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.delete(f"/api/drive/files/{r.data['id']}/").status_code, 204)

    def test_employee_reads_own_linked_finance_file_only(self):
        mine = self.upload(self.ca, 'june-transfer.pdf', space='finance', employee=self.emp.pk).data
        theirs = self.upload(self.ca, 'other.pdf', space='finance', employee=self.other.pk).data
        self.client.force_authenticate(self.emp)
        self.assertEqual([f['id'] for f in self.client.get('/api/drive/browse/', {'view': 'mine'}).data['files']], [mine['id']])
        self.assertEqual(self.client.get(f"/api/drive/files/{mine['id']}/content/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/drive/files/{theirs['id']}/content/").status_code, 404)
        self.assertEqual(self.upload(self.emp, 'x.pdf', space='finance').status_code, 400)

    def test_only_finance_links_records_and_folder_upload_builds_tree(self):
        acct = Account.objects.create(name='A', opening_date=date(2025, 7, 17))
        t = Transaction.objects.create(account=acct, date=date(2025, 8, 1), description='x', debit=1, created_by=self.hr)
        self.assertEqual(self.upload(self.emp, space='company', transaction=t.pk).status_code, 400)
        r = self.upload(self.ca, 'june.pdf', space='finance', relative_path='salary logs/2026/june.pdf', transaction=t.pk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(File.objects.get().folder.path(), ['salary logs', '2026'])

    def test_share_link_zip_expiry_and_revoke(self):
        folder = Folder.objects.create(space='finance', name='FY 2081-82 audit', fiscal_year='2081/82')
        sub = Folder.objects.create(space='finance', name='Tax', parent=folder)
        self.upload(self.ca, 'return.pdf', folder=sub.pk)
        self.upload(self.ca, 'outside.pdf', space='finance')
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.post('/api/drive/share-links/', {'folder': folder.pk}, format='json').status_code, 403)
        self.client.force_authenticate(self.ca)
        link = self.client.post('/api/drive/share-links/', {'folder': folder.pk, 'label': 'CA', 'days': 7}, format='json').data
        self.client.force_authenticate(None)
        listing = self.client.get(f"/api/drive/shared/{link['token']}/").data
        self.assertEqual([(f['path'], f['name']) for f in listing['files']], [('Tax', 'return.pdf')])
        z = self.client.get(f"/api/drive/shared/{link['token']}/zip/")
        self.assertEqual(zipfile.ZipFile(io.BytesIO(b''.join(z.streaming_content))).namelist(), ['Tax/return.pdf'])
        outside = File.objects.get(name='outside.pdf')
        self.assertEqual(self.client.get(f"/api/drive/shared/{link['token']}/files/{outside.pk}/").status_code, 404)
        ShareLink.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(self.client.get(f"/api/drive/shared/{link['token']}/").status_code, 404)

    def test_non_empty_folder_cannot_be_deleted(self):
        folder = Folder.objects.create(space='company', name='Templates2', created_by=self.emp)
        self.upload(self.emp, folder=folder.pk)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.delete(f'/api/drive/folders/{folder.pk}/').status_code, 400)

    def test_employee_attaches_receipt_to_own_draft_claim_only(self):
        from apps.finance.models import Expense
        mine = Expense.objects.create(employee=self.emp, description='Taxi', amount=500, created_by=self.emp)
        theirs = Expense.objects.create(employee=self.other, description='Taxi', amount=500, created_by=self.other)
        r = self.upload(self.emp, 'bill.jpg', space='finance', expense=mine.pk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['employee'], File.objects.get().folder.path()[0]), (self.emp.pk, 'Receipts & claims'))
        self.assertEqual(self.upload(self.emp, 'x.jpg', space='finance', expense=theirs.pk).status_code, 400)
