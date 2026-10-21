"""Read-only overview contract, shared with OpenAPI generation."""
from rest_framework import serializers
from apps.finance.serializers import FinanceSummarySerializer
from apps.inventory.serializers import InventorySummarySerializer
from .serializers import AuditLogSerializer, MonitoringWindowSerializer


class DepartmentCountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class RoleCountSerializer(serializers.Serializer):
    role = serializers.CharField()
    count = serializers.IntegerField()


class HeadcountSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    unassigned = serializers.IntegerField()
    joined_this_month = serializers.IntegerField()
    by_department = DepartmentCountSerializer(many=True)
    by_role = RoleCountSerializer(many=True)


class AttendanceCountsSerializer(serializers.Serializer):
    present = serializers.IntegerField()
    late = serializers.IntegerField()
    absent = serializers.IntegerField()
    on_leave = serializers.IntegerField()
    not_checked_in = serializers.IntegerField()
    expected = serializers.IntegerField()
    attended = serializers.IntegerField()


class AttendanceDaySerializer(AttendanceCountsSerializer):
    date = serializers.DateField()
    kind = serializers.CharField()


class AttendanceTrendSerializer(serializers.Serializer):
    days = AttendanceDaySerializer(many=True)
    totals = AttendanceCountsSerializer()
    rate = serializers.FloatField(allow_null=True)
    roster_basis = serializers.CharField()


class LeaveExposureTypeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    quota_days = serializers.CharField(allow_null=True)
    used_days = serializers.CharField()
    pending_days = serializers.CharField()
    remaining_days = serializers.CharField(allow_null=True)


class LeaveExposureSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    remaining_paid_days = serializers.CharField()
    pending_paid_days = serializers.CharField()
    pending_requests = serializers.IntegerField()
    by_type = LeaveExposureTypeSerializer(many=True)


class ProjectHealthSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    key = serializers.CharField()
    name = serializers.CharField()
    due_date = serializers.DateField(allow_null=True)
    total = serializers.IntegerField()
    done = serializers.IntegerField()
    overdue = serializers.IntegerField()
    percent = serializers.IntegerField()
    health = serializers.ChoiceField(choices=['complete', 'at_risk', 'unplanned', 'on_track'])


class DeliverySerializer(serializers.Serializer):
    active = serializers.IntegerField()
    archived = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    unassigned_tasks = serializers.IntegerField()
    by_project = ProjectHealthSerializer(many=True)


class RecentAuditSerializer(serializers.Serializer):
    capture_started_at = serializers.DateTimeField(allow_null=True)
    last_24h = serializers.IntegerField()
    recent = AuditLogSerializer(many=True)


class MonitoringSerializer(serializers.Serializer):
    as_of = serializers.DateField()
    generated_at = serializers.DateTimeField()
    timezone = serializers.CharField()
    attendance_window = MonitoringWindowSerializer()
    headcount = HeadcountSerializer()
    attendance = AttendanceTrendSerializer()
    leave = LeaveExposureSerializer()
    projects = DeliverySerializer()
    finance = FinanceSummarySerializer()
    inventory = InventorySummarySerializer()
    audit = RecentAuditSerializer()
