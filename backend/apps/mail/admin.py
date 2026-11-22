from django.contrib import admin

from .models import MailAccount


@admin.register(MailAccount)
class MailAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'needs_reconnect', 'connected_at')
    search_fields = ('email', 'user__email')
    fields = ('user', 'email', 'display_name', 'account_id', 'mail_server', 'needs_reconnect', 'connected_at')
    readonly_fields = fields

    def has_add_permission(self, request):
        return False  # connect from /app/mail; the OAuth handshake is the only way in
