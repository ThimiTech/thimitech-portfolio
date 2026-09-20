from django.contrib import admin

# Register your models here.
from .models import NormalUser, NormalUserProfile, Project, Service, Category, Courses, Technology


class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
    list_filter = ('title',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)

class CoursesAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'category')
    search_fields = ('title', 'description', 'category__name')
    list_filter = ('category',)

class NormalUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')
    search_fields = ('username', 'email')
    list_filter = ('username',)

class NormalUserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username', 'bio')
    list_filter = ('user',)     

class TechnologyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'subtitle',)
    search_fields = ('name',)
    list_filter = ('name',)           
    
admin.site.register(Service, ServiceAdmin)    
admin.site.register(Category, CategoryAdmin)
admin.site.register(Courses, CoursesAdmin)
admin.site.register(NormalUser, NormalUserAdmin)
admin.site.register(NormalUserProfile, NormalUserProfileAdmin)  
admin.site.register(Technology, TechnologyAdmin)
admin.site.register(Project, ProjectAdmin)  
