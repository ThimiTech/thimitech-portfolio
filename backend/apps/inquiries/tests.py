from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User

from .models import Inquiry

URL = '/api/inquiries/'
BODY = {'name': 'Asha', 'email': 'asha@client.test', 'message': 'We need a ward-level map portal.'}


class InquiryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(username='m', email='m@x.test', password='x', role='manager')
        cls.staff = User.objects.create_user(username='s', email='s@x.test', password='x', role='employee')

    def setUp(self):
        cache.clear()  # throttle counters

    def test_public_submit_notifies_inbox_and_echoes_nothing(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer stale-token')  # must not 401 the form
        r = self.client.post(URL, BODY, format='json')
        self.assertEqual((r.status_code, r.data), (201, None))
        self.assertEqual(Inquiry.objects.get().status, 'new')
        self.assertEqual(list(Notification.objects.values_list('recipient', flat=True)), [self.manager.pk])

    def test_validation_and_honeypot(self):
        self.assertEqual(self.client.post(URL, {**BODY, 'message': 'hi'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(URL, {**BODY, 'website': 'http://spam'}, format='json').status_code, 201)
        self.assertFalse(Inquiry.objects.exists())

    def test_throttled_per_ip(self):
        codes = [self.client.post(URL, BODY, format='json').status_code for _ in range(11)]
        self.assertEqual(codes[-1], 429)

    def test_inbox_is_manager_only_and_content_is_read_only(self):
        inquiry = Inquiry.objects.create(**BODY)
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get('/api/nav-counts/').data['new_inquiries'], 1)
        url = f'{URL}{inquiry.pk}/'
        r = self.client.patch(url, {'status': 'closed', 'assignee': self.manager.pk, 'message': 'x'}, format='json')
        self.assertEqual((r.data['status'], r.data['message'], r.data['assignee']),
                         ('closed', BODY['message'], self.manager.pk))
        self.assertEqual(self.client.patch(url, {'assignee': self.staff.pk}, format='json').status_code, 400)
