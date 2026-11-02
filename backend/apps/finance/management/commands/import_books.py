"""Import existing books kept outside the app. Every part is optional and safe to re-run (duplicates are skipped).
Usually run for you by `load_books_bundle`; the real files and names live in that private bundle, never in this repo.

  manage.py import_books --ledger ledger.json              # {opening, statementClosing, rows:[{ad,bs,desc,party,cat,note,dr,cr}]}
                         --account "Bank · Current" --institution "Bank, branch" --number 0123...
                         --salary-xlsx book.xlsx --salary-sheet "2026-salary sheet"   # "Salary Month:" blocks
                         --expense-xlsx book.xlsx --expense-sheet Finance            # staff-paid expenses + dollar card
                         --claimants '{"Sam": "Sam Shrestha"}'                      # sheet short name -> staff full name
                         --ledger-categories '{"Transfer to Sam": "Director transfers"}'
                         --statement-images DIR --create-staff
"""
import json
import os
import re
from datetime import date, datetime
from decimal import Decimal

from django.core.files import File as DjFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.drive.access import ensure_path
from apps.drive.models import File
from apps.finance.fiscal import fy_of, fy_range
from apps.finance.models import Account, Category, Expense, Payslip, SalaryStructure, Statement, q2
from apps.finance.services import import_rows, match_payments
from apps.org.models import EmployeeProfile
from apps.users.models import User

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
REVIEW = re.compile(r'confirm|not stated|not named|not on statement|please check|purpose', re.I)
LEDGER_CATEGORIES = {
    'Bank charges': 'Bank charges', 'Salary': 'Salary', 'Dashain bonus': 'Bonus & festival allowance',
    'TT Credit payback': 'Loan repaid', 'Printing & binding': 'Printing & stationery', 'Loan given': 'Loan given',
    'Loan repaid': 'Loan repaid', 'Income': 'Client income',
}
CLAIM_CATEGORIES = [  # (regex on particulars, regex on sheet category, category)
    (r'meet|khaaja|momo|qfx|movie', r'', 'Meetings & refreshments'),
    (r'flex|sticker|festival', r'', 'Marketing & events'),
    (r'domain|server|email|google api', r'', 'Server & domains'),
    (r'punching|stamp|furniture|plug|bottle|vat bill', r'', 'Office & operations'),
    (r'', r'^salary', 'Salary'), (r'', r'^legal', 'Legal & professional fees'), (r'', r'^accounting', 'Accounting & audit'),
    (r'', r'^bank', 'Bank charges'), (r'', r'^project', 'Project expenses'), (r'', r'^tax', 'Income tax'),
    (r'', r'^r ?& ?d', 'Research & development'), (r'', r'^server', 'Server & domains'),
    (r'', r'^(meetup|refreshment)', 'Meetings & refreshments'), (r'', r'^service', 'Software & subscriptions'),
    (r'', r'', 'Office & operations'),
]


def cat(name):
    return Category.objects.get(name=name) if name else None


def month_of(text):
    t = str(text).lower()
    for i, m in enumerate(MONTHS):
        if m in t:
            return i + 1
    return None


def clean_number(v):
    if v is None or v == '':
        return ''
    return str(int(v)) if isinstance(v, float) else str(v).strip()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, p):
        p.add_argument('--ledger')
        p.add_argument('--account', default='Main bank account')
        p.add_argument('--institution', default='')
        p.add_argument('--number', default='')
        p.add_argument('--opening-date', required=False, help='Account opening date (YYYY-MM-DD); needed with --ledger.')
        p.add_argument('--statement-notes', default='')
        p.add_argument('--claimants', default='{}', help='JSON: name used in the expense sheet -> staff full name.')
        p.add_argument('--ledger-categories', default='{}', help='JSON: extra ledger category label -> category name.')
        p.add_argument('--statement-images')
        p.add_argument('--salary-xlsx')
        p.add_argument('--salary-sheet', default='2026-salary sheet')
        p.add_argument('--expense-xlsx')
        p.add_argument('--expense-sheet', default='Finance')
        p.add_argument('--create-staff', action='store_true')

    def handle(self, **o):
        self.create_staff = o['create_staff']
        self.claimants = json.loads(o['claimants'])
        self.categories = {**LEDGER_CATEGORIES, **json.loads(o['ledger_categories'])}
        self.admin = User.objects.filter(role='super_admin').order_by('pk').first()
        if not self.admin:
            raise CommandError('Create a super admin first; imported records need a "created by".')
        # Sheets first (they name the staff), then the bank ledger, then link salary payments to bank lines.
        if o['expense_xlsx']:
            self.expenses(o['expense_xlsx'], o['expense_sheet'])
        if o['salary_xlsx']:
            self.salary(o['salary_xlsx'], o['salary_sheet'])
        if o['ledger']:
            self.ledger(o)
        for period in Payslip.objects.order_by('period').values_list('period', flat=True).distinct():
            res = match_payments(period, self.admin)
            if res['linked']:
                self.stdout.write(f"  {period:%b %Y} salary paid by bank: {', '.join(res['linked'])}")

    # ------------------------------------------------------------ people

    def person(self, full_name, create=True):
        full_name = ' '.join(str(full_name or '').split())
        if not full_name:
            return None
        first, _, last = full_name.partition(' ')
        qs = User.objects.exclude(role='guest')
        u = qs.filter(first_name__iexact=first, last_name__iexact=last).first() if last else None
        if not u:
            hits = list(qs.filter(first_name__iexact=first))
            u = hits[0] if len(hits) == 1 and (not last or not hits[0].last_name) else None
        if u or not (create and self.create_staff):
            return u
        slug = re.sub(r'[^a-z]+', '.', full_name.lower()).strip('.')
        u = User.objects.create_user(username=slug, email=f'{slug}@staff.thimitech.local', first_name=first,
                                     last_name=last, role='employee')
        u.set_unusable_password()
        u.save()
        self.stdout.write(f'  + staff {full_name} <{u.email}> (placeholder email: set the real one in People)')
        return u

    # ------------------------------------------------------------ ledger

    @transaction.atomic
    def ledger(self, o):
        if not o['opening_date']:
            raise CommandError('--opening-date is required with --ledger.')
        with open(o['ledger'], encoding='utf-8') as fh:
            data = json.load(fh)
        data = data.get('data', data)
        acct, made = Account.objects.get_or_create(name=o['account'], defaults={
            'institution': o['institution'], 'number': o['number'], 'opening_balance': Decimal(str(data['opening'])),
            'opening_date': date.fromisoformat(o['opening_date'])})
        rows = []
        for r in data['rows']:
            category = self.categories.get(r.get('cat') or '')
            party = (r.get('party') or '').strip()
            note = (r.get('note') or '').strip()
            rows.append({'date': date.fromisoformat(r['ad']), 'description': r['desc'][:500], 'party': party[:200],
                         'debit': q2(Decimal(str(r.get('dr') or 0))), 'credit': q2(Decimal(str(r.get('cr') or 0))),
                         'category': cat(category), 'note': note, 'reference': '',
                         'employee': self.person(party, create=False) if party else None,
                         'status': 'review' if not category or REVIEW.search(note) else 'confirmed'})
        res = import_rows(acct, rows, self.admin)
        self.stdout.write(self.style.SUCCESS(f"Ledger '{acct.name}': {res['created']} added, {res['duplicates']} already there"))
        if data.get('statementClosing') is not None:
            st, _ = Statement.objects.get_or_create(account=acct, start=acct.opening_date, end=fy_range(fy_of(acct.opening_date))[1],
                                                   defaults={'opening_balance': acct.opening_balance, 'closing_balance': Decimal(str(data['statementClosing'])),
                                                             'notes': o['statement_notes'], 'created_by': self.admin})
            from apps.finance.reports import reconciliation
            rec = reconciliation(st)
            self.stdout.write(f"  statement {st.start}..{st.end}: closing {st.closing_balance}, ledger {rec['computed_closing']} "
                              f"-> {'RECONCILED' if rec['reconciled'] else 'difference ' + rec['difference']}")
            if o['statement_images']:
                folder = ensure_path('finance', ['Bank statements', f'FY {fy_of(st.end).replace("/", "-")}'], fiscal_year=fy_of(st.end))
                for name in sorted(os.listdir(o['statement_images'])):
                    if not name.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                        continue
                    label = f'{acct.name} statement page {name}'
                    if File.objects.filter(folder=folder, name=label).exists():
                        continue
                    with open(os.path.join(o['statement_images'], name), 'rb') as fh:
                        f = File(space='finance', folder=folder, name=label, statement=st, fiscal_year=fy_of(st.end),
                                 size=os.path.getsize(os.path.join(o['statement_images'], name)))
                        f.file.save(name, DjFile(fh), save=True)

    # ------------------------------------------------------------ salary sheet

    def salary(self, path, sheet):
        from openpyxl import load_workbook
        ws = load_workbook(path, data_only=True)[sheet]
        blocks, cur, cols = [], None, None
        for row in ws.iter_rows(values_only=True):
            a = str(row[0] or '')
            if a.startswith('Salary Month:'):
                label = a.split(':', 1)[1].strip()
                m, y = month_of(label), int(re.search(r'20\d\d', label)[0])
                paid = re.search(r'(\d+)-(\d+)-(\d{4})', str(row[1] or ''))
                cur = {'period': date(y, m, 1), 'paid': date(int(paid[3]), int(paid[1]), int(paid[2])) if paid else None, 'rows': []}
                blocks.append(cur)
            elif a.startswith('S.N'):
                cols = {str(h or '').strip().lower(): i for i, h in enumerate(row)}
            elif cur and cols and isinstance(row[0], (int, float)) and row[1]:
                g = lambda *keys: next((row[i] for k, i in cols.items() if any(k.startswith(x) for x in keys) and i < len(row)), None)  # noqa: E731
                cur['rows'].append({'name': row[1], 'bank_account': clean_number(row[2]), 'bank_name': str(row[3] or '').strip(),
                                    'pan': clean_number(row[4]),
                                    'join': row[6] if isinstance(row[6], datetime) else None,
                                    'basic': g('monthly salary'), 'da': g('dearness'), 'bonus': g('dashain'),
                                    'wd': g('working days'), 'worked': g('days worked'), 'gross': g('gross'),
                                    'ssf': g('ssf'), 'tds': g('sst'), 'other': g('other'), 'net': g('net')})
        latest, first_seen = {}, {}
        made = 0
        D = lambda v: q2(Decimal(str(v or 0)))  # noqa: E731
        with transaction.atomic():
            for b in blocks:
                for r in b['rows']:
                    u = self.person(r['name'])
                    if not u:
                        self.stdout.write(self.style.WARNING(f"  ? no staff named {r['name']} (use --create-staff)"))
                        continue
                    latest[u] = (b['period'], r)
                    first_seen.setdefault(u, b['period'])
                    if r['join']:
                        EmployeeProfile.objects.update_or_create(user=u, defaults={'join_date': r['join'].date()})
                    wd, worked = (int(r['wd']), int(r['worked'])) if r['wd'] and r['worked'] else (None, None)
                    slip = Payslip(employee=u, period=b['period'], basic=D(r['basic']), allowances=D(r['da']), bonus=D(r['bonus']),
                                   working_days=wd, days_worked=worked, ssf_employee=D(r['ssf']), tds=D(r['tds']),
                                   deductions=D(r['other']), ssf_employer=q2(D(r['basic']) * Decimal('0.20')) if D(r['ssf']) else D(0),
                                   status='paid', issued_at=timezone.now(), created_by=self.admin,
                                   paid_at=datetime.combine(b['paid'], datetime.min.time(), tzinfo=timezone.get_current_timezone()) if b['paid'] else None,
                                   notes='Imported from the 2026 salary sheet.')
                    if r['net'] is not None and slip.net != D(r['net']):
                        slip.notes += f" Sheet net {D(r['net'])} differs from computed {slip.net}."
                    if not Payslip.objects.filter(employee=u, period=b['period']).exists():
                        slip.save()
                        made += 1
            last_period = max(b['period'] for b in blocks)
            for u, (period, r) in latest.items():
                SalaryStructure.objects.update_or_create(employee=u, defaults={
                    'basic': D(r['basic']), 'allowances': D(r['da']), 'ssf_enrolled': bool(D(r['ssf'])),
                    'bank_name': r['bank_name'], 'bank_account': r['bank_account'], 'pan': r['pan'],
                    'effective_from': first_seen[u],
                    'active': period == last_period, 'notes': 'Imported from the 2026 salary sheet.'})
        self.stdout.write(self.style.SUCCESS(f'Salary sheet: {made} payslips added across {len(blocks)} months, '
                                             f'{len(latest)} salary structures'))

    # ------------------------------------------------------------ expense sheet (staff-paid claims) + dollar card

    def expenses(self, path, sheet):
        from openpyxl import load_workbook
        rows = list(load_workbook(path, data_only=True)[sheet].iter_rows(values_only=True))
        today = timezone.localdate()
        year, prev_m, prev_user, parsed = 2024, None, None, []
        for r in rows[1:]:
            when, what, amount, who, sheet_cat, is_paid = (list(r) + [None] * 6)[:6]
            if not what or not isinstance(amount, (int, float)) or str(what).lower().startswith(('pending', 'subtotal')):
                continue
            if isinstance(when, datetime):
                year, m, day = when.year, when.month, when.day
            else:
                m = month_of(when) or prev_m or 1
                if prev_m and m < prev_m:
                    year += 1
                day = int(re.match(r'\s*(\d{1,2})', str(when))[1]) if re.match(r'\s*\d{1,2}\D', str(when) or '') else 1
            d = date(year, m, day)
            if d > today:  # a later block restarts the year
                d, year = d.replace(year=d.year - 1), d.year - 1
            prev_m = m
            who = (who or prev_user or '').strip().title()
            prev_user = who
            parsed.append({'date': d, 'what': ' '.join(str(what).split()), 'amount': q2(Decimal(str(amount))), 'who': who,
                           'cat': str(sheet_cat or '').strip().lower(), 'paid': str(is_paid or '').strip().lower() == 'yes',
                           'month_only': not isinstance(when, datetime) and day == 1})
        # The sheet keeps "Pending Amt (name)" totals: the latest unreimbursed claims of each person add up to it.
        pending = {m[1].strip().title(): q2(Decimal(str(r[2]))) for r in rows
                   if r[1] and (m := re.match(r'pending amt \((\w+)\)', str(r[1]), re.I)) and isinstance(r[2], (int, float))}
        owed_ids = set()
        for name, total in pending.items():
            mine = [i for i, p in enumerate(parsed) if p['who'] == name and p['paid']]
            run = Decimal('0')
            for i in reversed(mine):
                run += parsed[i]['amount']
                owed_ids.add(i)
                if run >= total:
                    break
            if run != total:
                self.stdout.write(self.style.WARNING(f'  pending total for {name} ({total}) does not match a run of their latest '
                                                     f'claims ({run}); check reimbursement status by hand'))
        names = self.claimants
        made = 0
        with transaction.atomic():
            for i, p in enumerate(parsed):
                u = self.person(names.get(p['who'], p['who']))
                if not u:
                    continue
                category = next(c for rx, cx, c in CLAIM_CATEGORIES
                                if (not rx or re.search(rx, p['what'], re.I)) and (not cx or re.search(cx, p['cat'])))
                status = 'approved' if i in owed_ids else ('paid' if p['paid'] else 'draft')
                exists = Expense.objects.filter(employee=u, date=p['date'], description=p['what'][:500], amount=p['amount']).exists()
                if exists:
                    continue
                Expense.objects.create(
                    employee=u, date=p['date'], description=p['what'][:500], amount=p['amount'], category=cat(category),
                    status=status, created_by=self.admin, decided_by=self.admin if status != 'draft' else None,
                    decided_at=timezone.now() if status != 'draft' else None,
                    payment_reference='Settled before import (expense sheet)' if status == 'paid' else '',
                    paid_at=timezone.now() if status == 'paid' else None,
                    notes='Imported from the expense sheet.' + (' Sheet gives the month only.' if p['month_only'] else '')
                          + (' Not paid yet in the sheet.' if status == 'draft' else ''))
                made += 1
        self.stdout.write(self.style.SUCCESS(f'Staff claims: {made} added ({len(owed_ids)} still owed to staff)'))
        self.dollar_card(rows)

    def dollar_card(self, rows):
        """The 'Dollor card' block (columns H-J): loads are money in, spends are negative."""
        lines = [(r[7], r[8], r[9]) for r in rows if isinstance(r[7], datetime) and isinstance(r[9], (int, float)) and r[8]]
        if not lines:
            return
        acct, _ = Account.objects.get_or_create(name='Dollar card', defaults={
            'kind': 'card', 'currency': 'USD', 'opening_date': min(d for d, _, _ in lines).date(),
            'notes': 'Prepaid USD card for SaaS and API subscriptions.'})
        rules = [(r'load|top ?up', 'Internal transfer'), (r'google play|zoho|claud|antropic|anthropic|api', 'Software & subscriptions')]
        out = []
        for d, what, amt in lines:
            what = ' '.join(str(what).split())
            name = next((c for rx, c in rules if re.search(rx, what, re.I)), None)
            amt = q2(Decimal(str(amt)))
            out.append({'date': d.date(), 'description': what, 'party': '', 'note': '', 'reference': '', 'category': cat(name),
                        'debit': -amt if amt < 0 else Decimal('0'), 'credit': amt if amt > 0 else Decimal('0'),
                        'status': 'confirmed' if name else 'review'})
        res = import_rows(acct, out, self.admin)
        self.stdout.write(self.style.SUCCESS(f"Dollar card: {res['created']} added, {res['duplicates']} already there"))
