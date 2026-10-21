from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Case-insensitive email login. Sign-up stores emails lowercased, but users type them however they like;
    legacy mixed-case rows still work too (an exact match wins if two rows differ only by case)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = username if username is not None else kwargs.get(User.USERNAME_FIELD)
        if email is None or password is None:
            return None
        email = str(email).strip()
        users = User._default_manager.filter(email__iexact=email)
        user = users.filter(email=email).first() or users.order_by('pk').first()
        if user is None:
            User().set_password(password)  # same timing as a real check (ModelBackend does this too)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
