"""Phase 15 notifications test suite (ROADMAP §15.2, §15.3, §15.4)."""
import pytest
from django.core import mail
from django.test import Client, override_settings

from apps.accounts.models import NotificationPreference, User
from apps.notifications import services as notification_services
from apps.notifications.models import Notification, NotificationCategory

pytestmark = pytest.mark.django_db
PASSWORD = 'Str0ng!Passw0rd'


def _user(email):
    return User.objects.create_user(
        email=email,
        password=PASSWORD,
        first_name=email.split('@')[0].capitalize(),
    )


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_create_notification_and_unread_count():
    user = _user('notifyuser@example.com')
    assert notification_services.get_unread_notification_count(user) == 0

    n1 = notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.ORDERS,
        title='Order Shipped',
        message='Your parcel is on its way.',
        action_url='/orders/JV-1234',
    )
    assert n1.is_read is False
    assert notification_services.get_unread_notification_count(user) == 1

    n2 = notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.MESSAGING,
        title='New Message',
        message='Seller replied to you.',
        action_url='/account/messages?id=1',
    )
    assert notification_services.get_unread_notification_count(user) == 2


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_notification_email_preferences():
    mail.outbox.clear()
    user = _user('prefuser@example.com')
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    prefs.order_updates_email = False
    prefs.messaging_email = True
    prefs.save()

    # Order update should not send email because opted out
    notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.ORDERS,
        title='Order Placed',
        message='Order placed.',
    )
    assert len(mail.outbox) == 0

    # Messaging update should send email
    notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.MESSAGING,
        title='Message Received',
        message='You received a message.',
    )
    assert len(mail.outbox) == 1
    assert '[JEYVRO] Message Received' in mail.outbox[0].subject


def test_notification_api_endpoints():
    user = _user('apiuser@example.com')
    client = Client()
    client.force_login(user)

    n1 = notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.SYSTEM,
        title='Welcome to Jeyvro',
        message='Thanks for joining!',
    )
    n2 = notification_services.create_notification(
        recipient=user,
        category=NotificationCategory.ORDERS,
        title='Order Placed',
        message='Order confirmed.',
    )

    # 1. Unread count endpoint
    resp = client.get('/api/v1/notifications/unread-count/')
    assert resp.status_code == 200
    assert resp.json()['unread_count'] == 2

    # 2. List notifications
    resp = client.get('/api/v1/notifications/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['count'] == 2
    assert body['unread_count'] == 2
    assert len(body['items']) == 2

    # 3. Mark single notification read
    resp = client.post(f'/api/v1/notifications/{n1.id}/read/')
    assert resp.status_code == 200
    assert resp.json()['is_read'] is True

    resp = client.get('/api/v1/notifications/unread-count/')
    assert resp.json()['unread_count'] == 1

    # 4. Mark all read
    resp = client.post('/api/v1/notifications/read-all/')
    assert resp.status_code == 200
    assert resp.json()['unread_count'] == 0

    resp = client.get('/api/v1/notifications/unread-count/')
    assert resp.json()['unread_count'] == 0
