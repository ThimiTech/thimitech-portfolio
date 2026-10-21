from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'status', 'work_mode', 'check_in', 'check_out', 'check_in_ip')
    list_filter = ('status', 'work_mode', 'date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    date_hierarchy = 'date'
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
