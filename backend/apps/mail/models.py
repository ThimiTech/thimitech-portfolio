from django.conf import settings
from django.db import models

from . import crypto


class MailAccount(models.Model):
    """One person's connected Zoho Mail mailbox. Tokens are encrypted (crypto.py) and never leave the server."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mail_account')
    account_id = models.CharField(max_length=40)  # Zoho accountId
    email = models.EmailField()
    display_name = models.CharField(max_length=200, blank=True)
    accounts_server = models.URLField()  # e.g. https://accounts.zoho.com (the person's Zoho data centre)
    mail_server = models.URLField()  # e.g. https://mail.zoho.com
    send_from = models.JSONField(default=list, blank=True)  # [{address, name}] the mailbox may send as
    refresh_token_enc = models.TextField()
    access_token_enc = models.TextField(blank=True)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    needs_reconnect = models.BooleanField(default=False)  # Zoho rejected the refresh token (revoked / expired)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.email} ({self.user})'

    @property
    def refresh_token(self):
        return crypto.decrypt(self.refresh_token_enc)

    @refresh_token.setter
    def refresh_token(self, value):
        self.refresh_token_enc = crypto.encrypt(value)

    @property
    def access_token(self):
        return crypto.decrypt(self.access_token_enc)

    @access_token.setter
    def access_token(self, value):
        self.access_token_enc = crypto.encrypt(value)
