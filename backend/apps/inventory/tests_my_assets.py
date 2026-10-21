from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User

from .models import Asset, Assignment, Category


def mk(email, role):
    return User.objects.create_user(username=email.split('@')[0], email=email, password='x', role=role, first_name=email[:3])


class MyAssetsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = mk('hr@mine.test', 'hr_admin')
        cls.hr2 = mk('hr2@mine.test', 'super_admin')
        cls.emp = mk('emp@mine.test', 'employee')
        cls.other = mk('oth@mine.test', 'employee')
        cat = Category.objects.create(name='Laptops')
        a1, a2, a3 = (Asset.objects.create(tag=f'M-{i}', name=f'Laptop {i}', category=cat, created_by=cls.hr,
                                           purchase_cost='999.00') for i in range(3))
        cls.current = Assignment.objects.create(asset=a1, employee=cls.emp, assigned_by=cls.hr)
        cls.past = Assignment.objects.create(asset=a2, employee=cls.emp, assigned_by=cls.hr, returned_at=timezone.now())
        cls.theirs = Assignment.objects.create(asset=a3, employee=cls.other, assigned_by=cls.hr)

    def setUp(self):
        self.client.force_authenticate(self.emp)

    def test_lists_own_current_then_history(self):
        r = self.client.get('/api/inventory/my-assets/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a['id'] for a in r.data], [self.current.pk, self.past.pk])
        self.assertNotIn('purchase_cost', r.data[0])
        self.assertEqual(self.client.get(f'/api/inventory/my-assets/{self.theirs.pk}/').status_code, 404)

    def test_report_issue_notifies_hr(self):
        r = self.client.post(f'/api/inventory/my-assets/{self.current.pk}/report-issue/', {'note': 'Screen flickers'}, format='json')
        self.assertEqual(r.status_code, 204)
        notes = Notification.objects.filter(kind='asset_issue')
        self.assertEqual({n.recipient_id for n in notes}, {self.hr.pk, self.hr2.pk})
        self.assertEqual(notes[0].body, 'Screen flickers')

    def test_report_issue_rules(self):
        base = '/api/inventory/my-assets/'
        self.assertEqual(self.client.post(f'{base}{self.theirs.pk}/report-issue/', {'note': 'x'}).status_code, 404)
        self.assertEqual(self.client.post(f'{base}{self.past.pk}/report-issue/', {'note': 'x'}).status_code, 400)
        self.assertEqual(self.client.post(f'{base}{self.current.pk}/report-issue/', {'note': ''}).status_code, 400)
        self.assertFalse(Notification.objects.filter(kind='asset_issue').exists())

    def test_assignment_notification_links_to_my_assets(self):
        asset = Asset.objects.create(tag='M-9', name='Phone', category=Category.objects.get(), created_by=self.hr)
        self.client.force_authenticate(self.hr)
        r = self.client.post('/api/inventory/assignments/', {'asset': asset.pk, 'employee': self.emp.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Notification.objects.get(kind='asset_assigned').link, '/app/my-assets')
