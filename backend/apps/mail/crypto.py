"""Encryption at rest for Zoho OAuth tokens. Key: MAIL_TOKEN_KEY, else derived from SECRET_KEY.
Changing the key makes stored tokens unreadable; people then just connect again."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    secret = (getattr(settings, 'MAIL_TOKEN_KEY', '') or settings.SECRET_KEY or '').encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b'thimi-mail-tokens:' + secret).digest()))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ''


def decrypt(value: str) -> str:
    if not value:
        return ''
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ''
