from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

ZERO = Decimal('0.00')


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
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_id']
        constraints = [models.CheckConstraint(condition=models.Q(deductions__lte=models.F('basic') + models.F('allowances')), name='salary_nonnegative_net')]


class Payslip(SalaryAmounts):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payslips')
    period = models.DateField(help_text='First day of the payroll month.')
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('issued', 'Issued'), ('paid', 'Paid'), ('void', 'Void')], default='draft')
    notes = models.TextField(blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period', '-id']
        constraints = [models.UniqueConstraint(fields=['employee', 'period'], name='one_payslip_per_month'), models.CheckConstraint(condition=models.Q(deductions__lte=models.F('basic') + models.F('allowances')), name='payslip_nonnegative_net')]


class Expense(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='expenses')
    description = models.CharField(max_length=500)
    date = models.DateField(default=timezone.localdate)
    category = models.CharField(max_length=16, choices=[('travel', 'Travel'), ('software', 'Software'), ('equipment', 'Equipment'), ('office', 'Office'), ('other', 'Other')], default='other')
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
