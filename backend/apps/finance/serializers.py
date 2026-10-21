import calendar
import re
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers
from .models import SalaryStructure, Payslip, Expense, Invoice, InvoiceLine

User = get_user_model()


def active_staff():
    return User.objects.filter(is_active=True).exclude(role='guest')


def person_name(user):
    return user.get_full_name() or user.email


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
    net = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)

    class Meta:
        model = SalaryStructure
        fields = ['id', 'employee', 'employee_name', 'basic', 'allowances', 'deductions', 'gross', 'net', 'currency', 'effective_from', 'active', 'notes', 'updated_at']
        read_only_fields = ['currency', 'updated_at']
        validators = [serializers.UniqueTogetherValidator(queryset=SalaryStructure.objects.all(), fields=['employee'])]

    def validate(self, attrs):
        if self.instance and attrs.get('employee', self.instance.employee).pk != self.instance.employee_id:
            raise serializers.ValidationError({'employee': 'Create a separate salary structure for another employee.'})
        return validate_net(attrs, self.instance)


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    gross = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)
    net = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)

    class Meta:
        model = Payslip
        fields = ['id', 'employee', 'employee_name', 'period', 'basic', 'allowances', 'deductions', 'gross', 'net', 'currency', 'status', 'notes', 'payment_reference', 'issued_at', 'paid_at', 'created_at']
        read_only_fields = ['employee', 'period', 'currency', 'status', 'payment_reference', 'issued_at', 'paid_at', 'created_at']

    def validate(self, attrs):
        return validate_net(attrs, self.instance)


class MyPayslipSerializer(serializers.ModelSerializer):
    """Read-only payslip for its owner, with what a printed slip needs."""
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_email = serializers.EmailField(source='employee.email', read_only=True)
    designation = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    gross = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)
    net = serializers.DecimalField(max_digits=13, decimal_places=2, read_only=True)

    class Meta:
        model = Payslip
        fields = ['id', 'employee_name', 'employee_email', 'designation', 'department', 'period', 'basic',
                  'allowances', 'deductions', 'gross', 'net', 'currency', 'status', 'notes', 'payment_reference',
                  'issued_at', 'paid_at']
        read_only_fields = fields

    def _profile(self, slip):
        return getattr(slip.employee, 'profile', None)

    def get_designation(self, slip) -> str:
        p = self._profile(slip)
        return p.designation if p else ''

    def get_department(self, slip) -> str:
        p = self._profile(slip)
        return p.department.name if p and p.department else ''


class GenerateSerializer(serializers.Serializer):
    salary = serializers.PrimaryKeyRelatedField(queryset=SalaryStructure.objects.filter(active=True, employee__is_active=True).exclude(employee__role='guest'))
    period = serializers.DateField()

    def validate(self, attrs):
        period = attrs['period']
        if period.day != 1:
            raise serializers.ValidationError({'period': 'Use the first day of the payroll month.'})
        end = period.replace(day=calendar.monthrange(period.year, period.month)[1])
        if attrs['salary'].effective_from > end:
            raise serializers.ValidationError({'salary': 'This salary structure is not effective in the selected month.'})
        return attrs


class ExpenseSerializer(CurrencySerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=active_staff())
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'employee', 'employee_name', 'description', 'date', 'category', 'amount', 'currency', 'status', 'notes', 'decision_note', 'decided_by', 'decided_at', 'payment_reference', 'paid_at', 'created_at']
        read_only_fields = ['status', 'decision_note', 'decided_by', 'decided_at', 'payment_reference', 'paid_at', 'created_at']


class LineSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ['id', 'description', 'quantity', 'unit_price', 'line_total']


class InvoiceSerializer(CurrencySerializer):
    items = LineSerializer(many=True, allow_empty=False)
    subtotal = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'client_name', 'client_email', 'issue_date', 'due_date', 'currency', 'tax_amount', 'items', 'subtotal', 'total', 'notes', 'status', 'payment_reference', 'issued_at', 'paid_at', 'created_at']
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
    payment_reference = serializers.CharField(max_length=200)


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
