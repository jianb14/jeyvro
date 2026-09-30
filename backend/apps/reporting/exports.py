"""CSV exports for the reporting aggregates (§19.4).

CSV is the **only** export format, deliberately: a real `.xlsx`/`.pdf` writer
would need a new runtime dependency, and a mislabelled text file pretending to
be a spreadsheet is worse than no export at all (C3 — the same reason §19.1
pinned "CSV only").

Every figure leaves as the server's own string: the rows are the *serializer
output* of the same read the JSON endpoints serve, so a report can never show a
number the API does not, and money keeps its exact decimals instead of being
re-formatted into a float somewhere in a spreadsheet.
"""
import csv
from io import StringIO

from . import serializers, services

# A spreadsheet is a bad place to discover a million rows; a range that would
# produce more than this is refused with a 400 rather than truncated silently.
MAX_EXPORT_ROWS = 5000

# Human headers for the people who open the file; the *values* stay the API's.
LABELS = {
    'day': 'Day',
    'store_id': 'Store ID',
    'store__name': 'Store',
    'store__slug': 'Store slug',
    'product_id': 'Product ID',
    'product__title': 'Product',
    'store_name': 'Store',
    'is_active': 'Active',
    'gmv': 'GMV',
    'commission_rate_percent': 'Commission rate (%)',
    'orders_count': 'Orders',
    'orders_cancelled': 'Orders cancelled',
    'orders_paid': 'Orders paid',
    'orders_open': 'Orders open',
    'orders_completed': 'Orders completed',
    'orders_refunded': 'Orders refunded',
    'units_sold': 'Units sold',
    'products_sold': 'Products sold',
    'active_customers': 'Active customers',
    'active_sellers': 'Active sellers',
    'customer_days': 'Customer days',
    'seller_days': 'Seller days',
    'merchandise': 'Merchandise',
    'shipping': 'Shipping',
    'discounts': 'Discounts',
    'captured_total': 'Collected',
    'refunded_total': 'Refunded',
    'revenue': 'Revenue',
    'commission_base': 'Commission base',
    'commission': 'Commission',
    'gross_sales': 'Gross sales',
    'seller_funded_discount': 'Store-funded discounts',
    'voucher_seller_share': 'Store-funded voucher share',
    'voucher_discount': 'Voucher discount',
    'voucher_redemptions': 'Voucher redemptions',
    'reviews_count': 'Reviews',
    'reviews_rating_sum': 'Review rating sum',
    'shipments_created': 'Parcels sent',
    'shipments_delivered': 'Parcels delivered',
    'returns_filed': 'Returns filed',
    'returns_approved': 'Returns approved',
    'returns_rejected': 'Returns rejected',
    'returns_received': 'Returns received',
    'refunds_issued': 'Refunds issued',
    'refunds_settled': 'Refunds settled',
    'requests_filed': 'Requests filed',
    'conversations_opened': 'Conversations opened',
    'messages_sent': 'Messages sent',
    'disputes_opened': 'Disputes opened',
    'disputes_resolved': 'Disputes resolved',
}

# slug -> (title, serializer, row source). The serializer is the *same* one the
# JSON endpoint uses, so a report and the API can never disagree; the row
# source is the same rollup read, with no limit — an export is the whole range.
REPORTS = {
    'summary': (
        'Platform summary',
        serializers.DailyPlatformMetricSerializer,
        lambda start, end: services.platform_series(start, end),
    ),
    'stores': (
        'Store report',
        serializers.StoreLeaderboardRowSerializer,
        lambda start, end: services.store_leaderboard(start, end, limit=None),
    ),
    'products': (
        'Product activity',
        serializers.TopProductRowSerializer,
        lambda start, end: services.top_products(start, end, limit=None),
    ),
    'operations': (
        'Operational report',
        serializers.DailyOperationsMetricSerializer,
        lambda start, end: services.operations_series(start, end),
    ),
    'performance': (
        'Seller performance',
        serializers.StorePerformanceRowSerializer,
        lambda start, end: services.store_performance(start, end, limit=None),
    ),
}


class UnknownReport(Exception):
    """The `report` slug is not one of the reports (§8: validated server-side)."""


class ExportTooLarge(Exception):
    """The range holds more rows than a spreadsheet should be handed."""


def _csv(headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)  # CRLF + minimal quoting: opens in any spreadsheet
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()


def render(report, start, end):
    """The CSV body, filename and row count for one report (§19.4).

    An empty range still exports its header — a file with the columns and no
    rows is a truthful answer, where an empty body would look like a broken
    download. The row count comes back with the file so the caller can audit
    *what* left the building, not just that something did (§20.3).
    """
    try:
        _title, serializer_class, rows_of = REPORTS[report]
    except KeyError:
        raise UnknownReport(report) from None

    payload = serializer_class(rows_of(start, end), many=True).data
    if len(payload) > MAX_EXPORT_ROWS:
        raise ExportTooLarge(
            f'That range holds more than {MAX_EXPORT_ROWS} rows — narrow it and '
            'export again.'
        )
    fields = list(serializer_class().fields)
    headers = [LABELS.get(name, name.replace('_', ' ').title()) for name in fields]
    rows = [[row.get(name, '') for name in fields] for row in payload]
    return (
        _csv(headers, rows),
        f'jeyvro-{report}-{start}-{end}.csv',
        len(rows),
    )