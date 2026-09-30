"""Review services — the verified-buyer gate, moderation and aggregates (§6).

Every review is born from a real purchase: `create_review` resolves the
caller's own delivered/completed OrderItem for the product before a row
exists — the client never proves anything (marketplace-community rule 1).
Product and Store rating aggregates are recomputed inside the same
transaction as every review state change (rule 3), never by a
background job or a frontend calculation.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.audit.services import log_event
from apps.moderation import services as moderation_services
from apps.orders.models import OrderItem, OrderStatus

from .models import Review, ReviewImage, ReviewReport, ReviewStatus
from apps.notifications import services as notification_services
from apps.notifications.models import NotificationCategory


# A review needs a purchase that actually reached the customer — paid but
# not yet delivered orders, and cancelled/refunded ones, don't qualify.
REVIEWABLE_ORDER_STATUSES = (OrderStatus.DELIVERED, OrderStatus.COMPLETED)

# Distinct reporters before the abuse foundation flags a review for staff
# (14.3 — one angry buyer cannot bury a review, moderators decide after).
REPORT_FLAG_THRESHOLD = 3

MAX_REVIEW_IMAGES = 4


class ReviewError(ValueError):
    """Customer-safe review rejection — code + message, never a stack."""

    def __init__(self, message, *, code='review_rejected'):
        super().__init__(message)
        self.code = code


def _quantize(value):
    """Aggregate averages land as Decimal(3,2) — money-style rounding."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _eligible_item(user, product):
    """The newest order line that makes `user` a verified buyer of `product`."""
    if not (user and user.is_authenticated):
        return None
    return (
        OrderItem.objects
        .filter(
            product=product,
            seller_order__order__user=user,
            seller_order__order__status__in=REVIEWABLE_ORDER_STATUSES,
        )
        .select_related('seller_order__order')
        .order_by('-seller_order__order__created_at')
        .first()
    )


def eligibility(user, product):
    """Server verdict behind the review form (§6 — never a client claim).

    `review_id` is handed back when the caller already owns a review so the
    form can open in edit mode without guessing rows by author name.
    """
    if not (user and user.is_authenticated):
        return {'can_review': False, 'reason': 'sign_in', 'order_number': None,
                'review_id': None}
    existing = Review.objects.filter(user=user, product=product).values_list('id', flat=True).first()
    if existing is not None:
        return {'can_review': False, 'reason': 'already_reviewed', 'order_number': None,
                'review_id': existing}
    item = _eligible_item(user, product)
    if item is None:
        return {'can_review': False, 'reason': 'not_eligible', 'order_number': None,
                'review_id': None}
    return {
        'can_review': True,
        'reason': 'verified_purchase',
        'order_number': item.seller_order.order.number,
        'review_id': None,
    }


# --------------------------------------------------------------------------------------
# Rating aggregates — server-computed, rewritten inside every review transaction (rule 3)
# --------------------------------------------------------------------------------------

def recompute_product_rating(product):
    """Average + count of PUBLISHED reviews written onto the product row."""
    stats = product.reviews.filter(status=ReviewStatus.PUBLISHED).aggregate(
        average=Avg('rating'), count=Count('id')
    )
    product.rating_average = _quantize(stats['average']) if stats['average'] is not None else None
    product.rating_count = stats['count']
    product.save(update_fields=['rating_average', 'rating_count', 'updated_at'])
    return product


def recompute_store_rating(store):
    """Seller rating derives from its products' reviews (§6)."""
    stats = store.reviews.filter(status=ReviewStatus.PUBLISHED).aggregate(
        average=Avg('rating'), count=Count('id')
    )
    store.rating_average = _quantize(stats['average']) if stats['average'] is not None else None
    store.rating_count = stats['count']
    store.save(update_fields=['rating_average', 'rating_count', 'updated_at'])
    return store


def _refresh_ratings(product, store):
    recompute_product_rating(product)
    recompute_store_rating(store)


# --------------------------------------------------------------------------------------
# Lifecycle — create / edit (owner) / report / moderate / reply
# --------------------------------------------------------------------------------------

@transaction.atomic
def create_review(user, *, product, rating, title='', body='', image_urls=None):
    """Create the buyer's one review for this product (14.1).

    Eligibility, the unique constraint, and the aggregate refresh all
    happen inside one transaction — a failed review never leaves a
    half-updated average behind.
    """
    item = _eligible_item(user, product)
    if item is None:
        raise ReviewError(
            'Only delivered purchases can be reviewed.', code='not_eligible'
        )
    if Review.objects.filter(user=user, product=product).exists():
        raise ReviewError('You already reviewed this product.', code='already_reviewed')

    body = (body or '').strip()
    if not body:
        raise ReviewError('Please write a few words about the product.', code='body_required')

    review = Review.objects.create(
        user=user,
        product=product,
        store=product.store,
        order=item.seller_order.order,
        rating=rating,
        title=(title or '').strip()[:150],
        body=body,
    )
    urls = (image_urls or [])[:MAX_REVIEW_IMAGES]
    ReviewImage.objects.bulk_create(
        [ReviewImage(review=review, image_url=url) for url in urls]
    )

    # §20.2 — the automatic spam rules. The row is born first and screened
    # second, and a hit does not reject the write: it parks the review as
    # FLAGGED, exactly like the 3-reporter path above, so the buyer keeps
    # their review and a human decides. `FLAGGED` is not `PUBLISHED`, so it is
    # absent from the public list and from the rating aggregates until staff
    # clear it — the spam cannot vote on a rating while it waits.
    flag = moderation_services.screen_review(
        review=review, text=f'{review.title}\n{review.body}',
    )
    if flag is not None:
        review.status = ReviewStatus.FLAGGED
        review.save(update_fields=['status', 'updated_at'])

    _refresh_ratings(product, product.store)
    return review


@transaction.atomic
def update_review(user, review_id, *, rating=None, title=None, body=None):
    """Owner edits their own review — aggregates follow the new rating."""
    review = (
        Review.objects.select_related('product__store')
        .filter(pk=review_id)
        .first()
    )
    if review is None:
        raise Review.DoesNotExist('Review not found.')
    if review.user_id != user.pk:
        raise ReviewError('You may only edit your own review.', code='not_owner')

    if rating is not None:
        if not (1 <= int(rating) <= 5):
            raise ReviewError('Rating must be between 1 and 5.', code='rating_bounds')
        review.rating = int(rating)
    if title is not None:
        review.title = title.strip()[:150]
    if body is not None:
        body = body.strip()
        if not body:
            raise ReviewError('Please write a few words about the product.', code='body_required')
        review.body = body

    review.save(update_fields=['rating', 'title', 'body', 'updated_at'])

    # §20.2 — an edit is a second chance to smuggle a link or a phone number
    # into an already-published review, so the same rules run again. A hit
    # pulls it to FLAGGED and re-opens the existing flag row (one row per
    # subject), rather than filing a second one staff would triage twice.
    if review.status == ReviewStatus.PUBLISHED:
        if moderation_services.screen_review(
            review=review, text=f'{review.title}\n{review.body}',
        ) is not None:
            review.status = ReviewStatus.FLAGGED
            review.save(update_fields=['status', 'updated_at'])

    _refresh_ratings(review.product, review.store)
    return review


@transaction.atomic
def report_review(user, review, *, reason, notes=''):
    """Customer abuse report (14.3). Distinct reports flag for moderators."""
    if review.user_id == user.pk:
        raise ReviewError('You cannot report your own review.', code='self_report')
    if review.status == ReviewStatus.HIDDEN:
        raise ReviewError('This review is no longer visible.', code='not_visible')
    if ReviewReport.objects.filter(review=review, reporter=user).exists():
        raise ReviewError('You already reported this review.', code='already_reported')

    report = ReviewReport.objects.create(
        review=review, reporter=user, reason=reason, notes=(notes or '').strip()
    )
    reporters = review.reports.values('reporter').distinct().count()
    if reporters >= REPORT_FLAG_THRESHOLD and review.status == ReviewStatus.PUBLISHED:
        # Abuse foundation: drop it off the public list, staff decides after.
        review.status = ReviewStatus.FLAGGED
        review.save(update_fields=['status', 'updated_at'])
        _refresh_ratings(review.product, review.store)
    return report


@transaction.atomic
def moderate_review(actor, *, review, action, reason=''):
    """Staff hide/restore — audit-logged, seller-free (§6, §4).

    `action` is 'hide' or 'restore'. Hiding demands a reason; every call
    lands an AuditLog row carrying the acting staff member.
    """
    if action not in ('hide', 'restore'):
        raise ReviewError('Unknown moderation action.', code='invalid_action')
    reason = (reason or '').strip()

    if action == 'hide':
        if not reason:
            raise ReviewError('A reason is required to hide a review.', code='reason_required')
        if review.status == ReviewStatus.HIDDEN:
            raise ReviewError('This review is already hidden.', code='already_hidden')
        review.status = ReviewStatus.HIDDEN
        audit_action = 'review_hidden'
    else:
        # A flagged review comes back through restore too: staff looked at
        # the reports and decided it stays (§6 abuse foundation).
        if review.status not in (ReviewStatus.HIDDEN, ReviewStatus.FLAGGED):
            raise ReviewError('Only hidden or flagged reviews can be restored.', code='not_hidden')
        review.status = ReviewStatus.PUBLISHED
        audit_action = 'review_restored'

    review.moderation_reason = reason
    review.moderated_by = actor
    review.moderated_at = timezone.now()
    review.save(update_fields=[
        'status', 'moderation_reason', 'moderated_by', 'moderated_at', 'updated_at',
    ])
    _refresh_ratings(review.product, review.store)
    log_event(
        actor,
        audit_action,
        review,
        detail={
            'product': review.product_id,
            'store': review.store_id,
            'rating': review.rating,
            'reason': reason,
        },
    )
    return review


@transaction.atomic
def resolve_reports(actor, *, review):
    """Staff marks a review's open reports resolved (moderation bookkeeping)."""
    updated = review.reports.filter(resolved=False).update(resolved=True)
    if updated:
        log_event(
            actor,
            'review_reports_resolved',
            review,
            detail={'count': updated, 'store': review.store_id},
        )
    return updated


@transaction.atomic
def reply_to_review(*, seller_user, review, text):
    """The store's official reply — own store only, exactly one per review."""
    if review.store.user_id != seller_user.pk:
        raise ReviewError(
            'You may only reply to reviews of your own store.', code='not_owner'
        )
    if review.status == ReviewStatus.HIDDEN:
        raise ReviewError('This review is not visible.', code='not_visible')
    text = (text or '').strip()
    if not text:
        raise ReviewError('Please write a reply.', code='reply_required')
    if review.seller_reply:
        raise ReviewError('This review already has a reply.', code='already_replied')

    review.seller_reply = text
    review.seller_replied_at = timezone.now()
    review.save(update_fields=['seller_reply', 'seller_replied_at', 'updated_at'])
    notification_services.create_notification(
        recipient=review.user,
        category=NotificationCategory.MESSAGING,
        title=f'{review.store.name} replied to your review',
        message=text[:120],
        action_url=f'/product/{review.product.slug}#reviews',
    )

    return review


def public_list(product):
    """Published reviews only — hidden and flagged never reach strangers."""
    return (
        Review.objects
        .filter(product=product, status=ReviewStatus.PUBLISHED)
        .select_related('user')
        .prefetch_related('images')
    )
