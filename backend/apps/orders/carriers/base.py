"""Base carrier adapter interface (§10.2).

Every carrier implements tracking generation, tracking number validation,
and status inquiry.
"""


class BaseCarrier:
    """Contract for courier integrations."""

    carrier_code = 'base'
    carrier_name = 'Base Carrier'

    def generate_tracking_number(self):
        """Generates a unique tracking identifier for a new shipment."""
        raise NotImplementedError

    def validate_tracking_number(self, tracking_number):
        """Returns True if the tracking number conforms to this carrier's format."""
        return bool(tracking_number and isinstance(tracking_number, str))

    def get_display_name(self):
        return self.carrier_name
