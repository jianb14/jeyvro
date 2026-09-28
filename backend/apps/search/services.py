"""Search services (Phase 18 — ROADMAP §18.1, §18.2).

Marketplace discovery in one place. Three ideas drive the design:

1. **Relevance is server truth.** A shopper's query is ranked by PostgreSQL
   full-text search (`ts_rank` over a weighted `tsvector`), never by the
   client, and never by insertion order (marketplace-catalog rule 3).

2. **Permission-safe by construction.** There is exactly one function that
   produces a searchable product set — `searchable_products()` — and it filters
   to published products from active stores. Every caller, facet included,
   goes through it, so a suspended store's catalog or a seller's draft can
   never surface through search no matter what the caller asks for.

3. **Facets describe the result set, they don't filter it.** Counts come from
   the same filtered queryset, so the numbers a shopper sees always add up to
   the list above them. Facet counts are computed with the facet's own filter
   lifted (the standard "OR-count" behaviour): a shopper who picks Wicker can
   still see how many Baskets are one click away.

Typo tolerance (§18.1) is layered rather than fussy: exact/prefix full-text
match first, then a `pg_trgm` similarity pass only when the strict pass came
back empty. That keeps the common case fast and index-friendly, and still lets
"banan" find "banana basket" instead of a blank page.
"""
from decimal import Decimal

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db.models import (
    Count,
    DecimalField,
    Exists,
    F,
    Max,
    Min,
    OrderBy,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce, Greatest

from apps.catalog.models import Category, Product, Variant
from apps.stores.models import Store

# Ranked weights: a title hit is worth more than a description hit, which is
# worth more than the store or category the item happens to sit in. These are
# the standard tsvector weight letters (D < C < B < A).
PRODUCT_VECTOR = (
    SearchVector('title', weight='A')
    + SearchVector('description', weight='B')
    + SearchVector('category__name', weight='C')
    + SearchVector('brand__name', weight='C')
    + SearchVector('store__name', weight='D')
)

STORE_VECTOR = (
    SearchVector('name', weight='A') + SearchVector('description', weight='B')
)

CATEGORY_VECTOR = (
    SearchVector('name', weight='A') + SearchVector('description', weight='B')
)

# A trigram score at or above this counts as "close enough" on the typo
# fallback. 0.3 is deliberately forgiving: it only ever runs after a strict
# search found nothing, so a false positive costs nothing when the shopper
# already had no results.
TRIGRAM_THRESHOLD = 0.3

# Sort keys the API accepts. `relevance` is absent because rank is a computed
# full-text score rather than a column, so `_sort_terms` handles it directly.
SORT_KEYS = ('relevance', 'newest', 'price_asc', 'price_desc', 'rating')

# Price buckets for the price facet (§18.1). Fixed server-side so the bands
# never shift under the shopper between requests.
PRICE_BANDS = (
    (Decimal('0'), Decimal('100'), 'Under ₱100'),
    (Decimal('100'), Decimal('500'), '₱100 – ₱500'),
    (Decimal('500'), Decimal('2000'), '₱500 – ₱2,000'),
    (Decimal('2000'), Decimal('10000'), '₱2,000 – ₱10,000'),
    (Decimal('10000'), None, '₱10,000+'),
)

# Guards the endpoint against pathological queries and keeps the prefix scan
# in autocomplete off a single-character keystroke.
MAX_QUERY_LENGTH = 120
MIN_SUGGEST_LENGTH = 2
FACET_LIMIT = 20

# Query aliases (see `alias()` in services below) — named once so the filter,
# the facet, and the sort can never drift apart on a string literal.
PRICE_ALIAS = 'shelf_price'
SIMILARITY_ALIAS = 'trigram_similarity'


class SearchQueryError(ValueError):
    """A query the caller can fix — surfaced as a 400 with a readable detail."""

    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def check_needle(raw):
    """Trim and length-check raw search text into a usable needle.

    Shared by the search and autocomplete entry points so the limit, and the
    message a caller gets for breaking it, cannot drift between them. Raises
    `SearchQueryError` for the caller to map onto a 400.
    """
    needle = (raw or '').strip()
    if len(needle) > MAX_QUERY_LENGTH:
        raise SearchQueryError(
            'query_too_long',
            f'Search text is limited to {MAX_QUERY_LENGTH} characters.',
        )
    return needle


def parse_params(params):
    """Normalize and validate the query string into a plain dict.

    Rejecting bad input here (rather than silently coercing it) keeps the §8
    error envelope honest: a caller sending `page=abc` gets a 400 naming the
    field, not a silently different result set.
    """
    raw = check_needle(params.get('q'))

    def _int(name, default=None, minimum=1):
        value = params.get(name)
        if value in (None, ''):
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise SearchQueryError(
                'invalid_parameter', f'"{name}" must be a whole number.'
            )
        if parsed < minimum:
            raise SearchQueryError(
                'invalid_parameter', f'"{name}" must be {minimum} or greater.'
            )
        return parsed

    def _decimal(name, default=None):
        value = params.get(name)
        if value in (None, ''):
            return default
        try:
            parsed = Decimal(value)
        except Exception:
            raise SearchQueryError(
                'invalid_parameter', f'"{name}" must be a number.'
            )
        if parsed < 0:
            raise SearchQueryError(
                'invalid_parameter', f'"{name}" cannot be negative.'
            )
        return parsed

    sort = (params.get('sort') or 'relevance').strip()
    if sort not in SORT_KEYS:
        raise SearchQueryError(
            'invalid_parameter', f'"{sort}" is not a supported sort.'
        )

    # `in_stock` is tri-state: absent means "don't care", so a shopper can
    # never widen their own results by sending ?in_stock=0.
    in_stock = None
    if params.get('in_stock') not in (None, ''):
        in_stock = params.get('in_stock') in ('1', 'true', 'True')

    page = _int('page', default=1)
    page_size = _int('page_size', default=20)
    if page_size > 100:
        # Mirrors CountItemsPagination.max_page_size so search and browse
        # cannot be made to disagree about the largest legal page.
        raise SearchQueryError(
            'invalid_parameter', '"page_size" must be 100 or fewer.'
        )

    return {
        'q': raw,
        'store': (params.get('store') or '').strip(),
        'category': (params.get('category') or '').strip(),
        'brand': (params.get('brand') or '').strip(),
        'min_price': _decimal('min_price'),
        'max_price': _decimal('max_price'),
        'min_rating': _decimal('min_rating'),
        'in_stock': in_stock,
        'sort': sort,
        'page': page,
        'page_size': page_size,
    }


def searchable_products():
    """The only product set search may ever see.

    Published products from active stores. Drafts, rejected items, and
    everything in a suspended store are excluded here, once, for every caller,
    so no downstream filter or facet can ever widen the set.

    Deliberately annotation-free: facets group and count this queryset, and an
    aggregate annotation here would leak into every facet's GROUP BY and split
    the counts into nonsense. Price is expressed as a scalar subquery instead
    (see `shelf_price`), which filters and sorts like a column without ever
    needing a group.
    """
    return Product.objects.filter(
        status=Product.Status.PUBLISHED,
        store__status=Store.Status.ACTIVE,
    ).select_related('store', 'store__user', 'category', 'brand')


def shelf_price():
    """The SQL for a product's sellable price, matching `resolve_display_price`.

    Cheapest active variant, falling back to `base_price` when a product has no
    sellable variant yet. Expressed as a correlated scalar subquery rather than
    `Min(...)` on purpose: an aggregate would force a GROUP BY that every facet
    query would then have to work around, and a scalar subquery filters, sorts,
    and aggregates like an ordinary column.

    This *must* stay in lockstep with `apps.catalog.services.resolve_display_price`
    (which the product serializer uses to render the price the shopper reads) —
    if the two disagree, the price facet counts the wrong products.
    """
    cheapest_variant_price = Subquery(
        Variant.objects.filter(product=OuterRef('pk'), is_active=True)
        .order_by('price')
        .values('price')[:1]
    )
    return Coalesce(
        cheapest_variant_price,
        F('base_price'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def _with_shelf_price(queryset):
    """Attach the shelf price as a filterable alias.

    `alias()` and not `annotate()`: an alias is invisible to the SELECT clause,
    and therefore invisible to GROUP BY. That is the whole point — filtering by
    price must not change how any facet counts its groups, and a plain
    `filter(shelf_price__gte=...)` keyword lookup only resolves against a name
    Django knows about.
    """
    return queryset.alias(**{PRICE_ALIAS: shelf_price()})


def _with_similarity(queryset, needle):
    """Narrow to fuzzy matches, again via an alias so facets stay unaffected."""
    return queryset.alias(
        **{SIMILARITY_ALIAS: _similarity_expression(needle)}
    ).filter(**{f'{SIMILARITY_ALIAS}__gte': TRIGRAM_THRESHOLD})


def _has_available_variant():
    """SQL EXISTS for "this product has sellable stock right now".

    Availability is a derived server fact (on_hand − reserved), never a stored
    flag and never a client claim, so the filter has to ask the inventory rows
    rather than trust anything on the product.

    Wrapped in `Exists` rather than returning the queryset: an `OuterRef`
    queryset may only be compiled inside a subquery, so handing it to the
    caller unwrapped would try to run it standalone and blow up.
    """
    return Exists(
        Variant.objects.filter(
            product=OuterRef('pk'),
            is_active=True,
            inventory__on_hand__gt=F('inventory__reserved'),
        )
    )


def _apply_filters(queryset, params, *, lift=None):
    """Apply every filter except the ones named in `lift`.

    `lift` is how OR-count facet math works: a shopper who has selected
    "Wicker" still sees the count for "Baskets", because the category filter is
    lifted for the category facet only. Without this, selecting a facet would
    silently zero out its siblings.

    Callers therefore always pass a *fresh* base queryset for faceting —
    lifting a filter means never applying it, since a filter already baked into
    a queryset cannot be taken back out.
    """
    lift = lift or frozenset()
    queryset = _with_shelf_price(queryset)

    if params['store'] and 'store' not in lift:
        queryset = queryset.filter(store__slug=params['store'])

    if params['category'] and 'category' not in lift:
        queryset = queryset.filter(category__slug=params['category'])

    if params['brand'] and 'brand' not in lift:
        queryset = queryset.filter(brand__slug=params['brand'])

    if params['min_price'] is not None and 'price' not in lift:
        queryset = queryset.filter(**{f'{PRICE_ALIAS}__gte': params['min_price']})

    if params['max_price'] is not None and 'price' not in lift:
        queryset = queryset.filter(**{f'{PRICE_ALIAS}__lte': params['max_price']})

    if params['min_rating'] is not None and 'rating' not in lift:
        # NULL rating_average (no published reviews) is correctly excluded:
        # "4★ & up" must never include an unrated product.
        queryset = queryset.filter(rating_average__gte=params['min_rating'])

    if params['in_stock'] and 'stock' not in lift:
        queryset = queryset.filter(_has_available_variant())

    return queryset


def _full_text_query(needle):
    """A websearch query: every word must match, but order doesn't matter.

    `websearch` (rather than `plainto_tsquery`) gives shoppers quoted phrases
    and `OR` for free without us having to parse user input into a query
    language, and it is total — malformed input yields an empty query rather
    than a Postgres syntax error.
    """
    return SearchQuery(needle, search_type='websearch', config='english')


def _sort_terms(sort):
    """Ordering expressions for a sort key, without the stable tiebreaker.

    Price and rating need expressions rather than plain column names: price is
    a computed subquery (`shelf_price`) and rating must place unrated products
    last instead of letting Postgres decide where NULLs land.
    """
    if sort == 'newest':
        return ['-created_at']
    if sort == 'price_asc':
        return [shelf_price().asc()]
    if sort == 'price_desc':
        return [shelf_price().desc()]
    if sort == 'rating':
        return [OrderBy(F('rating_average'), descending=True, nulls_last=True)]
    raise SearchQueryError('invalid_parameter', f'"{sort}" is not a supported sort.')


def _ranked_products(params, needle):
    """Products matching `needle`, ranked; or the filtered set when blank.

    A blank query is a legitimate request (the browse page with filters but no
    keyword), so it must not be treated as "match nothing" — it returns the
    filtered set under the requested sort instead. The returned flag says
    whether the list is genuinely relevance-ranked, which the UI uses to decide
    whether to explain the ordering.
    """
    queryset = _apply_filters(searchable_products(), params)
    if not needle:
        sort = 'newest' if params['sort'] == 'relevance' else params['sort']
        return queryset.order_by(*_sort_terms(sort), '-created_at'), False

    query = _full_text_query(needle)
    ranked = queryset.annotate(
        # normalization=32 divides the rank by itself + 1, compressing ts_rank
        # into 0..1 so a long description cannot outrank a title match purely
        # by being long.
        rank=SearchRank(PRODUCT_VECTOR, query, normalization=32),
    ).filter(rank__gt=0)

    if params['sort'] == 'relevance':
        # Rank first, then newest as a stable tiebreaker so paging can never
        # show the same item twice or skip one (pagination must be total).
        return ranked.order_by('-rank', '-created_at'), True
    return ranked.order_by(*_sort_terms(params['sort']), '-created_at'), True


def _similarity_expression(needle):
    """Trigram closeness of a product to the query, as a SQL expression.

    Deliberately an expression rather than an `annotate()`: facets aggregate
    over this same queryset, and a stray non-aggregate annotation would be
    pulled into every facet's GROUP BY — splitting the counts per similarity
    value and making Postgres return one arbitrary group. Filtering and
    ordering on the expression directly keeps the set annotation-free.
    """
    return Greatest(
        TrigramSimilarity('title', needle),
        TrigramSimilarity('description', needle),
    )


def _typo_fallback_products(params, needle):
    """Fuzzy rescue for a query the strict search could not satisfy.

    Runs *only* on an empty result set, which is what makes a trigram scan
    acceptable here — it is the difference between a blank page and a near
    miss, and it costs nothing on the happy path.
    """
    similarity = _similarity_expression(needle)
    return (
        _with_similarity(_apply_filters(searchable_products(), params), needle)
        .order_by(similarity.desc(), '-created_at')
    )


def facet_source(params, lift=None, fuzzy_needle=None):
    """The set a facet counts over: the shopper's filters, minus its own.

    `lift` names the filter this facet is counting *for*; leaving it unapplied
    is what produces OR-count behaviour ("what would I get if I clicked this")
    rather than the dead-end "everything is zero now" that a naive AND-count
    gives.

    Always built fresh from `searchable_products()`. A filter that has already
    been applied cannot be lifted, so a facet must never be handed an
    already-filtered queryset.
    """
    queryset = _apply_filters(searchable_products(), params, lift=lift)
    if fuzzy_needle:
        queryset = _with_similarity(queryset, fuzzy_needle)
    return queryset


def run_search(params):
    """The full search: ranked products, companion strips, facets, and a total.

    Fuzzy rescue applies to the product set, and when it fires the facet counts
    are rebuilt from the rescued set — otherwise the sidebar would describe a
    list the shopper is not looking at, which is exactly the kind of quiet
    inconsistency that makes faceted search untrustworthy.
    """
    needle = params['q']
    products, ranked = _ranked_products(params, needle)

    total = products.count()
    fuzzy_needle = None
    if needle and total == 0:
        # Nothing matched: retry loosely before telling the shopper the
        # marketplace has nothing. The flag rides back so the UI can say so.
        products = _typo_fallback_products(params, needle)
        total = products.count()
        fuzzy_needle = needle if total else None

    offset = (params['page'] - 1) * params['page_size']
    page_items = list(products[offset:offset + params['page_size']])

    return {
        'products': page_items,
        'count': total,
        'fuzzy': fuzzy_needle is not None,
        'ranked': ranked,
        'facets': build_facets(params, fuzzy_needle=fuzzy_needle),
        'stores': search_stores(needle),
        'categories': search_categories(needle),
    }



# --- Facets (§18.1) ----------------------------------------------------------
# Each facet lifts its own filter before counting (OR-count), so a shopper who
# has already narrowed by category can still see what the other categories
# would add. The counts therefore answer "what would I get if I clicked this",
# not "what is left after everything I picked" — the behaviour shoppers expect
# from a faceted sidebar, and the reason clicking a facet never dead-ends.


def build_facets(params, *, fuzzy_needle=None):
    """Category / brand / price / rating / stock counts for the current set."""
    return {
        'categories': _category_facet(params, fuzzy_needle),
        'brands': _brand_facet(params, fuzzy_needle),
        'prices': _price_facet(params, fuzzy_needle),
        'ratings': _rating_facet(params, fuzzy_needle),
        'in_stock': _stock_facet(params, fuzzy_needle),
    }


def _category_facet(params, fuzzy_needle=None):
    rows = (
        facet_source(params, {'category'}, fuzzy_needle)
        .filter(category__isnull=False)
        .values('category__slug', 'category__name')
        .annotate(count=Count('id', distinct=True))
        .order_by('-count', 'category__name')[:FACET_LIMIT]
    )
    return [
        {
            'slug': row['category__slug'],
            'name': row['category__name'],
            'count': row['count'],
        }
        for row in rows
    ]


def _brand_facet(params, fuzzy_needle=None):
    rows = (
        facet_source(params, {'brand'}, fuzzy_needle)
        .filter(brand__isnull=False)
        .values('brand__slug', 'brand__name')
        .annotate(count=Count('id', distinct=True))
        .order_by('-count', 'brand__name')[:FACET_LIMIT]
    )
    return [
        {
            'slug': row['brand__slug'],
            'name': row['brand__name'],
            'count': row['count'],
        }
        for row in rows
    ]


def _price_facet(params, fuzzy_needle=None):
    """Fixed server-side price bands over the current result set.

    Bands come from the set with the price filter lifted, so a shopper who has
    narrowed to ₱100–₱500 can still see and leave the band they are inside.
    """
    source = facet_source(params, {'price'}, fuzzy_needle)
    price = shelf_price()
    bounds = source.aggregate(low=Min(price), high=Max(price))
    bands = []
    for low, high, label in PRICE_BANDS:
        # Skip bands that cannot contain anything, so the sidebar never offers
        # a filter that is guaranteed to return zero results.
        if high is not None and bounds['low'] is not None and high <= bounds['low']:
            continue
        if bounds['high'] is not None and low > bounds['high']:
            continue
        # Counted through the same alias the price filter uses, so the band a
        # shopper clicks and the order they then see can never disagree.
        bucket = source.filter(**{f'{PRICE_ALIAS}__gte': low})
        if high is not None:
            bucket = bucket.filter(**{f'{PRICE_ALIAS}__lt': high})
        count = bucket.aggregate(total=Count('id', distinct=True))['total']
        if count:
            bands.append({
                'label': label,
                'min': float(low),
                'max': float(high) if high is not None else None,
                'count': count,
            })
    return bands


def _rating_facet(params, fuzzy_needle=None):
    """Cumulative rating buckets — "4★ & up" includes 5★, as shoppers expect."""
    source = facet_source(params, {'rating'}, fuzzy_needle)
    rows = []
    for floor in (Decimal('4'), Decimal('3'), Decimal('2')):
        count = source.filter(rating_average__gte=floor).aggregate(
            total=Count('id', distinct=True)
        )['total']
        if count:
            rows.append({
                'label': f'{floor}★ & up',
                'min': float(floor),
                'count': count,
            })
    return rows


def _stock_facet(params, fuzzy_needle=None):
    source = facet_source(params, {'stock'}, fuzzy_needle)
    total = source.aggregate(total=Count('id', distinct=True))['total']
    in_stock = source.filter(_has_available_variant()).aggregate(
        total=Count('id', distinct=True)
    )['total']
    return {
        'total': total,
        'in_stock': in_stock,
        'out_of_stock': total - in_stock,
    }


# --- Companion entities (§18.1 "search by store / by category") --------------


def _published_products_in_store():
    """Filter fragment: only count a store's *sellable* catalog.

    A store's "12 products" badge must mean 12 things a shopper can actually
    reach, so drafts and rejected items are excluded from the count too.
    """
    return Q(
        products__status=Product.Status.PUBLISHED,
        products__store__status=Store.Status.ACTIVE,
    )


def search_stores(needle, limit=5):
    """Active stores matching the needle — never a suspended storefront.

    `product_count` is annotated here rather than left to the serializer, so
    the companion strip costs one query instead of one per store.
    """
    queryset = Store.objects.filter(status=Store.Status.ACTIVE).annotate(
        product_count=Count(
            'products', filter=_published_products_in_store(), distinct=True
        )
    )
    if needle:
        queryset = queryset.annotate(
            rank=SearchRank(STORE_VECTOR, _full_text_query(needle), normalization=32)
        ).filter(rank__gt=0).order_by('-rank', 'name')
    else:
        queryset = queryset.order_by('name')
    return list(queryset[:limit])


def search_categories(needle, limit=5):
    """Active categories matching the needle, each with a live product count."""
    queryset = Category.objects.filter(is_active=True).annotate(
        product_count=Count(
            'products', filter=_published_products_in_store(), distinct=True
        )
    )
    if needle:
        queryset = queryset.annotate(
            rank=SearchRank(CATEGORY_VECTOR, _full_text_query(needle), normalization=32)
        ).filter(rank__gt=0).order_by('-rank', 'name')
    else:
        queryset = queryset.order_by('position', 'name')
    return list(queryset[:limit])


# --- Autocomplete (§18.1) ----------------------------------------------------


def suggest(needle, limit=8):
    """Cheap prefix-first suggestions for the search box.

    Suggestions are deliberately *prefix* matches rather than relevance
    matches: a shopper typing "bask" wants "Basket" to appear while they are
    still typing, and a ranked full-text pass would bury it behind anything
    whose description happens to contain a whole word. Ranking is left for the
    results page. `istartswith` compiles to a prefix comparison Postgres can
    index, so this stays fast enough to fire behind a keystroke debounce.

    Below `MIN_SUGGEST_LENGTH` this returns empty lists rather than an error:
    the shopper is mid-word, not making a mistake.
    """
    needle = (needle or '').strip()
    if len(needle) < MIN_SUGGEST_LENGTH:
        return {'products': [], 'stores': [], 'categories': []}

    products = (
        searchable_products()
        .filter(title__istartswith=needle)
        .order_by('title')[:limit]
    )
    stores = (
        Store.objects.filter(status=Store.Status.ACTIVE, name__istartswith=needle)
        .order_by('name')[:3]
    )
    categories = (
        Category.objects.filter(is_active=True, name__istartswith=needle)
        .order_by('position', 'name')[:3]
    )
    return {
        'products': list(products),
        'stores': list(stores),
        'categories': list(categories),
    }

