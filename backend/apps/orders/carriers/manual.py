"""Standard manual/internal carrier adapter (§10.2).

Used for seller's own fleet, local riders, and standard manual courier dispatch.
Generates tracking format: JVTRK-YYYYMMDD-XXXXXXXX.
"""
from django.utils import timezone
from django.utils.crypto import get_random_string

from .base import BaseCarrier

TRACKING_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


class ManualCarrier(BaseCarrier):
    """Default courier adapter for Jeyvro."""

    carrier_code = 'manual'
    carrier_name = 'Standard Delivery'

    def generate_tracking_number(self):
        date = timezone.now().strftime('%Y%m%d')
        suffix = get_random_string(8, TRACKING_ALPHABET)
        return f'JVTRK-{date}-{suffix}'

    def validate_tracking_number(self, tracking_number):
        if not super().validate_tracking_number(tracking_number):
            return False
        return tracking_number.startswith('JVTRK-')
