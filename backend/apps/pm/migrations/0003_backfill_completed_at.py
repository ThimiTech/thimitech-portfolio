from django.db import migrations
from django.db.models import F


def backfill(apps, schema_editor):
    Task = apps.get_model('pm', 'Task')
    Task.objects.filter(column__status='done', completed_at__isnull=True).update(completed_at=F('updated_at'))


class Migration(migrations.Migration):
    dependencies = [('pm', '0002_project_cover_project_health_project_public_sections_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
