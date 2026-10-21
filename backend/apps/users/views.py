import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    MeSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer, RegisterSerializer,
)
from drf_spectacular.utils import extend_schema, inline_serializer
from .tasks import send_email
from .throttles import (
    PasswordResetConfirmThrottle, PasswordResetIPThrottle, PasswordResetThrottle, RegisterThrottle,
)

log = logging.getLogger(__name__)



@extend_schema(
    tags=["Authentication"],
    summary="Register a new user (always a guest) and sign them in",
    description=(
        "Creates a guest account from email + password (+ optional first/last name) and returns a JWT pair, "
        "so sign-up is one call. Username is optional; it is generated from the email address."
    ),
    request=RegisterSerializer,
    responses={201: inline_serializer('RegisterResult', {
        'message': serializers.CharField(), 'access': serializers.CharField(), 'refresh': serializers.CharField(),
    })},
)
@api_view(['POST'])
@authentication_classes([])  # a stale token in the browser must not turn sign-up into a 401
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"message": "User registered successfully", "access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@extend_schema(
    tags=["Authentication"],
    summary="Current user",
    description="Returns the authenticated user with role and profile summary. PATCH updates first/last name and theme.",
    request=MeSerializer,
    responses={200: MeSerializer},
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'PATCH':
        serializer = MeSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(MeSerializer(request.user, context={'request': request}).data)


def revoke_all_tokens(user):
    """Blacklist every outstanding refresh token. CHECK_REVOKE_TOKEN already rejects tokens minted before the
    password changed; this also stops old refresh tokens from rotating at all."""
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=t) for t in OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)],
        ignore_conflicts=True,
    )


@extend_schema(
    tags=["Authentication"],
    summary="Request a password reset email",
    description="Always 200 (never reveals whether the email has an account). Active accounts get a one-time link.",
    request=PasswordResetRequestSerializer,
    responses={200: inline_serializer('PasswordResetRequested', {'message': serializers.CharField()})},
)
@api_view(['POST'])
@authentication_classes([])  # a stale token in the browser must not turn this into a 401
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle, PasswordResetIPThrottle])
def password_reset(request):
    s = PasswordResetRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = User.objects.filter(email__iexact=s.validated_data['email'].strip(), is_active=True).first()
    if user and user.has_usable_password():
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        link = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={default_token_generator.make_token(user)}'
        body = (f'Hi {user.full_name},\n\nSomeone (hopefully you) asked to reset your Thimi Tech password. '
                f'Open this link to choose a new one:\n\n{link}\n\n'
                'The link works once and expires in a few days. If you did not ask for this, ignore this email; '
                'your password stays the same.')
        try:
            send_email.delay('Reset your Thimi Tech password', body, [user.email])
        except Exception:  # noqa: BLE001 -- broker down must not reveal anything or 500
            log.exception('Could not queue password reset email')
    return Response({'message': 'If that email has an account, a reset link is on its way.'})


@extend_schema(
    tags=["Authentication"],
    summary="Set a new password from a reset link",
    description="Validates the uid/token pair and the password rules. Revokes every existing session token.",
    request=PasswordResetConfirmSerializer,
    responses={200: inline_serializer('PasswordResetDone', {'message': serializers.CharField()})},
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetConfirmThrottle])
def password_reset_confirm(request):
    s = PasswordResetConfirmSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    user = s.validated_data['user']
    user.set_password(s.validated_data['new_password'])
    user.save(update_fields=['password'])  # also invalidates the reset token (it hashes the password)
    revoke_all_tokens(user)
    return Response({'message': 'Password updated. Sign in with your new password.'})
