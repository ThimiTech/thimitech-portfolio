from django.conf import settings
from django.db import models


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        LATE = 'late', 'Late'
        ABSENT = 'absent', 'Absent'
        ON_LEAVE = 'on_leave', 'On leave'

    class WorkMode(models.TextChoices):
        OFFICE = 'office', 'Office'
        REMOTE = 'remote', 'Remote'

    class Source(models.TextChoices):
        SELF = 'self', 'Self check-in'
        HR = 'hr', 'HR entry'
        SYSTEM = 'system', 'System'
        CORRECTED = 'corrected', 'Approved correction'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()  # local (Asia/Kathmandu) date
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.OFFICE)
    note = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.SELF)
    check_in_ip = models.GenericIPAddressField(null=True, blank=True)
    check_out_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='one_attendance_per_user_per_day'),
        ]

    def __str__(self):
        return f'{self.user} {self.date} {self.status}'

    @property
    def worked_minutes(self):
        if self.check_in and self.check_out:
            return int((self.check_out - self.check_in).total_seconds() // 60)
        return None


class AttendanceCorrection(models.Model):
    """An employee's request to fix a past day's times. Approval rewrites that day's AttendanceRecord."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_corrections')
    date = models.DateField()
    check_in = models.TimeField(help_text='Desired local (Asia/Kathmandu) check-in time')
    check_out = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    decision_note = models.CharField(max_length=2000, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], condition=models.Q(status='pending'),
                                    name='one_pending_correction_per_day'),
        ]

    def __str__(self):
        return f'{self.user} {self.date} {self.status}'
