from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

ZERO = Decimal('0.00')
CENT = Decimal('.01')


def q2(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def money_field(**kwargs):
    return models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(ZERO)], **kwargs)


class SalaryAmounts(models.Model):
    basic = money_field(default=0)
    allowances = money_field(default=0)
    deductions = money_field(default=0)
    currency = models.CharField(max_length=3, default='NPR', editable=False)

    @property
    def gross(self):
        return self.basic + self.allowances

    @property
    def net(self):
        return self.gross - self.deductions

    class Meta:
        abstract = True


class SalaryStructure(SalaryAmounts):
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='salary_structure')
    effective_from = models.DateField(default=timezone.localdate)
    active = models.BooleanField(default=True)
    ssf_enrolled = models.BooleanField(default=False, help_text='Enrolled in the Social Security Fund: 11% + 20% of basic, no 1% SST.')
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account = models.CharField(max_length=40, blank=True)
    pan = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_id']
        constraints = [models.CheckConstraint(condition=models.Q(deductions__lte=models.F('basic') + models.F('allowances')), name='salary_nonnegative_net')]


class Payslip(SalaryAmounts):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payslips')
    period = models.DateField(help_text='First day of the payroll month.')
    bonus = money_field(default=0, help_text='Festival (Dashain) bonus or other one-off pay.')
    working_days = models.PositiveSmallIntegerField(null=True, blank=True)
    days_worked = models.PositiveSmallIntegerField(null=True, blank=True)
    ssf_employee = money_field(default=0, help_text="Employee's SSF share, deducted from pay.")
    ssf_employer = money_field(default=0, help_text="Company's SSF share, paid on top of pay.")
    tds = money_field(default=0, help_text='Tax deducted at source (1% SST when not in SSF).')
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('issued', 'Issued'), ('paid', 'Paid'), ('void', 'Void')], default='draft')
    notes = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def earned(self):
        """Basic + allowances, pro-rated by days worked when both day counts are set."""
        full = self.basic + self.allowances
        if self.working_days and self.days_worked is not None and self.days_worked < self.working_days:
            return q2(full * self.days_worked / self.working_days)
        return full

    @property
    def gross(self):
        return self.earned + self.bonus

    @property
    def total_deductions(self):
        return self.ssf_employee + self.tds + self.deductions

    @property
    def net(self):
        return self.gross - self.total_deductions

    @property
    def cost_to_company(self):
        return self.gross + self.ssf_employer

    class Meta:
        ordering = ['-period', '-id']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'period'], name='one_payslip_per_month'),
            models.CheckConstraint(condition=models.Q(deductions__lte=models.F('basic') + models.F('allowances') + models.F('bonus') - models.F('ssf_employee') - models.F('tds')), name='payslip_nonnegative_net_v2'),
        ]


class Expense(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses')
    description = models.CharField(max_length=500)
    date = models.DateField(default=timezone.localdate)
    category = models.ForeignKey('Category', null=True, blank=True, on_delete=models.PROTECT, related_name='expenses')
    project = models.ForeignKey('pm.Project', null=True, blank=True, on_delete=models.SET_NULL, related_name='finance_expenses')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('.01'))])
    currency = models.CharField(max_length=3, default='NPR')
    status = models.CharField(max_length=12, choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('paid', 'Paid')], default='draft')
    notes = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='expense_positive_amount')]


class Invoice(models.Model):
    number = models.CharField(max_length=40, unique=True)
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    project = models.ForeignKey('pm.Project', null=True, blank=True, on_delete=models.SET_NULL, related_name='finance_invoices')
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default='NPR')
    tax_amount = money_field(default=0)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('issued', 'Issued'), ('paid', 'Paid'), ('void', 'Void')], default='draft')
    payment_reference = models.CharField(max_length=200, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), ZERO)

    @property
    def total(self):
        return self.subtotal + self.tax_amount

    class Meta:
        ordering = ['-issue_date', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(due_date__gte=models.F('issue_date')), name='invoice_due_after_issue')]


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('.01'))])
    unit_price = money_field()

    @property
    def line_total(self):
        return (self.quantity * self.unit_price).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    class Meta:
        ordering = ['id']


class Category(models.Model):
    class Kind(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Operating expense'
        PAYROLL = 'payroll', 'Payroll'
        TAX = 'tax', 'Tax & statutory'
        TRANSFER = 'transfer', 'Transfer / loan / capital'  # moves money without being profit or loss

    name = models.CharField(max_length=80, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    description = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['kind', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Account(models.Model):
    """Where money sits: a bank account, petty cash, a dollar card, a wallet."""
    class Kind(models.TextChoices):
        BANK = 'bank', 'Bank account'
        CASH = 'cash', 'Cash / petty cash'
        CARD = 'card', 'Card'
        WALLET = 'wallet', 'Digital wallet'

    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.BANK)
    institution = models.CharField(max_length=120, blank=True)
    number = models.CharField(max_length=40, blank=True)
    currency = models.CharField(max_length=3, default='NPR')
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opening_date = models.DateField(help_text='Balance is as of the start of this day; transactions start here.')
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-active', 'name']

    def __str__(self):
        return self.name

    def balance_on(self, day=None):
        qs = self.transactions.all()
        if day:
            qs = qs.filter(date__lte=day)
        totals = qs.aggregate(cr=models.Sum('credit'), dr=models.Sum('debit'))
        return self.opening_balance + (totals['cr'] or ZERO) - (totals['dr'] or ZERO)

    def balance_before(self, day):
        """Balance at the start of `day`."""
        return self.opening_balance if day <= self.opening_date else self.balance_on(day - timedelta(days=1))


class Transaction(models.Model):
    """One line of a bank statement (or cash/card book). Debit = money out, credit = money in."""
    class Status(models.TextChoices):
        REVIEW = 'review', 'Needs review'
        CONFIRMED = 'confirmed', 'Confirmed'

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transactions')
    date = models.DateField()
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=120, blank=True)
    party = models.CharField(max_length=200, blank=True, help_text='Paid to / received from.')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name='transactions')
    debit = money_field(default=0)
    credit = money_field(default=0)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REVIEW)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='finance_transactions')
    project = models.ForeignKey('pm.Project', null=True, blank=True, on_delete=models.SET_NULL, related_name='finance_transactions')
    payslip = models.ForeignKey(Payslip, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    expense = models.ForeignKey(Expense, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']
        indexes = [models.Index(fields=['account', 'date', 'id'])]
        constraints = [models.CheckConstraint(
            condition=(models.Q(debit__gt=0, credit=0) | models.Q(credit__gt=0, debit=0)), name='transaction_one_side')]

    @property
    def amount(self):
        return self.credit - self.debit


class Statement(models.Model):
    """A bank statement period; reconciles when the ledger's balance at `end` equals `closing_balance`."""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='statements')
    start = models.DateField()
    end = models.DateField()
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-end', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(end__gte=models.F('start')), name='statement_end_after_start')]


class FiscalYearClose(models.Model):
    """A closed fiscal year: its ledger lines and statements can no longer be added, edited or deleted."""
    name = models.CharField(max_length=7, unique=True, help_text='e.g. 2082/83')
    notes = models.TextField(blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    closed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-name']
