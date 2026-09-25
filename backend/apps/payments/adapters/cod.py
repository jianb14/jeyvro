"""Cash on Delivery adapter — the first payment method (§6, skill rule 4).

COD needs no gateway: the reservation is committed when staff confirm the
cash was collected at delivery (Phase 10 wires the same service into its
delivery flow). Cash refunds are recorded by staff — there is no callback.
"""
from ..models import PaymentMethod, RefundStatus
from .base import CheckoutSession, GatewayNotConfigured, PaymentAdapter


class CodAdapter(PaymentAdapter):
    provider = 'cod'
    method = PaymentMethod.COD
    description = 'Pay in cash when your order arrives — no online payment needed.'

    def is_available(self):
        return True

    def create_checkout(self, payment):
        # Nothing to start: the money moves on delivery.
        return CheckoutSession()

    def verify_webhook_signature(self, body, signature):
        return False  # COD has no gateway and therefore no callbacks

    def parse_event(self, payload):
        raise GatewayNotConfigured('Cash on Delivery receives no webhook events.')

    def refund(self, refund):
        """Cash is handed back by staff — the refund settles immediately."""
        return {'status': RefundStatus.SUCCEEDED, 'gateway_reference': ''}
