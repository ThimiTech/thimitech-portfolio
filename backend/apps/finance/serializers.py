import calendar
import re
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from apps.pm.models import Project
from .fiscal import bs_str, fy_of
from .models import (Account, Category, Expense, FiscalYearClose, Invoice, InvoiceLine, Payslip, SalaryStructure,
                     Statement, Transaction)
from .services import apply_statutory, assert_open

User = get_user_model()
MONEY = dict(max_digits=14, decimal_places=2, read_only=True)


def active_staff():
    return User.objects.filter(is_active=True).exclude(role='guest')


def person_name(user):
    return (user.get_full_name() or user.email) if user else ''


def validate_net(attrs, instance):
    amounts = {field: attrs.get(field, getattr(instance, field, Decimal('0'))) for field in ['basic', 'allowances', 'deductions']}
    if amounts['deductions'] > amounts['basic'] + amounts['allowances']:
        raise serializers.ValidationError({'deductions': 'Deductions cannot exceed gross pay.'})
    return attrs


class CurrencySerializer(serializers.ModelSerializer):
    def validate_currency(self, value):
        if not re.fullmatch('[A-Z]{3}', value):
            raise serializers.ValidationError('Use an uppercase three-letter currency code, e.g. NPR.')
        return value


class SalarySerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=active_staff())
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    gross = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)
    net = serializers.SerializerMethodField(help_text='Monthly take-home for a full month: after SSF or 1% SST and other deductions.')

    def get_net(self, st) -> str:
        slip = Payslip(basic=st.basic, allowances=st.allowances, deductions=st.deductions)
        return str(apply_statutory(slip, st.ssf_enrolled).net)

    class Meta:
        model = SalaryStructure
        fields = ['id', 'employee', 'employee_name', 'basic', 'allowances', 'deductions', 'gross', 'net', 'currency',
                  'effective_from', 'active', 'ssf_enrolled', 'bank_name', 'bank_account', 'pan', 'notes', 'updated_at']
        read_only_fields = ['currency', 'updated_at']
        validators = [serializers.UniqueTogetherValidator(queryset=SalaryStructure.objects.all(), fields=['employee'])]

    def validate(self, attrs):
        if self.instance and attrs.get('employee', self.instance.employee).pk != self.instance.employee_id:
            raise serializers.ValidationError({'employee': 'Create a separate salary structure for another employee.'})
        return validate_net(attrs, self.instance)


PAYSLIP_AMOUNTS = ['basic', 'allowances', 'bonus', 'working_days', 'days_worked', 'ssf_employee', 'ssf_employer', 'tds', 'deductions']


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    earned = serializers.DecimalField(**MONEY)
    gross = serializers.DecimalField(**MONEY)
    total_deductions = serializers.DecimalField(**MONEY)
    net = serializers.DecimalField(**MONEY)
    cost_to_company = serializers.DecimalField(**MONEY)
    employee_meta = serializers.SerializerMethodField()
    transaction_ids = serializers.SerializerMethodField()
    recalculate = serializers.BooleanField(write_only=True, required=False, default=False,
                                           help_text='Recompute SSF and TDS from the salary structure after applying this edit.')

    class Meta:
        model = Payslip
        fields = ['id', 'employee', 'employee_name', 'employee_meta', 'period', *PAYSLIP_AMOUNTS, 'earned', 'gross',
                  'total_deductions', 'net', 'cost_to_company', 'currency', 'status', 'notes', 'payment_reference',
                  'issued_at', 'paid_at', 'created_at', 'transaction_ids', 'recalculate']
        read_only_fields = ['employee', 'period', 'currency', 'status', 'payment_reference', 'issued_at', 'paid_at', 'created_at']

    def get_employee_meta(self, slip) -> dict:
        st, prof = getattr(slip.employee, 'salary_structure', None), getattr(slip.employee, 'profile', None)
        return {'designation': prof.designation if prof else '', 'join_date': prof.join_date if prof else None,
                'pan': st.pan if st else '', 'bank_name': st.bank_name if st else '',
                'bank_account': st.bank_account if st else '', 'ssf_enrolled': st.ssf_enrolled if st else False}

    def get_transaction_ids(self, slip) -> list[int]:
        return [t.pk for t in slip.transactions.all()]

    def validate(self, attrs):
        recalc = attrs.pop('recalculate', False)
        slip = Payslip(**{f: attrs.get(f, getattr(self.instance, f, None) if self.instance else None) for f in PAYSLIP_AMOUNTS})
        if slip.working_days and slip.days_worked is not None and slip.days_worked > slip.working_days:
            raise serializers.ValidationError({'days_worked': 'Days worked cannot exceed working days.'})
        if recalc and self.instance:
            st = getattr(self.instance.employee, 'salary_structure', None)
            apply_statutory(slip, bool(st and st.ssf_enrolled))
            attrs.update(ssf_employee=slip.ssf_employee, ssf_employer=slip.ssf_employer, tds=slip.tds)
        if slip.net < 0:
            raise serializers.ValidationError({'deductions': 'Deductions cannot exceed gross pay.'})
        return attrs


class MyPayslipSerializer(serializers.ModelSerializer):
    """Read-only payslip for its owner, with what a printed slip needs."""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_email = serializers.EmailField(source='employee.email', read_only=True)
    designation = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    earned = serializers.DecimalField(**MONEY)
    gross = serializers.DecimalField(**MONEY)
    total_deductions = serializers.DecimalField(**MONEY)
    net = serializers.DecimalField(**MONEY)
    fiscal_year = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = ['id', 'employee_name', 'employee_email', 'designation', 'department', 'period', 'fiscal_year', 'basic',
                  'allowances', 'bonus', 'working_days', 'days_worked', 'earned', 'ssf_employee', 'ssf_employer', 'tds',
                  'deductions', 'gross', 'total_deductions', 'net', 'currency', 'status', 'notes', 'payment_reference',
                  'issued_at', 'paid_at']
        read_only_fields = fields

    def get_fiscal_year(self, slip) -> str:
        return fy_of(slip.period)

    def _profile(self, slip):
        return getattr(slip.employee, 'profile', None)

    def get_designation(self, slip) -> str:
        p = self._profile(slip)
        return p.designation if p else ''

    def get_department(self, slip) -> str:
        p = self._profile(slip)
        return p.department.name if p and p.department else ''


def first_of_month(value):
    if value.day != 1:
        raise serializers.ValidationError({'period': 'Use the first day of the payroll month.'})
    return value


class GenerateSerializer(serializers.Serializer):
    salary = serializers.PrimaryKeyRelatedField(queryset=SalaryStructure.objects.filter(active=True, employee__is_active=True).exclude(employee__role='guest'))
    period = serializers.DateField()
    working_days = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    days_worked = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=31)
    bonus = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal('0'), default=Decimal('0'))

    def validate(self, attrs):
        period = first_of_month(attrs['period'])
        end = period.replace(day=calendar.monthrange(period.year, period.month)[1])
        if attrs['salary'].effective_from > end:
            raise serializers.ValidationError({'salary': 'This salary structure is not effective in the selected month.'})
        if attrs.get('working_days') and attrs.get('days_worked') is not None and attrs['days_worked'] > attrs['working_days']:
            raise serializers.ValidationError({'days_worked': 'Days worked cannot exceed working days.'})
        return attrs


class PeriodSerializer(serializers.Serializer):
    period = serializers.DateField()
    working_days = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)

    def validate_period(self, value):
        return first_of_month(value)


class CategorySerializer(serializers.ModelSerializer):
    entries = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ['id', 'name', 'kind', 'description', 'active', 'entries']


def project_queryset():
    return Project.objects.all()


class ExpenseSerializer(CurrencySerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=active_staff())
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(active=True), required=False, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    project = serializers.PrimaryKeyRelatedField(queryset=project_queryset(), required=False, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    files = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = ['id', 'employee', 'employee_name', 'description', 'date', 'category', 'category_name', 'project',
                  'project_name', 'amount', 'currency', 'status', 'notes', 'decision_note', 'decided_by', 'decided_at',
                  'payment_reference', 'paid_at', 'created_at', 'files']
        read_only_fields = ['status', 'decision_note', 'decided_by', 'decided_at', 'payment_reference', 'paid_at', 'created_at']

    def get_files(self, expense) -> list[dict]:
        return [{'id': f.pk, 'name': f.name, 'title': f.name, 'extension': f.extension, 'size': f.size,
                 'url': f'/api/drive/files/{f.pk}/content/'} for f in expense.files.all()]


class MyExpenseSerializer(ExpenseSerializer):
    employee = serializers.PrimaryKeyRelatedField(read_only=True)


class LineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ['id', 'description', 'quantity', 'unit_price', 'line_total']


class InvoiceSerializer(CurrencySerializer):
    items = LineSerializer(many=True, allow_empty=False)
    subtotal = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    project = serializers.PrimaryKeyRelatedField(queryset=project_queryset(), required=False, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'client_name', 'client_email', 'project', 'project_name', 'issue_date', 'due_date',
                  'currency', 'tax_amount', 'items', 'subtotal', 'total', 'notes', 'status', 'payment_reference',
                  'issued_at', 'paid_at', 'created_at']
        read_only_fields = ['status', 'payment_reference', 'issued_at', 'paid_at', 'created_at']

    def validate(self, attrs):
        start = attrs.get('issue_date', getattr(self.instance, 'issue_date', timezone.localdate()))
        end = attrs.get('due_date', getattr(self.instance, 'due_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'due_date': 'Due date must be on or after the issue date.'})
        if len(attrs.get('items', [])) > 100:
            raise serializers.ValidationError({'items': 'Use at most 100 invoice lines.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items')
        invoice = super().create(validated_data)
        from apps.audit.services import record_created
        for item in InvoiceLine.objects.bulk_create([InvoiceLine(invoice=invoice, **item) for item in items]):
            record_created(item)
        return invoice

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)
        if items is not None:
            instance.items.all().delete()
            from apps.audit.services import record_created
            for item in InvoiceLine.objects.bulk_create([InvoiceLine(invoice=instance, **item) for item in items]):
                record_created(item)
            instance._prefetched_objects_cache = {}
        return instance


class PaymentSerializer(serializers.Serializer):
    payment_reference = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    transaction = serializers.PrimaryKeyRelatedField(queryset=Transaction.objects.all(), required=False, allow_null=True,
                                                     help_text='The bank line that paid it; linked to the record.')

    def validate(self, attrs):
        txn = attrs.get('transaction')
        if not attrs['payment_reference'] and not txn:
            raise serializers.ValidationError({'payment_reference': 'Enter a payment reference or pick the bank transaction.'})
        if txn and not attrs['payment_reference']:
            attrs['payment_reference'] = (txn.reference or txn.description)[:200]
        return attrs


@extend_schema_serializer(component_name='ExpenseDecision')
class DecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class CurrencySummarySerializer(serializers.Serializer):
    currency = serializers.CharField()
    payroll_paid = serializers.DecimalField(max_digits=20, decimal_places=2)
    expenses_approved = serializers.DecimalField(max_digits=20, decimal_places=2)
    invoice_outstanding = serializers.DecimalField(max_digits=20, decimal_places=2)


class FinanceSummarySerializer(serializers.Serializer):
    currencies = CurrencySummarySerializer(many=True)
    draft_payslips = serializers.IntegerField()
    submitted_expenses = serializers.IntegerField()


# ---------------------------------------------------------------- books

class AccountSerializer(CurrencySerializer):
    balance = serializers.SerializerMethodField()
    entries = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Account
        fields = ['id', 'name', 'kind', 'institution', 'number', 'currency', 'opening_balance', 'opening_date', 'active',
                  'notes', 'balance', 'entries']

    def get_balance(self, account) -> str:
        return str(account.balance_on())

    def validate(self, attrs):
        inst = self.instance
        first = inst and inst.transactions.order_by('date').values_list('date', flat=True).first()
        if first:
            if attrs.get('currency', inst.currency) != inst.currency:
                raise serializers.ValidationError({'currency': 'This account has transactions; its currency cannot change.'})
            if attrs.get('opening_date', inst.opening_date) > first:
                raise serializers.ValidationError({'opening_date': f'Must be on or before the first transaction ({first}).'})
            if attrs.get('opening_balance', inst.opening_balance) != inst.opening_balance:
                assert_open(inst.opening_date)
        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    currency = serializers.CharField(source='account.currency', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    category_kind = serializers.CharField(source='category.kind', read_only=True, default='')
    employee = serializers.PrimaryKeyRelatedField(queryset=User.objects.exclude(role='guest'), required=False, allow_null=True)
    employee_name = serializers.SerializerMethodField()
    project = serializers.PrimaryKeyRelatedField(queryset=project_queryset(), required=False, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    payslip_label = serializers.SerializerMethodField()
    invoice_number = serializers.CharField(source='invoice.number', read_only=True, default='')
    expense_label = serializers.CharField(source='expense.description', read_only=True, default='')
    bs_date = serializers.SerializerMethodField()
    fiscal_year = serializers.SerializerMethodField()
    balance = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True, required=False, allow_null=True)
    files = serializers.IntegerField(source='files_count', read_only=True, default=0)

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'account_name', 'currency', 'date', 'bs_date', 'fiscal_year', 'description', 'reference',
                  'party', 'category', 'category_name', 'category_kind', 'debit', 'credit', 'balance', 'note', 'status',
                  'employee', 'employee_name', 'project', 'project_name', 'payslip', 'payslip_label', 'expense',
                  'expense_label', 'invoice', 'invoice_number', 'files', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_name(self, t) -> str:
        return person_name(t.employee)

    def get_payslip_label(self, t) -> str:
        return f'{person_name(t.payslip.employee)} · {t.payslip.period:%b %Y}' if t.payslip else ''

    def get_bs_date(self, t) -> str:
        return bs_str(t.date)

    def get_fiscal_year(self, t) -> str:
        return fy_of(t.date)

    def validate(self, attrs):
        get = lambda f: attrs.get(f, getattr(self.instance, f, None))  # noqa: E731
        debit, credit = get('debit') or 0, get('credit') or 0
        if (debit > 0) == (credit > 0):
            raise serializers.ValidationError({'debit': 'Enter either money out (debit) or money in (credit), not both.'})
        account, day = get('account'), get('date')
        if account and day and day < account.opening_date:
            raise serializers.ValidationError({'date': f"Before this account's opening date ({account.opening_date})."})
        assert_open(day, self.instance.date if self.instance else None)
        for link in ('payslip', 'expense'):
            obj = attrs.get(link)
            if obj and not get('employee'):
                attrs['employee'] = obj.employee
        if attrs.get('invoice') and not get('project') and attrs['invoice'].project_id:
            attrs['project'] = attrs['invoice'].project
        return attrs


class BulkSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=500)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Transaction.Status.choices, required=False)
    employee = serializers.PrimaryKeyRelatedField(queryset=User.objects.exclude(role='guest'), required=False, allow_null=True)
    project = serializers.PrimaryKeyRelatedField(queryset=project_queryset(), required=False, allow_null=True)


class ImportSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    file = serializers.FileField()
    dry_run = serializers.BooleanField(default=True)


class StatementSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    reconciliation = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = Statement
        fields = ['id', 'account', 'account_name', 'start', 'end', 'opening_balance', 'closing_balance', 'notes',
                  'reconciliation', 'files', 'created_at']
        read_only_fields = ['created_at']

    def get_reconciliation(self, st) -> dict:
        from .reports import reconciliation
        return reconciliation(st)

    def get_files(self, st) -> list[dict]:
        return [{'id': f.pk, 'name': f.name, 'title': f.name, 'extension': f.extension, 'size': f.size,
                 'url': f'/api/drive/files/{f.pk}/content/'} for f in st.files.all()]

    def validate(self, attrs):
        start, end = attrs.get('start', getattr(self.instance, 'start', None)), attrs.get('end', getattr(self.instance, 'end', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end': 'End must be on or after start.'})
        assert_open(end)
        return attrs


class FiscalYearCloseSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FiscalYearClose
        fields = ['id', 'name', 'notes', 'closed_by_name', 'closed_at']
        read_only_fields = ['closed_at']

    def get_closed_by_name(self, c) -> str:
        return person_name(c.closed_by)

    def validate_name(self, value):
        from .fiscal import parse_fy
        try:
            parse_fy(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value
