from django.contrib import admin

from .models import Job, Requirement, JobApplication


class RequirementInline(admin.TabularInline):
    model = Requirement
    extra = 1


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

    inlines = [RequirementInline]


admin.site.register(Job, JobAdmin)
admin.site.register(Requirement)
admin.site.register(JobApplication)