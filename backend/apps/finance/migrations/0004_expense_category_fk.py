from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('finance', '0003_categories_seed')]

    operations = [
        migrations.RemoveField('expense', 'category'),
        migrations.RenameField('expense', 'category_ref', 'category'),
        migrations.AlterField('expense', 'category', models.ForeignKey(
            null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='expenses', to='finance.category')),
    ]
