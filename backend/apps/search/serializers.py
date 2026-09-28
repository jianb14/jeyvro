"""Search response shapes (Phase 18 — ROADMAP §18.1).

Declared fields only (backend-api rule 2). Product results reuse the catalog's
`PublicProductSerializer` rather than defining a lookalike: the shopper's
search page renders the exact same product card as the browse page, so a
second shape would be a second thing to keep in sync and the first place a
drift bug would hide. Store and category results are deliberately lean — a
companion row in the results header needs a name, a link, and a count, and
nothing else.

Facets are computed server-side and passed through as plain dicts: they are
aggregate facts (label + count), not model rows, so there is no object to
serialize.
"""
from rest_framework import serializers

from apps.catalog.models import Category, Product
from apps.stores.models import Store


class SearchStoreSerializer(serializers.ModelSerializer):
    """A store as it appears in the "Stores" strip of search results.

    `product_count` is a plain read of the service's annotation rather than a
    computed field: the count is a permission-shaped fact (published products
    only) and belongs with the query that knows the rules, not in a serializer
    that would have to re-derive them.
    """

    product_count = serializers.IntegerField(read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = [
            'id', 'slug', 'name', 'description',
            'logo_url', 'rating', 'product_count',
        ]

    def get_rating(self, obj):
        # Mirrors the catalog contract: a JSON number, or null when the store
        # has no published reviews yet — never a faked 0.
        return float(obj.rating_average) if obj.rating_average is not None else None


class SearchCategorySerializer(serializers.ModelSerializer):
    """A category as it appears in the "Categories" strip of search results."""

    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'slug', 'name', 'product_count']


class SearchSuggestionSerializer(serializers.ModelSerializer):
    """Minimal product row for the autocomplete dropdown.

    The dropdown is a list of titles-with-a-link, so this carries strictly less
    than a product card — fetching a card's worth of images and variants on
    every keystroke would be waste.
    """

    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'slug', 'title', 'store_name']
