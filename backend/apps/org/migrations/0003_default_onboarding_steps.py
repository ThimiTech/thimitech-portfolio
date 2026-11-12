from django.db import migrations

STEPS = [
    ('Complete your profile', 'Add your phone, address, emergency contact and a photo under My profile.'),
    ('Sign and return your contract', 'HR shares it with you in Drive.'),
    ('Collect your equipment', 'Laptop and accessories are recorded under My assets.'),
    ('Set up your accounts', 'Company email, GitHub and the tools your team uses.'),
    ('Read the pinned notices', 'Working hours, leave policy and house rules are on the notice board.'),
    ('Meet your manager', 'Agree your first two weeks of work and who to ask for what.'),
]


def seed(apps, schema_editor):
    Step = apps.get_model('org', 'OnboardingStep')
    if not Step.objects.exists():
        Step.objects.bulk_create(Step(title=t, description=d, position=i) for i, (t, d) in enumerate(STEPS))


class Migration(migrations.Migration):
    dependencies = [('org', '0002_onboardingstep_onboardingtask')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
