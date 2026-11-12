from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Department, OnboardingStep
from .onboarding import start_onboarding

TASKS = '/api/org/onboarding/tasks/'


def mk(name, role):
    return User.objects.create_user(username=name, email=f'{name}@x.test', password='x', role=role)


class OnboardingTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr, cls.lead = mk('hr', 'hr_admin'), mk('lead', 'manager')
        cls.new, cls.other = mk('new', 'employee'), mk('other', 'employee')
        cls.new.profile.department = Department.objects.create(name='Eng', manager=cls.lead)
        cls.new.profile.save()
        OnboardingStep.objects.create(title='Retired step', is_active=False, position=99)

    def test_start_copies_active_steps_once(self):
        active = OnboardingStep.objects.filter(is_active=True).count()
        self.assertGreater(active, 0)  # seeded by migration 0003
        self.assertEqual(start_onboarding(self.new), active)
        self.assertEqual(start_onboarding(self.new), 0)

    def test_visibility_and_toggle(self):
        start_onboarding(self.new)
        task = self.new.onboarding_tasks.first()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'{TASKS}?user={self.new.pk}').data, [])
        self.assertEqual(self.client.post(f'{TASKS}{task.pk}/toggle/').status_code, 404)
        self.client.force_authenticate(self.lead)  # sees the team checklist, cannot tick it
        self.assertTrue(self.client.get(f'{TASKS}?user={self.new.pk}').data)
        self.assertEqual(self.client.post(f'{TASKS}{task.pk}/toggle/').status_code, 403)
        self.client.force_authenticate(self.new)
        self.assertTrue(self.client.post(f'{TASKS}{task.pk}/toggle/').data['done'])
        self.assertFalse(self.client.post(f'{TASKS}{task.pk}/toggle/').data['done'])

    def test_only_hr_starts_and_edits_template(self):
        self.client.force_authenticate(self.lead)
        self.assertEqual(self.client.post(f'{TASKS}start/', {'user': self.other.pk}, format='json').status_code, 403)
        self.assertEqual(self.client.get('/api/org/onboarding/steps/').status_code, 403)
        self.client.force_authenticate(self.hr)
        self.assertEqual(self.client.post(f'{TASKS}start/', {'user': self.other.pk}, format='json').status_code, 201)
        self.assertEqual(self.client.post(f'{TASKS}start/', {'user': self.other.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/org/onboarding/steps/', {'title': 'Tour'}, format='json').status_code, 201)
