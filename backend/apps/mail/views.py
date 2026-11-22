"""/api/mail/: each signed-in staff member's own Zoho Mail mailbox, read and sent through the Zoho Mail API.

Nothing from the mailbox is stored here; every request goes to Zoho with the person's own token.
Connecting: GET connect/ → Zoho consent page → Zoho redirects to {FRONTEND_URL}/app/mail/callback, which
POSTs the code to callback/. The signed `state` ties the code to the person who started the flow.
"""
from email.utils import getaddresses

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.http import StreamingHttpResponse
from django.utils.http import content_disposition_header
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.permissions.permissions import IsEmployee

from . import zoho
from .models import MailAccount
from .zoho import Reconnect, ZohoError

STATE_SALT = 'mail.oauth'
STATE_MAX_AGE = 15 * 60
PAGE = 50
FOLDER_ORDER = ['Inbox', 'Drafts', 'Templates', 'Snoozed', 'Sent', 'Outbox', 'Normal', 'Spam', 'Trash']


class MailSendThrottle(UserRateThrottle):
    scope = 'mail_send'


class NotConnected(ZohoError):
    def __init__(self):
        super().__init__('Connect your Zoho Mail mailbox first.', 409)


# ───────────── request shapes ─────────────

class Recipients(serializers.ListField):
    """A list of addresses ("a@b.com" or "Name <a@b.com>"; a comma-separated string also works) → bare addresses."""

    def __init__(self, **kw):
        super().__init__(child=serializers.CharField(max_length=320), max_length=100, **kw)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = [data]
        out = []
        for _, addr in getaddresses(super().to_internal_value(data)):
            try:
                validate_email(addr)
            except DjangoValidationError:
                raise serializers.ValidationError(f'"{addr or "?"}" is not a valid email address.')
            if addr.lower() not in (a.lower() for a in out):
                out.append(addr)
        return out


class AttachmentRef(serializers.Serializer):
    storeName = serializers.CharField(max_length=500)
    attachmentPath = serializers.CharField(max_length=1000, allow_blank=True)
    attachmentName = serializers.CharField(max_length=500)


class SendSerializer(serializers.Serializer):
    from_address = serializers.EmailField(required=False)
    to = Recipients()
    cc = Recipients(required=False, default=list)
    bcc = Recipients(required=False, default=list)
    subject = serializers.CharField(max_length=998, allow_blank=True, default='')
    content = serializers.CharField(max_length=2_000_000, allow_blank=True, default='', trim_whitespace=False)
    format = serializers.ChoiceField(choices=['html', 'plaintext'], default='html')
    attachments = AttachmentRef(many=True, required=False, default=list)
    reply_to = serializers.RegexField(r'^\d{1,30}$', required=False)
    action = serializers.ChoiceField(choices=['reply', 'forward'], required=False, default='reply')

    def validate(self, attrs):
        if not attrs['to']:
            raise serializers.ValidationError({'to': 'Add at least one recipient.'})
        return attrs


class CallbackSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=1000)
    state = serializers.CharField(max_length=1000)
    accounts_server = serializers.CharField(max_length=200, required=False, allow_blank=True)


class ReadSerializer(serializers.Serializer):
    read = serializers.BooleanField(default=True)


class MoveSerializer(serializers.Serializer):
    to = serializers.RegexField(r'^\d{1,30}$')


def status_payload(account):
    return {
        'configured': zoho.configured(),
        'connected': bool(account and not account.needs_reconnect),
        'needs_reconnect': bool(account and account.needs_reconnect),
        'email': account.email if account else '',
        'display_name': account.display_name if account else '',
        'send_from': account.send_from if account else [],
    }


class MailMixin:
    permission_classes = [IsEmployee]

    def handle_exception(self, exc):
        if isinstance(exc, ZohoError):
            return Response({'detail': exc.detail, 'reconnect': isinstance(exc, Reconnect),
                             'not_connected': isinstance(exc, NotConnected)}, status=exc.status)
        return super().handle_exception(exc)

    def account(self):
        account = MailAccount.objects.filter(user=self.request.user).first()
        if not account:
            raise NotConnected()
        if account.needs_reconnect:
            raise Reconnect()
        return account


@extend_schema(tags=['Mail'])
class MailViewSet(MailMixin, viewsets.ViewSet):
    """Connection, folders, sending and attachment upload."""

    def get_throttles(self):
        return [MailSendThrottle()] if self.action in ('send', 'upload') else []

    @extend_schema(summary='Is my Zoho mailbox connected?', responses={200: dict})
    @action(detail=False, methods=['get'])
    def status(self, request):
        return Response(status_payload(MailAccount.objects.filter(user=request.user).first()))

    @extend_schema(summary='Zoho consent URL to connect my mailbox', responses={200: dict})
    @action(detail=False, methods=['get'])
    def connect(self, request):
        if not zoho.configured():
            raise ZohoError('Zoho Mail is not set up on this server yet (ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET).', 503)
        state = signing.dumps({'u': request.user.pk}, salt=STATE_SALT)
        return Response({'url': zoho.authorize_url(state)})

    @extend_schema(summary='Finish connecting: exchange the Zoho code', request=CallbackSerializer,
                   responses={200: dict})
    @action(detail=False, methods=['post'])
    def callback(self, request):
        s = CallbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            state = signing.loads(s.validated_data['state'], salt=STATE_SALT, max_age=STATE_MAX_AGE)
        except signing.BadSignature:
            raise ZohoError('This sign-in link has expired. Start connecting again.', 400)
        if state.get('u') != request.user.pk:
            raise ZohoError('This sign-in was started by someone else. Start connecting again.', 400)
        server = zoho.accounts_server(s.validated_data.get('accounts_server'))
        account = zoho.connect(request.user, s.validated_data['code'], server)
        return Response(status_payload(account))

    @extend_schema(summary='Disconnect my mailbox (revokes the Zoho grant)', request=None, responses={204: None})
    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        account = MailAccount.objects.filter(user=request.user).first()
        if account:
            zoho.revoke(account)
            account.delete()
        return Response(status=204)

    @extend_schema(summary='My mail folders', responses={200: dict})
    @action(detail=False, methods=['get'])
    def folders(self, request):
        rows = zoho.folders(self.account())
        rank = {t: i for i, t in enumerate(FOLDER_ORDER)}
        rows.sort(key=lambda f: (rank.get(f['type'], len(rank)), f['path'] or f['name']))
        return Response(rows)

    @extend_schema(summary='Send, reply or forward', request=SendSerializer, responses={201: None})
    @action(detail=False, methods=['post'])
    def send(self, request):
        account = self.account()
        s = SendSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        allowed = [a['address'] for a in account.send_from] or [account.email]
        sender = d.get('from_address') or allowed[0]
        if sender.lower() not in (a.lower() for a in allowed):
            raise serializers.ValidationError({'from_address': 'You cannot send as that address.'})
        payload = {'fromAddress': sender, 'toAddress': ','.join(d['to']), 'subject': d['subject'],
                   'content': d['content'], 'mailFormat': d['format']}
        if d['cc']:
            payload['ccAddress'] = ','.join(d['cc'])
        if d['bcc']:
            payload['bccAddress'] = ','.join(d['bcc'])
        if d['attachments']:
            payload['attachments'] = [dict(a) for a in d['attachments']]
        if d.get('reply_to'):
            payload['action'] = d['action']
        zoho.send(account, payload, reply_to=d.get('reply_to'))
        return Response(status=201)

    @extend_schema(summary='Upload an attachment for a message being written',
                   request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
                   responses={201: dict})
    @action(detail=False, methods=['post'], url_path='attachments', parser_classes=[MultiPartParser])
    def upload(self, request):
        account = self.account()
        f = request.FILES.get('file')
        if not f:
            raise serializers.ValidationError({'file': 'Choose a file.'})
        if f.size > settings.MAIL_ATTACHMENT_MAX_BYTES:
            raise serializers.ValidationError(
                {'file': f'Attachments can be at most {settings.MAIL_ATTACHMENT_MAX_BYTES // (1024 * 1024)} MB.'})
        name = (f.name or 'attachment').replace('/', '_').replace('\\', '_')[:200]
        return Response(zoho.upload(account, name, f.read()), status=201)


FOLDER_PARAM = OpenApiParameter('folder', str, description='Zoho folder id the message is in')


@extend_schema(tags=['Mail'])
class MessageViewSet(MailMixin, viewsets.ViewSet):
    """Messages in my mailbox. Every call names the folder (?folder=) because Zoho addresses messages by folder."""
    lookup_value_regex = r'\d{1,30}'

    def _folder(self, request):
        return zoho.check_id(request.query_params.get('folder') or request.data.get('folder') or '')

    @extend_schema(summary='List a folder, or search all mail (?q=)', operation_id='mail_messages_list', parameters=[
        FOLDER_PARAM, OpenApiParameter('q', str), OpenApiParameter('start', int), OpenApiParameter('unread', bool)],
        responses={200: dict})
    def list(self, request):
        account = self.account()
        q = (request.query_params.get('q') or '').strip()[:200]
        try:
            start = max(int(request.query_params.get('start', 1)), 1)
        except ValueError:
            start = 1
        rows = zoho.messages(account, folder_id=None if q else self._folder(request), query=q, start=start,
                             limit=PAGE, unread=request.query_params.get('unread') in ('1', 'true'))
        return Response({'results': rows, 'start': start, 'next': start + PAGE if len(rows) >= PAGE else None})

    @extend_schema(summary='Open a message (headers, HTML body, attachment list)',
                   parameters=[FOLDER_PARAM, OpenApiParameter('mark_read', bool)], responses={200: dict})
    def retrieve(self, request, pk=None):
        account = self.account()
        msg = zoho.message_detail(account, self._folder(request), pk)
        if msg['unread'] and request.query_params.get('mark_read') in ('1', 'true'):
            zoho.update(account, 'markAsRead', [pk])
            msg['unread'] = False
        return Response(msg)

    @extend_schema(summary='Move to Trash, or delete for good when already in Trash', parameters=[FOLDER_PARAM],
                   responses={204: None})
    def destroy(self, request, pk=None):
        account = self.account()
        folder = self._folder(request)
        trash = next((f['id'] for f in zoho.folders(account) if f['type'] == 'Trash'), None)
        if trash and trash != folder:
            zoho.update(account, 'moveMessage', [pk], destfolderId=trash)
        else:
            zoho.delete(account, folder, pk)
        return Response(status=204)

    @extend_schema(summary='Mark read / unread', request=ReadSerializer, responses={204: None})
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        s = ReadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        zoho.update(self.account(), 'markAsRead' if s.validated_data['read'] else 'markAsUnread', [pk])
        return Response(status=204)

    @extend_schema(summary='Move to another folder', request=MoveSerializer, responses={204: None})
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        s = MoveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        zoho.update(self.account(), 'moveMessage', [pk], destfolderId=s.validated_data['to'])
        return Response(status=204)

    @extend_schema(summary='Download an attachment', parameters=[FOLDER_PARAM, OpenApiParameter('name', str)],
                   responses={(200, 'application/octet-stream'): bytes})
    @action(detail=True, methods=['get'], url_path=r'attachments/(?P<attachment_id>[A-Za-z0-9_.\-]{1,200})')
    def attachment(self, request, pk=None, attachment_id=None):
        upstream = zoho.attachment(self.account(), self._folder(request), pk, attachment_id)
        name = (request.query_params.get('name') or 'attachment')[:200]

        def chunks():
            try:
                while block := upstream.read(64 * 1024):
                    yield block
            finally:
                upstream.close()

        # Always a download, never rendered: the bytes come from whoever sent the email.
        resp = StreamingHttpResponse(chunks(), content_type='application/octet-stream')
        resp['Content-Disposition'] = content_disposition_header(True, name)
        resp['Content-Security-Policy'] = 'sandbox'
        resp['X-Content-Type-Options'] = 'nosniff'
        if upstream.headers.get('Content-Length'):
            resp['Content-Length'] = upstream.headers['Content-Length']
        return resp
