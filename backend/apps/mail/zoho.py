"""Zoho Mail REST API client: OAuth handshake, token refresh, and the handful of calls /app/mail needs.

Docs: https://www.zoho.com/mail/help/api/ . Every call is made with the person's own OAuth token, so Zoho itself
decides what they can read and send. Responses are reshaped into small dicts (see `message`, `folder`) so the
frontend never depends on Zoho's field names.
"""
import json
import re
from datetime import timedelta
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import MailAccount

SCOPES = 'ZohoMail.accounts.READ,ZohoMail.folders.ALL,ZohoMail.messages.ALL'
TIMEOUT = 20
# Zoho data centres. The OAuth callback names the person's one in `accounts-server`; only these are trusted,
# since the authorization code (and our client secret) get sent there.
ACCOUNTS_SERVERS = {
    'https://accounts.zoho.com', 'https://accounts.zoho.eu', 'https://accounts.zoho.in',
    'https://accounts.zoho.com.au', 'https://accounts.zoho.jp', 'https://accounts.zoho.com.cn',
    'https://accounts.zoho.sa', 'https://accounts.zoho.uk', 'https://accounts.zohocloud.ca',
}
# Token-endpoint errors that mean the grant itself is gone (anything else, e.g. rate limiting, is temporary).
REVOKED = {'invalid_code', 'invalid_grant', 'invalid_token'}
ID = re.compile(r'^\d{1,30}$')
ATTACHMENT_ID = re.compile(r'^[A-Za-z0-9_.\-]{1,200}$')


class ZohoError(Exception):
    def __init__(self, detail, status=502):
        super().__init__(detail)
        self.detail, self.status = detail, status


class Reconnect(ZohoError):
    """The stored grant no longer works; the person has to connect again."""

    def __init__(self, detail='Your Zoho Mail connection has expired. Connect your mailbox again.'):
        super().__init__(detail, 409)


def configured():
    return bool(settings.ZOHO_CLIENT_ID and settings.ZOHO_CLIENT_SECRET)


def accounts_server(candidate=''):
    """The person's data centre from the callback, if it is a known Zoho one; else the configured default."""
    candidate = (candidate or '').rstrip('/')
    return candidate if candidate in ACCOUNTS_SERVERS else settings.ZOHO_ACCOUNTS_URL


def mail_server_for(accounts):
    return accounts.replace('://accounts.', '://mail.', 1)


def check_id(value, pattern=ID):
    if not isinstance(value, str) or not pattern.match(value):
        raise ZohoError('Invalid mail id.', 400)
    return value


# ───────────── HTTP ─────────────

def _http(method, url, *, params=None, form=None, body=None, json_body=None, headers=None, stream=False):
    if params:
        url = f'{url}?{urlencode(params)}'
    headers = dict(headers or {})
    data = None
    if json_body is not None:
        data, headers['Content-Type'] = json.dumps(json_body).encode(), 'application/json'
    elif form is not None:
        data, headers['Content-Type'] = urlencode(form).encode(), 'application/x-www-form-urlencoded'
    elif body is not None:
        data = body
    try:
        resp = urlopen(Request(url, data=data, method=method, headers=headers), timeout=TIMEOUT)
    except HTTPError as e:
        return e.code, _json(e.read()), None
    except (URLError, TimeoutError, OSError):
        raise ZohoError("Can't reach Zoho Mail right now. Try again in a minute.", 503)
    if stream:
        return resp.status, None, resp
    with resp:
        return resp.status, _json(resp.read()), None


def _json(raw):
    try:
        return json.loads(raw or b'{}')
    except ValueError:
        return {}


# ───────────── OAuth ─────────────

def authorize_url(state):
    return f'{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/auth?' + urlencode({
        'response_type': 'code', 'client_id': settings.ZOHO_CLIENT_ID, 'scope': SCOPES,
        'redirect_uri': settings.ZOHO_REDIRECT_URI, 'access_type': 'offline', 'prompt': 'consent', 'state': state,
    })


def _token(server, form):
    status, data, _ = _http('POST', f'{server}/oauth/v2/token', form={
        'client_id': settings.ZOHO_CLIENT_ID, 'client_secret': settings.ZOHO_CLIENT_SECRET, **form})
    # Zoho reports token errors as {"error": "..."}, often with HTTP 200.
    if status != 200 or data.get('error') or not data.get('access_token'):
        return None, data.get('error') or f'http_{status}'
    return data, None


def connect(user, code, server):
    """Finish the OAuth handshake: trade the code for tokens, look up the mailbox, store it for `user`."""
    tokens, error = _token(server, {
        'grant_type': 'authorization_code', 'code': code, 'redirect_uri': settings.ZOHO_REDIRECT_URI})
    if error:
        raise ZohoError('Zoho did not accept the sign-in. Try connecting again.', 400)
    if not tokens.get('refresh_token'):
        raise ZohoError('Zoho did not grant offline access. Try connecting again.', 400)
    mail = mail_server_for(server)
    status, data, _ = _http('GET', f'{mail}/api/accounts', headers=_auth(tokens['access_token']))
    accounts = data.get('data') if status == 200 else None
    if not accounts:
        raise ZohoError('No Zoho Mail mailbox was found for that Zoho account.', 400)
    acc = accounts[0]

    send_from = [{'address': s.get('fromAddress', ''), 'name': s.get('displayName', '')}
                 for s in acc.get('sendMailDetails') or [] if s.get('fromAddress')]
    email = acc.get('primaryEmailAddress') or acc.get('mailboxAddress') or (send_from[0]['address'] if send_from else '')
    if not send_from and email:
        send_from = [{'address': email, 'name': acc.get('displayName', '')}]

    old = MailAccount.objects.filter(user=user).first()
    if old and old.refresh_token:
        revoke(old)
    account = old or MailAccount(user=user)
    account.account_id = str(acc['accountId'])
    account.email = email
    account.display_name = acc.get('displayName') or ''
    account.accounts_server, account.mail_server = server, mail
    account.send_from = send_from
    account.refresh_token = tokens['refresh_token']
    account.access_token = tokens['access_token']
    account.access_expires_at = _expiry(tokens)
    account.needs_reconnect = False
    account.save()
    return account


def revoke(account):
    try:
        _http('POST', f'{account.accounts_server}/oauth/v2/token/revoke', form={'token': account.refresh_token})
    except ZohoError:
        pass  # best effort: the local grant is dropped either way


def _expiry(tokens):
    return timezone.now() + timedelta(seconds=max(int(tokens.get('expires_in') or 3600) - 120, 60))


def access_token(account, force=False):
    """A live access token, refreshing it (once, under a row lock) when it is about to expire."""
    if account.needs_reconnect:
        raise Reconnect()

    def live(a):
        return bool(a.access_token_enc and a.access_expires_at and a.access_expires_at > timezone.now())

    if not force and live(account):
        return account.access_token
    with transaction.atomic():
        locked = MailAccount.objects.select_for_update().get(pk=account.pk)
        # Another request may have refreshed while we waited for the lock (force: only if it's a different token
        # from the one Zoho just rejected).
        if live(locked) and (not force or locked.access_token_enc != account.access_token_enc):
            account.access_token_enc, account.access_expires_at = locked.access_token_enc, locked.access_expires_at
            return locked.access_token
        tokens, error = _token(locked.accounts_server, {
            'grant_type': 'refresh_token', 'refresh_token': locked.refresh_token})
        if error in REVOKED:
            locked.needs_reconnect = True  # raised below, after the commit, so the flag sticks
            locked.save(update_fields=['needs_reconnect', 'updated_at'])
        elif not error:
            locked.access_token = tokens['access_token']
            locked.access_expires_at = _expiry(tokens)
            locked.save(update_fields=['access_token_enc', 'access_expires_at', 'updated_at'])
    if error:
        if not locked.needs_reconnect:
            raise ZohoError("Zoho didn't renew the mail access just now. Try again in a minute.", 503)
        account.needs_reconnect = True
        raise Reconnect()
    account.access_token_enc, account.access_expires_at = locked.access_token_enc, locked.access_expires_at
    return locked.access_token


def _auth(token):
    return {'Authorization': f'Zoho-oauthtoken {token}', 'Accept': 'application/json'}


# ───────────── Mail API ─────────────

def call(account, method, path, *, stream=False, **kw):
    """One Mail API call under /api/accounts/{accountId}{path}. Retries once with a fresh token on 401."""
    url = f'{account.mail_server}/api/accounts/{account.account_id}{path}'
    extra = kw.pop('headers', {})
    for attempt in (0, 1):
        headers = {**_auth(access_token(account, force=attempt == 1)), **extra}
        status, data, resp = _http(method, url, headers=headers, stream=stream, **kw)
        if status != 401:
            break
    if status == 401:
        raise Reconnect()
    if status >= 400:
        if resp:
            resp.close()
        detail = (data.get('data') or {}).get('moreInfo') if isinstance(data.get('data'), dict) else None
        detail = detail or (data.get('status') or {}).get('description') or 'Zoho Mail rejected the request.'
        raise ZohoError(f'Zoho Mail: {detail}', 404 if status == 404 else 502)
    return resp if stream else data.get('data')


def _addr(value):
    value = unescape(value or '').strip()
    return '' if value in ('Not Provided', 'null') else value


def _ms(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def folder(f):
    return {'id': str(f.get('folderId')), 'name': f.get('folderName', ''), 'type': f.get('folderType', ''),
            'path': f.get('path', '')}


def message(m):
    return {
        'id': str(m.get('messageId')),
        'folder': str(m.get('folderId') or ''),
        'thread': str(m.get('threadId') or ''),
        'subject': unescape(m.get('subject') or ''),
        'summary': unescape(m.get('summary') or ''),
        'from': _addr(m.get('fromAddress')),
        'sender': unescape(m.get('sender') or ''),
        'to': _addr(m.get('toAddress')),
        'cc': _addr(m.get('ccAddress')),
        'received': _ms(m.get('receivedTime') or m.get('sentDateInGMT')),
        'unread': str(m.get('status')) == '0',
        'has_attachments': str(m.get('hasAttachment')) == '1',
        'flagged': (m.get('flagid') or 'flag_not_set') != 'flag_not_set',
    }


def folders(account):
    return [folder(f) for f in call(account, 'GET', '/folders') or []]


def messages(account, *, folder_id=None, query='', start=1, limit=50, unread=False):
    params = {'start': start, 'limit': limit, 'includeto': 'true'}
    if query:
        params['searchKey'] = f'entire:{query}'
        rows = call(account, 'GET', '/messages/search', params=params)
    else:
        params['folderId'] = check_id(folder_id)
        if unread:
            params['status'] = 'unread'
        rows = call(account, 'GET', '/messages/view', params=params)
    return [message(m) for m in rows or []]


def message_detail(account, folder_id, message_id):
    base = f'/folders/{check_id(folder_id)}/messages/{check_id(message_id)}'
    out = message({**(call(account, 'GET', f'{base}/details') or {}), 'messageId': message_id, 'folderId': folder_id})
    out['content'] = (call(account, 'GET', f'{base}/content') or {}).get('content', '')
    out['attachments'] = []
    if out['has_attachments']:
        info = call(account, 'GET', f'{base}/attachmentinfo') or {}
        out['attachments'] = [{'id': str(a.get('attachmentId')), 'name': a.get('attachmentName', ''),
                               'size': _ms(a.get('attachmentSize'))} for a in info.get('attachments') or []]
    return out


def update(account, mode, message_ids, **extra):
    call(account, 'PUT', '/updatemessage', json_body={'mode': mode, 'messageId': [int(check_id(i)) for i in message_ids],
                                                      **extra})


def delete(account, folder_id, message_id):
    call(account, 'DELETE', f'/folders/{check_id(folder_id)}/messages/{check_id(message_id)}')


def attachment(account, folder_id, message_id, attachment_id):
    """Streamed response for one attachment; the caller closes it."""
    return call(account, 'GET', f'/folders/{check_id(folder_id)}/messages/{check_id(message_id)}/attachments/'
                                f'{quote(check_id(attachment_id, ATTACHMENT_ID))}', stream=True)


def upload(account, name, data):
    out = call(account, 'POST', '/messages/attachments', params={'fileName': name}, body=data,
               headers={'Content-Type': 'application/octet-stream'})
    out = out[0] if isinstance(out, list) and out else out
    if not isinstance(out, dict) or not out.get('storeName'):
        raise ZohoError('Zoho Mail did not accept the attachment.')
    return {'storeName': out['storeName'], 'attachmentPath': out.get('attachmentPath', ''),
            'attachmentName': out.get('attachmentName', name)}


def send(account, payload, reply_to=None):
    """Send a new message, or a reply/forward of `reply_to` (message id) when given."""
    if reply_to:
        return call(account, 'POST', f'/messages/{check_id(reply_to)}', json_body=payload)
    return call(account, 'POST', '/messages', json_body=payload)
