"""Analytics read API (Phase 19 — ROADMAP §19.1, PROJECT_CONTEXT §6 v1.16).

Every endpoint here reads the **reporting aggregates** and never the
transactional tables — that is the §17 promise the whole phase is built on, and
it is why a busy marketplace's dashboard costs the same as a quiet one's.

Grouping follows §4 as §6 v1.16 spells it out: the money figures (GMV, revenue,
commission, refunds) and the store leaderboard belong to `finance` and
`administrator`; product activity is open to the read-only oversight groups
that already see those records. The seller endpoint is scoped by **ownership**
instead: a seller reads their own store's aggregates, resolved from the
session, and never another store's. Nothing here writes — the aggregates are
rebuilt by `manage.py rebuild_reporting`, so a dashboard can never invent a
number, only display one. The one live read on this module is the seller's
*current* stock, which is a snapshot rather than a period metric and is labeled
as one (§19.2).
"""
from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.stores.models import Store

from . import serializers, services

FINANCIAL_GROUPS = ['finance', 'administrator']
OPERATIONAL_GROUPS = ['support', 'operations', 'finance', 'administrator']

DEFAULT_DAYS = 30
MAX_DAYS = 366


def _day(value):
    """A query-string day, or None when absent (§8: no silent defaults)."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Dates use YYYY-MM-DD.') from exc


def _range(request):
    """`?from=&to=` as ISO days, defaulting to the trailing 30 days."""
    end = _day(request.query_params.get('to')) or timezone.localdate()
    start = _day(request.query_params.get('from')) or end - timedelta(
        days=DEFAULT_DAYS - 1
    )
    if end < start:
        raise ValueError('The end of the range cannot precede its start.')
    if (end - start).days + 1 > MAX_DAYS:
        raise ValueError(f'A range spans at most {MAX_DAYS} days.')
    return start, end


def _bad_range(exc):
    return Response(
        {'error': 'invalid_range', 'detail': str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


class StaffAnalyticsSummaryView(APIView):
    """GET /api/v1/admin/analytics/summary/?from=&to= — totals + daily series."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = FINANCIAL_GROUPS

    def get(self, request):
        try:
            start, end = _range(request)
        except ValueError as exc:
            return _bad_range(exc)
        return Response({
            'start': start,
            'end': end,
            'totals': serializers.PlatformTotalsSerializer(
                services.platform_totals(start, end)
            ).data,
            'days': serializers.DailyPlatformMetricSerializer(
                services.platform_series(start, end), many=True
            ).data,
        })


class StaffAnalyticsStoresView(APIView):
    """GET /api/v1/admin/analytics/stores/?from=&to=&limit= — store leaderboard."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = FINANCIAL_GROUPS

    def get(self, request):
        try:
            start, end = _range(request)
        except ValueError as exc:
            return _bad_range(exc)
        limit = _limit(request)
        return Response({
            'start': start,
            'end': end,
            'items': serializers.StoreLeaderboardRowSerializer(
                services.store_leaderboard(start, end, limit=limit), many=True
            ).data,
        })


class StaffAnalyticsProductsView(APIView):
    """GET /api/v1/admin/analytics/products/?from=&to=&limit= — product activity."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = OPERATIONAL_GROUPS

    def get(self, request):
        try:
            start, end = _range(request)
        except ValueError as exc:
            return _bad_range(exc)
        return Response({
            'start': start,
            'end': end,
            'items': serializers.TopProductRowSerializer(
                services.top_products(start, end, limit=_limit(request)), many=True
            ).data,
        })


class StaffAnalyticsStoreDetailView(APIView):
    """GET /api/v1/admin/analytics/stores/<store_id>/ — one store's own days."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = FINANCIAL_GROUPS

    def get(self, request, store_id):
        try:
            start, end = _range(request)
        except ValueError as exc:
            return _bad_range(exc)
        rows = services.store_series(store_id, start, end)
        return Response({
            'start': start,
            'end': end,
            'items': serializers.DailyStoreMetricSerializer(rows, many=True).data,
        })


def _limit(request, default=10, cap=100):
    """`?limit=` bounded to something a dashboard can actually render."""
    raw = request.query_params.get('limit')
    if not raw:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, cap))


# --- The seller's own window (§19.2) ----------------------------------------


class SellerAnalyticsView(APIView):
    """GET /api/v1/seller/analytics/?from=&to=&limit= — the seller's own numbers.

    A seller reads *their own* store and nothing else: the store is resolved
    from the session (`Store.user=request.user`), so there is no id parameter
    to tamper with and no group gate to forget — ownership is the scope
    (marketplace-sellers rules 4/5). The period figures come from the reporting
    aggregates; `inventory` is the store's stock right now, a snapshot rather
    than a period metric, and the page labels it as such.
    """

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        store = get_object_or_404(Store, user=request.user)
        try:
            start, end = _range(request)
        except ValueError as exc:
            return _bad_range(exc)
        return Response({
            'start': start,
            'end': end,
            'totals': serializers.StoreTotalsSerializer(
                services.store_totals(store.id, start, end)
            ).data,
            'days': serializers.DailyStoreMetricSerializer(
                services.store_series(store.id, start, end), many=True
            ).data,
            'top_products': serializers.TopProductRowSerializer(
                services.top_products(
                    start, end, limit=_limit(request), store_id=store.id
                ),
                many=True,
            ).data,
            'inventory': serializers.StoreInventorySerializer(
                services.store_inventory_snapshot(store.id)
            ).data,
        })
