"""Authentication + account API (Phase 3).

Rules honoured: thin views (parse → validate → service → serialize) —
backend-api rule 5; explicit permission class on every view (rule 6); the
server is the final line of defense (§10) — lockouts, verification, and
ownership checks all happen here, never in the UI.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.middleware.csrf import get_token
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Address, NotificationPreference, User
from .permissions import IsOwner
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    NotificationPreferenceSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


class CsrfView(APIView):
    """Issues the CSRF cookie the frontend reads for X-CSRFToken headers."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'detail': 'csrf cookie set', 'csrfToken': get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        services.send_verification_email(request, user)
        return Response(
            UserSerializer(user).data, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        if services.is_locked_out(email):
            return Response(
                {'error': 'account_locked',
                 'detail': 'Too many failed attempts. Try again in 15 minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(request, email=email, password=password)
        if user is None:
            services.register_failed_login(email)
            return Response(
                {'error': 'invalid_credentials',
                 'detail': 'Email or password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_login_allowed:
            return Response(
                {'error': 'account_suspended',
                 'detail': 'This account is suspended.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        services.clear_failed_logins(email)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'logged out'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'error': 'invalid_credentials',
                 'detail': 'Current password is incorrect.',
                 'field_errors': {'current_password': ['Incorrect password.']}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Fetch a FRESH copy from the DB so update_session_auth_hash's guard
        # sees the password change (mutating request.user in place hides it,
        # leaving the session on the old auth hash — the user gets logged out).
        db_user = User.objects.get(pk=user.pk)
        db_user.set_password(serializer.validated_data['new_password'])
        db_user.save(update_fields=['password', 'updated_at'])
        update_session_auth_hash(request, db_user)
        return Response({'detail': 'password changed'})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = services.decode_uid(request.query_params.get('uid', ''))
        token = request.query_params.get('token', '')
        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'invalid_token',
                 'detail': 'This verification link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified', 'updated_at'])
        return Response({'detail': 'email verified'})


class ResendVerificationView(APIView):
    """Always responds 200 — never reveals whether an email exists (§10)."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '')
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.email_verified and user.is_login_allowed:
            services.send_verification_email(request, user)
        return Response({'detail': 'If the address exists, a link was sent.'})


class PasswordResetRequestView(APIView):
    """Always responds 200 — no user enumeration (§10)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data['email']
        ).first()
        if user and user.is_login_allowed:
            services.send_password_reset_email(request, user)
        return Response({'detail': 'If the address exists, a link was sent.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.decode_uid(token_uid := serializer.validated_data['uid'])
        if user is None or not default_token_generator.check_token(
            user, serializer.validated_data['token']
        ):
            return Response(
                {'error': 'invalid_token',
                 'detail': 'This reset link is invalid or expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        services.clear_failed_logins(user.email)
        user.save(update_fields=['password', 'updated_at'])
        return Response({'detail': 'password reset'})


class AddressViewSet(viewsets.ModelViewSet):
    """Ownership-scoped: customers only ever see/touch their own addresses
    (backend-feature rule 3). Ownership enforced by queryset + IsOwner."""

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

        update_session_auth_hash(request, user)
        return Response({'detail': 'password changed'})

        return Response(UserSerializer(user).data)
