"""Ownership and role permission classes (Phase 3.3).

Every viewset/endpoint declares its permission class explicitly
(backend-api rule 6). Role checks are server-side, never UI-only (§4).
"""
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level: only the owning user may read/write the object."""

    message = 'You may only access your own records.'

    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, 'user', None) or obj
        return owner == request.user


class IsSeller(BasePermission):
    """Role foundation: the user owns (or will own) a store (Phase 4)."""

    message = 'Seller account required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_seller)


class IsStaff(BasePermission):
    """Staff members (is_staff flag) — admin-site capable users."""

    message = 'Staff account required.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class InStaffGroup(BasePermission):
    """Group-based staff permissions (§4 — group-based, not all-or-nothing).

    Usage: InStaffGroup with view.required_groups = ['support', 'moderator'].
    Superusers always pass.
    """

    message = 'Your staff group is not permitted for this action.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and (user.is_staff or user.is_superuser)):
            return False
        required = getattr(view, 'required_groups', None)
        if not required:
            return user.is_staff or user.is_superuser
        return user.groups.filter(name__in=required).exists() or user.is_superuser
