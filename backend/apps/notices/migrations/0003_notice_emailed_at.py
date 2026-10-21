from django.db import migrations, models
from django.db.models import F


def backfill(apps, schema_editor):
    # Notices that already exist were handled by the old create-time rule; never mail them again.
    apps.get_model('notices', 'Notice').objects.filter(emailed_at__isnull=True).update(emailed_at=F('publish_at'))


class Migration(migrations.Migration):

    dependencies = [
        ("notices", "0002_alter_notice_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="notice",
            name="emailed_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
