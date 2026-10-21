from decimal import Decimal
from rest_framework.test import APITestCase
from apps.users.models import User


class FinanceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = User.objects.create_user(username='financehr', email='hr@finance.test', password='x', role='hr_admin')
        cls.emp = User.objects.create_user(username='financeemp', email='emp@finance.test', password='x', role='employee')
        cls.manager = User.objects.create_user(username='financemgr', email='mgr@finance.test', password='x', role='manager')

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def salary(self):
        response = self.as_user(self.hr).post('/api/finance/salaries/', {'employee': self.emp.pk, 'basic': '50000.00', 'allowances': '5000.00', 'deductions': '1500.00', 'effective_from': '2026-01-01'}, format='json')
        self.assertEqual(response.status_code, 201, getattr(response, 'data', None))
        return response.data

    def test_private_finance_for_hr_only(self):
        for user in [self.emp, self.manager]:
            for path in ['salaries', 'payslips', 'expenses', 'invoices', 'summary']:
                self.assertEqual(self.as_user(user).get(f'/api/finance/{path}/').status_code, 403)

    def test_payslip_snapshot_duplicates_and_finalized_lock(self):
        salary = self.salary()
        response = self.client.post('/api/finance/payslips/generate/', {'salary': salary['id'], 'period': '2026-10-01'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        slip = response.data; url = f"/api/finance/payslips/{slip['id']}/"
        self.assertEqual(Decimal(slip['net']), Decimal('53500.00'))
        self.client.patch(f"/api/finance/salaries/{salary['id']}/", {'basic': '60000.00'}, format='json')
        self.assertEqual(Decimal(self.client.get(url).data['basic']), Decimal('50000.00'))
        self.assertEqual(self.client.post('/api/finance/payslips/generate/', {'salary': salary['id'], 'period': '2026-10-01'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'issue/').status_code, 200)
        self.assertEqual(self.client.patch(url, {'basic': '1.00'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'mark-paid/', {'payment_reference': 'TEST-ONLY'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(url + 'void/').status_code, 400)

    def test_salary_and_period_validation(self):
        salary = self.salary()
        self.assertEqual(self.client.patch(f"/api/finance/salaries/{salary['id']}/", {'deductions': '90000.00'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/finance/payslips/generate/', {'salary': salary['id'], 'period': '2026-10-15'}, format='json').status_code, 400)

    def test_invoice_decimal_totals_and_issue_lock(self):
        r = self.as_user(self.hr).post('/api/finance/invoices/', {'number': 'TT-26-001', 'client_name': 'Acceptance client', 'issue_date': '2026-10-17', 'due_date': '2026-10-31', 'tax_amount': '10.10', 'items': [{'description': 'Engineering', 'quantity': '1.50', 'unit_price': '100.25'}]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data['total']), Decimal('160.48'))
        url = f"/api/finance/invoices/{r.data['id']}/"
        self.assertEqual(self.client.post(url + 'issue/').status_code, 200)
        self.assertEqual(self.client.patch(url, {'items': []}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_expense_approval_and_summary(self):
        r = self.as_user(self.hr).post('/api/finance/expenses/', {'employee': self.emp.pk, 'description': 'Survey transport', 'date': '2026-10-17', 'amount': '1200.25', 'category': 'travel'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        url = f"/api/finance/expenses/{r.data['id']}/"
        self.assertEqual(self.client.post(url + 'approve/').status_code, 400)
        self.assertEqual(self.client.post(url + 'submit/').status_code, 200)
        self.assertEqual(self.client.post(url + 'approve/').status_code, 200)
        self.assertEqual(self.client.patch(url, {'amount': '1.00'}, format='json').status_code, 400)
        self.assertEqual(Decimal(self.client.get('/api/finance/summary/').data['currencies'][0]['expenses_approved']), Decimal('1200.25'))

    def test_invoice_defaults_and_input_validation(self):
        payload = {'number': 'INV-INVALID', 'client_name': 'Test client', 'due_date': '2000-01-01', 'items': [{'description': 'Work', 'quantity': '1', 'unit_price': '10'}]}
        self.assertEqual(self.as_user(self.hr).post('/api/finance/invoices/', payload, format='json').status_code, 400)
        payload['due_date'] = '2099-01-01'
        payload['items'] = []
        self.assertEqual(self.client.post('/api/finance/invoices/', payload, format='json').status_code, 400)
        payload['items'] = [{'description': 'Work', 'quantity': '-1', 'unit_price': '10'}]
        self.assertEqual(self.client.post('/api/finance/invoices/', payload, format='json').status_code, 400)

    def test_expense_rejection_resubmission_payment_and_state_tampering(self):
        r = self.as_user(self.hr).post('/api/finance/expenses/', {'employee': self.emp.pk, 'description': 'Test only', 'date': '2026-10-17', 'amount': '10.25', 'status': 'paid'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['status'], 'draft')
        url = f"/api/finance/expenses/{r.data['id']}/"
        self.client.post(url + 'submit/')
        self.assertEqual(self.client.post(url + 'reject/', {'decision_note': 'Add receipt reference'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'notes': 'Receipt reference EX-1'}, format='json').status_code, 200)
        self.client.post(url + 'submit/')
        self.client.post(url + 'approve/')
        self.assertEqual(self.client.post(url + 'mark-paid/', {}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'mark-paid/', {'payment_reference': 'TEST-ONLY'}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 400)

    def test_salary_excludes_guests_inactive_users_and_duplicate_structures(self):
        salary = self.salary()
        self.assertEqual(self.client.post('/api/finance/salaries/', {'employee': self.emp.pk}, format='json').status_code, 400)
        self.emp.is_active = False
        self.emp.save(update_fields=['is_active'])
        self.assertEqual(self.client.post('/api/finance/payslips/generate/', {'salary': salary['id'], 'period': '2026-10-01'}, format='json').status_code, 400)

    def test_summary_keeps_currencies_separate_and_excludes_void_invoices(self):
        for number, currency, amount in [('NPR-1', 'NPR', '100'), ('USD-1', 'USD', '2')]:
            invoice = self.as_user(self.hr).post('/api/finance/invoices/', {'number': number, 'client_name': 'Test', 'issue_date': '2026-10-17', 'due_date': '2026-10-31', 'currency': currency, 'items': [{'description': 'Test', 'quantity': '1', 'unit_price': amount}]}, format='json')
            self.assertEqual(invoice.status_code, 201, invoice.data)
            self.client.post(f"/api/finance/invoices/{invoice.data['id']}/issue/")
        totals = {row['currency']: row for row in self.client.get('/api/finance/summary/').data['currencies']}
        self.assertEqual(Decimal(totals['NPR']['invoice_outstanding']), Decimal('100'))
        self.assertEqual(Decimal(totals['USD']['invoice_outstanding']), Decimal('2'))
        self.client.post(f"/api/finance/invoices/{invoice.data['id']}/void/")
        totals = {row['currency']: row for row in self.client.get('/api/finance/summary/').data['currencies']}
        self.assertNotIn('USD', totals)


class FinanceSeparationOfDutiesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = User.objects.create_user(username='sodhr', email='hr@sod.test', password='x', role='hr_admin')
        cls.hr2 = User.objects.create_user(username='sodhr2', email='hr2@sod.test', password='x', role='hr_admin')
        cls.boss = User.objects.create_user(username='sodboss', email='boss@sod.test', password='x', role='super_admin')

    def test_hr_cannot_set_own_salary(self):
        self.client.force_authenticate(self.hr)
        r = self.client.post('/api/finance/salaries/', {'employee': self.hr.pk, 'basic': '1.00', 'allowances': '0', 'deductions': '0', 'effective_from': '2026-01-01'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.client.force_authenticate(self.hr2)
        r = self.client.post('/api/finance/salaries/', {'employee': self.hr.pk, 'basic': '1.00', 'allowances': '0', 'deductions': '0', 'effective_from': '2026-01-01'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.patch(f"/api/finance/salaries/{r.data['id']}/", {'basic': '999999.00'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/finance/payslips/generate/', {'salary': r.data['id'], 'period': '2026-10-01'}, format='json').status_code, 403)

    def test_hr_cannot_approve_own_expense_but_others_can(self):
        self.client.force_authenticate(self.hr)
        e = self.client.post('/api/finance/expenses/', {'employee': self.hr.pk, 'description': 'Taxi', 'date': '2026-10-01', 'category': 'travel', 'amount': '10.00', 'currency': 'NPR'}, format='json')
        self.assertEqual(e.status_code, 201, e.data)
        url = f"/api/finance/expenses/{e.data['id']}/"
        self.assertEqual(self.client.post(url + 'submit/').status_code, 200)
        self.assertEqual(self.client.post(url + 'approve/', {}, format='json').status_code, 403)
        self.client.force_authenticate(self.boss)
        self.assertEqual(self.client.post(url + 'approve/', {}, format='json').status_code, 200)


class FinanceListQueryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Expense
        cls.hr = User.objects.create_user(username='finq', email='q@finance.test', password='x', role='hr_admin')
        cls.emp = User.objects.create_user(username='finqe', email='qe@finance.test', password='x', role='employee',
                                           first_name='Sita')
        for i in range(12):
            Expense.objects.create(employee=cls.emp, description=f'Taxi {i}' if i % 3 else f'Laptop {i}',
                                   amount=Decimal(i + 1), status='submitted' if i < 4 else 'draft', created_by=cls.hr)

    def setUp(self):
        self.client.force_authenticate(self.hr)

    def test_expenses(self):
        self.assertIsInstance(self.client.get('/api/finance/expenses/').data, list)
        r = self.client.get('/api/finance/expenses/', {'page': 1, 'page_size': 5, 'ordering': '-amount'})
        self.assertEqual((r.data['count'], len(r.data['results']), r.data['results'][0]['amount']), (12, 5, '12.00'))
        self.assertEqual(self.client.get('/api/finance/expenses/', {'page': 1, 'search': 'laptop'}).data['count'], 4)
        self.assertEqual(self.client.get('/api/finance/expenses/', {'page': 1, 'search': 'sita'}).data['count'], 12)
        self.assertEqual(self.client.get('/api/finance/expenses/', {'page': 1, 'status': 'submitted'}).data['count'], 4)

    def test_other_finance_lists_accept_paging(self):
        for path in ('salaries', 'payslips', 'invoices'):
            r = self.client.get(f'/api/finance/{path}/', {'page': 1, 'search': 'x', 'ordering': 'id'})
            self.assertEqual((r.status_code, r.data['count']), (200, 0), path)
