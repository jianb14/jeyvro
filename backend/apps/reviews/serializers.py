"""Review serializers (Phase 14 — backend-api rule 2, declared fields only).

The public shape mirrors the `ReviewCard` contract the frontend already
renders (author / rating / verified / text / photos); write input goes
through its own serializer so rating bounds and body length are checked
server-side before services run.
"""
from rest_framework import serializers

from .models import Review, ReviewImage, ReviewReport


def _author_name(user):
    """Initial-masked display name — full names never leak on reviews."""
    first = (user.first_name or user.email.split('@')[0]).strip().capitalize()
    last = (user.last_name or '').strip()
    if last:
        return f'{first} {last[0]}.'
    return first


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image_url', 'caption']


class ReviewSerializer(serializers.ModelSerializer):
    """Public review row — moderation internals never cross the wire."""

    author = serializers.SerializerMethodField()
    verified_purchase = serializers.SerializerMethodField()
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'rating',
            'title',
            'body',
            'author',
            'verified_purchase',
            'images',
            'seller_reply',
            'seller_replied_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_author(self, obj):
        return _author_name(obj.user)

    def get_verified_purchase(self, obj):
        # Every persisted review proved a delivered purchase at creation —
        # this is a property of the row, not a client-supplied flag (§6).
        return True


class ReviewWriteSerializer(serializers.Serializer):
    """Create/edit input — rating 1–5, body required, photos optional."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(required=False, allow_blank=True, max_length=150)
    body = serializers.CharField(max_length=4000)
    image_urls = serializers.ListField(
        child=serializers.URLField(max_length=500),
        required=False,
        allow_empty=True,
        max_length=4,
    )


class ReviewReportSerializer(serializers.Serializer):
    """Abuse report input (14.3)."""

    reason = serializers.ChoiceField(choices=ReviewReport.Reason.choices)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ReviewReplySerializer(serializers.Serializer):
    """Seller's official reply input — one per review (14.2)."""

    text = serializers.CharField(max_length=2000)


class ReviewModerationSerializer(serializers.Serializer):
    """Staff hide/restore input — hiding demands a reason (§6)."""

    action = serializers.ChoiceField(choices=['hide', 'restore'])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class StaffReviewSerializer(serializers.ModelSerializer):
    """Console shape (staff queue + seller studio) — moderation context in,
    customer-facing detail out. Aggregates are never recomputed here."""

    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.CharField(source='store.slug', read_only=True)
    order_number = serializers.CharField(source='order.number', read_only=True)
    author = serializers.SerializerMethodField()
    author_email = serializers.CharField(source='user.email', read_only=True)
    report_count = serializers.SerializerMethodField()
    open_report_count = serializers.SerializerMethodField()
    moderated_by_email = serializers.EmailField(
        source='moderated_by.email', read_only=True, default=None
    )
    images = ReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'product_title',
            'product_slug',
            'store_name',
            'store_slug',
            'order_number',
            'author',
            'author_email',
            'rating',
            'title',
            'body',
            'status',
            'report_count',
            'open_report_count',
            'moderation_reason',
            'moderated_by_email',
            'moderated_at',
            'seller_reply',
            'seller_replied_at',
            'images',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_author(self, obj):
        return _author_name(obj.user)

    def get_report_count(self, obj):
        return len(obj.reports.all())

    def get_open_report_count(self, obj):
        return sum(1 for report in obj.reports.all() if not report.resolved)

