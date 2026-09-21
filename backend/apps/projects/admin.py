from django.contrib import admin
from .models import Project

# Register your models here.

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'subtitle',)
    search_fields = ('name',)
    list_filter = ('name',)    

admin.site.register(Project, ProjectAdmin)    
