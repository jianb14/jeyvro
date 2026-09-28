"""Search views (Phase 18 — ROADMAP §18.1).

Both endpoints are public and read-only: a shopper searches before they have
an account. Safety comes from the service layer's single `searchable_products`
choke point rather than from a permission class, so there is no path through
these views that can reach an unpublished product or a suspended store.

Views stay thin on purpose — parameter validation, ranking, and faceting all
live in `services`, which is what the tests exercise directly.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers import PublicProductSerializer

from . import services
from .serializers import (
    SearchCategorySerializer,
    SearchStoreSerializer,
    SearchSuggestionSerializer,
)


class SearchView(APIView):
    """GET /api/v1/search/ — ranked, faceted, multi-entity discovery.

    Returns the marketplace's products as the primary `{count, items}` result
    set (the §8 list convention, so the frontend can page it like any other
    list) plus the companion stores/categories strips and facet counts.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            params = services.parse_params(request.query_params)
        except services.SearchQueryError as exc:
            return Response(
                {'error': exc.code, 'detail': exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = services.run_search(params)

        return Response({
            'query': params['q'],
            'count': result['count'],
            'items': PublicProductSerializer(
                result['products'], many=True, context={'request': request}
            ).data,
            'fuzzy': result['fuzzy'],
            'stores': SearchStoreSerializer(
                result['stores'], many=True, context={'request': request}
            ).data,
            'categories': SearchCategorySerializer(
                result['categories'], many=True, context={'request': request}
            ).data,
            'facets': result['facets'],
        })


class SearchSuggestView(APIView):
    """GET /api/v1/search/suggest/ — autocomplete for the search box (§18.1).

    Kept separate from the full search so the navbar can poll it on every
    keystroke without paying for ranking, faceting, or serializing product
    cards. A query below the minimum length returns empty lists rather than a
    400: the shopper is mid-word, not making an error.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            needle = services.check_needle(request.query_params.get('q'))
        except services.SearchQueryError as exc:
            return Response(
                {'error': exc.code, 'detail': exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(needle) < services.MIN_SUGGEST_LENGTH:
            return Response({
                'query': needle,
                'products': [],
                'stores': [],
                'categories': [],
            })

        result = services.suggest(needle)
        return Response({
            'query': needle,
            'products': SearchSuggestionSerializer(
                result['products'], many=True, context={'request': request}
            ).data,
            'stores': SearchStoreSerializer(
                result['stores'], many=True, context={'request': request}
            ).data,
            'categories': SearchCategorySerializer(
                result['categories'], many=True, context={'request': request}
            ).data,
        })
