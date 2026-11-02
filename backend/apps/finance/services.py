import csv
import io
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .fiscal import fy_of
from .models import ZERO, Category, Expense, FiscalYearClose, Invoice, Payslip, Transaction, q2

SSF_EMPLOYEE_RATE = Decimal('0.11')
SSF_EMPLOYER_RATE = Decimal('0.20')
SST_RATE = Decimal('0.01')


def summary_payload():
    """All-period ledger totals, kept separate by currency."""
    totals = defaultdict(lambda: {'payroll_paid': Decimal('0'), 'expenses_approved': Decimal('0'), 'invoice_outstanding': Decimal('0')})
    for slip in Payslip.objects.filter(status='paid'):
        totals[slip.currency]['payroll_paid'] += slip.net
    for expense in Expense.objects.filter(status__in=['approved', 'paid']):
        totals[expense.currency]['expenses_approved'] += expense.amount
    for invoice in Invoice.objects.filter(status='issued').prefetch_related('items'):
        totals[invoice.currency]['invoice_outstanding'] += invoice.total
    return {'currencies': [{'currency': currency, **{key: str(value.quantize(Decimal('.01'))) for key, value in values.items()}} for currency, values in sorted(totals.items())], 'draft_payslips': Payslip.objects.filter(status='draft').count(), 'submitted_expenses': Expense.objects.filter(status='submitted').count()}


# ---------------------------------------------------------------- payroll

def apply_statutory(slip, ssf_enrolled):
    """SSF members: 11% of basic from the employee + 20% from the company, no SST.
    Others: 1% social security tax on gross."""
    # ponytail: flat 1% SST is only right inside the first tax slab; add slab-based TDS when an annual salary exceeds it.
    if ssf_enrolled:
        slip.ssf_employee = q2(slip.basic * SSF_EMPLOYEE_RATE)
        slip.ssf_employer = q2(slip.basic * SSF_EMPLOYER_RATE)
        slip.tds = ZERO
    else:
        slip.ssf_employee = slip.ssf_employer = ZERO
        slip.tds = q2(slip.gross * SST_RATE)
    return slip


def new_payslip(salary, period, user, working_days=None, days_worked=None, bonus=ZERO):
    slip = Payslip(employee=salary.employee, period=period, basic=salary.basic, allowances=salary.allowances,
                   deductions=salary.deductions, bonus=bonus, working_days=working_days, days_worked=days_worked,
                   created_by=user)
    apply_statutory(slip, salary.ssf_enrolled)
    if slip.net < 0:
        raise ValidationError(f'{salary.employee.get_full_name()}: deductions exceed pay for this month.')
    slip.save()
    return slip


def match_payments(period, user):
    """Link each issued/paid payslip of `period` to the bank debit that paid its net amount (exact, or + a Rs 10
    fonepay fee): within 3 days of its recorded paid date, else from a week before to 45 days after month end;
    issued slips become paid. A line already linked to
    the employee (or naming them) wins, earliest first, so matching months in order pairs equal monthly salaries
    correctly. Unnamed lines are used only when exactly one fits."""
    end = (period.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    linked, ambiguous, missing = [], [], []
    taken = set(Transaction.objects.filter(payslip__isnull=False).values_list('pk', flat=True))
    for slip in Payslip.objects.filter(period=period, status__in=['issued', 'paid'], transactions__isnull=True).select_related('employee'):
        first = (slip.employee.first_name or '').split(' ')[0]
        paid = slip.paid_at and timezone.localtime(slip.paid_at).date()
        window = (paid - timedelta(days=3), paid + timedelta(days=3)) if paid else (end - timedelta(days=7), end + timedelta(days=45))
        cands = [t for t in Transaction.objects.filter(
            debit__in=[slip.net, slip.net + 10], date__range=window,
            payslip__isnull=True).filter(Q(employee=slip.employee) | Q(employee__isnull=True)).order_by('date', 'id')
            if t.pk not in taken]
        named = [t for t in cands if t.employee_id == slip.employee_id or (first and first.lower() in t.party.lower())]
        pick = named[:1] or (cands if len(cands) == 1 else [])
        label = f'{slip.employee.get_full_name()} {slip.net}'
        if not pick:
            (ambiguous if cands else missing).append(label)
            continue
        txn = pick[0]
        with transaction.atomic():
            txn.payslip, txn.employee = slip, slip.employee
            txn.save(update_fields=['payslip', 'employee', 'updated_at'])
            if slip.status == 'issued':
                slip.status, slip.paid_at = 'paid', timezone.now()
                slip.payment_reference = slip.payment_reference or (txn.reference or txn.description)[:200]
                slip.save(update_fields=['status', 'paid_at', 'payment_reference'])
        taken.add(txn.pk)
        linked.append(label)
    return {'linked': linked, 'ambiguous': ambiguous, 'missing': missing}


# ---------------------------------------------------------------- books

def assert_open(*days):
    for day in days:
        if day and FiscalYearClose.objects.filter(name=fy_of(day)).exists():
            raise ValidationError(f'Fiscal year {fy_of(day)} is closed. Reopen it (super admin) to change its records.')


HEADER_KEYS = [  # (field, keywords) -- first match wins, in this order
    ('date', ['date (ad)', 'txn date', 'transaction date', 'date']),
    ('description', ['description', 'particular', 'narration', 'details', 'remarks']),
    ('debit', ['debit', 'withdraw', 'dr']),
    ('credit', ['credit', 'deposit', 'cr']),
    ('amount', ['amount']),
    ('party', ['party', 'paid to', 'payee']),
    ('category', ['category']),
    ('note', ['note']),
    ('reference', ['reference', 'ref', 'cheque', 'chq']),
]
SKIP_HEADER = re.compile(r'nepali|miti|\bbs\b|value date|balance')


def _map_header(cells):
    names = [str(c or '').strip().lower() for c in cells]
    cols = {}
    for field, keys in HEADER_KEYS:
        for i, n in enumerate(names):
            if i in cols.values() or not n or (field == 'date' and SKIP_HEADER.search(n)) or (field != 'date' and 'balance' in n):
                continue
            if any(n == k or (len(k) > 3 and k in n) for k in keys):
                cols[field] = i
                break
    return cols if 'date' in cols and ({'debit', 'credit'} & cols.keys() or 'amount' in cols) else None


def _money(v):
    if v in (None, ''):
        return ZERO
    if isinstance(v, (int, float, Decimal)):
        return q2(Decimal(str(v)))
    s = re.sub(r'[^\d.\-]', '', str(v).replace(',', ''))
    try:
        return q2(Decimal(s)) if s not in ('', '-', '.') else ZERO
    except InvalidOperation:
        return ZERO


def _date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or '').strip()[:10]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_statement(upload):
    """Rows from a CSV or Excel bank statement / ledger export. Finds the header row itself, skips
    opening-balance and total lines. Returns [{date, description, debit, credit, party, category, note, reference}]."""
    name = upload.name.lower()
    if name.endswith(('.xlsx', '.xlsm')):
        from openpyxl import load_workbook
        ws = load_workbook(upload, read_only=True, data_only=True).active
        table = [list(r) for r in ws.iter_rows(values_only=True)]
    elif name.endswith('.csv'):
        text = upload.read().decode('utf-8-sig', errors='replace')
        table = list(csv.reader(io.StringIO(text)))
    else:
        raise ValidationError({'file': 'Upload a .csv or .xlsx statement.'})
    for h, row in enumerate(table[:30]):
        cols = _map_header(row)
        if cols:
            break
    else:
        raise ValidationError({'file': 'No header row with a date and debit/credit (or amount) column was found.'})
    cats = {c.name.lower(): c for c in Category.objects.all()}
    out = []
    for row in table[h + 1:]:
        get = lambda f: row[cols[f]] if f in cols and cols[f] < len(row) else None  # noqa: E731
        day = _date(get('date'))
        if 'amount' in cols and not ({'debit', 'credit'} & cols.keys()):
            amt = _money(get('amount'))
            debit, credit = (-amt, ZERO) if amt < 0 else (ZERO, amt)
        else:
            debit, credit = abs(_money(get('debit'))), abs(_money(get('credit')))
        desc = ' '.join(str(get('description') or '').split())
        if not day or (debit == 0) == (credit == 0) or re.search(r'previous balance|opening balance|^total', desc, re.I):
            continue
        cat = str(get('category') or '').strip().lower()
        out.append({'date': day, 'description': desc[:500] or '(no description)', 'debit': debit, 'credit': credit,
                    'party': str(get('party') or '').strip()[:200], 'category': cats.get(cat),
                    'note': str(get('note') or '').strip(), 'reference': str(get('reference') or '').strip()[:120]})
    return out


def _key(r):
    return (r['date'], r['debit'], r['credit'], re.sub(r'\W+', '', r['description'].lower())[:40])


@transaction.atomic
def import_rows(account, rows, user, dry_run=False, status=Transaction.Status.REVIEW):
    """Add statement rows to `account`, skipping rows already in the ledger (same date, amounts, description)."""
    if not rows:
        return {'created': 0, 'duplicates': 0, 'rows': []}
    days = [r['date'] for r in rows]
    have = {_key({'date': t.date, 'debit': t.debit, 'credit': t.credit, 'description': t.description})
            for t in account.transactions.filter(date__range=(min(days), max(days)))}
    preview, new = [], []
    for r in rows:
        dup = _key(r) in have
        if r['date'] < account.opening_date:
            raise ValidationError(f"{r['date']} is before this account's opening date ({account.opening_date}).")
        preview.append({**{k: (v.name if isinstance(v, Category) else str(v) if isinstance(v, (Decimal, date)) else v)
                           for k, v in r.items() if k != 'employee'}, 'duplicate': dup})
        if not dup:
            new.append(Transaction(account=account, created_by=user, status=r.get('status', status),
                                   **{k: v for k, v in r.items() if k not in ('status',)}))
    if not dry_run:
        assert_open(*{t.date for t in new})
        from apps.audit.services import record_created
        for t in Transaction.objects.bulk_create(new):
            record_created(t)
    return {'created': len(new), 'duplicates': len(rows) - len(new), 'rows': preview}
