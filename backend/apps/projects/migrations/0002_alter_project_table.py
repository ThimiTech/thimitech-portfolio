from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Project',
                    fields=[
                        (
                            'id',
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name='ID',
                            ),
                        ),
                        (
                            'name',
                            models.CharField(max_length=200),
                        ),
                        (
                            'subtitle',
                            models.CharField(
                                default='',
                                max_length=200,
                            ),
                        ),
                        (
                            'description',
                            models.TextField(default=''),
                        ),
                        (
                            'image',
                            models.CharField(
                                blank=True,
                                max_length=300,
                            ),
                        ),
                        (
                            'url',
                            models.URLField(blank=True),
                        ),
                    ],
                    options={
                        'db_table': 'services_project',
                    },
                ),
            ],
        ),
    ]