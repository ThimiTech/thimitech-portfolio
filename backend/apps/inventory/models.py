from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']


class Asset(models.Model):
    tag = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='assets')
    serial_number = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=200, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    currency = models.CharField(max_length=3, default='NPR')
    status = models.CharField(max_length=12, choices=[('available', 'Available'), ('assigned', 'Assigned'), ('maintenance', 'Maintenance'), ('retired', 'Retired')], default='available')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tag']


class Assignment(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name='assignments')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='asset_assignments')
    assigned_at = models.DateTimeField(default=timezone.now)
    due_back = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    return_note = models.TextField(blank=True)
    return_condition = models.CharField(max_length=12, blank=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    returned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        ordering = ['-assigned_at', '-id']
        constraints = [models.UniqueConstraint(fields=['asset'], condition=models.Q(returned_at__isnull=True), name='one_active_assignment_per_asset')]
