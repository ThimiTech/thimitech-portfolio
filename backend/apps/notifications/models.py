from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app inbox item. Not audited (apps/audit/policy.py TRACKED_APPS): it is a derived copy of an audited event."""

    class Kind(models.TextChoices):
        LEAVE_REQUESTED = 'leave_requested', 'Leave requested'
        LEAVE_DECIDED = 'leave_decided', 'Leave decided'
        TASK_ASSIGNED = 'task_assigned', 'Task assigned'
        NOTICE = 'notice', 'Notice'
        PAYSLIP_ISSUED = 'payslip_issued', 'Payslip issued'
        ASSET_ASSIGNED = 'asset_assigned', 'Asset assigned'
        ASSET_ISSUE = 'asset_issue', 'Asset issue reported'
        CORRECTION_REQUESTED = 'correction_requested', 'Attendance correction requested'
        CORRECTION_DECIDED = 'correction_decided', 'Attendance correction decided'
        MEETING = 'meeting', 'Meeting scheduled'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True, help_text='In-app path, e.g. /app/leave')
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recipient', 'read_at'])]

    def __str__(self):
        return f'{self.recipient_id}: {self.title}'
