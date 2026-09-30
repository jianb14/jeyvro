"""`rebuild_reporting` — recompute the reporting aggregates (§19.1).

The gate this command exists to satisfy is "the metrics reconcile with the
transactional data", and the only way to *show* that is to make the aggregates
a pure function of the records: run it, and the tables are whatever the
transactions say they are.

    python manage.py rebuild_reporting                  # every day with data
    python manage.py rebuild_reporting --from 2026-09-01 --to 2026-09-30
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.reporting import services


def _parse(value, flag):
    """`--from`/`--to` are ISO days; anything else is a usage error."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CommandError(f'--{flag} must be a date in YYYY-MM-DD form.') from exc


class Command(BaseCommand):
    help = 'Rebuild the daily reporting aggregates from the transactional records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from', dest='start', default=None,
            help='First day to rebuild (YYYY-MM-DD). Defaults to the first day with data.',
        )
        parser.add_argument(
            '--to', dest='end', default=None,
            help='Last day to rebuild (YYYY-MM-DD). Defaults to today.',
        )

    def handle(self, *args, **options):
        start = _parse(options.get('start'), 'from')
        end = _parse(options.get('end'), 'to')
        try:
            summary = services.rebuild(start=start, end=end)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                # ASCII on purpose: the console here is cp1252, and the arrow
                # that reads so well in the docstring crashes the command *after*
                # it has done all its work (UnicodeEncodeError on stdout).
                f"Rebuilt reporting for {summary['start']} -> {summary['end']} "
                f"({summary['days']} day(s), {summary['stores']} store(s), "
                f"{summary['products']} product(s))."
            )
        )
