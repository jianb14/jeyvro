"""Audit views (Phase 13.7) — group-gated audit log viewer API."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import InStaffGroup
from apps.common.pagination import CountItemsPagination

from .models import AuditLog
from .serializers import AuditLogSerializer


class StaffAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff audit viewer (§13.7) — administrator/operations/moderator access.

    Supports filtering by actor email, action, object_type, and object_id.
    """

    queryset = AuditLog.objects.select_related('actor').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator', 'operations', 'moderator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        action = params.get('action')
        if action:
            qs = qs.filter(action=action)

        object_type = params.get('object_type')
        if object_type:
            qs = qs.filter(object_type=object_type)

        object_id = params.get('object_id')
        if object_id:
            qs = qs.filter(object_id=object_id)

        actor_email = params.get('actor')
        if actor_email:
            qs = qs.filter(actor__email__icontains=actor_email)

        return qs
