from django.db import migrations

DEFAULTS = {
    'income': ['Client income', 'Grants & installments', 'Interest income', 'Other income'],
    'payroll': ['Salary', 'Bonus & festival allowance', 'SSF contribution'],
    'tax': ['TDS deposit', 'Income tax', 'VAT', 'Government & registration fees'],
    'expense': ['Software & subscriptions', 'Server & domains', 'Office rent', 'Office & operations',
                'Meetings & refreshments', 'Legal & professional fees', 'Accounting & audit',
                'Printing & stationery', 'Travel', 'Equipment', 'Marketing & events', 'Project expenses',
                'Research & development', 'Bank charges', 'Other expenses'],
    'transfer': ['Capital introduced', 'Loan received', 'Loan repaid', 'Loan given', 'Loan recovered',
                 'Director transfers', 'Claim reimbursement', 'Internal transfer'],
}
OLD = {'travel': 'Travel', 'software': 'Software & subscriptions', 'equipment': 'Equipment',
       'office': 'Office & operations', 'other': 'Other expenses'}


def seed(apps, schema_editor):
    Category = apps.get_model('finance', 'Category')
    Expense = apps.get_model('finance', 'Expense')
    for kind, names in DEFAULTS.items():
        for name in names:
            Category.objects.get_or_create(name=name, defaults={'kind': kind})
    for old, name in OLD.items():
        Expense.objects.filter(category=old).update(category_ref=Category.objects.get(name=name))


class Migration(migrations.Migration):
    dependencies = [('finance', '0002_ledger_payroll_links')]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
