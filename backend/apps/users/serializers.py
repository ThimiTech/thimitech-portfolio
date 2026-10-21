from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Public sign-up. Always creates a `guest` (role/is_staff are not accepted fields)."""

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs['password'], user=User(
                email=attrs['email'], username=attrs.get('username', ''),
                first_name=attrs.get('first_name', ''), last_name=attrs.get('last_name', ''),
            ))
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def create(self, validated_data):
        base = validated_data.get('username') or validated_data['email'].split('@')[0][:140] or 'user'
        username, n = base, 1
        while User.objects.filter(username=username).exists():  # alice@a.com and alice@b.com must not 500
            n += 1
            username = f'{base}{n}'

        return User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', '').strip(),
            last_name=validated_data.get('last_name', '').strip(),
        )


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    INVALID = 'This reset link is invalid or has expired. Request a new one.'

    def validate(self, attrs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(attrs['uid'])), is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is None or not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': self.INVALID})
        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        attrs['user'] = user
        return attrs

class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'is_staff', 'department', 'designation', 'photo', 'theme',
        ]
        read_only_fields = ['id', 'email', 'username', 'role', 'is_staff']

    def _profile(self, user):
        return getattr(user, 'profile', None)

    def get_department(self, user):
        p = self._profile(user)
        return {'id': p.department_id, 'name': p.department.name} if p and p.department else None

    def get_designation(self, user):
        p = self._profile(user)
        return p.designation if p else ''

    def get_photo(self, user):
        p = self._profile(user)
        if not (p and p.photo):
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(p.photo.url) if request else p.photo.url
