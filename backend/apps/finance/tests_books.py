import io
import zipfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.users.models import User
from .fiscal import bs_str, fy_of, fy_range, next_bs_month_day
from .models import Account, Category, FiscalYearClose, Payslip, SalaryStructure, Transaction
from .services import new_payslip


def user(email, role, **kw):
    return User.objects.create_user(username=email, email=email, password='x', role=role, **kw)


class FiscalTests(APITestCase):
    def test_dates_match_the_prabhu_statement(self):
        self.assertEqual(bs_str(date(2025, 7, 18)), '2082-04-02')
        self.assertEqual(bs_str(date(2026, 5, 15)), '2083-02-01')
        self.assertEqual(fy_of(date(2025, 7, 17)), '2082/83')
        self.assertEqual(fy_of(date(2025, 7, 16)), '2081/82')
        self.assertEqual(fy_range('2082/83'), (date(2025, 7, 17), date(2026, 7, 16)))
        self.assertEqual(next_bs_month_day(date(2026, 1, 31), 25), date(2026, 3, 9))  # 17 Magh 2082 -> 25 Falgun


class PayrollMathTests(APITestCase):
    """Salary-sheet arithmetic (SSF + Dashain bonus; a pro-rated month with 1% SST), to the rupee."""
    def setUp(self):
        self.hr = user('hr@x.com', 'hr_admin')

    def slip(self, basic, allowances, ssf, **kw):
        emp = user(f'e{basic}{allowances}@x.com', 'employee', first_name='E')
        st = SalaryStructure.objects.create(employee=emp, basic=basic, allowances=allowances, ssf_enrolled=ssf)
        return new_payslip(st, date(2026, 9, 1), self.hr, **kw)

    def test_ssf_member_with_dashain_bonus(self):
        s = self.slip(Decimal('30000'), Decimal('10000'), True, bonus=Decimal('30000'))
        self.assertEqual((s.gross, s.ssf_employee, s.tds, s.net, s.ssf_employer), (70000, Decimal('3300.00'), 0, Decimal('66700.00'), Decimal('6000.00')))

    def test_prorated_month_with_one_percent_sst(self):
        s = self.slip(Decimal('17000'), Decimal('0'), False, working_days=27, days_worked=21)
        self.assertEqual((s.gross, s.tds, s.net), (Decimal('13222.22'), Decimal('132.22'), Decimal('13090.00')))


class BooksTests(APITestCase):
    def setUp(self):
        self.hr = user('hr@x.com', 'hr_admin')
        self.ca = user('ca@x.com', 'accountant')
        self.emp = user('emp@x.com', 'employee', first_name='Asha', last_name='Tamang')
        self.acct = Account.objects.create(name='Bank', opening_balance=Decimal('1000000.00'), opening_date=date(2025, 7, 17))
        self.fee = Category.objects.get(name='Bank charges')

    def txn(self, day, debit=0, credit=0, **kw):
        return Transaction.objects.create(account=self.acct, date=day, description=kw.pop('description', 'x'), debit=debit,
                                          credit=credit, created_by=self.hr, **kw)

    def test_access_finance_roles_only(self):
        self.client.force_authenticate(self.emp)
        for path in ['transactions', 'accounts', 'statements', 'reports/overview', 'export']:
            self.assertEqual(self.client.get(f'/api/finance/{path}/').status_code, 403, path)
        self.assertEqual(self.client.get('/api/finance/categories/').status_code, 200)  # claims need them
        self.client.force_authenticate(self.ca)
        self.assertEqual(self.client.get('/api/finance/transactions/').status_code, 200)
        self.assertEqual(self.client.get('/api/finance/payslips/').status_code, 200)
        self.assertEqual(self.client.get('/api/org/people/').status_code, 200)  # staff-level elsewhere

    def test_one_side_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.txn(date(2025, 8, 1), debit=5, credit=5)

    def test_running_balance_ignores_filters(self):
        self.txn(date(2025, 7, 18), debit=Decimal('400000'))
        self.txn(date(2025, 7, 18), debit=Decimal('8'), category=self.fee)
        self.txn(date(2026, 1, 1), credit=Decimal('250000'))
        self.client.force_authenticate(self.hr)
        rows = self.client.get('/api/finance/transactions/', {'category': self.fee.pk}).data
        self.assertEqual(Decimal(rows[0]['balance']), Decimal('599992.00'))
        self.assertEqual(rows[0]['bs_date'], '2082-04-02')
        self.assertEqual(self.acct.balance_on(), Decimal('849992.00'))

    def test_statement_import_previews_then_skips_duplicates(self):
        csv = ('Date,Nepali Date,Description,Debit,Credit,Balance\n'
               '16-07-2025,,PREVIOUS BALANCE,,,"10,00,000.00"\n'
               '18-07-2025,02-04-2082,TRF/EXP-1001 Account Check,111.00,0.00,"9,99,889.00"\n'
               '23-09-2025,07-06-2082,QR-2002,0.00,"100,000.00","10,99,889.00"\n')
        self.client.force_authenticate(self.ca)
        up = lambda dry: self.client.post('/api/finance/transactions/import/', {  # noqa: E731
            'account': self.acct.pk, 'dry_run': dry, 'file': SimpleUploadedFile('s.csv', csv.encode())}, format='multipart')
        r = up(True)
        self.assertEqual((r.data['created'], Transaction.objects.count()), (2, 0))
        self.assertEqual(up(False).data['created'], 2)
        again = up(False).data
        self.assertEqual((again['created'], again['duplicates']), (0, 2))
        self.assertEqual(self.acct.balance_on(), Decimal('1099889.00'))

    def test_closed_year_is_read_only(self):
        t = self.txn(date(2025, 8, 1), debit=10)
        FiscalYearClose.objects.create(name='2082/83', closed_by=self.hr)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.patch(f'/api/finance/transactions/{t.pk}/', {'note': 'late'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/finance/transactions/{t.pk}/').status_code, 400)

    def test_match_payments_links_salary_and_marks_paid(self):
        st = SalaryStructure.objects.create(employee=self.emp, basic=Decimal('17000'))
        slip = new_payslip(st, date(2026, 1, 1), self.hr)
        Payslip.objects.filter(pk=slip.pk).update(status='issued')
        t = self.txn(date(2026, 2, 3), debit=slip.net, party='Asha Tamang')
        self.txn(date(2026, 2, 3), debit=Decimal('25000'))  # someone else's salary
        self.client.force_authenticate(self.hr)
        r = self.client.post('/api/finance/payslips/match-payments/', {'period': '2026-01-01'}, format='json')
        self.assertEqual(len(r.data['linked']), 1, r.data)
        t.refresh_from_db(); slip.refresh_from_db()
        self.assertEqual((t.payslip_id, t.employee_id, slip.status), (slip.pk, self.emp.pk, 'paid'))

    def test_reconciliation_and_exports(self):
        self.txn(date(2025, 7, 18), debit=Decimal('300000'))
        self.client.force_authenticate(self.hr)
        st = self.client.post('/api/finance/statements/', {'account': self.acct.pk, 'start': '2025-07-17', 'end': '2025-07-31',
                                                           'opening_balance': '1000000.00', 'closing_balance': '700000.00'}, format='json')
        self.assertTrue(st.data['reconciliation']['reconciled'], st.data)
        x = self.client.get('/api/finance/export/', {'what': 'book', 'fy': '2082/83'})
        self.assertEqual(x.status_code, 200)
        self.assertTrue(x.content.startswith(b'PK'))
        c = self.client.get('/api/finance/export/', {'what': 'ledger', 'type': 'csv', 'fy': '2082/83'})
        self.assertIn('700000.00', c.content.decode('utf-8-sig'))
        pack = self.client.get('/api/finance/export/audit-pack/', {'fy': '2082/83'})
        names = zipfile.ZipFile(io.BytesIO(b''.join(pack.streaming_content))).namelist()
        self.assertIn('README.txt', names)
        overview = self.client.get('/api/finance/reports/overview/', {'fy': '2082/83'}).data
        self.assertEqual(overview['kinds']['uncategorized']['out'], '300000.00')
