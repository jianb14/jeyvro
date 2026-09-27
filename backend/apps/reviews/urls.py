"""Review URLs — mounted at the API root (config/urls.py).

The product-scoped path sits under /catalog/…/reviews/ (reads + writes);
the row-scoped paths live under /reviews/….
"""
from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path(
        'catalog/products/<slug:slug>/reviews/',
        views.ProductReviewListView.as_view(),
        name='product-reviews',
    ),
    path(
        'catalog/products/<slug:slug>/reviews/eligibility/',
        views.ProductReviewEligibilityView.as_view(),
        name='product-review-eligibility',
    ),
    path(
        'reviews/<int:pk>/',
        views.ReviewDetailView.as_view(),
        name='review-detail',
    ),
    path(
        'reviews/<int:pk>/report/',
        views.ReviewReportView.as_view(),
        name='review-report',
    ),
    path(
        'reviews/<int:pk>/reply/',
        views.ReviewReplyView.as_view(),
        name='review-reply',
    ),
    path(
        'reviews/<int:pk>/moderate/',
        views.StaffReviewModerateView.as_view(),
        name='review-moderate',
    ),
    path(
        'reviews/<int:pk>/reports/resolve/',
        views.StaffReviewReportsResolveView.as_view(),
        name='review-reports-resolve',
    ),
    path(
        'reviews/moderation/',
        views.StaffReviewQueueView.as_view(),
        name='staff-review-queue',
    ),
    path(
        'reviews/store/',
        views.StoreReviewListView.as_view(),
        name='store-reviews',
    ),
]
