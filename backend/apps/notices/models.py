import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def attachment_path(instance, filename):
    # Unguessable dir so a guessed /media URL is not enough; the API serves files through
    # /api/notices/{id}/attachment/ with audience scoping.
    return f'notices/{uuid.uuid4().hex}/{os.path.basename(filename)}'


class Notice(models.Model):
    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        HR = 'hr', 'HR'
        POLICY = 'policy', 'Policy'
        EVENT = 'event', 'Event'
        URGENT = 'urgent', 'Urgent'

    class Audience(models.TextChoices):
        ALL = 'all', 'Everyone'
        DEPARTMENT = 'department', 'Department'

    title = models.CharField(max_length=200)
    body = models.TextField()  # plain text; UI renders with whitespace-pre-line (no markdown)
    category = models.CharField(max_length=10, choices=Category.choices, default=Category.GENERAL)
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL)
    department = models.ForeignKey(
        'org.Department', null=True, blank=True, on_delete=models.CASCADE, related_name='notices'
    )
    pinned = models.BooleanField(default=False)
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to=attachment_path, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='notices'
    )
    # set when the urgent email went out (at create, or by notices.tasks.email_due_urgent_notices once live)
    emailed_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-publish_at']

    def __str__(self):
        return self.title


class NoticeRead(models.Model):
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notice_reads')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['notice', 'user'], name='one_read_per_user_per_notice'),
        ]
