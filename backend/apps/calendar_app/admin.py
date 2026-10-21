from django.contrib import admin

from .models import CalendarEvent, Holiday


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('date', 'name', 'is_optional')
    list_filter = ('is_optional',)
    search_fields = ('name',)
    date_hierarchy = 'date'


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start', 'end', 'audience', 'department', 'created_by')
    list_filter = ('audience', 'department')
    search_fields = ('title',)
    filter_horizontal = ('attendees',)
    date_hierarchy = 'start'
