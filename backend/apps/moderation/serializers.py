"""Moderation serializers (§20.2).

A flag row carries rules, not prose: `rule_detail` is a code summary, and the
content itself is reached through the linked review or conversation. That is
deliberate — the staff list response must not become a second copy of every
customer message on the platform.
"""
from rest_framework import serializers

from apps.messaging.models import Conversation, ConversationStatus
from apps.messaging.serializers import PublicUserSerializer
from apps.reviews.models import Review

from .models import ContentFlag


class ContentFlagSerializer(serializers.ModelSerializer):
    author = PublicUserSerializer(read_only=True)
    resolved_by = PublicUserSerializer(read_only=True)
    rule_labels = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    # Just enough of the subject for a moderator to recognise the row and open
    # it — identifiers and public-facing labels, no review body, no messages.
    review_id = serializers.IntegerField(read_only=True, allow_null=True)
    review_product = serializers.CharField(
        source='review.product.name', read_only=True, default='', allow_null=True,
    )
    review_author_email = serializers.CharField(
        source='review.user.email', read_only=True, default='', allow_null=True,
    )
    review_rating = serializers.IntegerField(
        source='review.rating', read_only=True, default=None, allow_null=True,
    )
    conversation_id = serializers.IntegerField(read_only=True, allow_null=True)
    conversation_subject = serializers.CharField(
        source='conversation.subject', read_only=True, default='', allow_null=True,
    )
    conversation_store = serializers.CharField(
        source='conversation.store.name', read_only=True, default='', allow_null=True,
    )
    conversation_status = serializers.CharField(
        source='conversation.status', read_only=True, default='', allow_null=True,
    )

    class Meta:
        model = ContentFlag
        fields = [
            'id',
            'kind',
            'kind_label',
            'status',
            'status_label',
            'rules',
            'rule_labels',
            'rule_detail',
            'author',
            'review_id',
            'review_product',
            'review_author_email',
            'review_rating',
            'conversation_id',
            'conversation_subject',
            'conversation_store',
            'conversation_status',
            'resolved_by',
            'resolved_at',
            'resolution_note',
            'created_at',
        ]
        read_only_fields = fields

    def get_rule_labels(self, obj) -> list:
        labels = dict(ContentFlag.Rule.choices)
        return [labels.get(code, code) for code in (obj.rules or [])]


class ResolveFlagSerializer(serializers.Serializer):
    """A staff decision. Confirming abuse demands a written reason."""

    action = serializers.ChoiceField(choices=['dismiss', 'confirm'])
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        default='',
        help_text='Required when confirming a flag as abuse.',
    )

    def validate(self, attrs):
        if attrs['action'] == 'confirm' and not (attrs.get('note') or '').strip():
            raise serializers.ValidationError(
                {'note': 'A reason is required to confirm a flag as abuse.'}
            )
        return attrs
