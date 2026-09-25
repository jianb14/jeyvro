"""Carrier adapter interface and registry (Phase 10 — §10.2).

Just like payment gateways have adapters (Phase 9), shipping carriers
use a uniform interface so manual/local riders, J&T, LBC, and NinjaVan
all speak the same tracking and dispatch contract.
"""
from .base import BaseCarrier
from .manual import ManualCarrier

CARRIERS = {
    'manual': ManualCarrier(),
    'standard': ManualCarrier(),
}


def get_carrier(code='manual'):
    """Returns the carrier adapter for code, defaulting to manual/standard."""
    return CARRIERS.get(code or 'manual', CARRIERS['manual'])
