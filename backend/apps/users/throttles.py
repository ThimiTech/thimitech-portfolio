from rest_framework.throttling import SimpleRateThrottle


class ClientIPThrottle(SimpleRateThrottle):
    """Per-scope rate limit keyed on the real client IP. Behind nginx REMOTE_ADDR is the proxy, so DRF's default
    ident would put every user in one bucket; reuse attendance's proxy-aware client_ip instead.
    Rates: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'][scope]."""

    def ident(self, request):
        from apps.attendance.services import client_ip  # lazy: attendance pulls in leave/calendar models
        return client_ip(request) or self.get_ident(request)

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.ident(request)}


class LoginThrottle(ClientIPThrottle):
    """Per IP + submitted email: stops password guessing on one account without locking out an office NAT."""
    scope = 'login'

    def ident(self, request):
        email = request.data.get('email', '') if hasattr(request.data, 'get') else ''
        return f'{super().ident(request)}:{str(email).strip().lower()[:254]}'


class LoginIPThrottle(ClientIPThrottle):
    """Looser per-IP ceiling against spraying many accounts from one address."""
    scope = 'login_ip'


class RegisterThrottle(ClientIPThrottle):
    scope = 'register'


class PasswordThrottle(ClientIPThrottle):
    scope = 'password'


class TokenRefreshThrottle(ClientIPThrottle):
    scope = 'token_refresh'


class PasswordResetThrottle(LoginThrottle):
    """Reset emails per IP + email: stops mail-bombing one inbox without locking out an office NAT."""
    scope = 'password_reset'


class PasswordResetIPThrottle(ClientIPThrottle):
    scope = 'password_reset_ip'


class PasswordResetConfirmThrottle(ClientIPThrottle):
    scope = 'password_reset_confirm'
