from django.conf import settings
from django.db import models


class Holiday(models.Model):
    """Public/company holiday. Nepali holidays follow lunar calendars, so each year is entered explicitly."""

    name = models.CharField(max_length=150)
    date = models.DateField(unique=True)
    description = models.TextField(blank=True)
    is_optional = models.BooleanField(default=False)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.name} ({self.date})'


class CalendarEvent(models.Model):
    class Audience(models.TextChoices):
        ORGANIZATION = 'organization', 'Whole organization'
        DEPARTMENT = 'department', 'Department'
        PRIVATE = 'private', 'Only me + attendees'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ORGANIZATION)
    department = models.ForeignKey(
        'org.Department', null=True, blank=True, on_delete=models.CASCADE, related_name='events'
    )
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='calendar_events')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='created_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']
        constraints = [
            models.CheckConstraint(condition=models.Q(end__gte=models.F('start')), name='event_end_after_start'),
        ]

    def __str__(self):
        return self.title
