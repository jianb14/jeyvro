"""Audit serializers (Phase 13.7) — read-only representation for the audit viewer."""
from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor_email',
            'action',
            'object_type',
            'object_id',
            'detail',
            'created_at',
        ]
