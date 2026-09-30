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
]
