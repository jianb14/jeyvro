"""Payment gateway adapter interface (§6, §17).

Domain code never calls a gateway SDK directly: every money movement goes
through an adapter, so PayMongo / GCash / Maya plug in later without touching
the payment services. Adapters start checkouts, verify webhook signatures,
and normalize gateway events — but services remains the only writer of
payment state (payments-skill rule 4).
"""
from dataclasses import dataclass, field


class GatewayError(RuntimeError):
    """Adapter-level failure — message is safe to show the customer."""


class GatewayNotConfigured(GatewayError):
    """No credentials/sandbox for this gateway yet (§17 — deployment)."""


@dataclass(frozen=True)
class CheckoutSession:
    """What a gateway returns when a payment is started."""

    gateway_reference: str = ''
    checkout_url: str = ''
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GatewayEvent:
    """A normalized webhook event — signature-checked before it is used."""

    event_id: str
    event_type: str
    reference: str
    amount: str = None  # decimal string as claimed by the gateway
    raw: dict = field(default_factory=dict)


class PaymentAdapter:
    """One adapter per payment method — COD is the first (skill rule 4)."""

    provider = ''
    method = ''
    description = ''
    unavailable_note = ''

    def is_available(self):
        """Whether checkout may start with this method right now."""
        raise NotImplementedError

    def create_checkout(self, payment):
        """Starts the money movement; returns a CheckoutSession."""
        raise NotImplementedError

    def verify_webhook_signature(self, body, signature):
        """True only when the raw body matches the gateway signature."""
        raise NotImplementedError

    def parse_event(self, payload):
        """Gateway JSON → GatewayEvent; raises GatewayError when malformed."""
        raise NotImplementedError

    def refund(self, refund):
        """Requests money back; returns {'status':…, 'gateway_reference':…}."""
        raise NotImplementedError
