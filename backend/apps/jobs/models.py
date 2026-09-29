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