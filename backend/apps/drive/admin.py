from django.contrib import admin

from .models import File, Folder, ShareLink

admin.site.register(Folder, list_display=['name', 'space', 'parent', 'fiscal_year'], list_filter=['space'])
admin.site.register(File, list_display=['name', 'space', 'folder', 'size', 'employee', 'created_at'], list_filter=['space'],
                    search_fields=['name'])
admin.site.register(ShareLink, list_display=['label', 'folder', 'file', 'expires_at', 'revoked_at'])
