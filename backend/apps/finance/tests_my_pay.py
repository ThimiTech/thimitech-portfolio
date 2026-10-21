import datetime
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User

from .models import Payslip, SalaryStructure


def mk(email, role):
    return User.objects.create_user(username=email.split('@')[0], email=email, password='x', role=role, first_name=email[:3])


def slip(user, month, status, by):
    return Payslip.objects.create(employee=user, period=datetime.date(2026, month, 1), basic=Decimal('1000.00'),
                                  allowances=Decimal('100.00'), deductions=Decimal('50.00'), status=status, created_by=by)


class MyPayTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = mk('hr@pay.test', 'hr_admin')
        cls.owner = mk('own@pay.test', 'super_admin')
        cls.emp = mk('emp@pay.test', 'employee')
        cls.other = mk('oth@pay.test', 'employee')
        cls.guest = mk('gst@pay.test', 'guest')
        cls.issued = slip(cls.emp, 1, 'issued', cls.hr)
        cls.paid = slip(cls.emp, 2, 'paid', cls.hr)
        cls.draft = slip(cls.emp, 3, 'draft', cls.hr)
        cls.void = slip(cls.emp, 4, 'void', cls.hr)
        cls.others = slip(cls.other, 1, 'issued', cls.hr)
        cls.owners = slip(cls.owner, 1, 'paid', cls.hr)
        cls.hrs = slip(cls.hr, 1, 'issued', cls.owner)

    def get(self, user, path=''):
        self.client.force_authenticate(user)
        return self.client.get(f'/api/finance/my-payslips/{path}')

    def test_lists_only_own_issued_and_paid(self):
        r = self.get(self.emp)
        self.assertEqual(r.status_code, 200)
        self.assertEqual({s['id'] for s in r.data}, {self.issued.pk, self.paid.pk})
        self.assertEqual(Decimal(r.data[0]['net']), Decimal('1050.00'))
        self.assertNotIn('employee', r.data[0])  # no ids to pivot on

    def test_cannot_open_drafts_void_or_someone_elses(self):
        for s in (self.draft, self.void, self.others, self.owners):
            self.assertEqual(self.get(self.emp, f'{s.pk}/').status_code, 404, s.status)
        self.assertEqual(self.get(self.emp, f'{self.issued.pk}/').status_code, 200)

    def test_hr_my_pay_never_shows_super_admins_or_others(self):
        r = self.get(self.hr)
        self.assertEqual([s['id'] for s in r.data], [self.hrs.pk])
        self.assertEqual(self.get(self.hr, f'{self.owners.pk}/').status_code, 404)

    def test_read_only_and_staff_only(self):
        self.client.force_authenticate(self.emp)
        self.assertEqual(self.client.post('/api/finance/my-payslips/', {}).status_code, 405)
        self.assertEqual(self.client.patch(f'/api/finance/my-payslips/{self.issued.pk}/', {'basic': '1'}).status_code, 405)
        self.assertEqual(self.get(self.guest).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/finance/my-payslips/').status_code, 401)

    def test_issue_notification_links_to_my_pay(self):
        salary = SalaryStructure.objects.create(employee=self.other, basic=Decimal('500.00'), effective_from=datetime.date(2026, 1, 1))
        self.client.force_authenticate(self.hr)
        r = self.client.post('/api/finance/payslips/generate/', {'salary': salary.pk, 'period': '2026-09-01'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.post(f"/api/finance/payslips/{r.data['id']}/issue/").status_code, 200)
        n = Notification.objects.get(recipient=self.other, kind='payslip_issued')
        self.assertEqual(n.link, f"/app/my-pay/{r.data['id']}")
