from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, default="")
    description = models.TextField(default="")
    image = models.ImageField(upload_to='projects/', blank=True)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.name