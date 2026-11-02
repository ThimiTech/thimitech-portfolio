from django.db import migrations

TREE = {
    'company': ['Brand kit', 'Letterheads', 'Email signatures', 'Templates', 'Policies & handbooks', 'Shared'],
    'finance': ['Bank statements', 'Payroll/Salary transfer slips', 'Payroll/Salary sheets', 'Payroll/SSF',
                'Tax & IRD', 'Audit', 'Rent', 'Invoices & receipts', 'Loans & capital', 'Seals & signatures', 'Transactions'],
    'people': ['Employees', 'Letters', 'Contracts'],
}


def seed(apps, schema_editor):
    Folder = apps.get_model('drive', 'Folder')
    for space, paths in TREE.items():
        for path in paths:
            parent = None
            for name in path.split('/'):
                parent, _ = Folder.objects.get_or_create(space=space, parent=parent, name=name)


class Migration(migrations.Migration):
    dependencies = [('drive', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
