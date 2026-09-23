from django.db import models

# Create your models here.
class TeamMember(models.Model):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    initials = models.CharField(max_length=10)
    image = models.ImageField(upload_to='team/', blank=True)
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name