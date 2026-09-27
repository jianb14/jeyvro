"""Notification serializers."""
from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'category',
            'title',
            'message',
            'action_url',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = fields
