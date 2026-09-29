from django.contrib import admin

# Register your models here.
from .models import Service


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
    list_filter = ('title',)

admin.site.register(Service, ServiceAdmin)    

