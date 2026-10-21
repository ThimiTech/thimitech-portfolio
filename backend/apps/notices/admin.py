from django.contrib import admin

from .models import Notice, NoticeRead


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'audience', 'department', 'pinned', 'publish_at', 'expires_at', 'author']
    list_filter = ['category', 'audience', 'pinned']
    search_fields = ['title', 'body']


@admin.register(NoticeRead)
class NoticeReadAdmin(admin.ModelAdmin):
    list_display = ['notice', 'user', 'read_at']
