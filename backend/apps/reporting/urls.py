"""Reporting URLs (§19.1–§19.3) — mounted at /api/v1/."""
from django.urls import path

from . import views

app_name = 'reporting'

urlpatterns = [
    path(
        'admin/analytics/summary/',
        views.StaffAnalyticsSummaryView.as_view(),
        name='staff-analytics-summary',
    ),
    path(
        'admin/analytics/stores/',
        views.StaffAnalyticsStoresView.as_view(),
        name='staff-analytics-stores',
    ),
    path(
        'admin/analytics/stores/<int:store_id>/',
        views.StaffAnalyticsStoreDetailView.as_view(),
        name='staff-analytics-store-detail',
    ),
    path(
        'admin/analytics/products/',
        views.StaffAnalyticsProductsView.as_view(),
        name='staff-analytics-products',
    ),
    path(
        'admin/analytics/operations/',
        views.StaffAnalyticsOperationsView.as_view(),
        name='staff-analytics-operations',
    ),
    path(
        'admin/analytics/performance/',
        views.StaffAnalyticsPerformanceView.as_view(),
        name='staff-analytics-performance',
    ),
    path(
        'seller/analytics/',
        views.SellerAnalyticsView.as_view(),
        name='seller-analytics',
    ),
    # §19.4 reports — the report slug and its §4 gate are part of the route,
    # not a branch inside one view, so no parameter can hand a money report to
    # an oversight group. CSV is the only format (C3).
    path(
        'admin/analytics/export/summary/',
        views.StaffAnalyticsExportView.as_view(
            report='summary', required_groups=views.FINANCIAL_GROUPS
        ),
        name='staff-analytics-export-summary',
    ),
    path(
        'admin/analytics/export/stores/',
        views.StaffAnalyticsExportView.as_view(
            report='stores', required_groups=views.FINANCIAL_GROUPS
        ),
        name='staff-analytics-export-stores',
    ),
    path(
        'admin/analytics/export/products/',
        views.StaffAnalyticsExportView.as_view(
            report='products', required_groups=views.OPERATIONAL_GROUPS
        ),
        name='staff-analytics-export-products',
    ),
    path(
        'admin/analytics/export/operations/',
        views.StaffAnalyticsExportView.as_view(
            report='operations', required_groups=views.OPERATIONAL_GROUPS
        ),
        name='staff-analytics-export-operations',
    ),
    path(
        'admin/analytics/export/performance/',
        views.StaffAnalyticsExportView.as_view(
            report='performance', required_groups=views.OPERATIONAL_GROUPS
        ),
        name='staff-analytics-export-performance',
    ),
]
