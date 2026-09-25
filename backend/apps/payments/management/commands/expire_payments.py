"""Cron entry point: release orders whose online payment window passed (§9.1).

Scheduling (cron / Celery) lands with deployment — the command is the seam.
"""
from django.core.management.base import BaseCommand

from apps.payments import services


class Command(BaseCommand):
    help = (
        'Expire unpaid online payments, cancelling their orders and '
        'releasing reserved stock.'
    )

    def handle(self, *args, **options):
        expired = services.expire_overdue_payments()
        for payment in expired:
            self.stdout.write(
                f'{payment.reference}: expired ({payment.order.number})'
            )
        self.stdout.write(
            self.style.SUCCESS(f'Expired {len(expired)} payment(s).')
        )
