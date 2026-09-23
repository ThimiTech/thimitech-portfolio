from django.contrib import admin

# Register your models here.
from .models import TeamMember

class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'role',
        'is_active',
        'display_order',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'role')
    ordering = ('display_order', 'name')

admin.site.register(TeamMember, TeamMemberAdmin)      