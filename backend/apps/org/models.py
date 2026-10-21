import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def default_weekend_days():
    return [5]  # Python weekday(): Monday=0 ... Saturday=5 (Nepal standard weekend)


class Organization(models.Model):
    """Singleton (pk=1): public profile + work policy. Use Organization.load()."""

    name = models.CharField(max_length=200, default='Thimi Tech')
    tagline = models.CharField(max_length=255, blank=True)
    about = models.TextField(blank=True)
    logo = models.ImageField(upload_to='org/', blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    founded = models.DateField(null=True, blank=True)

    # Work policy (drives attendance lateness and working-day maths)
    work_start = models.TimeField(default=datetime.time(10, 0))
    work_end = models.TimeField(default=datetime.time(17, 0))
    late_grace_minutes = models.PositiveSmallIntegerField(default=15)
    weekend_days = models.JSONField(default=default_weekend_days)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='managed_departments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def creates_cycle(self, parent):
        """True if `parent` is self, a descendant of self, or sits on an existing parent loop."""
        seen, node = set(), parent
        while node is not None:
            if node.pk in seen or (self.pk and node.pk == self.pk):
                return True
            seen.add(node.pk)
            node = node.parent
        return False

    def clean(self):
        if self.creates_cycle(self.parent):
            raise ValidationError(
                {'parent': 'A department cannot be its own parent or a child of one of its sub-departments.'}
            )


class EmployeeProfile(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'
        CONTRACT = 'contract', 'Contract'
        INTERN = 'intern', 'Intern'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile'
    )
    employee_code = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(
        Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='members'
    )
    designation = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    join_date = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to='profiles/', blank=True)
    bio = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name', 'user__email']

    def __str__(self):
        return f'{self.user} profile'

    @property
    def manager(self):
        """The approver for this employee: their department's manager (never themselves)."""
        m = self.department.manager if self.department else None
        return m if m and m.pk != self.user_id else None
