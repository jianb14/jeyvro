"""Store permission classes (Phase 4).

Every view declares permissions explicitly (backend-api rule 6); ownership
is re-verified per endpoint (marketplace-sellers rule 2 / §10.3).
"""
from rest_framework.permissions import BasePermission


class IsStoreOwner(BasePermission):
    """Object-level: only the store's owning user may touch it."""

    message = 'You may only manage your own store.'

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.pk