from django.contrib import admin

from .models import Department, EmployeeProfile, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'work_start', 'work_end', 'late_grace_minutes', 'weekend_days')

    def has_add_permission(self, request):
        return not Organization.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'manager')
    search_fields = ('name',)
    autocomplete_fields = ('manager',)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_code', 'department', 'designation', 'employment_type', 'join_date')
    list_filter = ('department', 'employment_type')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'designation', 'employee_code')
    autocomplete_fields = ('user',)
