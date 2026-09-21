from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0007_remove_project_technologies'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(
                    name='Project',
                ),
            ],
        ),
    ]