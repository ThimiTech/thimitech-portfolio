"""Read-only finance reports for a fiscal year. Cash basis: the bank ledger is the source of truth;
staff-paid claims are added as spending that has not passed through the bank yet."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from .fiscal import bs_str, fy_months, fy_range, next_bs_month_day
from .models import ZERO, Account, Category, Expense, Invoice, Payslip, Transaction

BASE = 'NPR'
OUT_KINDS = [Category.Kind.EXPENSE, Category.Kind.PAYROLL, Category.Kind.TAX]


def s(v):
    return str((v or ZERO).quantize(Decimal('.01')))


def sums(qs):
    t = qs.aggregate(dr=Sum('debit'), cr=Sum('credit'), n=Count('id'))
    return t['dr'] or ZERO, t['cr'] or ZERO, t['n']


def month_end(period):
    return (period.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def overview(fy):
    start, end = fy_range(fy)
    today = timezone.localdate()
    txns = Transaction.objects.filter(date__range=(start, end))
    base = txns.filter(account__currency=BASE)

    accounts = []
    for a in Account.objects.all():
        dr, cr, n = sums(txns.filter(account=a))
        accounts.append({'id': a.pk, 'name': a.name, 'kind': a.kind, 'currency': a.currency, 'active': a.active,
                         'balance': s(a.balance_on(today)), 'fy_in': s(cr), 'fy_out': s(dr), 'entries': n})

    kinds = {k: {'out': ZERO, 'in': ZERO} for k in [*Category.Kind.values, 'uncategorized']}
    for row in base.values('category__kind').annotate(dr=Sum('debit'), cr=Sum('credit')):
        k = kinds[row['category__kind'] or 'uncategorized']
        k['out'] += row['dr'] or ZERO
        k['in'] += row['cr'] or ZERO

    categories = [{'id': r['category'], 'name': r['category__name'] or 'Uncategorized', 'kind': r['category__kind'] or 'uncategorized',
                   'out': s(r['dr']), 'in': s(r['cr']), 'entries': r['n']}
                  for r in base.values('category', 'category__name', 'category__kind').annotate(
                      dr=Sum('debit'), cr=Sum('credit'), n=Count('id')).order_by('-dr', '-cr')]

    months = []
    for m in fy_months(fy):
        mq = base.filter(date__range=(m['start'], m['end']))
        dr, cr, _ = sums(mq)
        months.append({'label': m['label'], 'start': m['start'], 'end': m['end'], 'in': s(cr), 'out': s(dr),
                       'operating_out': s(sums(mq.filter(category__kind__in=OUT_KINDS))[0]),
                       'payroll': s(sums(mq.filter(category__kind=Category.Kind.PAYROLL))[0])})

    slips = Payslip.objects.filter(period__range=(start, end)).exclude(status='void')
    payroll = {'gross': ZERO, 'net': ZERO, 'ssf_employee': ZERO, 'ssf_employer': ZERO, 'tds': ZERO, 'cost': ZERO, 'slips': 0}
    for slip in slips:
        payroll['slips'] += 1
        for k, v in (('gross', slip.gross), ('net', slip.net), ('ssf_employee', slip.ssf_employee),
                     ('ssf_employer', slip.ssf_employer), ('tds', slip.tds), ('cost', slip.cost_to_company)):
            payroll[k] += v

    claims = Expense.objects.filter(date__range=(start, end), currency=BASE).exclude(status__in=['draft', 'rejected'])
    owed = [{'employee': r['employee'], 'name': f"{r['employee__first_name']} {r['employee__last_name']}".strip() or r['employee__email'],
             'amount': s(r['t']), 'claims': r['n']}
            for r in Expense.objects.filter(status='approved', currency=BASE).values(
                'employee', 'employee__first_name', 'employee__last_name', 'employee__email').annotate(t=Sum('amount'), n=Count('id')).order_by('-t')]
    receivable = sum((i.total for i in Invoice.objects.filter(status='issued').prefetch_related('items')), ZERO)

    # Runway: NPR cash / average operating outflow of the last three complete months.
    month_start = today.replace(day=1)
    window = (month_start - timedelta(days=1)).replace(day=1)
    for _ in range(2):
        window = (window - timedelta(days=1)).replace(day=1)
    burn = sums(Transaction.objects.filter(account__currency=BASE, category__kind__in=OUT_KINDS,
                                           date__range=(window, month_start - timedelta(days=1))))[0] / 3
    cash = sum((Decimal(a['balance']) for a in accounts if a['currency'] == BASE and a['active']), ZERO)

    income, spent = kinds[Category.Kind.INCOME]['in'], sum((kinds[k]['out'] for k in OUT_KINDS), ZERO)
    claims_total = claims.aggregate(t=Sum('amount'))['t'] or ZERO
    return {
        'fy': fy, 'start': start, 'end': end, 'currency': BASE,
        'cash': s(cash), 'accounts': accounts,
        'kinds': {k: {'in': s(v['in']), 'out': s(v['out'])} for k, v in kinds.items()},
        'income': s(income), 'spent': s(spent), 'claims_spent': s(claims_total),
        'result': s(income - spent - claims_total),
        'months': months, 'categories': categories,
        'payroll': {k: (v if k == 'slips' else s(v)) for k, v in payroll.items()},
        'owed_to_staff': owed, 'receivable': s(receivable),
        'claims_waiting': Expense.objects.filter(status='submitted').count(),
        'to_review': Transaction.objects.filter(status=Transaction.Status.REVIEW).count(),
        'uncategorized': Transaction.objects.filter(category__isnull=True).count(),
        'monthly_burn': s(burn), 'runway_months': round(float(cash / burn), 1) if burn else None,
        'statutory': statutory(fy)['totals'],
    }


def statutory(fy):
    """TDS and SSF accrued by payroll month, with deadlines (TDS: 25th, SSF: 15th of the next Nepali month),
    against deposits recorded in the 'TDS deposit' and 'SSF contribution' categories."""
    start, end = fy_range(fy)
    rows = defaultdict(lambda: {'tds': ZERO, 'ssf_employee': ZERO, 'ssf_employer': ZERO})
    for slip in Payslip.objects.filter(period__range=(start, end)).exclude(status__in=['void', 'draft']):
        r = rows[slip.period]
        r['tds'] += slip.tds
        r['ssf_employee'] += slip.ssf_employee
        r['ssf_employer'] += slip.ssf_employer
    out = []
    for period in sorted(rows):
        r, ref = rows[period], month_end(period)
        out.append({'period': period, 'tds': s(r['tds']), 'ssf_employee': s(r['ssf_employee']), 'ssf_employer': s(r['ssf_employer']),
                    'ssf_total': s(r['ssf_employee'] + r['ssf_employer']),
                    'tds_due': next_bs_month_day(ref, 25), 'ssf_due': next_bs_month_day(ref, 15)})
    txns = Transaction.objects.filter(date__range=(start, end))
    deposited = {k: txns.filter(category__name=name).aggregate(t=Sum('debit'))['t'] or ZERO
                 for k, name in (('tds', 'TDS deposit'), ('ssf', 'SSF contribution'))}
    accrued = {'tds': sum((Decimal(r['tds']) for r in out), ZERO),
               'ssf': sum((Decimal(r['ssf_total']) for r in out), ZERO)}
    totals = {k: {'accrued': s(accrued[k]), 'deposited': s(deposited[k]), 'outstanding': s(accrued[k] - deposited[k])} for k in accrued}
    return {'fy': fy, 'months': out, 'totals': totals}


def parties(fy):
    """Money in/out per counterparty (party text, else the linked employee). Shows loans, directors, vendors at a glance."""
    start, end = fy_range(fy)
    agg = defaultdict(lambda: {'in': ZERO, 'out': ZERO, 'entries': 0, 'last': None, 'categories': set()})
    for t in Transaction.objects.filter(date__range=(start, end), account__currency=BASE).select_related('employee', 'category'):
        name = t.party or (t.employee.get_full_name() if t.employee else '') or 'Unknown'
        a = agg[name]
        a['in'] += t.credit
        a['out'] += t.debit
        a['entries'] += 1
        a['last'] = max(a['last'] or t.date, t.date)
        if t.category:
            a['categories'].add(t.category.name)
    rows = [{'party': k, 'in': s(v['in']), 'out': s(v['out']), 'net': s(v['in'] - v['out']), 'entries': v['entries'],
             'last': v['last'], 'categories': sorted(v['categories'])} for k, v in agg.items()]
    return sorted(rows, key=lambda r: -(Decimal(r['in']) + Decimal(r['out'])))


def reconciliation(statement):
    acct = statement.account
    opening = acct.balance_before(statement.start)
    closing = acct.balance_on(statement.end)
    return {'computed_opening': s(opening), 'computed_closing': s(closing),
            'difference': s(statement.closing_balance - closing),
            'reconciled': closing == statement.closing_balance and opening == statement.opening_balance,
            'bs_start': bs_str(statement.start), 'bs_end': bs_str(statement.end)}

