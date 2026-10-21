from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import User

STRONG = 'Correct-Horse-9-Battery'


class RegistrationSecurityTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counters

    def register(self, **data):
        return self.client.post('/api/register/', {'email': 'new@x.test', 'password': STRONG, **data}, format='json')

    def test_signup_is_always_guest(self):
        r = self.register(role='super_admin', is_staff=True, is_superuser=True)
        self.assertEqual(r.status_code, 201, r.data)
        u = User.objects.get(email='new@x.test')
        self.assertEqual((u.role, u.is_staff, u.is_superuser), ('guest', False, False))

    def test_weak_password_rejected(self):
        for pw in ['12345678', 'password', 'abc']:
            self.assertEqual(self.register(password=pw).status_code, 400, pw)

    def test_email_normalised_and_case_duplicates_rejected(self):
        self.assertEqual(self.register(email='Mixed@X.test').status_code, 201)
        self.assertTrue(User.objects.filter(email='mixed@x.test').exists())
        self.assertEqual(self.register(email='MIXED@x.test').status_code, 400)

    def test_username_collision_does_not_500(self):
        self.assertEqual(self.register(email='alice@a.test').status_code, 201)
        self.assertEqual(self.register(email='alice@b.test').status_code, 201)
        self.assertEqual(User.objects.filter(username__startswith='alice').count(), 2)

    def test_register_throttled(self):
        codes = [self.register(email=f'u{i}@x.test').status_code for i in range(11)]
        self.assertEqual(codes[-1], 429)


class TokenSecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tok', email='tok@x.test', password=STRONG, role='employee')

    def setUp(self):
        cache.clear()

    def login(self, password=STRONG):
        return self.client.post('/api/token/', {'email': 'tok@x.test', 'password': password}, format='json')

    def test_login_bruteforce_throttled(self):
        codes = [self.login('wrong').status_code for _ in range(11)]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[10], 429)
        # another account from the same IP is not locked out by the per-account limit
        other = self.client.post('/api/token/', {'email': 'other@x.test', 'password': 'x'}, format='json')
        self.assertEqual(other.status_code, 401)

    def test_login_email_is_case_insensitive(self):
        r = self.client.post('/api/token/', {'email': ' TOK@X.test', 'password': STRONG}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

    def test_register_ignores_stale_bearer_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        r = self.client.post('/api/register/', {'email': 'fresh@x.test', 'password': STRONG}, format='json')
        self.assertEqual(r.status_code, 201, r.data)

    def test_refresh_rotates_and_old_refresh_is_blacklisted(self):
        refresh = self.login().data['refresh']
        r = self.client.post('/api/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('refresh', r.data)
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)

    def test_logout_blacklists_refresh(self):
        refresh = self.login().data['refresh']
        self.assertEqual(self.client.post('/api/token/blacklist/', {'refresh': refresh}, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)

    def test_password_change_revokes_existing_tokens(self):
        access = self.login().data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(self.client.get('/api/me/').status_code, 200)
        r = self.client.post('/api/org/people/me/password/',
                             {'current_password': STRONG, 'new_password': 'Another-Strong-Pass-7'}, format='json')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.client.get('/api/me/').status_code, 401)

    def test_password_change_throttled(self):
        self.client.force_authenticate(self.user)
        codes = [self.client.post('/api/org/people/me/password/',
                                  {'current_password': 'wrong', 'new_password': 'x'}, format='json').status_code
                 for _ in range(6)]
        self.assertEqual(codes[-1], 429)

    def test_me_cannot_escalate_role(self):
        self.client.force_authenticate(self.user)
        self.client.patch('/api/me/', {'role': 'super_admin', 'is_staff': True}, format='json')
        self.user.refresh_from_db()
        self.assertEqual((self.user.role, self.user.is_staff), ('employee', False))


class RegistrationFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_one_char_password_rejected(self):
        r = self.client.post('/api/register/', {'email': 'a@x.test', 'password': 'a'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)

    def test_password_similar_to_name_rejected(self):
        r = self.client.post('/api/register/', {'email': 'z@x.test', 'password': 'Bishnuprasad',
                                                'first_name': 'Bishnuprasad'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_signup_returns_working_tokens_and_names_as_guest(self):
        r = self.client.post('/api/register/', {'email': 'Sita@X.test', 'password': STRONG, 'first_name': ' Sita ',
                                                'last_name': 'Rai', 'role': 'manager'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {r.data["access"]}')
        me = self.client.get('/api/me/').data
        self.assertEqual((me['email'], me['first_name'], me['last_name'], me['role']), ('sita@x.test', 'Sita', 'Rai', 'guest'))
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': r.data['refresh']}, format='json').status_code, 200)


class PasswordResetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='rs', email='reset@x.test', password=STRONG, role='employee',
                                            first_name='Reset')

    def setUp(self):
        cache.clear()

    def request_reset(self, email):
        from django.core import mail
        mail.outbox = []
        r = self.client.post('/api/password-reset/', {'email': email}, format='json')
        return r, mail.outbox

    def link_params(self, outbox):
        import re
        from urllib.parse import parse_qs, urlparse
        url = re.search(r'https?://\S+', outbox[0].body).group(0)
        self.assertTrue(urlparse(url).path.endswith('/reset-password'))
        q = parse_qs(urlparse(url).query)
        return q['uid'][0], q['token'][0]

    def confirm(self, uid, token, pw='Brand-New-Pass-42'):
        return self.client.post('/api/password-reset/confirm/', {'uid': uid, 'token': token, 'new_password': pw}, format='json')

    def test_unknown_and_inactive_emails_get_same_200_and_no_mail(self):
        r, out = self.request_reset('nobody@x.test')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(out, [])
        User.objects.create_user(username='off', email='off@x.test', password=STRONG, is_active=False)
        r2, out2 = self.request_reset('off@x.test')
        self.assertEqual((r2.status_code, r2.data), (200, r.data))
        self.assertEqual(out2, [])

    def test_full_reset_revokes_old_tokens_and_link_is_single_use(self):
        login = self.client.post('/api/token/', {'email': 'reset@x.test', 'password': STRONG}, format='json').data
        r, out = self.request_reset('RESET@x.test')  # case-insensitive
        self.assertEqual((r.status_code, len(out), out[0].to), (200, 1, ['reset@x.test']))
        uid, token = self.link_params(out)

        self.assertEqual(self.confirm(uid, token).status_code, 200)
        self.assertEqual(self.confirm(uid, token, 'Other-New-Pass-43').status_code, 400)  # used up
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Brand-New-Pass-42'))
        # every pre-reset token is dead: access rejected, refresh blacklisted
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login["access"]}')
        self.assertEqual(self.client.get('/api/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': login['refresh']}, format='json').status_code, 401)

    def test_bad_token_and_weak_password_rejected(self):
        _, out = self.request_reset('reset@x.test')
        uid, token = self.link_params(out)
        self.assertEqual(self.confirm(uid, 'x-' + token).status_code, 400)
        self.assertEqual(self.confirm('garbage', token).status_code, 400)
        r = self.confirm(uid, token, '123')
        self.assertEqual(r.status_code, 400)
        self.assertIn('new_password', r.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG))

    def test_stale_bearer_token_does_not_block_reset(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-real-token')
        self.assertEqual(self.client.post('/api/password-reset/', {'email': 'reset@x.test'}, format='json').status_code, 200)

    def test_reset_throttled_per_email_not_per_office(self):
        codes = [self.client.post('/api/password-reset/', {'email': 'n@x.test'}, format='json').status_code
                 for _ in range(6)]
        self.assertEqual(codes[-1], 429)
        # a colleague behind the same NAT can still reset theirs
        self.assertEqual(self.client.post('/api/password-reset/', {'email': 'm@x.test'}, format='json').status_code, 200)


class ThemePreferenceTests(APITestCase):
    def test_theme_round_trip_and_validation(self):
        u = User.objects.create_user(username='th', email='th@x.test', password=STRONG, role='employee')
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get('/api/me/').data['theme'], 'system')
        self.assertEqual(self.client.patch('/api/me/', {'theme': 'dark'}, format='json').data['theme'], 'dark')
        self.assertEqual(self.client.patch('/api/me/', {'theme': 'neon'}, format='json').status_code, 400)
        u.refresh_from_db()
        self.assertEqual(u.theme, 'dark')
