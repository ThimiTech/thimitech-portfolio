from django.conf import settings
from django.db import models


class Job(models.Model):
    title = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.title

class Requirement(models.Model):
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='requirements'
    )

    text = models.TextField()

    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.text    
    
class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    cover_letter = models.TextField(blank=True)
    cv = models.FileField(upload_to='applications/cv/')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )


    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='unique_job_application'
            )
        ]

    def __str__(self):
       return f"{self.name} - {self.job}"

    