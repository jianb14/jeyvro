"""Seed staff permission groups (Phase 13.1) — idempotent command.

Creates the 6 canonical staff groups from PROJECT_CONTEXT §4:
- support
- moderator
- finance
- operations
- administrator
- super_administrator

Run: python manage.py seed_staff_groups
Optional promotion flag: python manage.py seed_staff_groups --promote email@example.com --group administrator
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.models import User

STAFF_GROUPS = [
    'support',
    'moderator',
    'finance',
    'operations',
    'administrator',
    'super_administrator',
]


class Command(BaseCommand):
    help = 'Seeds canonical staff groups and optionally assigns a staff user.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--promote',
            type=str,
            help='Email of a user to promote to staff and assign to a group.',
        )
        parser.add_argument(
            '--group',
            type=str,
            default='administrator',
            choices=STAFF_GROUPS,
            help='Group to assign the promoted user to (default: administrator).',
        )

    def handle(self, *args, **options):
        created_count = 0
        for name in STAFF_GROUPS:
            _, created = Group.objects.get_or_create(name=name)
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Staff groups ensured: {len(STAFF_GROUPS)} total ({created_count} newly created).'
            )
        )

        promote_email = options.get('promote')
        if promote_email:
            target_group = options['group']
            try:
                user = User.objects.get(email=promote_email)
            except User.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f'User "{promote_email}" does not exist.')
                )
                return

            user.is_staff = True
            user.save(update_fields=['is_staff', 'updated_at'])
            group = Group.objects.get(name=target_group)
            user.groups.add(group)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Promoted "{promote_email}" to staff and added to group "{target_group}".'
                )
            )
