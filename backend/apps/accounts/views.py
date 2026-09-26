"""Authentication + account API (Phase 3).

Rules honoured: thin views (parse → validate → service → serialize) —
backend-api rule 5; explicit permission class on every view (rule 6); the
server is the final line of defense (§10) — lockouts, verification, and
ownership checks all happen here, never in the UI.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart import services as cart_services
from apps.common.pagination import CountItemsPagination
from apps.platform.services import notification_defaults

from . import services
from .models import Address, NotificationPreference, User
from .permissions import InStaffGroup, IsOwner
from .serializers import (
    AddressSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    NotificationPreferenceSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    StaffMemberSerializer,
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
            UserSerializer(user, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
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

        # Suspension gate runs BEFORE authenticate(): suspend() now sets
        # is_active=False (live sessions revoked, §4 v1.10) and the auth
        # backend refuses inactive users — without this pre-check a suspended
        # account would collapse into a generic "invalid credentials".
        target = User.objects.filter(email__iexact=email).first()
        if target and not target.is_login_allowed:
            return Response(
                {'error': 'account_suspended',
                 'detail': 'This account is suspended.'},
                status=status.HTTP_403_FORBIDDEN,
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
        # Guest carts follow the visitor into their account (§6 Phase 7):
        # capture the pre-login session key — login() cycles it.
        guest_session_key = request.session.session_key
        login(request, user)
        cart_services.merge_guest_cart(user, guest_session_key)
        return Response(UserSerializer(user, context={'request': request}).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'logged out'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
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
        # New accounts start from the platform defaults (§6 v1.13); an
        # existing row always wins — the customer's own choice is theirs.
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user, defaults=notification_defaults()
        )
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user, defaults=notification_defaults()
        )
        serializer = NotificationPreferenceSerializer(prefs, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# --- Phase 13.1/13.2 staff administration views ------------------------------
#
# Group-gated (§4): support has read-only oversight of accounts; the
# administrator group owns role assignment, user suspension, and the staff
# directory. Views stay thin — every write goes through the accounts services,
# so powers never bypass validation or the audit trail (marketplace-admin
# rules 2/3).

class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """13.2 user management — {count, items} with q/status/role filters."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'administrator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        qs = User.objects.prefetch_related('groups').order_by('-date_joined')
        params = self.request.query_params

        q = params.get('q')
        if q:
            qs = qs.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone__icontains=q)
            )

        account_status = params.get('status')
        if account_status in User.AccountStatus.values:
            qs = qs.filter(account_status=account_status)

        role = params.get('role')
        if role == 'customer':
            qs = qs.filter(is_seller=False, is_staff=False)
        elif role == 'seller':
            qs = qs.filter(is_seller=True)
        elif role == 'staff':
            qs = qs.filter(is_staff=True)

        return qs


class SuspendUserView(APIView):
    """POST /api/v1/auth/admin/users/<pk>/suspend — administrator only (§4)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator']

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            services.suspend_user(
                request.user, target, reason=request.data.get('reason', '')
            )
        except ValueError as exc:
            return Response(
                {'error': 'suspend_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            AdminUserSerializer(target, context={'request': request}).data
        )


class ReactivateUserView(APIView):
    """POST /api/v1/auth/admin/users/<pk>/reactivate — administrator only (§4)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator']

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            services.reactivate_user(
                request.user, target, reason=request.data.get('reason', '')
            )
        except ValueError as exc:
            return Response(
                {'error': 'reactivate_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            AdminUserSerializer(target, context={'request': request}).data
        )


class StaffMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """13.1 staff & permission directory — administrator-only permission audit."""

    serializer_class = StaffMemberSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        qs = (
            User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
            .prefetch_related('groups')
            .order_by('email')
        )
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        return qs


class AssignStaffRoleView(APIView):
    """POST /api/v1/auth/admin/staff/<pk>/roles/assign — administrator only."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator']

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            services.assign_staff_group(
                request.user, target, group_name=request.data.get('group', '')
            )
        except ValueError as exc:
            return Response(
                {'error': 'role_change_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            StaffMemberSerializer(target, context={'request': request}).data
        )


class RemoveStaffRoleView(APIView):
    """POST /api/v1/auth/admin/staff/<pk>/roles/remove — administrator only."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator']

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        try:
            services.remove_staff_group(
                request.user, target, group_name=request.data.get('group', '')
            )
        except ValueError as exc:
            return Response(
                {'error': 'role_change_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            StaffMemberSerializer(target, context={'request': request}).data
        )
