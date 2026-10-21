from django.conf import settings
from django.db import models


class LeaveType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    code = models.SlugField(max_length=30, unique=True)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # days per calendar year
    is_paid = models.BooleanField(default=True)
    color = models.CharField(max_length=7, blank=True)  # hex, e.g. #7a6a52
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='requests')
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)  # only valid when start_date == end_date
    days = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # working days, computed server-side
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='leave_decisions'
    )
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='leave_end_after_start'),
        ]

    def __str__(self):
        return f'{self.user} {self.leave_type} {self.start_date}–{self.end_date}'
