from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, default="")
    description = models.TextField(default="")
    image = models.ImageField(upload_to='projects/', blank=True)
    url = models.URLField(blank=True)

    class Meta:
        db_table = 'services_project'

    def __str__(self):
        return self.name