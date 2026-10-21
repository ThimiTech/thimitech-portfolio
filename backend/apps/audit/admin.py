from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'actor_label', 'action', 'target_model', 'target_id', 'source']
    list_filter = ['action', 'source', 'target_model']
    search_fields = ['actor_label', 'target_model', 'target_id']
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    actions = None

    def has_module_permission(self, request):
        return request.user.has_role('super_admin')

    def has_view_permission(self, request, obj=None):
        return request.user.has_role('super_admin')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
