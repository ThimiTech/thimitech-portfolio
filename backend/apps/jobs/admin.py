from django.contrib import admin
from .models import Job


class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'employment_type',
        'is_active',
        'display_order',
    )
    list_filter = ('is_active', 'employment_type')
    search_fields = ('title', 'description')
    ordering = ('display_order', 'title')

admin.site.register(Job, JobAdmin)    