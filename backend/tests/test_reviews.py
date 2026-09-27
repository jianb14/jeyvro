"""Phase 14 gate tests — reviews, ratings & trust (§6, marketplace-community).

Contracts proven here:
1. Verified buyers only: a review is accepted solely from a delivered/
   completed order line — paid-but-undelivered orders and strangers are
   refused server-side (never a client claim).
2. One review per (user, product): service refusal backed by the DB
   unique constraint.
3. Rating aggregates are server-computed: product and store rows are
   rewritten inside every review transaction (create/edit/hide/restore/
   flag) — the frontend only ever renders them.
4. Moderation: hiding demands a reason, lands an AuditLog row carrying
   the acting staff member, and takes the review off the public list;
   restore brings it back with the aggregates.
5. Reports: self/duplicate reports refused; distinct reporters at the
   threshold flag the review for staff (abuse foundation).
6. Seller replies: own store only, exactly one reply per review.
7. The eligibility endpoint is the server verdict the review form reads.
"""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Product, Variant
from apps.orders import services as order_services
from apps.orders.models import OrderStatus, ShipmentStatus
from apps.reviews import services as review_services
from apps.reviews.models import Review, ReviewReport, ReviewStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
LIST = '/api/v1/catalog/products/{slug}/reviews/'
ELIGIBILITY = '/api/v1/catalog/products/{slug}/reviews/eligibility/'
REPORT = '/api/v1/reviews/{id}/report/'
DETAIL = '/api/v1/reviews/{id}/'


def _user(email):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='Buyer',
    )


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _address(user):
    return Address.objects.create(
        user=user,
        full_name='Review Buyer',
        phone='09171234567',
        line1='12 Mabini Street',
        city='Quezon City',
        province='Metro Manila',
        postal_code='1100',
    )


def _catalog():
    """An active store with one published, stocked product."""
    seller = _user('reviewseller@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=seller,
        name='Review Store',
        slug='review-store',
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('0.00'),
    )
    product = Product.objects.create(
        store=store,
        title='Review Product',
        base_price=Decimal('199.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product,
        name='Default',
        price=Decimal('199.00'),
        is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=10)
    return seller, store, product, variant


def _cart_order(buyer, variant):
    address = _address(buyer)
    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=1)
    return order_services.create_order(buyer, address.id, payment_method='cod')


def _place_order(buyer, variant):
    """Places an order that stays awaiting payment (not reviewable)."""
    return _cart_order(buyer, variant)


def _deliver_order(buyer, variant):
    """Runs the real order flow until the parcel is delivered (§10)."""
    order = _cart_order(buyer, variant)

    seller = variant.product.store.user
    seller_order = order.seller_orders.first()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    order_services.mark_seller_order_packed(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order,
        carrier_code='manual',
        package_notes='Review fixture',
        package_weight_grams=300,
        actor=seller,
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.DELIVERED, actor=seller
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED
    return order


def _review_payload(rating=5, body='Solid item, matches the photos.'):
    return {'rating': rating, 'title': 'Worth it', 'body': body}


# --------------------------------------------------------------------------------------
# 14.1 — verified buyer gate, creation, one-per-user, editing rules
# --------------------------------------------------------------------------------------

def test_anonymous_cannot_post_a_review():
    seller, store, product, variant = _catalog()
    response = Client().post(
        LIST.format(slug=product.slug), _review_payload(),
        content_type='application/json',
    )
    assert response.status_code == 403


def test_review_refused_without_a_delivered_purchase():
    """Paid-but-undelivered orders and strangers are not eligible (§6)."""
    seller, store, product, variant = _catalog()

    awaiting = _user('awaitingbuyer@example.com')
    _place_order(awaiting, variant)  # order exists but never delivered
    response = _client_for(awaiting).post(
        LIST.format(slug=product.slug), _review_payload(),
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'not_eligible'

    stranger = _user('stranger@example.com')
    response = _client_for(stranger).post(
        LIST.format(slug=product.slug), _review_payload(),
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.json()['error'] == 'not_eligible'
    assert Review.objects.count() == 0


def test_verified_buyer_creates_review_and_aggregates_update():
    """The delivered buyer's review lands and rewrites both aggregates."""
    seller, store, product, variant = _catalog()
    buyer = _user('verifiedbuyer@example.com')
    order = _deliver_order(buyer, variant)

    response = _client_for(buyer).post(
        LIST.format(slug=product.slug),
        {**_review_payload(rating=4),
         'image_urls': ['https://cdn.example.com/photo1.jpg']},
        content_type='application/json',
    )
    assert response.status_code == 201, response.content
    data = response.json()
    assert data['rating'] == 4
    assert data['verified_purchase'] is True
    assert data['author'] == 'Verifiedbuyer B.'
    assert len(data['images']) == 1
    assert data['seller_reply'] == ''

    review = Review.objects.get(pk=data['id'])
    assert review.order_id == order.pk
    assert review.store_id == store.pk
    assert review.status == ReviewStatus.PUBLISHED

    product.refresh_from_db()
    store.refresh_from_db()
    assert product.rating_average == Decimal('4.00')
    assert product.rating_count == 1
    assert store.rating_average == Decimal('4.00')
    assert store.rating_count == 1


def test_one_review_per_user_product_is_enforced():
    seller, store, product, variant = _catalog()
    buyer = _user('onceonly@example.com')
    _deliver_order(buyer, variant)
    client = _client_for(buyer)

    first = client.post(
        LIST.format(slug=product.slug), _review_payload(rating=5),
        content_type='application/json',
    )
    assert first.status_code == 201

    second = client.post(
        LIST.format(slug=product.slug), _review_payload(rating=1),
        content_type='application/json',
    )
    assert second.status_code == 400
    assert second.json()['error'] == 'already_reviewed'
    assert Review.objects.filter(user=buyer, product=product).count() == 1

    # The DB constraint is the floor (§9), not just the service check.
    constraint_names = [c.name for c in Review._meta.constraints]
    assert 'reviews_one_per_user_product' in constraint_names
    assert 'reviews_rating_bounds' in constraint_names


def test_rating_bounds_and_body_are_validated_server_side():
    seller, store, product, variant = _catalog()
    buyer = _user('boundsbuyer@example.com')
    _deliver_order(buyer, variant)
    client = _client_for(buyer)

    low = client.post(
        LIST.format(slug=product.slug), _review_payload(rating=0),
        content_type='application/json',
    )
    high = client.post(
        LIST.format(slug=product.slug), _review_payload(rating=6),
        content_type='application/json',
    )
    blank = client.post(
        LIST.format(slug=product.slug), _review_payload(body='   '),
        content_type='application/json',
    )
    assert low.status_code == 400
    assert high.status_code == 400
    assert blank.status_code == 400
    assert Review.objects.count() == 0


def test_owner_edit_recomputes_aggregates_and_strangers_are_denied():
    seller, store, product, variant = _catalog()
    owner = _user('ownerbuyer@example.com')
    other = _user('otherbuyer@example.com')
    _deliver_order(owner, variant)
    _deliver_order(other, variant)

    created = _client_for(owner).post(
        LIST.format(slug=product.slug), _review_payload(rating=5),
        content_type='application/json',
    )
    assert created.status_code == 201
    review_id = created.json()['id']

    edited = _client_for(owner).patch(
        DETAIL.format(id=review_id),
        {'rating': 3, 'body': 'Changed my mind after a month of use.'},
        content_type='application/json',
    )
    assert edited.status_code == 200, edited.content
    product.refresh_from_db()
    assert product.rating_average == Decimal('3.00')

    denied = _client_for(other).patch(
        DETAIL.format(id=review_id), {'rating': 1},
        content_type='application/json',
    )
    assert denied.status_code == 400
    assert denied.json()['error'] == 'not_owner'


def test_reviews_of_unpublished_products_are_not_writable():
    seller, store, product, variant = _catalog()
    buyer = _user('draftbuyer@example.com')
    _deliver_order(buyer, variant)
    product.status = Product.Status.DRAFT
    product.save(update_fields=['status'])
    response = _client_for(buyer).post(
        LIST.format(slug=product.slug), _review_payload(),
        content_type='application/json',
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------------------
# Public list, moderation and the abuse foundation (14.3)
# --------------------------------------------------------------------------------------

def test_public_list_serves_only_published_reviews_in_card_shape():
    seller, store, product, variant = _catalog()
    buyer_a = _user('listbuyerone@example.com')
    buyer_b = _user('listbuyertwo@example.com')
    _deliver_order(buyer_a, variant)
    _deliver_order(buyer_b, variant)
    _client_for(buyer_a).post(
        LIST.format(slug=product.slug), _review_payload(rating=5),
        content_type='application/json',
    )
    second = _client_for(buyer_b).post(
        LIST.format(slug=product.slug), _review_payload(rating=3),
        content_type='application/json',
    )

    moderator = _user('reviewmod@example.com')
    moderator_group, _ = Group.objects.get_or_create(name='moderator')
    moderator.groups.add(moderator_group)
    review_services.moderate_review(
        moderator,
        review=Review.objects.get(pk=second.json()['id']),
        action='hide',
        reason='Contains an unrelated promo link.',
    )

    response = Client().get(LIST.format(slug=product.slug))
    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 1
    row = payload['items'][0]
    # ReviewCard contract: author / rating / verified / text / photos.
    assert set(row) >= {'id', 'rating', 'author', 'verified_purchase', 'body', 'images'}
    assert row['verified_purchase'] is True
    assert row['rating'] == 5


def test_moderation_hide_restore_moves_aggregates_and_writes_audit():
    seller, store, product, variant = _catalog()
    buyer = _user('moderatebuyer@example.com')
    _deliver_order(buyer, variant)
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Arrived broken, photos attached.'
    )

    moderator = _user('staffmod@example.com')
    moderator_group, _ = Group.objects.get_or_create(name='moderator')
    moderator.groups.add(moderator_group)

    with pytest.raises(review_services.ReviewError) as no_reason:
        review_services.moderate_review(
            moderator, review=review, action='hide', reason='   '
        )
    assert no_reason.value.code == 'reason_required'

    review_services.moderate_review(
        moderator, review=review, action='hide', reason='Buyer posted seller contacts.'
    )
    review.refresh_from_db()
    product.refresh_from_db()
    store.refresh_from_db()
    assert review.status == ReviewStatus.HIDDEN
    assert review.moderated_by_id == moderator.pk
    assert product.rating_average is None and product.rating_count == 0
    assert store.rating_average is None and store.rating_count == 0
    assert Client().get(LIST.format(slug=product.slug)).json()['count'] == 0
    assert AuditLog.objects.filter(
        action='review_hidden', actor=moderator, object_id=str(review.pk)
    ).exists()

    review_services.moderate_review(moderator, review=review, action='restore')
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == ReviewStatus.PUBLISHED
    assert product.rating_average == Decimal('1.00')
    assert AuditLog.objects.filter(
        action='review_restored', actor=moderator, object_id=str(review.pk)
    ).exists()


def test_reports_flag_a_review_only_after_the_threshold():
    seller, store, product, variant = _catalog()
    author = _user('flaggedauthor@example.com')
    _deliver_order(author, variant)
    review = review_services.create_review(
        author, product=product, rating=5, body='Best purchase ever, buy now!'
    )

    reporters = [_user(f'reporter{i}@example.com') for i in range(3)]
    clients = [_client_for(reporter) for reporter in reporters]

    # Self-report and duplicate report are refused.
    self_report = _client_for(author).post(
        REPORT.format(id=review.pk), {'reason': 'spam'},
        content_type='application/json',
    )
    assert self_report.status_code == 400
    assert self_report.json()['error'] == 'self_report'

    first = clients[0].post(
        REPORT.format(id=review.pk), {'reason': 'spam'},
        content_type='application/json',
    )
    assert first.status_code == 201
    duplicate = clients[0].post(
        REPORT.format(id=review.pk), {'reason': 'abusive'},
        content_type='application/json',
    )
    assert duplicate.status_code == 400
    assert duplicate.json()['error'] == 'already_reported'

    # Two distinct reports leave it published; the third flags it.
    clients[1].post(
        REPORT.format(id=review.pk), {'reason': 'irrelevant'},
        content_type='application/json',
    )
    review.refresh_from_db()
    assert review.status == ReviewStatus.PUBLISHED
    clients[2].post(
        REPORT.format(id=review.pk), {'reason': 'spam', 'notes': 'Repeated text.'},
        content_type='application/json',
    )
    review.refresh_from_db()
    assert review.status == ReviewStatus.FLAGGED
    assert ReviewReport.objects.filter(review=review).count() == 3
    # Flagged drops off the public list and out of the aggregates.
    assert Client().get(LIST.format(slug=product.slug)).json()['count'] == 0
    product.refresh_from_db()
    assert product.rating_count == 0


# --------------------------------------------------------------------------------------
# 14.2/14.3 — seller replies and the server eligibility verdict
# --------------------------------------------------------------------------------------

def test_seller_replies_to_own_store_review_exactly_once():
    seller, store, product, variant = _catalog()
    buyer = _user('replybuyer@example.com')
    _deliver_order(buyer, variant)
    review = review_services.create_review(
        buyer, product=product, rating=4, body='Good value for the price.'
    )

    stranger_seller = _user('strangerseller@example.com')
    stranger_seller.is_seller = True
    stranger_seller.save(update_fields=['is_seller'])
    Store.objects.create(
        user=stranger_seller,
        name='Other Store',
        slug='other-store',
        status=Store.Status.ACTIVE,
    )
    with pytest.raises(review_services.ReviewError) as not_owner:
        review_services.reply_to_review(
            seller_user=stranger_seller, review=review, text='Thanks!'
        )
    assert not_owner.value.code == 'not_owner'

    review_services.reply_to_review(
        seller_user=seller, review=review, text='Salamat sa feedback!'
    )
    review.refresh_from_db()
    assert review.seller_reply == 'Salamat sa feedback!'
    assert review.seller_replied_at is not None

    with pytest.raises(review_services.ReviewError) as again:
        review_services.reply_to_review(
            seller_user=seller, review=review, text='One more time.'
        )
    assert again.value.code == 'already_replied'


def test_eligibility_endpoint_is_the_servers_verdict():
    seller, store, product, variant = _catalog()

    anonymous = Client().get(ELIGIBILITY.format(slug=product.slug))
    assert anonymous.status_code == 403

    buyer = _user('eligibilitybuyer@example.com')
    client = _client_for(buyer)

    not_yet = client.get(ELIGIBILITY.format(slug=product.slug)).json()
    assert not_yet['can_review'] is False
    assert not_yet['reason'] == 'not_eligible'

    order = _deliver_order(buyer, variant)
    eligible = client.get(ELIGIBILITY.format(slug=product.slug)).json()
    assert eligible['can_review'] is True
    assert eligible['order_number'] == order.number
    assert eligible['review_id'] is None

    created = client.post(
        LIST.format(slug=product.slug), _review_payload(),
        content_type='application/json',
    )
    already = client.get(ELIGIBILITY.format(slug=product.slug)).json()
    assert already['can_review'] is False
    assert already['reason'] == 'already_reviewed'
    # The form opens in edit mode straight from the verdict (no guessing).
    assert already['review_id'] == created.json()['id']


# --------------------------------------------------------------------------------------
# Console surface — staff queue + moderation actions, seller replies (§4, §6)
# --------------------------------------------------------------------------------------

MODERATION = '/api/v1/reviews/moderation/'
STORE_REVIEWS = '/api/v1/reviews/store/'
MODERATE = '/api/v1/reviews/{id}/moderate/'
REPLY = '/api/v1/reviews/{id}/reply/'
RESOLVE_REPORTS = '/api/v1/reviews/{id}/reports/resolve/'


def _staff_client(email, group_name):
    """A staff account inside one §4 group."""
    user = _user(email)
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user, _client_for(user)


def test_staff_moderation_queue_is_group_gated():
    seller, store, product, variant = _catalog()
    buyer = _user('queuebuyer@example.com')
    _deliver_order(buyer, variant)
    review_services.create_review(
        buyer, product=product, rating=2, body='Packaging arrived crushed.'
    )

    customer = _user('plaincustomer@example.com')
    assert _client_for(customer).get(MODERATION).status_code == 403

    staff_only = _user('staffnogroup@example.com')
    staff_only.is_staff = True
    staff_only.save(update_fields=['is_staff'])
    assert _client_for(staff_only).get(MODERATION).status_code == 403

    support, support_client = _staff_client('supportqueue@example.com', 'support')
    response = support_client.get(MODERATION)
    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == 1
    row = payload['items'][0]
    assert row['product_title'] == product.title
    assert row['store_name'] == store.name
    assert row['rating'] == 2
    assert row['status'] == ReviewStatus.PUBLISHED
    assert row['report_count'] == 0

    # Support reads along but cannot act (§4 matrix).
    denied = support_client.post(
        MODERATE.format(id=row['id']), {'action': 'hide', 'reason': 'Nope.'},
        content_type='application/json',
    )
    assert denied.status_code == 403


def test_moderator_hides_and_restores_through_the_api():
    seller, store, product, variant = _catalog()
    buyer = _user('apibuyer@example.com')
    _deliver_order(buyer, variant)
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Arrived with a cracked lid.'
    )

    moderator, moderator_client = _staff_client('moderatorapi@example.com', 'moderator')

    missing_reason = moderator_client.post(
        MODERATE.format(id=review.pk), {'action': 'hide', 'reason': '  '},
        content_type='application/json',
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()['error'] == 'reason_required'

    hidden = moderator_client.post(
        MODERATE.format(id=review.pk), {'action': 'hide', 'reason': 'Contains contacts.'},
        content_type='application/json',
    )
    assert hidden.status_code == 200, hidden.content
    assert hidden.json()['status'] == ReviewStatus.HIDDEN
    assert hidden.json()['moderated_by_email'] == 'moderatorapi@example.com'
    product.refresh_from_db()
    assert product.rating_count == 0
    assert AuditLog.objects.filter(
        action='review_hidden', actor=moderator, object_id=str(review.pk)
    ).exists()

    restored = moderator_client.post(
        MODERATE.format(id=review.pk), {'action': 'restore'},
        content_type='application/json',
    )
    assert restored.status_code == 200
    assert restored.json()['status'] == ReviewStatus.PUBLISHED
    product.refresh_from_db()
    assert product.rating_count == 1

    # The queue filters by status server-side.
    assert moderator_client.get(f'{MODERATION}?status=hidden').json()['count'] == 0
    assert moderator_client.get(f'{MODERATION}?status=published').json()['count'] == 1


def test_seller_replies_through_the_api_and_sees_only_own_store():
    seller, store, product, variant = _catalog()
    buyer = _user('storescopedbuyer@example.com')
    _deliver_order(buyer, variant)
    review = review_services.create_review(
        buyer, product=product, rating=5, body='Fast shipping, well packed.'
    )

    # A customer is not a seller — the role gate refuses before the owner check.
    assert _client_for(buyer).post(
        REPLY.format(id=review.pk), {'text': 'Thanks!'},
        content_type='application/json',
    ).status_code == 403

    other_seller = _user('otherseller@example.com')
    other_seller.is_seller = True
    other_seller.save(update_fields=['is_seller'])
    Store.objects.create(
        user=other_seller,
        name='Other Store',
        slug='other-store',
        status=Store.Status.ACTIVE,
    )
    stranger = _client_for(other_seller).post(
        REPLY.format(id=review.pk), {'text': 'Nice.'},
        content_type='application/json',
    )
    assert stranger.status_code == 400
    assert stranger.json()['error'] == 'not_owner'

    replied = _client_for(seller).post(
        REPLY.format(id=review.pk), {'text': 'Salamat! Message us anytime.'},
        content_type='application/json',
    )
    assert replied.status_code == 200, replied.content
    assert replied.json()['seller_reply'] == 'Salamat! Message us anytime.'

    again = _client_for(seller).post(
        REPLY.format(id=review.pk), {'text': 'One more.'},
        content_type='application/json',
    )
    assert again.status_code == 400
    assert again.json()['error'] == 'already_replied'

    mine = _client_for(seller).get(STORE_REVIEWS).json()
    assert mine['count'] == 1
    assert mine['items'][0]['seller_reply'] == 'Salamat! Message us anytime.'
    assert mine['items'][0]['order_number'] == review.order.number

    # The reply shows on the public product list too.
    public = Client().get(LIST.format(slug=product.slug)).json()
    assert public['items'][0]['seller_reply'] == 'Salamat! Message us anytime.'

    # Another seller's console never shows this store's reviews.
    assert _client_for(other_seller).get(STORE_REVIEWS).json()['count'] == 0
    assert Client().get(STORE_REVIEWS).status_code == 403


def test_reported_filter_and_report_resolution_round_trip():
    seller, store, product, variant = _catalog()
    author = _user('resolveauthor@example.com')
    _deliver_order(author, variant)
    review = review_services.create_review(
        author, product=product, rating=4, body='Works fine after a week.'
    )
    for index in range(3):
        review_services.report_review(
            _user(f'resolvereporter{index}@example.com'), review, reason='spam'
        )
    review.refresh_from_db()
    assert review.status == ReviewStatus.FLAGGED

    moderator, moderator_client = _staff_client('moderatorresolve@example.com', 'moderator')
    flagged = moderator_client.get(f'{MODERATION}?reported=1').json()
    assert flagged['count'] == 1
    assert flagged['items'][0]['status'] == ReviewStatus.FLAGGED
    assert flagged['items'][0]['open_report_count'] == 3

    resolved = moderator_client.post(
        RESOLVE_REPORTS.format(id=review.pk), {},
        content_type='application/json',
    )
    assert resolved.status_code == 200
    assert resolved.json()['resolved'] == 3
    assert ReviewReport.objects.filter(review=review, resolved=True).count() == 3
    assert AuditLog.objects.filter(
        action='review_reports_resolved', actor=moderator, object_id=str(review.pk)
    ).exists()

    # Still flagged (staff has not decided yet) — so it stays in the queue…
    assert moderator_client.get(f'{MODERATION}?reported=1').json()['count'] == 1
    # …until restore clears it back to published, reports already closed.
    restored = moderator_client.post(
        MODERATE.format(id=review.pk), {'action': 'restore'},
        content_type='application/json',
    )
    assert restored.status_code == 200, restored.content
    assert restored.json()['status'] == ReviewStatus.PUBLISHED
    assert moderator_client.get(f'{MODERATION}?reported=1').json()['count'] == 0
    product.refresh_from_db()
    assert product.rating_count == 1


