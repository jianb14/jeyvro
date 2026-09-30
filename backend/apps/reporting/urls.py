"""Reporting URLs (§19.1) — mounted at /api/v1/."""
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
]
