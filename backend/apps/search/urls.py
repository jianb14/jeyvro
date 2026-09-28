"""Search URLs (Phase 18 — ROADMAP §18.1, §18.3).

Three public surfaces, all under /api/v1/search/:
- ``''``                    ranked multi-entity results with faceted counts
- ``suggest/``              lightweight autocomplete as the shopper types
- ``recommendations/``      §18.3 discovery shelves (trending/popular/related/
                            similar/personalized)

Everything is public and permission-safe by construction: the only rows a
query can reach are published products from active stores, active categories,
and active stores (see `services.searchable_products`).
"""
from django.urls import path

from . import views

app_name = 'search'

urlpatterns = [
    path('', views.SearchView.as_view(), name='search'),
    path('suggest/', views.SearchSuggestView.as_view(), name='search-suggest'),
    path(
        'recommendations/',
        views.RecommendationsView.as_view(),
        name='search-recommendations',
    ),
]
