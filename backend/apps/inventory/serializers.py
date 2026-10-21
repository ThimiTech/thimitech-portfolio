import re
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Category, Asset, Assignment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class AssignedStaffSerializer(serializers.Serializer):
    assignment = serializers.IntegerField()
    id = serializers.IntegerField()
    name = serializers.CharField()
    due_back = serializers.DateField(allow_null=True)


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ['id', 'tag', 'name', 'category', 'category_name', 'serial_number', 'location', 'purchase_date', 'purchase_cost', 'currency', 'status', 'notes', 'assigned_to', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    @extend_schema_field(AssignedStaffSerializer(allow_null=True))
    def get_assigned_to(self, asset):
        assignment = next((a for a in asset.assignments.all() if a.returned_at is None), None)
        if not assignment:
            return None
        return {'assignment': assignment.pk, 'id': assignment.employee_id, 'name': assignment.employee.get_full_name() or assignment.employee.email, 'due_back': assignment.due_back}

    def validate_currency(self, value):
        if not re.fullmatch('[A-Z]{3}', value):
            raise serializers.ValidationError('Use an uppercase three-letter currency code.')
        return value

    def validate_status(self, value):
        active = self.instance and self.instance.assignments.filter(returned_at__isnull=True).exists()
        if value == 'assigned' and not active:
            raise serializers.ValidationError('Use an assignment to check out an asset.')
        if active and value != 'assigned':
            raise serializers.ValidationError('Return the current assignment before changing availability.')
        return value


class AssignmentSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(is_active=True).exclude(role='guest'))
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_tag = serializers.CharField(source='asset.tag', read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'asset', 'asset_name', 'asset_tag', 'employee', 'employee_name', 'assigned_at', 'due_back', 'notes', 'returned_at', 'return_note', 'return_condition', 'assigned_by', 'returned_by']
        read_only_fields = ['assigned_at', 'returned_at', 'return_note', 'return_condition', 'assigned_by', 'returned_by']
        validators = []  # Availability is checked under the asset row lock in perform_create.

    def validate_due_back(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError('Return date cannot be in the past.')
        return value


class MyAssignmentSerializer(serializers.ModelSerializer):
    """An employee's view of their own assignment: no cost, no internal asset notes."""
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_tag = serializers.CharField(source='asset.tag', read_only=True)
    category = serializers.CharField(source='asset.category.name', read_only=True)
    serial_number = serializers.CharField(source='asset.serial_number', read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'asset_name', 'asset_tag', 'category', 'serial_number', 'assigned_at', 'due_back', 'notes',
                  'returned_at', 'return_condition']
        read_only_fields = fields


class IssueReportSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000)


class ReturnSerializer(serializers.Serializer):
    condition = serializers.ChoiceField(choices=['available', 'maintenance', 'retired'], default='available')
    return_note = serializers.CharField(max_length=5000, required=False, allow_blank=True, default='')


class InventorySummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    available = serializers.IntegerField()
    assigned = serializers.IntegerField()
    maintenance = serializers.IntegerField()
    retired = serializers.IntegerField()
    overdue = serializers.IntegerField()
