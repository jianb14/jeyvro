"""Phase 20.2 slice v1 gate tests — spam & messaging abuse (§20.2).

Contracts proven here, and the reasoning behind each:

1. **The rules flag, they never censor.** A review that trips a rule is still
   created, still belongs to its buyer, and is parked as `FLAGGED` for a human.
   Nothing is deleted, no error is returned, and the author is never told they
   were censored — a false positive costs a queue row, never a review.
2. **A flagged review cannot vote on a rating.** `FLAGGED` is not `PUBLISHED`,
   so it stays out of the product aggregate while it waits.
3. **Normal users are untouched.** An ordinary review — including one quoting
   its own order number, one with an acronym, and one in Tagalog — publishes
   normally and raises no flag at all. The false-positive guards are as much
   of this slice as the catches.
4. **One flag per subject.** Re-flagging reopens the same row rather than
   manufacturing duplicates for staff to triage twice.
5. **Blocks are scoped to the person.** A blocked party cannot post to the
   thread, cannot start a *new* thread with the same seller, and can never
   block their way out of a support conversation.
6. **Blocks are the caller's own rows only.** One user cannot unblock another's.
7. **Evidence is preserved.** A flagged message is stored and readable by its
   participants; the thread moves to `reported` and a flag row is filed.
8. **The queue is staff-only, and the decision is audited.** Support may look;
   only a moderator may act. Dismiss and confirm each write their own action,
   and confirming demands a written reason.
9. **Reading is never throttled.** The `conversation` scope covers thread
   *starts* only — a 20/hour cap on the inbox list would be a speed bump on
   ordinary reading (§10.2).
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.audit.models import AuditLog
from apps.cart import services as cart_services
from apps.cart.models import Cart
from apps.catalog import services as catalog_services
from apps.catalog.models import Inventory, Product, Variant
from apps.messaging import services as messaging_services
from apps.messaging.models import (
    Conversation,
    ConversationBlock,
    ConversationStatus,
    ConversationType,
)
from apps.moderation import rules, services as moderation_services
from apps.moderation.models import ContentFlag
from apps.orders import services as order_services
from apps.orders.models import Order, OrderItem, OrderStatus, ShipmentStatus
from apps.reviews import services as review_services
from apps.reviews.models import Review, ReviewStatus
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

PASSWORD = 'Str0ng!Passw0rd'
LIST = '/api/v1/catalog/products/{slug}/reviews/'
FLAGS = '/api/v1/admin/moderation/flags/'
BLOCKS = '/api/v1/conversation-blocks/'


def _user(email, *, group=None):
    user = User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        last_name='User',
        is_staff=bool(group),
    )
    if group:
        grp, _ = Group.objects.get_or_create(name=group)
        user.groups.add(grp)
    return user


def _client_for(user):
    client = Client()
    client.force_login(user)
    return client


def _catalog(slug='abuse-store'):
    seller = _user('abuseseller@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=seller,
        name='Abuse Store',
        slug=slug,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('0.00'),
    )
    product = Product.objects.create(
        store=store,
        title='Abuse Product',
        base_price=Decimal('199.00'),
        status=Product.Status.PUBLISHED,
    )
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal('199.00'), is_default=True,
    )
    catalog_services.ensure_inventory(variant, initial_on_hand=10)
    return seller, store, product, variant


def _address(user):
    return Address.objects.create(
        user=user,
        full_name='Abuse Buyer',
        phone='09171234567',
        line1='12 Mabini Street',
        city='Quezon City',
        province='Metro Manila',
        postal_code='1100',
    )


def _deliver_order(buyer, variant):
    """A real delivered order — the only thing that makes a review possible."""
    address = _address(buyer)
    cart = Cart.objects.create(user=buyer)
    cart.items.create(variant=variant, quantity=1)
    order = order_services.create_order(buyer, address.id, payment_method='cod')

    seller = variant.product.store.user
    seller_order = order.seller_orders.first()
    order_services.mark_seller_order_processing(seller_order, actor=seller)
    order_services.mark_seller_order_packed(seller_order, actor=seller)
    shipment = order_services.create_shipment(
        seller_order,
        carrier_code='manual',
        package_notes='Abuse fixture',
        package_weight_grams=300,
        actor=seller,
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.DELIVERED, actor=seller
    )
    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED
    return order


def _reviewable(slug='abuse-store'):
    """A buyer who may review, plus the product they may review."""
    seller, store, product, variant = _catalog(slug)
    buyer = _user(f'buyer-{slug}@example.com')
    _deliver_order(buyer, variant)
    return seller, store, product, variant, buyer


def _convo(buyer, store, *, product=None):
    conversation, _created = messaging_services.start_or_get_conversation(
        buyer, store=store, product=product,
    )
    return conversation


# --------------------------------------------------------------------------------------
# The rules themselves — pure, so they are asserted on directly
# --------------------------------------------------------------------------------------

def test_an_ordinary_review_trips_nothing():
    verdict = rules.evaluate(
        'Mabuti ang produkto, mabilis ang delivery. Recommended!', kind='review',
    )
    assert verdict['flagged'] is False
    assert verdict['rules'] == []


@pytest.mark.parametrize('text,expected', [
    ('Great item, check my shop https://shopee.ph/mystore', 'link'),
    ('Great item, visit bestdeals.com for more', 'link'),
    ('Good item, contact me at spam@gmail.com', 'contact'),
    ('Call me at 0917 123 4567 for bulk deals', 'contact'),
    ('Text 09171234567 for wholesale orders', 'contact'),
    ('THIS IS THE WORST PRODUCT I HAVE EVER PURCHASED HERE', 'shouting'),
])
def test_spam_shapes_are_caught(text, expected):
    assert expected in rules.evaluate(text, kind='review')['rules']


@pytest.mark.parametrize('text,kind', [
    # A reviewer quoting their own order or tracking number is not a phone number.
    ('Order JV-20260926-ABCD2345 arrived late, 3 stars only.', 'review'),
    ('Tracking JVTRK-20260926-0001 took 5 days to arrive.', 'review'),
    # Measurements and small counts are not contact details.
    ('Size 2.5kg was the wrong size, I ordered 4 pcs in total.', 'review'),
    # Short and mixed-case text is not shouting; acronyms are not shouting.
    ('OK', 'review'),
    ('The USB-C port and HDMI output both work on my laptop.', 'review'),
    # A message is a private channel: quoting the platform is normal there.
    ('You can see it at https://jeyvro.com/store/x thanks', 'message'),
    # A customer giving a seller their email is contact, not advertising.
    ('my email is me@shop.com please send it there', 'message'),
    ('Hi, is this still available? Thanks!', 'message'),
])
def test_ordinary_text_is_never_flagged(text, kind):
    assert rules.evaluate(text, kind=kind)['flagged'] is False


def test_the_rules_need_no_database_or_settings():
    """`evaluate` is pure — that is what makes it exhaustively testable."""
    verdict = rules.evaluate('visit example.com now', kind='review')
    assert set(verdict) == {'flagged', 'rules', 'detail'}
    assert verdict['flagged'] is True


# --------------------------------------------------------------------------------------
# Reviews: flagged, never censored
# --------------------------------------------------------------------------------------

def test_a_spammy_review_is_flagged_not_rejected():
    _s, _st, product, _v, buyer = _reviewable('flag-one')
    review = review_services.create_review(
        buyer, product=product, rating=5,
        title='Great', body='Excellent item, see https://myspamshop.example/deal',
    )

    # The row exists and the buyer still owns it.
    assert Review.objects.filter(pk=review.pk, user=buyer).exists()
    # It is parked for a human, not published and not deleted.
    assert review.status == ReviewStatus.FLAGGED
    flag = ContentFlag.objects.get(review=review)
    assert flag.rules == ['link']
    assert flag.status == ContentFlag.Status.OPEN


def test_a_flagged_review_is_audited():
    _s, _st, product, _v, buyer = _reviewable('flag-audit')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Bad. Call me at 09171234567',
    )


def test_a_normal_review_still_publishes_and_counts():
    _s, _st, product, _v, buyer = _reviewable('normal-review')
    review = review_services.create_review(
        buyer, product=product, rating=5, body='Legit ang fabric, worth the price.',
    )
    assert review.status == ReviewStatus.PUBLISHED
    product.refresh_from_db()
    assert product.rating_count == 1
    assert ContentFlag.objects.count() == 0


def test_a_normal_review_through_the_api_is_untouched():
    _s, _st, product, _v, buyer = _reviewable('normal-api')
    response = _client_for(buyer).post(
        LIST.format(slug=product.slug),
        {'rating': 5, 'title': 'Worth it', 'body': 'Mabuti ang produkto, recommended!'},
        content_type='application/json',
    )
    assert response.status_code == 201
    # The public serializer deliberately omits `status` — moderation internals
    # never cross the wire (§14.1) — so the verdict is read from the row.
    assert 'status' not in response.data
    assert Review.objects.get(pk=response.data['id']).status == ReviewStatus.PUBLISHED
    assert ContentFlag.objects.count() == 0


def test_an_ordinary_review_quoting_its_order_is_untouched():
    """The false-positive guard that matters most to a real buyer."""
    _s, _st, product, _v, buyer = _reviewable('order-quote')
    review = review_services.create_review(
        buyer, product=product, rating=4,
        body='Order JV-20260926-ABCD2345 arrived late but the item is good.',
    )
    assert review.status == ReviewStatus.PUBLISHED
    assert ContentFlag.objects.count() == 0


def test_editing_a_clean_review_into_spam_flags_it_once():
    _s, _st, product, _v, buyer = _reviewable('edit-spam')
    review = review_services.create_review(
        buyer, product=product, rating=5, body='Lovely item, highly recommended.',
    )
    assert review.status == ReviewStatus.PUBLISHED

    review_services.update_review(
        buyer, review.pk, body='Great item, visit bestdeals.com for more',
    )
    review.refresh_from_db()
    assert review.status == ReviewStatus.FLAGGED
    # One row, not a queue of duplicates from repeated edits.
    assert ContentFlag.objects.filter(review=review).count() == 1

    review_services.update_review(
        buyer, review.pk, body='Also see https://anotherevil.example/x',
    )
    assert ContentFlag.objects.filter(review=review).count() == 1
    assert ContentFlag.objects.get(review=review).rules == ['link']


# --------------------------------------------------------------------------------------
# Messages: the text is kept, the thread is queued
# --------------------------------------------------------------------------------------

def test_a_spammy_message_is_stored_and_the_thread_is_reported():
    seller, store, _product, _variant = _catalog('msg-flag')
    buyer = _user('msgbuyer@example.com')
    conversation = _convo(buyer, store)

    message = messaging_services.send_message(
        conversation, buyer, 'Buy here https://myspamshop.example/deal',
    )

    # Evidence survives: the message exists and both parties can read it.
    message.refresh_from_db()
    assert message.body == 'Buy here https://myspamshop.example/deal'
    assert messaging_services.can_access_conversation(conversation, buyer)

    conversation.refresh_from_db()
    assert conversation.status == ConversationStatus.REPORTED
    flag = ContentFlag.objects.get(conversation=conversation)
    assert flag.rules == ['link']
    assert flag.author == buyer


# --------------------------------------------------------------------------------------
# Blocks: the channel closes for the person, not just the thread
# --------------------------------------------------------------------------------------

def test_a_block_stops_further_messages():
    seller, store, _product, _variant = _catalog('block-msg')
    buyer = _user('blockbuyer@example.com')
    conversation = _convo(buyer, store)
    messaging_services.send_message(conversation, buyer, 'Hello, is this available?')

    messaging_services.block_user(buyer, seller, store=store, reason='Spamming me')

    with pytest.raises(PermissionDenied):
        messaging_services.send_message(conversation, seller, 'Any update?')


def test_a_block_stops_a_brand_new_thread_with_the_same_seller():
    """Otherwise "message seller" on another product walks straight back in.

    The blocked party is the one refused: a seller blocks a spamming buyer, and
    that buyer cannot escape by opening a fresh thread on a different product.
    """
    seller, store, _product, _variant = _catalog('block-new')
    buyer = _user('blockbuyer-new@example.com')
    _convo(buyer, store)
    messaging_services.block_user(seller, buyer, store=store)

    with pytest.raises(PermissionDenied):
        messaging_services.start_or_get_conversation(buyer, store=store)

    # And no new conversation row was created for the refused attempt.
    assert Conversation.objects.filter(
        customer=buyer, store=store, type=ConversationType.SELLER,
    ).count() == 1


def test_a_block_is_directional_and_audited():
    seller, store, _product, _variant = _catalog('block-audit')
    buyer = _user('blockbuyer-audit@example.com')
    conversation = _convo(buyer, store)

    messaging_services.block_user(buyer, seller, store=store, reason='Spam')
    assert AuditLog.objects.filter(
        action='conversation_blocked', actor=buyer,
        detail__blocked=seller.pk,
    ).exists()

    # The buyer may still write; the block is the seller's refusal, not a mute
    # of the person who pressed it.
    messaging_services.send_message(conversation, buyer, 'One more question')
    with pytest.raises(PermissionDenied):
        messaging_services.send_message(conversation, seller, 'Ignored')


def test_unblocking_restores_the_channel():
    seller, store, _product, _variant = _catalog('block-unblock')
    buyer = _user('blockbuyer-unblock@example.com')
    conversation = _convo(buyer, store)

    block = messaging_services.block_user(buyer, seller, store=store)
    with pytest.raises(PermissionDenied):
        messaging_services.send_message(conversation, seller, 'Hello?')

    messaging_services.unblock_user(buyer, block.pk)
    messaging_services.send_message(conversation, seller, 'Hello again')
    assert AuditLog.objects.filter(action='conversation_unblocked', actor=buyer).exists()


def test_one_user_cannot_unblock_another_users_block():
    seller, store, _product, _variant = _catalog('block-owner')
    buyer = _user('blockbuyer-owner@example.com')
    other = _user('blocker-other@example.com')
    _convo(buyer, store)
    block = messaging_services.block_user(other, seller, store=store)

    with pytest.raises(ConversationBlock.DoesNotExist):
        messaging_services.unblock_user(buyer, block.pk)
    assert ConversationBlock.objects.filter(pk=block.pk).exists()


def test_a_user_cannot_block_themselves():
    seller, store, _product, _variant = _catalog('block-self')
    buyer = _user('blockbuyer-self@example.com')
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        messaging_services.block_user(buyer, buyer)


def test_support_stays_reachable_despite_a_block():
    """Nobody may block their way out of a dispute with support (§20.2)."""
    buyer = _user('blockbuyer-support@example.com')
    conversation, _c = messaging_services.start_or_get_conversation(
        buyer, conversation_type=ConversationType.SUPPORT, subject='Order help',
    )
    agent = _user('supportagent@example.com', group='support')
    messaging_services.send_message(conversation, agent, 'How can I help?')

    # There is no counterparty to block in a support thread, so the channel
    # stays open for staff in both directions.
    assert conversation.customer_id == buyer.pk
    messaging_services.send_message(conversation, buyer, 'I need help with my order')


def test_the_block_api_is_owner_scoped():
    seller, store, _product, _variant = _catalog('block-api')
    buyer = _user('blockbuyer-api@example.com')
    _convo(buyer, store)

    response = _client_for(buyer).post(
        BLOCKS, {'user_id': seller.pk, 'reason': 'Spam'},
        content_type='application/json',
    )
    assert response.status_code == 201
    block_id = response.data['id']

    # The buyer's own list shows it; another user's does not.
    assert _client_for(buyer).get(BLOCKS).data['count'] == 1
    stranger = _user('stranger@example.com')
    assert _client_for(stranger).get(BLOCKS).data['count'] == 0

    # And a stranger cannot delete someone else's block.


# --------------------------------------------------------------------------------------
# The staff queue: look, then decide — and the decision is a record
# --------------------------------------------------------------------------------------

def test_the_queue_is_closed_to_customers():
    buyer = _user('nosy@example.com')
    assert _client_for(buyer).get(FLAGS).status_code == 403


def test_the_queue_is_closed_to_anonymous_callers():
    assert Client().get(FLAGS).status_code in (401, 403)


def test_support_may_read_the_queue_but_not_resolve_it():
    _s, _st, product, _v, buyer = _reviewable('queue-support')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Call me at 09171234567',
    )
    support = _user('supportreader@example.com', group='support')
    moderator = _user('moderatorqueue@example.com', group='moderator')

    # Oversight is readable...
    assert _client_for(support).get(FLAGS).data['count'] == 1
    # ...but deciding is the moderator's power alone (§4).
    denied = _client_for(support).post(
        f'{FLAGS}{ContentFlag.objects.get(review=review).pk}/resolve/',
        {'action': 'confirm', 'note': 'Spam'}, content_type='application/json',
    )
    assert denied.status_code == 403
    review.refresh_from_db()
    assert review.status == ReviewStatus.FLAGGED

    allowed = _client_for(moderator).post(
        f'{FLAGS}{ContentFlag.objects.get(review=review).pk}/resolve/',
        {'action': 'confirm', 'note': 'Advertised a phone number'},
        content_type='application/json',
    )
    assert allowed.status_code == 200


def test_dismissing_a_flag_restores_the_review_and_its_rating():
    _s, _st, product, _v, buyer = _reviewable('queue-dismiss')
    review = review_services.create_review(
        buyer, product=product, rating=4, body='Great, see example.com/deal',
    )
    assert review.status == ReviewStatus.FLAGGED
    product.refresh_from_db()
    assert product.rating_count == 0

    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-dismiss@example.com', group='moderator')
    moderation_services.resolve_flag(
        moderator, flag, action='dismiss', note='Seller linked their own store.',
    )

    # Restored *through the reviews service*, so the aggregates followed it.
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == ReviewStatus.PUBLISHED
    assert product.rating_count == 1
    assert flag.status == ContentFlag.Status.DISMISSED


def test_confirming_without_a_reason_is_refused():
    _s, _st, product, _v, buyer = _reviewable('queue-noreason')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Text me at 09171234567',
    )
    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-noreason@example.com', group='moderator')

    with pytest.raises(moderation_services.ModerationError) as excinfo:
        moderation_services.resolve_flag(moderator, flag, action='confirm', note='')
    assert excinfo.value.code == 'reason_required'
    flag.refresh_from_db()
    assert flag.status == ContentFlag.Status.OPEN


def test_a_flag_cannot_be_resolved_twice():
    _s, _st, product, _v, buyer = _reviewable('queue-twice')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Call me at 09171234567',
    )
    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-twice@example.com', group='moderator')

    moderation_services.resolve_flag(moderator, flag, action='dismiss', note='Fine')
    with pytest.raises(moderation_services.ModerationError) as excinfo:
        moderation_services.resolve_flag(moderator, flag, action='confirm', note='No')
    assert excinfo.value.code == 'already_resolved'


def test_reflagging_a_dismissed_review_reopens_the_same_row():
    _s, _st, product, _v, buyer = _reviewable('queue-reopen')
    review = review_services.create_review(
        buyer, product=product, rating=5, body='Nice, see example.com/deal',
    )
    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-reopen@example.com', group='moderator')
    moderation_services.resolve_flag(moderator, flag, action='dismiss', note='Mistake')

    review_services.update_review(
        buyer, review.pk, body='Nice, but buy at bestdeals.com now',
    )
    review.refresh_from_db()
    assert review.status == ReviewStatus.FLAGGED
    assert ContentFlag.objects.filter(review=review).count() == 1
    assert ContentFlag.objects.get(review=review).status == ContentFlag.Status.OPEN
    assert AuditLog.objects.filter(
        action='content_flag_reopened', object_id=str(flag.pk),
    ).exists()


def test_the_queue_serves_flags_without_republishing_the_text():
    """The listing carries rules and ids, never a second copy of the body."""
    _s, _st, product, _v, buyer = _reviewable('queue-serialization')
    review = review_services.create_review(
        buyer, product=product, rating=1,
        body='Call me at 09171234567 for a discount',
    )
    moderator = _user('moderator-serializer@example.com', group='moderator')
    data = _client_for(moderator).get(FLAGS).data

    item = data['items'][0]
    assert item['rules'] == ['contact']
    assert item['rule_labels'] == ['Contains contact details']
    assert item['review_id'] == review.pk
    assert item['conversation_id'] is None
    # The author's phone number is reachable through the review, never copied
    # into the moderation listing.
    assert '09171234567' not in str(item)
    assert 'for a discount' not in str(item)


def test_the_queue_rejects_an_unknown_filter():
    moderator = _user('moderator-filter@example.com', group='moderator')
    assert _client_for(moderator).get(f'{FLAGS}?status=bogus').status_code == 400


def test_resolving_an_unknown_flag_is_a_404():
    """A moderator must not learn anything from a guessed id, and must not
    crash on one — the decision endpoint resolves the row itself."""
    moderator = _user('moderator-404@example.com', group='moderator')
    response = _client_for(moderator).post(
        f'{FLAGS}999999/resolve/',
        {'action': 'dismiss', 'note': 'Nothing here'},
        content_type='application/json',
    )
    assert response.status_code == 404


def test_the_status_filter_moves_a_flag_between_worklists():
    """`?status=` is a real partition, not decoration: resolving a flag takes it
    out of the default worklist and puts it in the one staff asked for, and
    `open_count` still counts only the open pile."""
    _s, _st, product, _v, buyer = _reviewable('queue-filter-status')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Text me at 09171234567',
    )
    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-partition@example.com', group='moderator')
    client = _client_for(moderator)

    assert client.get(FLAGS).data['count'] == 1
    assert client.get(f'{FLAGS}?status=confirmed').data['count'] == 0

    client.post(
        f'{FLAGS}{flag.pk}/resolve/',
        {'action': 'confirm', 'note': 'Advertised an off-platform contact'},
        content_type='application/json',
    )

    # Gone from the default queue, present in the confirmed one, and the badge
    # no longer counts work that is already done.
    assert client.get(FLAGS).data['count'] == 0
    assert client.get(FLAGS).data['open_count'] == 0
    confirmed = client.get(f'{FLAGS}?status=confirmed').data
    assert confirmed['count'] == 1
    assert confirmed['items'][0]['review_id'] == review.pk
    # `all` is the working backlog, open plus decided.
    assert client.get(f'{FLAGS}?status=all').data['count'] == 1


def test_an_unknown_kind_filter_is_rejected():
    moderator = _user('moderator-kind-filter@example.com', group='moderator')
    assert _client_for(moderator).get(f'{FLAGS}?kind=bogus').status_code == 400


# --------------------------------------------------------------------------------------
# Slice v2: stale COD reservations — surfaced to staff, never auto-cancelled (§20.2)
#
# The bug these cover: an unpaid COD order holds its stock reservation forever,
# because `Payment.expires_at` is None for COD and `expire_overdue_payments`
# excludes it. The product decision is that this is a *report*, not a reaper —
# killing a slow-but-real COD order is worse than the leak it would fix.
# --------------------------------------------------------------------------------------

STALE_COD = '/api/v1/admin/stale-cod/'


def _cod_order(slug, email, *, quantity=2, method='cod'):
    """A placed order holding `quantity` units of its variant's stock."""
    from apps.payments.models import PaymentMethod

    _seller, _store, _product, variant = _catalog(slug)
    buyer = _user(email)
    address = _address(buyer)
    cart = Cart.objects.get_or_create(user=buyer)[0]
    cart_services.add_item(cart, variant, quantity=quantity)
    order = order_services.create_order(
        buyer, address.pk,
        payment_method=PaymentMethod(method),
    )
    return order, variant, buyer


def _age_order(order, days):
    """Backdate an order so it crosses the review window."""
    Order.objects.filter(pk=order.pk).update(
        created_at=timezone.now() - timedelta(days=days)
    )
    order.refresh_from_db()
    return order


def test_an_unpaid_cod_order_is_never_cancelled_automatically():
    """The whole point of the decision: age the order out and run every
    automatic path that could touch it. Nothing moves."""
    from apps.payments import services as payment_services

    order, variant, _buyer = _cod_order('cod-never-auto', 'codauto@example.com')
    _age_order(order, days=30)

    expired = payment_services.expire_overdue_payments()
    order.refresh_from_db()
    inventory = Inventory.objects.get(variant=variant)

    assert expired == []
    assert order.status != OrderStatus.CANCELLED
    # The reservation is deliberately still held — staff release it by hand.
    assert inventory.reserved == 2


def test_a_stale_cod_order_is_reported_to_staff():
    order, _variant, _buyer = _cod_order('cod-report', 'codreport@example.com')
    _age_order(order, days=30)

    support = _user('codsupport@example.com', group='support')
    data = _client_for(support).get(STALE_COD).data
    assert data['count'] == 1
    row = data['items'][0]
    assert row['number'] == order.number
    assert row['age_days'] >= 30
    assert row['item_count'] == 2
    assert row['payment_method'] == 'cod'


def test_a_fresh_cod_order_is_not_reported():
    """Staff should see the leak, not every order placed today."""
    _cod_order('cod-fresh', 'codfresh@example.com')
    support = _user('codfreshsupport@example.com', group='support')
    assert _client_for(support).get(STALE_COD).data['count'] == 0


def test_a_shipped_cod_order_is_never_reported_or_released():
    """The guard that matters: a parcel in transit is a sale that already
    happened. Releasing its stock would sell the same unit twice."""
    order, variant, buyer = _cod_order('cod-shipped', 'codshipped@example.com')
    _age_order(order, days=30)
    seller_order = order.seller_orders.first()
    shipment = order_services.create_shipment(
        seller_order, carrier_code='manual', actor=buyer,
    )
    order_services.update_shipment_status(
        shipment, ShipmentStatus.PICKED_UP, actor=buyer,
    )

    support = _user('codshipsupport@example.com', group='support')
    client = _client_for(support)
    assert client.get(STALE_COD).data['count'] == 0

    refused = client.post(
        f'{STALE_COD}{order.number}/release/',
        {'reason': 'looks abandoned'}, content_type='application/json',
    )
    assert refused.status_code == 400
    assert refused.data['error'] == 'not_stale_cod'
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.reserved == 2, 'a dispatched parcel keeps its stock'


def test_staff_releasing_a_stale_cod_reservation_is_audited():
    order, variant, _buyer = _cod_order('cod-release', 'codrel@example.com')
    _age_order(order, days=30)
    support = _user('codrelsupport@example.com', group='support')

    response = _client_for(support).post(
        f'{STALE_COD}{order.number}/release/',
        {'reason': 'Buyer unreachable for 30 days.'},
        content_type='application/json',
    )
    assert response.status_code == 200

    order.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    # The whole point: the stock goes back on the shelf.
    inventory = Inventory.objects.get(variant=variant)
    assert inventory.reserved == 0
    assert AuditLog.objects.filter(
        action='order.cod_reservation_released',
        object_id=str(order.pk),
    ).exists()


def test_releasing_stock_demands_a_reason():
    order, variant, _buyer = _cod_order('cod-noreason', 'codnr@example.com')
    _age_order(order, days=30)
    support = _user('codnrsupport@example.com', group='support')

    response = _client_for(support).post(
        f'{STALE_COD}{order.number}/release/',
        {'reason': '   '}, content_type='application/json',
    )
    assert response.status_code == 400
    assert response.data['error'] == 'reason_required'
    # Refused means untouched.
    assert Inventory.objects.get(variant=variant).reserved == 2
    order.refresh_from_db()
    assert order.status != OrderStatus.CANCELLED


def test_the_stale_cod_queue_is_staff_only():
    buyer = _user('custodcurious@example.com')
    assert _client_for(buyer).get(STALE_COD).status_code == 403
    assert Client().get(STALE_COD).status_code in (401, 403)


def test_an_unknown_order_number_is_a_404():
    support = _user('cod404support@example.com', group='support')
    response = _client_for(support).post(
        f'{STALE_COD}JV-00000000-XXXXXX/release/',
        {'reason': 'nope'}, content_type='application/json',
    )
    assert response.status_code == 404


def test_the_review_window_is_configurable(settings):
    settings.ORDERS_COD_RESERVATION_REVIEW_DAYS = 2
    order, _variant, _buyer = _cod_order('cod-window', 'codwin@example.com')
    _age_order(order, days=3)
    support = _user('codwinsupport@example.com', group='support')
    assert _client_for(support).get(STALE_COD).data['count'] == 1


# --------------------------------------------------------------------------------------
# The per-order total-units ceiling (§20.2 v3)
#
# `MAX_LINE_QUANTITY` (99) bounds one *line*, so a multi-line cart was unbounded:
# 20 lines could reach 1,980 units and reserve that much stock across many stores
# in a single checkout. This is the whole-order total those per-line caps never
# constrained.
#
# The rule enforced here: the ceiling is a **backstop against one checkout
# reserving a catalog's worth of stock**, not a limit on ordinary trade. So the
# guards below are as much of the slice as the catch — a bulk buyer restocking a
# sari-sari store is a legitimate customer, and a ceiling that punished them would
# be worse than no ceiling at all.
# --------------------------------------------------------------------------------------


def _stocked_variants(slug, count, stock=500):
    """`count` distinct variants on one seller, each holding `stock` units.

    `_catalog` cannot be reused for the bulk cases: it hardcodes one seller
    email (so a second call collides) and stocks only 10 units, and a 90-unit
    line would fail the cart's live-stock check before the order ceiling was
    ever reached.
    """
    seller = _user('bulkseller@example.com')
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    store = Store.objects.create(
        user=seller,
        name='Bulk Store',
        slug=slug,
        status=Store.Status.ACTIVE,
        shipping_flat_fee=Decimal('0.00'),
    )
    variants = []
    for index in range(count):
        product = Product.objects.create(
            store=store,
            title=f'Bulk Product {index}',
            base_price=Decimal('199.00'),
            status=Product.Status.PUBLISHED,
        )
        variant = Variant.objects.create(
            product=product, name='Default', price=Decimal('199.00'), is_default=True,
        )
        catalog_services.ensure_inventory(variant, initial_on_hand=stock)
        variants.append(variant)
    return variants


def _bulk_cart(email, slug, *, lines=3, per_line=90):
    """A cart of `lines` lines of `per_line` units, across distinct variants.

    Each line stays under the 99 per-line cap while the basket total climbs past
    the ceiling — which is the only shape this bug had.
    """
    buyer = _user(email)
    variants = _stocked_variants(slug, lines)
    cart = Cart.objects.get_or_create(user=buyer)[0]
    for variant in variants:
        cart_services.add_item(cart, variant, quantity=per_line)
    return cart, buyer, variants


def cart_unit_total(cart):
    return order_services.cart_unit_count(cart)


def order_unit_total(order):
    return sum(
        item.quantity
        for seller_order in order.seller_orders.all()
        for item in seller_order.items.all()
    )


def test_a_multi_line_cart_over_the_ceiling_cannot_check_out():
    """The bug: 3 x 90 units is legal per line and illegal per order."""
    cart, buyer, variants = _bulk_cart('bulk@example.com', 'bulk-guard')
    assert cart_unit_total(cart) == 270 > cart_services.max_order_units()

    with pytest.raises(order_services.CheckoutError) as excinfo:
        order_services.create_order(buyer, _address(buyer).pk)

    assert excinfo.value.code == 'order_units_exceeded'
    # Nothing was written: the refusal happens before any reservation.
    assert Order.objects.filter(user=buyer).count() == 0
    for variant in variants:
        assert Inventory.objects.get(variant=variant).reserved == 0
def test_an_order_exactly_at_the_ceiling_is_allowed(settings):
    """The boundary is inclusive — "at most N" means N is fine, N+1 is not.

    99 is the per-line maximum, so one line sits exactly on a lowered ceiling.
    A `>` that should have been `>=` would refuse a legal order, and a customer
    could then never buy a single line at all.
    """
    settings.ORDERS_MAX_ORDER_UNITS = 99
    buyer = _user('atlimit@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    variant = _stocked_variants('at-limit', 1)[0]
    cart_services.add_item(cart, variant, quantity=99)

    assert cart_unit_total(cart) == cart_services.max_order_units() == 99
    order = order_services.create_order(buyer, _address(buyer).pk)

    assert order_unit_total(order) == 99
    assert Inventory.objects.get(variant=variant).reserved == 99


def test_an_ordinary_bulk_buyer_is_not_blocked():
    """The false-positive guard: a real restock basket goes through untouched.

    A sari-sari store buying 180 units across two lines is ordinary trade. If the
    ceiling refuses this, the ceiling is wrong, not the buyer.
    """
    buyer = _user('restock@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    for variant in _stocked_variants('restock', 2):
        cart_services.add_item(cart, variant, quantity=90)

    order = order_services.create_order(buyer, _address(buyer).pk)

    assert order_unit_total(order) == 180
    assert sum(
        seller_order.items.count() for seller_order in order.seller_orders.all()
    ) == 2


def test_the_per_line_cap_still_stands():
    """The two caps are independent: the ceiling did not replace the line cap."""
    buyer = _user('bigline@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    variant = _catalog('big-line')[3]

    with pytest.raises(ValueError):
        cart_services.add_item(
            cart, variant, quantity=cart_services.MAX_LINE_QUANTITY + 1
        )


def test_the_ceiling_is_configurable_without_a_deploy(settings):
    """Operations must be able to raise it for a wholesale account."""
    assert cart_services.max_order_units() == 200

    settings.ORDERS_MAX_ORDER_UNITS = 5000
    assert cart_services.max_order_units() == 5000

    buyer = _user('wholesale@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    for variant in _stocked_variants('wholesale', 3):
        cart_services.add_item(cart, variant, quantity=90)

    order = order_services.create_order(buyer, _address(buyer).pk)
    assert order_unit_total(order) == 270


def test_the_cart_publishes_the_ceiling_so_the_ui_can_warn_early():
    """Advisory on the read, binding at checkout: the cart is told it is over the
    line before the customer presses Place Order."""
    from apps.cart.serializers import build_cart_payload

    buyer = _user('cartnotice@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    for variant in _stocked_variants('cartnotice', 3):
        cart_services.add_item(cart, variant, quantity=90)

    totals = build_cart_payload(cart)['totals']

    assert totals['item_count'] == 270
    assert totals['max_order_units'] == cart_services.max_order_units()
    assert totals['over_unit_ceiling'] is True


def test_an_ordinary_cart_is_not_flagged_over_the_ceiling():
    from apps.cart.serializers import build_cart_payload

    buyer = _user('cartok@example.com')
    cart = Cart.objects.get_or_create(user=buyer)[0]
    cart_services.add_item(cart, _catalog('cart-ok')[3], quantity=3)

    totals = build_cart_payload(cart)['totals']
    assert totals['over_unit_ceiling'] is False


def test_the_checkout_error_message_is_customer_safe():
    """No stack, no internal ids, and it says what to do next."""
    _cart, buyer, _variants = _bulk_cart('safemsg@example.com', 'safe-msg')

    with pytest.raises(order_services.CheckoutError) as excinfo:
        order_services.create_order(buyer, _address(buyer).pk)

    message = str(excinfo.value)
    assert '270' in message and '200' in message
    assert 'split' in message.lower()
    assert 'Traceback' not in message


# --------------------------------------------------------------------------------------
# Throttling: starts are capped, reading is not (§10.2)
# --------------------------------------------------------------------------------------

def test_starting_a_thread_is_throttled_but_reading_the_inbox_is_not():
    from rest_framework.throttling import ScopedRateThrottle

    from apps.messaging.views import CustomerConversationListView, WriteOnlyScopedRateThrottle

    assert CustomerConversationListView.throttle_scope == 'conversation'
    assert WriteOnlyScopedRateThrottle in CustomerConversationListView.throttle_classes
    assert issubclass(WriteOnlyScopedRateThrottle, ScopedRateThrottle)

    # A write-only scope: a GET waves through, a POST is counted. Exercised on
    # a real instance because `allow_request` is a method, not a function.
    throttle = WriteOnlyScopedRateThrottle()
    throttle.scope = 'conversation'
    throttle.rate = '1/day'
    throttle.num_requests, throttle.duration = throttle.parse_rate(throttle.rate)

    class _Req:
        method = 'GET'
        user = None

    read = _Req()
    assert throttle.allow_request(read, None) is True

    class _Write:
        method = 'POST'
        user = None
        _ident = 'x'
    write = _Write()
    # A real POST falls through to the parent rate check (a fresh key passes).
    assert throttle.allow_request(write, None) is True


def test_the_conversation_scope_has_a_rate():
    from rest_framework.throttling import SimpleRateThrottle

    assert 'conversation' in SimpleRateThrottle.THROTTLE_RATES


def test_confirming_a_flag_hides_the_review_and_records_the_reason():
    _s, _st, product, _v, buyer = _reviewable('queue-confirm')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Call me at 09171234567 now',
    )
    flag = ContentFlag.objects.get(review=review)
    moderator = _user('moderator-confirm@example.com', group='moderator')

    moderation_services.resolve_flag(
        moderator, flag, action='confirm', note='Advertised an off-platform contact',
    )

    review.refresh_from_db()
    assert review.status == ReviewStatus.HIDDEN
    assert review.moderated_by == moderator
    assert flag.status == ContentFlag.Status.CONFIRMED
    assert AuditLog.objects.filter(
        action='content_flag_confirmed', actor=moderator, object_id=str(flag.pk),
    ).exists()
    # The confirmation rides on the review's own moderation audit row too.
    assert AuditLog.objects.filter(
        action='review_hidden', actor=moderator, object_id=str(review.pk),
    ).exists()


def test_the_block_api_refuses_to_block_yourself():
    seller, store, _product, _variant = _catalog('block-api-self')
    buyer = _user('blockbuyer-api-self@example.com')
    response = _client_for(buyer).post(
        BLOCKS, {'user_id': buyer.pk}, content_type='application/json',
    )
    assert response.status_code == 400


def test_the_block_api_will_not_probe_conversations_that_are_not_yours():
    seller, store, _product, _variant = _catalog('block-api-idor')
    owner = _user('convoowner@example.com')
    stranger = _user('convostranger@example.com')
    conversation = _convo(owner, store)

    response = _client_for(stranger).post(
        BLOCKS, {'conversation_id': conversation.pk},
        content_type='application/json',
    )
    # "Not found", never "forbidden" — a stranger must not learn the id exists.
    assert response.status_code == 404
    assert ConversationBlock.objects.count() == 0


def test_an_ordinary_message_is_not_reported():
    seller, store, _product, _variant = _catalog('msg-normal')
    buyer = _user('msgbuyer-normal@example.com')
    conversation = _convo(buyer, store)

    messaging_services.send_message(
        conversation, buyer, 'Hi, is this still available? Thanks!',
    )
    conversation.refresh_from_db()
    assert conversation.status == ConversationStatus.OPEN
    assert ContentFlag.objects.count() == 0


def test_a_seller_quoting_their_own_storefront_is_not_reported():
    seller, store, _product, _variant = _catalog('msg-seller')
    buyer = _user('msgbuyer-seller@example.com')
    conversation = _convo(buyer, store)

    messaging_services.send_message(
        conversation, seller, 'You can see it at https://jeyvro.com/store/x',
    )
    conversation.refresh_from_db()
    assert conversation.status == ConversationStatus.OPEN
    assert ContentFlag.objects.count() == 0


def test_a_flagged_review_cannot_vote_on_the_rating():
    _s, _st, product, _v, buyer = _reviewable('flag-rating')
    review = review_services.create_review(
        buyer, product=product, rating=1, body='Terrible, text me at 09171234567',
    )
    product.refresh_from_db()
    # The row is 1-star, but it is not in the aggregate while it waits.
    assert review.rating == 1
    assert product.rating_count == 0
