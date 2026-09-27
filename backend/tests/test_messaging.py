"""Phase 15 messaging test suite (ROADMAP §15.1, §12.6, §15.3)."""
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client

from apps.accounts.models import User
from apps.catalog import services as catalog_services
from apps.messaging import services as messaging_services
from apps.messaging.models import (
    Conversation,
    ConversationReport,
    ConversationStatus,
    ConversationType,
    Message,
)
from apps.notifications.models import Notification
from apps.stores.models import Store

pytestmark = pytest.mark.django_db
PASSWORD = 'Str0ng!Passw0rd'


def _user(email, is_staff=False):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
        is_staff=is_staff,
    )


def _store(seller, name='Seller Store', slug='seller-store'):
    seller.is_seller = True
    seller.save(update_fields=['is_seller'])
    return Store.objects.create(
        user=seller,
        name=name,
        slug=slug,
        status='active',
    )


def test_start_conversation_and_send_message():
    buyer = _user('buyer@example.com')
    seller = _user('seller@example.com')
    store = _store(seller)

    # 1. Start conversation
    conv, created = messaging_services.start_or_get_conversation(
        buyer,
        store=store,
        subject='Question about stock',
        initial_message='Hi, do you have more in blue?',
    )
    assert created is True
    assert conv.customer == buyer
    assert conv.store == store
    assert conv.messages.count() == 1
    assert conv.messages.first().body == 'Hi, do you have more in blue?'

    # 2. Seller should have an in-app notification
    notification = Notification.objects.filter(recipient=seller).first()
    assert notification is not None
    assert 'New message from Buyer' in notification.title

    # 3. Seller has 1 unread message
    assert messaging_services.get_conversation_unread_count(conv, seller) == 1
    assert messaging_services.get_conversation_unread_count(conv, buyer) == 0

    # 4. Seller replies
    reply = messaging_services.send_message(
        conv,
        seller,
        body='Yes, we will restock next week!',
    )
    assert reply.body == 'Yes, we will restock next week!'
    assert messaging_services.get_conversation_unread_count(conv, buyer) == 1

    # 5. Buyer reads conversation
    messaging_services.mark_conversation_as_read(conv, buyer)
    assert messaging_services.get_conversation_unread_count(conv, buyer) == 0


def test_stranger_cannot_read_or_post_to_conversation():
    buyer = _user('buyer2@example.com')
    seller = _user('seller2@example.com')
    stranger = _user('stranger@example.com')
    store = _store(seller, name='Store 2', slug='store-2')

    conv, _ = messaging_services.start_or_get_conversation(
        buyer,
        store=store,
        initial_message='Hello!',
    )

    # Stranger check
    assert messaging_services.can_access_conversation(conv, stranger) is False

    with pytest.raises(PermissionDenied):
        messaging_services.send_message(conv, stranger, body='Intruder!')


def test_messaging_api_endpoints():
    buyer = _user('buyer3@example.com')
    seller = _user('seller3@example.com')
    store = _store(seller, name='Store 3', slug='store-3')

    buyer_client = Client()
    buyer_client.force_login(buyer)

    # 1. Start conversation via API
    resp = buyer_client.post('/api/v1/conversations/', {
        'store_id': store.id,
        'subject': 'Discount inquiry',
        'message': 'Can I get a voucher?',
    }, content_type='application/json')
    assert resp.status_code == 201
    conv_id = resp.json()['id']

    # 2. List customer conversations
    resp = buyer_client.get('/api/v1/conversations/')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1
    assert resp.json()['items'][0]['store_name'] == 'Store 3'

    # 3. Seller lists their store conversations (§12.6)
    seller_client = Client()
    seller_client.force_login(seller)

    resp = seller_client.get('/api/v1/seller/conversations/')
    assert resp.status_code == 200
    assert resp.json()['count'] == 1
    assert resp.json()['unread_count'] == 1

    # 4. Seller posts reply
    resp = seller_client.post(f'/api/v1/conversations/{conv_id}/messages/', {
        'body': 'Sure, use CODE10!',
    }, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['body'] == 'Sure, use CODE10!'

    # 5. Buyer fetches detail -> automatically marks as read
    resp = buyer_client.get(f'/api/v1/conversations/{conv_id}/')
    assert resp.status_code == 200
    assert len(resp.json()['messages']) == 2
    assert resp.json()['unread_count'] == 0

    # 6. Report conversation
    resp = buyer_client.post(f'/api/v1/conversations/{conv_id}/report/', {
        'reason': 'Spam or advertising',
        'details': 'Sent promotional codes.',
    }, content_type='application/json')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'reported'
