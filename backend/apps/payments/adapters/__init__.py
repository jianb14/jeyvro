"""Adapter registry — the one place methods and providers resolve (§6).

Services and views never import a concrete adapter: they ask the registry,
so a real PayMongo/GCash/Maya integration lands as one new subclass plus one
registration here, with zero changes to the payment domain.
"""
from ..models import PaymentMethod
from .base import (  # noqa: F401 — re-exported for services/views
    CheckoutSession,
    GatewayError,
    GatewayEvent,
    GatewayNotConfigured,
    PaymentAdapter,
)
from .cod import CodAdapter
from .gateway import GenericGatewayAdapter

COD = CodAdapter()
GENERIC = GenericGatewayAdapter(PaymentMethod.CARD)

_METHOD_ADAPTERS = {
    PaymentMethod.COD: COD,
    PaymentMethod.CARD: GENERIC,
    PaymentMethod.GCASH: GenericGatewayAdapter(PaymentMethod.GCASH),
    PaymentMethod.MAYA: GenericGatewayAdapter(PaymentMethod.MAYA),
}

# Webhook providers register here when real gateways land (§17). COD is
# absent on purpose: it has no gateway and therefore no callbacks.
_WEBHOOK_ADAPTERS = {
    GENERIC.provider: GENERIC,
}


def get_adapter(method):
    """Method → adapter; raises ValueError for anything unregistered."""
    adapter = _METHOD_ADAPTERS.get(method)
    if adapter is None:
        raise ValueError(f'Unknown payment method: {method}')
    return adapter


def get_webhook_adapter(provider):
    """Provider → adapter for webhook intake; None when unknown (→ 404)."""
    return _WEBHOOK_ADAPTERS.get(provider)


def payment_method_options():
    """Checkout options with live availability — server truth for the UI."""
    options = []
    for method, label in PaymentMethod.choices:
        adapter = _METHOD_ADAPTERS[method]
        available = adapter.is_available()
        options.append({
            'id': method,
            'label': label,
            'description': (
                adapter.description if available
                else adapter.unavailable_note or adapter.description
            ),
            'available': available,
        })
    return options
