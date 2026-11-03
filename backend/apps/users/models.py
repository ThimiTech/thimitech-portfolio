from django.db import models
from django.contrib.auth.models import AbstractUser


class Clearance(models.IntegerChoices):
    """Security clearance (users) and classification (documents, notes, drive files...), one ladder.
    A user sees an item only when user.clearance >= item.classification, on top of the module's own checks."""
    INTERNAL = 1, 'Internal'          # every staff member who can already reach the item
    CONFIDENTIAL = 2, 'Confidential'  # e.g. leads: estimates, client correspondence
    RESTRICTED = 3, 'Restricted'      # e.g. contracts, agreements, HR and finance papers
    SECRET = 4, 'Secret'              # owner / directors only


def classification_field():
    return models.PositiveSmallIntegerField(
        choices=Clearance.choices, default=Clearance.INTERNAL, db_index=True,
        help_text='Minimum clearance needed to see this.')


class User(AbstractUser):
    class Role(models.TextChoices):
        GUEST = 'guest', 'Guest'
        EMPLOYEE = 'employee', 'Employee'
        ACCOUNTANT = 'accountant', 'Accountant / CA'
        MANAGER = 'manager', 'Manager'
        HR_ADMIN = 'hr_admin', 'HR / Admin'
        SUPER_ADMIN = 'super_admin', 'Super admin'

    # Ascending privilege; a higher rank implies every lower one.
    RANK = {
        Role.GUEST: 0,
        Role.EMPLOYEE: 1,
        Role.ACCOUNTANT: 1,  # staff-level everywhere else; finance access comes from can_finance()
        Role.MANAGER: 2,
        Role.HR_ADMIN: 3,
        Role.SUPER_ADMIN: 4,
    }

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    # Separate from role: a developer and a lead can share a role but not a clearance. Only a super admin sets it.
    clearance = models.PositiveSmallIntegerField(choices=Clearance.choices, default=Clearance.INTERNAL)
    # Workspace appearance, synced across devices; 'system' follows the OS.
    theme = models.CharField(max_length=6, choices=[('system', 'System'), ('light', 'Light'), ('dark', 'Dark')],
                             default='system')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def has_role(self, minimum):
        return self.RANK[self.role] >= self.RANK[minimum]

    def can_finance(self):
        """Books, payroll and finance documents: HR/admin and above, or the accountant/CA role."""
        return self.is_authenticated and (self.role == self.Role.ACCOUNTANT or self.has_role('hr_admin'))

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        if self.role == self.Role.SUPER_ADMIN:
            self.clearance = Clearance.SECRET
        super().save(*args, **kwargs)
