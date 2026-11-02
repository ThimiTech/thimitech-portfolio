from django.db import models
from django.contrib.auth.models import AbstractUser


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
        super().save(*args, **kwargs)
