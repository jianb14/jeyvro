"""The online-payment seam — one generic adapter for every hosted gateway.

Real integrations (PayMongo, GCash, Maya — §17) subclass this adapter and
override `create_checkout` / `refund` with their SDK calls; signature
verification (HMAC-SHA256 over the raw request body) and event normalization
live here so every gateway's webhooks are handled identically. Until
credentials exist, `is_available()` is False and checkout refuses online
methods; the sandbox flag turns on a fake checkout so the entire flow
(checkout → signed webhook → paid) is exercised by the tests.
"""
import hashlib
import hmac

from django.conf import settings

from ..models import RefundStatus
from .base import CheckoutSession, GatewayEvent, GatewayError, GatewayNotConfigured, PaymentAdapter


class GenericGatewayAdapter(PaymentAdapter):
    """Adapter for hosted-checkout gateways; one subclass per provider later."""

    provider = 'generic'
    description = 'Pay securely online with your card or e-wallet.'
    unavailable_note = 'Coming soon — online payments need the gateway integration.'

    def __init__(self, method):
        self.method = method

    # --- Configuration (env-driven; secrets never in code — C7) ---

    def _secret(self):
        return getattr(settings, 'PAYMENTS_GATEWAY_WEBHOOK_SECRET', '')

    def _sandbox(self):
        return bool(getattr(settings, 'PAYMENTS_GATEWAY_SANDBOX', False))

    def is_available(self):
        return bool(
            self._sandbox()
            or getattr(settings, 'PAYMENTS_GATEWAY_CHECKOUT_URL', '')
        )

    # --- Adapter interface ---

    def create_checkout(self, payment):
        if not self.is_available():
            raise GatewayNotConfigured(
                'Online payments are not enabled yet — choose cash on delivery.'
            )
        if self._sandbox():
            return CheckoutSession(
                gateway_reference=f'sbx_{payment.reference}',
                checkout_url=f'https://sandbox.payments.local/checkout/{payment.reference}',
            )
        base_url = getattr(settings, 'PAYMENTS_GATEWAY_CHECKOUT_URL', '')
        return CheckoutSession(
            gateway_reference=f'{self.provider}_{payment.reference}',
            checkout_url=f'{base_url}?ref={payment.reference}',
        )

    def verify_webhook_signature(self, body, signature):
        secret = self._secret()
        if not secret or not signature:
            return False
        expected = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.strip())

    def parse_event(self, payload):
        try:
            event_id = str(payload['id'])
            event_type = str(payload['type'])
        except (KeyError, TypeError) as exc:
            raise GatewayError('Webhook payload is missing id/type.') from exc
        data = payload.get('data') or {}
        try:
            reference = str(data['reference'])
        except (KeyError, TypeError) as exc:
            raise GatewayError('Webhook payload is missing a reference.') from exc
        amount = data.get('amount')
        return GatewayEvent(
            event_id=event_id,
            event_type=event_type,
            reference=reference,
            amount=str(amount) if amount is not None else None,
            raw=payload,
        )

    def refund(self, refund):
        if not self.is_available():
            raise GatewayNotConfigured(
                'Online refunds need the gateway integration (Phase 23).'
            )
        return {
            'status': RefundStatus.SUCCEEDED,
            'gateway_reference': f'sbx_refund_{refund.reference}',
        }
