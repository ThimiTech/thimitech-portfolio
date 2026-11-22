from datetime import timedelta
from unittest import mock

from django.core import signing
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.users.models import User

from . import crypto
from .models import MailAccount

ZOHO = dict(ZOHO_CLIENT_ID='cid', ZOHO_CLIENT_SECRET='csecret', ZOHO_ACCOUNTS_URL='https://accounts.zoho.com',
            ZOHO_REDIRECT_URI='http://app.test/app/mail/callback')
MAIL = 'https://mail.zoho.com/api/accounts/77'


class FakeZoho:
    """Stands in for zoho._http: answers by (method, url prefix) and records every call."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for (m, prefix), answer in self.routes.items():
            if m == method and url.startswith(prefix):
                return answer(kw) if callable(answer) else answer
        raise AssertionError(f'unexpected Zoho call {method} {url}')


def ok(data):
    return 200, {'status': {'code': 200}, 'data': data}, None


@override_settings(**ZOHO)
class MailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username='s', email='s@thimitech.test', password='x', role='employee')
        cls.other = User.objects.create_user(username='o', email='o@thimitech.test', password='x', role='employee')
        cls.guest = User.objects.create_user(username='g', email='g@x.test', password='x', role='guest')

    def setUp(self):
        cache.clear()
        self.client.force_authenticate(self.staff)

    def connected(self, **kw):
        acc = MailAccount(user=self.staff, account_id='77', email='s@thimitech.test', accounts_server='https://accounts.zoho.com',
                          mail_server='https://mail.zoho.com', send_from=[{'address': 's@thimitech.test', 'name': 'S'}],
                          access_expires_at=timezone.now() + timedelta(minutes=30), **kw)
        acc.refresh_token, acc.access_token = 'r-tok', 'a-tok'
        acc.save()
        return acc

    def fake(self, routes):
        fake = FakeZoho(routes)
        patcher = mock.patch('apps.mail.zoho._http', fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def test_guests_cannot_use_mail_and_status_reports_not_connected(self):
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.get('/api/mail/status/').status_code, 403)
        self.client.force_authenticate(self.staff)
        r = self.client.get('/api/mail/status/')
        self.assertEqual((r.data['configured'], r.data['connected']), (True, False))
        r = self.client.get('/api/mail/folders/')
        self.assertEqual((r.status_code, r.data['not_connected']), (409, True))

    def test_connect_flow_stores_encrypted_tokens(self):
        url = self.client.get('/api/mail/connect/').data['url']
        self.assertIn('client_id=cid', url)
        self.assertIn('access_type=offline', url)
        state = url.split('state=')[1]
        fake = self.fake({
            ('POST', 'https://accounts.zoho.in/oauth/v2/token'): (200, {'access_token': 'A', 'refresh_token': '1000.refresh-secret', 'expires_in': 3600}, None),
            ('GET', 'https://mail.zoho.in/api/accounts'): ok([{'accountId': 99, 'primaryEmailAddress': 's@thimitech.com', 'displayName': 'Sachin',
                                                             'sendMailDetails': [{'fromAddress': 's@thimitech.com', 'displayName': 'Sachin'}]}]),
        })
        from urllib.parse import unquote
        r = self.client.post('/api/mail/callback/', {'code': 'c0de', 'state': unquote(state),
                                                     'accounts_server': 'https://accounts.zoho.in'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['connected'], r.data['email']), (True, 's@thimitech.com'))
        acc = MailAccount.objects.get(user=self.staff)
        self.assertEqual((acc.account_id, acc.mail_server, acc.refresh_token), ('99', 'https://mail.zoho.in', '1000.refresh-secret'))
        self.assertNotIn('refresh-secret', acc.refresh_token_enc)
        self.assertNotIn('refresh', str(r.data))
        self.assertEqual(fake.calls[0][2]['form']['code'], 'c0de')

    def test_callback_rejects_foreign_state_and_untrusted_server(self):
        theirs = signing.dumps({'u': self.other.pk}, salt='mail.oauth')
        r = self.client.post('/api/mail/callback/', {'code': 'c', 'state': theirs}, format='json')
        self.assertEqual(r.status_code, 400)
        mine = signing.dumps({'u': self.staff.pk}, salt='mail.oauth')
        fake = self.fake({('POST', 'https://accounts.zoho.com/oauth/v2/token'): (200, {'error': 'invalid_code'}, None)})
        r = self.client.post('/api/mail/callback/', {'code': 'c', 'state': mine, 'accounts_server': 'https://evil.test'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(fake.calls[0][1].startswith('https://accounts.zoho.com/'))  # never sent to evil.test
        self.assertFalse(MailAccount.objects.exists())

    def test_list_open_and_mark_read(self):
        self.connected()
        fake = self.fake({
            ('GET', f'{MAIL}/messages/view'): ok([{'messageId': '123', 'folderId': '5', 'subject': 'Hi &amp; bye',
                                                   'fromAddress': 'c@client.test', 'toAddress': '&lt;s@thimitech.test&gt;',
                                                   'ccAddress': 'Not Provided', 'receivedTime': '1700000000000',
                                                   'status': '0', 'hasAttachment': '1'}]),
            ('GET', f'{MAIL}/folders/5/messages/123/details'): ok({'subject': 'Hi', 'status': '0', 'hasAttachment': '1'}),
            ('GET', f'{MAIL}/folders/5/messages/123/content'): ok({'content': '<p>Hello</p>'}),
            ('GET', f'{MAIL}/folders/5/messages/123/attachmentinfo'): ok({'attachments': [{'attachmentId': '9', 'attachmentName': 'a.pdf', 'attachmentSize': '10'}]}),
            ('PUT', f'{MAIL}/updatemessage'): ok({}),
        })
        r = self.client.get('/api/mail/messages/', {'folder': '5'})
        m = r.data['results'][0]
        self.assertEqual((m['subject'], m['to'], m['cc'], m['unread'], m['has_attachments']),
                         ('Hi & bye', '<s@thimitech.test>', '', True, True))
        self.assertIsNone(r.data['next'])
        self.assertEqual(fake.calls[0][2]['headers']['Authorization'], 'Zoho-oauthtoken a-tok')

        r = self.client.get('/api/mail/messages/123/', {'folder': '5', 'mark_read': '1'})
        self.assertEqual((r.data['content'], r.data['unread'], r.data['attachments'][0]['name']), ('<p>Hello</p>', False, 'a.pdf'))
        self.assertEqual(fake.calls[-1][2]['json_body'], {'mode': 'markAsRead', 'messageId': [123]})

    def test_ids_are_validated_before_reaching_zoho(self):
        self.connected()
        fake = self.fake({})
        self.assertEqual(self.client.get('/api/mail/messages/', {'folder': '../x'}).status_code, 400)
        self.assertEqual(fake.calls, [])

    def test_expired_token_refreshes_and_revoked_grant_asks_to_reconnect(self):
        acc = self.connected()
        acc.access_expires_at = timezone.now() - timedelta(minutes=1)
        acc.save()
        self.fake({
            ('POST', 'https://accounts.zoho.com/oauth/v2/token'): (200, {'access_token': 'NEW', 'expires_in': 3600}, None),
            ('GET', f'{MAIL}/folders'): ok([{'folderId': 2, 'folderName': 'Trash', 'folderType': 'Trash'},
                                           {'folderId': 1, 'folderName': 'Inbox', 'folderType': 'Inbox'}]),
        })
        r = self.client.get('/api/mail/folders/')
        self.assertEqual([f['name'] for f in r.data], ['Inbox', 'Trash'])
        acc.refresh_from_db()
        self.assertEqual(acc.access_token, 'NEW')

        acc.access_expires_at = timezone.now() - timedelta(minutes=1)
        acc.save()
        self.fake({('POST', 'https://accounts.zoho.com/oauth/v2/token'): (400, {'error': 'Access Denied'}, None)})
        self.assertEqual(self.client.get('/api/mail/folders/').status_code, 503)  # rate limited: try later
        self.assertFalse(MailAccount.objects.get().needs_reconnect)
        self.fake({('POST', 'https://accounts.zoho.com/oauth/v2/token'): (200, {'error': 'invalid_code'}, None)})
        r = self.client.get('/api/mail/folders/')
        self.assertEqual((r.status_code, r.data['reconnect']), (409, True))
        self.assertTrue(MailAccount.objects.get().needs_reconnect)
        self.assertTrue(self.client.get('/api/mail/status/').data['needs_reconnect'])

    def test_send_checks_sender_and_recipients(self):
        self.connected()
        fake = self.fake({('POST', f'{MAIL}/messages'): ok({})})
        bad = self.client.post('/api/mail/send/', {'to': ['not-an-email']}, format='json')
        self.assertEqual(bad.status_code, 400)
        spoof = self.client.post('/api/mail/send/', {'to': ['c@client.test'], 'from_address': 'ceo@thimitech.test'}, format='json')
        self.assertEqual(spoof.status_code, 400)
        r = self.client.post('/api/mail/send/', {'to': ['Client <c@client.test>, d@client.test'], 'cc': 'e@client.test',
                                                 'subject': 'Quote', 'content': '<p>Hi</p>'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        body = fake.calls[-1][2]['json_body']
        self.assertEqual((body['fromAddress'], body['toAddress'], body['ccAddress'], body['mailFormat']),
                         ('s@thimitech.test', 'c@client.test,d@client.test', 'e@client.test', 'html'))

        self.fake({('POST', f'{MAIL}/messages/123'): ok({})})
        r = self.client.post('/api/mail/send/', {'to': ['c@client.test'], 'reply_to': '123', 'action': 'forward'}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_delete_moves_to_trash_then_deletes_for_good(self):
        self.connected()
        fake = self.fake({
            ('GET', f'{MAIL}/folders'): ok([{'folderId': 1, 'folderType': 'Inbox'}, {'folderId': 2, 'folderType': 'Trash'}]),
            ('PUT', f'{MAIL}/updatemessage'): ok({}),
            ('DELETE', f'{MAIL}/folders/2/messages/123'): ok({}),
        })
        self.assertEqual(self.client.delete('/api/mail/messages/123/?folder=1').status_code, 204)
        self.assertEqual(fake.calls[-1][2]['json_body'], {'mode': 'moveMessage', 'messageId': [123], 'destfolderId': '2'})
        self.assertEqual(self.client.delete('/api/mail/messages/123/?folder=2').status_code, 204)
        self.assertEqual(fake.calls[-1][0], 'DELETE')

    def test_disconnect_revokes_and_forgets(self):
        self.connected()
        fake = self.fake({('POST', 'https://accounts.zoho.com/oauth/v2/token/revoke'): (200, {}, None)})
        self.assertEqual(self.client.post('/api/mail/disconnect/').status_code, 204)
        self.assertEqual(fake.calls[0][2]['form'], {'token': 'r-tok'})
        self.assertFalse(MailAccount.objects.exists())

    def test_tokens_unreadable_with_another_key(self):
        enc = crypto.encrypt('secret')
        with override_settings(MAIL_TOKEN_KEY='different'):
            self.assertEqual(crypto.decrypt(enc), '')
        self.assertEqual(crypto.decrypt(enc), 'secret')
