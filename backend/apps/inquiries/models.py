from django.conf import settings
from django.db import models


class Inquiry(models.Model):
    """A message from the public contact form, worked from the /app/inquiries inbox."""

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        IN_PROGRESS = 'in_progress', 'In progress'
        CLOSED = 'closed', 'Closed'
        SPAM = 'spam', 'Spam'

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=160, blank=True)
    message = models.TextField(max_length=5000)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='inquiries')
    note = models.TextField(blank=True)  # internal follow-up notes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'inquiries'

    def __str__(self):
        return f'{self.name} <{self.email}>'
