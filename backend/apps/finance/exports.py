"""Tabular finance exports (CSV / Excel) and the fiscal-year audit pack for the CA."""
import csv
import io
import os
import tempfile
import zipfile
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone

from . import reports
from .fiscal import bs_str, fy_range
from .models import Account, Expense, Invoice, Payslip, Statement, Transaction

MONEY_FMT = '#,##0.00'


def _name(user):
    return (user.get_full_name() or user.email) if user else ''


def ledger(fy):
    start, end = fy_range(fy)
    rows, running = [], {}
    for a in Account.objects.all():
        running[a.pk] = a.balance_before(start)
    for t in Transaction.objects.filter(date__range=(start, end)).select_related(
            'account', 'category', 'employee', 'project').order_by('account', 'date', 'id'):
        running[t.account_id] += t.credit - t.debit
        rows.append([t.date, bs_str(t.date), t.account.name, t.description, t.reference, t.party,
                     t.category.name if t.category else '', t.category.get_kind_display() if t.category else '',
                     t.debit, t.credit, running[t.account_id], t.account.currency, t.get_status_display(),
                     _name(t.employee), t.project.name if t.project else '', t.note])
    return (['Date', 'Miti (BS)', 'Account', 'Description', 'Reference', 'Party', 'Category', 'Kind', 'Debit', 'Credit',
             'Balance', 'Currency', 'Status', 'Employee', 'Project', 'Note'], rows)


def payroll(fy=None, period=None):
    qs = Payslip.objects.exclude(status='void').select_related('employee__profile', 'employee__salary_structure')
    qs = qs.filter(period=period) if period else qs.filter(period__range=fy_range(fy))
    rows = []
    for p in qs.order_by('period', 'employee__first_name'):
        st = getattr(p.employee, 'salary_structure', None)
        prof = getattr(p.employee, 'profile', None)
        rows.append([p.period.strftime('%B %Y'), _name(p.employee), prof.designation if prof else '',
                     prof.join_date if prof else None, st.pan if st else '', st.bank_name if st else '',
                     st.bank_account if st else '', p.basic, p.allowances, p.bonus, p.working_days, p.days_worked,
                     p.gross, p.ssf_employee, p.tds, p.deductions, p.net, p.ssf_employer, p.cost_to_company,
                     p.get_status_display(), p.paid_at.date() if p.paid_at else None, p.payment_reference])
    return (['Month', 'Employee', 'Designation', 'Join date', 'PAN', 'Bank', 'Account no', 'Basic', 'Allowances', 'Bonus',
             'Working days', 'Days worked', 'Gross', 'SSF 11%', 'TDS', 'Other deductions', 'Net payable',
             'SSF employer 20%', 'Cost to company', 'Status', 'Paid on', 'Payment reference'], rows)


def statutory(fy):
    data = reports.statutory(fy)
    return (['Payroll month', 'TDS', 'SSF employee', 'SSF employer', 'SSF total', 'TDS due', 'SSF due'],
            [[r['period'].strftime('%B %Y'), Decimal(r['tds']), Decimal(r['ssf_employee']), Decimal(r['ssf_employer']),
              Decimal(r['ssf_total']), r['tds_due'], r['ssf_due']] for r in data['months']])


def claims(fy):
    rows = [[e.date, bs_str(e.date), _name(e.employee), e.description, e.category.name if e.category else '',
             e.project.name if e.project else '', e.amount, e.currency, e.get_status_display(), e.payment_reference]
            for e in Expense.objects.filter(date__range=fy_range(fy)).select_related('employee', 'category', 'project')]
    return (['Date', 'Miti (BS)', 'Claimant', 'Description', 'Category', 'Project', 'Amount', 'Currency', 'Status',
             'Payment reference'], rows)


def invoices(fy):
    rows = [[i.number, i.client_name, i.project.name if i.project else '', i.issue_date, i.due_date, i.subtotal,
             i.tax_amount, i.total, i.currency, i.get_status_display(), i.paid_at.date() if i.paid_at else None]
            for i in Invoice.objects.filter(issue_date__range=fy_range(fy)).select_related('project').prefetch_related('items')]
    return (['Number', 'Client', 'Project', 'Issued', 'Due', 'Subtotal', 'Tax', 'Total', 'Currency', 'Status', 'Paid on'], rows)


def categories(fy):
    data = reports.overview(fy)
    return (['Category', 'Kind', 'Money out', 'Money in', 'Entries'],
            [[c['name'], c['kind'], Decimal(c['out']), Decimal(c['in']), c['entries']] for c in data['categories']])


def parties(fy):
    return (['Party', 'Money in', 'Money out', 'Net', 'Entries', 'Last date', 'Categories'],
            [[r['party'], Decimal(r['in']), Decimal(r['out']), Decimal(r['net']), r['entries'], r['last'],
              ', '.join(r['categories'])] for r in reports.parties(fy)])


def accounts(fy):
    start, end = fy_range(fy)
    rows = []
    for a in Account.objects.all():
        opening = a.balance_before(start)
        recon = [reports.reconciliation(st) for st in a.statements.filter(end__range=(start, end))]
        rows.append([a.name, a.get_kind_display(), a.institution, a.number, a.currency, opening, a.balance_on(end),
                     'yes' if recon and all(r['reconciled'] for r in recon) else ('no' if recon else 'no statement')])
    return (['Account', 'Kind', 'Bank', 'Number', 'Currency', 'Opening (FY start)', 'Closing (FY end)', 'Reconciled'], rows)


SHEETS = {'ledger': ('Ledger', ledger), 'categories': ('Categories', categories), 'payroll': ('Payroll', payroll),
          'statutory': ('TDS & SSF', statutory), 'claims': ('Staff claims', claims), 'invoices': ('Invoices', invoices),
          'parties': ('Parties', parties), 'accounts': ('Accounts', accounts)}


def workbook(sheets):
    """[(title, (headers, rows))] -> xlsx bytes with bold frozen headers, money formatting and sensible widths."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    wb.remove(wb.active)
    for title, (headers, rows) in sheets:
        ws = wb.create_sheet(title[:31])
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.freeze_panes = 'A2'
        for r in rows:
            ws.append([float(v) if isinstance(v, Decimal) else v for v in r])
        for i, h in enumerate(headers, 1):
            col = ws.cell(row=1, column=i).column_letter
            values = [r[i - 1] for r in rows]
            if any(isinstance(v, Decimal) for v in values):
                for cell in ws[col][1:]:
                    cell.number_format = MONEY_FMT
            if any(isinstance(v, date) for v in values):
                for cell in ws[col][1:]:
                    cell.number_format = 'yyyy-mm-dd'
            ws.column_dimensions[col].width = min(48, max(10, len(h) + 2, *(len(str(v)) + 2 for v in values[:200] if v is not None)))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def csv_bytes(headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows([['' if v is None else v for v in r] for r in rows])
    return ('﻿' + buf.getvalue()).encode('utf-8')  # BOM so Excel opens Devanagari/UTF-8 correctly


def download(content, filename, content_type):
    resp = HttpResponse(content, content_type=content_type)
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


def export(what, fmt, fy, period=None):
    slug = fy.replace('/', '-')
    if what == 'book':
        sheets = [(title, fn(fy)) for title, fn in SHEETS.values()]
        return download(workbook(sheets), f'thimitech-books-FY{slug}.xlsx', XLSX)
    title, fn = SHEETS[what]
    data = payroll(period=period) if what == 'payroll' and period else fn(fy)
    name = f'thimitech-{what}-' + (period.strftime('%Y-%m') if period and what == 'payroll' else f'FY{slug}')
    if fmt == 'csv':
        return download(csv_bytes(*data), f'{name}.csv', 'text/csv; charset=utf-8')
    return download(workbook([(title, data)]), f'{name}.xlsx', XLSX)


XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def audit_pack(fy, user):
    """Zip for the CA: the full workbook, a README with balances and reconciliation, and every document
    tagged with this fiscal year or attached to one of its transactions, claims or statements."""
    from apps.drive.models import File
    start, end = fy_range(fy)
    slug = fy.replace('/', '-')
    files = File.objects.filter(
        Q(fiscal_year=fy) | Q(folder__fiscal_year=fy) | Q(transaction__date__range=(start, end))
        | Q(expense__date__range=(start, end)) | Q(statement__end__range=(start, end)),
        classification__lte=user.clearance).select_related('folder').distinct()
    acct_rows = accounts(fy)[1]
    lines = [f'Thimi Tech - books for fiscal year {fy} ({start} to {end})', f'Generated {timezone.localtime():%Y-%m-%d %H:%M} NPT', '',
             'Accounts (opening -> closing, reconciled):']
    lines += [f'  {r[0]} [{r[4]}]: {r[5]:,.2f} -> {r[6]:,.2f}  ({r[7]})' for r in acct_rows]
    review = Transaction.objects.filter(date__range=(start, end), status=Transaction.Status.REVIEW).count()
    lines += ['', f'Ledger lines still marked "needs review": {review}', f'Documents included: {files.count()}',
              f'Statements recorded: {Statement.objects.filter(end__range=(start, end)).count()}', '',
              f'books-FY{slug}.xlsx has one sheet per register: Ledger, Categories, Payroll, TDS & SSF, Staff claims, Invoices, Parties, Accounts.']
    tmp = tempfile.SpooledTemporaryFile(max_size=32 * 1024 * 1024)
    seen = set()
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('README.txt', '\r\n'.join(lines))
        zf.writestr(f'books-FY{slug}.xlsx', workbook([(t, fn(fy)) for t, fn in SHEETS.values()]))
        for f in files:
            arc = '/'.join(['documents', *(f.folder.path() if f.folder else [f.space]), f.name])
            stem, ext = os.path.splitext(arc)
            n = 1
            while arc.lower() in seen:
                n += 1
                arc = f'{stem} ({n}){ext}'
            seen.add(arc.lower())
            try:
                with f.file.open('rb') as fh:
                    zf.writestr(arc, fh.read())
            except FileNotFoundError:
                continue
    tmp.seek(0)
    return FileResponse(tmp, as_attachment=True, filename=f'thimitech-audit-pack-FY{slug}.zip', content_type='application/zip')
