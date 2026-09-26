"""Account serializers — declared fields only (backend-api rule 2).

All validation is server-side (§10.1); passwords never round-trip.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Address, NotificationPreference, User


class StaffRolesField(serializers.Field):
    """Exposes group names ONLY to authenticated staff/superusers.

    For regular customers, returns an empty list so staff roles/privileges
    never leak across the wire (PROJECT_CONTEXT §10, security skill).
    """

    def to_representation(self, user):
        request = self.context.get('request')
        caller = getattr(request, 'user', None)
        if not (caller and caller.is_authenticated and (caller.is_staff or caller.is_superuser)):
            return []
        if user.is_superuser:
            return ['super_administrator', 'administrator']
        return list(user.groups.values_list('name', flat=True))


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Read/update own profile. Email is the identity — never edited here."""

    staff_roles = StaffRolesField(source='*', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'avatar_url',
            'is_seller', 'is_staff', 'staff_roles', 'email_verified',
            'account_status', 'date_joined',
        ]
        read_only_fields = [
            'id', 'email', 'avatar_url', 'is_seller', 'is_staff',
            'staff_roles', 'email_verified', 'account_status', 'date_joined',
        ]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'label', 'full_name', 'phone', 'line1', 'line2', 'city',
            'province', 'postal_code', 'is_default', 'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['order_updates_email', 'promotions_email', 'messaging_email']


# --- Phase 13.1/13.2 staff administration (admin-gated views only) ----------

class AdminUserSerializer(serializers.ModelSerializer):
    """User-management row (13.2) — support oversight, administrator actions.

    Declared fields only; passwords and session data never cross the wire
    (backend-api rule 2, §10). `staff_roles` leaks to staff callers only via
    StaffRolesField.
    """

    full_name = serializers.SerializerMethodField()
    staff_roles = StaffRolesField(source='*', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'is_seller', 'is_staff', 'staff_roles', 'account_status',
            'suspended_at', 'email_verified', 'date_joined',
        ]

    def get_full_name(self, user):
        return user.get_full_name()


class StaffMemberSerializer(serializers.ModelSerializer):
    """Staff directory row (13.1 permission audit) — administrator-only view.

    `is_superuser` is exposed deliberately: administrators need to see which
    accounts are the technical-governance carve-out before any role action.
    """

    full_name = serializers.SerializerMethodField()
    staff_roles = StaffRolesField(source='*', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'staff_roles', 'is_staff', 'is_superuser', 'account_status',
            'date_joined',
        ]

    def get_full_name(self, user):
        return user.get_full_name()
