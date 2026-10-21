from collections import defaultdict
from decimal import Decimal
from .models import Payslip, Expense, Invoice


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
