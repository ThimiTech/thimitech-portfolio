from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Department, EmployeeProfile
from apps.audit.services import audited_update


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_employee_profile(sender, instance, **kwargs):
    """Every staff member (role >= employee) has an EmployeeProfile; only active staff lead departments."""
    if instance.has_role('employee'):
        EmployeeProfile.objects.get_or_create(user=instance)
    if not (instance.is_active and instance.has_role('employee')):
        audited_update(Department.objects.filter(manager=instance), manager=None)
