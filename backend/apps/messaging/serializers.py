"""Messaging serializers."""
from rest_framework import serializers

from apps.accounts.models import User
from .models import (
    Conversation,
    ConversationBlock,
    ConversationReport,
    ConversationStatus,
    ConversationType,
    Message,
)
from . import services


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    is_me = serializers.SerializerMethodField()


    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'sender_id',
            'body',
            'attachment_url',
            'is_system',
            'is_me',
            'created_at',
        ]
        read_only_fields = ['id', 'conversation', 'sender', 'sender_id', 'is_system', 'is_me', 'created_at']

    def get_is_me(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.sender_id == request.user.id


class ConversationListSerializer(serializers.ModelSerializer):
    customer = PublicUserSerializer(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    store_slug = serializers.CharField(source='store.slug', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'type',
            'customer',
            'store',
            'store_name',
            'store_slug',
            'order',
            'order_number',
            'product',
            'product_title',
            'product_slug',
            'subject',
            'status',
            'unread_count',
            'last_message',
            'created_at',
            'updated_at',
        ]

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if not msg:
            return None
        return {
            'id': msg.id,
            'body': msg.body,
            'sender_id': msg.sender_id,
            'created_at': msg.created_at,
        }

    def get_unread_count(self, obj) -> int:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return services.get_conversation_unread_count(obj, request.user)


class ConversationDetailSerializer(ConversationListSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationListSerializer.Meta):
        fields = ConversationListSerializer.Meta.fields + ['messages']


class StartConversationSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(required=False, allow_null=True)
    order_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=ConversationType.choices, default=ConversationType.SELLER)
    subject = serializers.CharField(max_length=200, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True)
    attachment_url = serializers.URLField(required=False, allow_blank=True)


class ReportConversationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=64)
    details = serializers.CharField(required=False, allow_blank=True)


class ConversationBlockSerializer(serializers.ModelSerializer):
    """The blocker's own list of people they have refused contact from.

    Only the blocker ever reads this, and only their own rows are listed. The
    blocked party is shown by name/email because the blocker chose them from a
    conversation they can already see — this endpoint is not a directory.
    """

    blocked = PublicUserSerializer(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True, default='')

    class Meta:
        model = ConversationBlock
        fields = [
            'id',
            'blocked',
            'store',
            'store_name',
            'reason',
            'created_at',
        ]
        read_only_fields = fields


class CreateConversationBlockSerializer(serializers.Serializer):
    """Block a user directly, or the store owner behind a conversation."""

    user_id = serializers.IntegerField(required=False, allow_null=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=''
    )

    def validate(self, attrs):
        has_user = bool(attrs.get('user_id'))
        has_conversation = bool(attrs.get('conversation_id'))
        if has_user == has_conversation:
            raise serializers.ValidationError(
                'Provide exactly one of user_id or conversation_id.'
            )
        return attrs

