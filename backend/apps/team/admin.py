from django.contrib import admin

from .models import TeamMember, SocialMedia


class SocialMediaInline(admin.TabularInline):
    model = SocialMedia
    extra = 1


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

    inlines = [SocialMediaInline]


admin.site.register(TeamMember, TeamMemberAdmin)
admin.site.register(SocialMedia)