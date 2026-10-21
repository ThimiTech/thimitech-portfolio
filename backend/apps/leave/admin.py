from django.contrib import admin

from .models import LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'annual_quota', 'is_paid', 'is_active')
    list_filter = ('is_paid', 'is_active')
    search_fields = ('name', 'code')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'leave_type', 'start_date', 'end_date', 'days', 'status', 'approver', 'decided_at')
    list_filter = ('status', 'leave_type')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'reason')
    date_hierarchy = 'start_date'
    raw_id_fields = ('user', 'approver')
    readonly_fields = ('days', 'created_at')
