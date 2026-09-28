"""Phase 18 §18.1 gate tests — search relevance, facets, and safety.

The roadmap gate for this slice is three claims, so these tests are organised
around them:

- *"Search returns relevant products"* — ranking puts a title match above a
  description match, sorts are server-side, and a typo still finds its product
  instead of a blank page.
- *"Filters work together"* — every filter narrows, they compose, and facet
  counts stay honest while they do (OR-count, not "everything is zero now").
- *"Search remains permission-safe"* — a draft, a rejected product, or anything
  in a suspended store is unreachable through results, facets, or autocomplete.

Fixtures are built with the ORM directly (the convention established by the
other domain tests: the register/apply/approve flow is proven in
`test_stores.py`, so repeating it here would only slow the suite down).
"""
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import Brand, Category, Inventory, Product, Variant
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

SEARCH = '/api/v1/search/'
SUGGEST = '/api/v1/search/suggest/'
PASSWORD = 'Str0ng!Passw0rd'

_seller_counter = 0


def _store(name='Search Store', *, status=Store.Status.ACTIVE):
    """A store with its own seller — one user owns exactly one store (§4)."""
    global _seller_counter
    _seller_counter += 1
    seller = User.objects.create_user(
        email=f'seller{_seller_counter}@example.com',
        password=PASSWORD,
        is_seller=True,
    )
    return Store.objects.create(user=seller, name=name, status=status)


def _product(store, title, *, price='100.00', status=Product.Status.PUBLISHED,
             category=None, brand=None, description='', stock=5,
             variant_prices=None, rating=None):
    """A product with a stocked, active variant — or an exact stock level.

    `variant_prices` creates several variants, which is how the "cheapest
    active variant is the shelf price" rule gets exercised.
    """
    product = Product.objects.create(
        store=store,
        title=title,
        description=description,
        base_price=Decimal(price),
        status=status,
        category=category,
        brand=brand,
        rating_average=Decimal(str(rating)) if rating is not None else None,
        rating_count=1 if rating is not None else 0,
    )
    for index, variant_price in enumerate(variant_prices or [price]):
        variant = Variant.objects.create(
            product=product,
            name=f'Variant {index}',
            price=Decimal(variant_price),
            is_default=index == 0,
        )
        Inventory.objects.create(variant=variant, on_hand=stock, reserved=0)
    return product


def _titles(response):
    return [item['title'] for item in response.json()['items']]


# --- Relevance (§18.1 "keyword search", "search by product") -----------------


def test_title_match_outranks_description_match(client):
    """Ranking is server truth: a title hit beats a description hit."""
    store = _store()
    _product(store, 'Ceramic Vase', description='A bamboo-inspired glaze finish.')
    _product(store, 'Bamboo Basket', description='Handwoven storage.')

    response = client.get(SEARCH, {'q': 'bamboo'})
    assert response.status_code == 200
    # Title weight A > description weight B, so the title match leads.
    assert _titles(response)[0] == 'Bamboo Basket'


def test_blank_query_returns_the_filtered_set_not_nothing(client):
    """Filters without a keyword is a real request (the browse-with-filters
    case) and must not be mistaken for "match nothing"."""
    store = _store()
    _product(store, 'Item One', price='50.00')
    _product(store, 'Item Two', price='5000.00')

    response = client.get(SEARCH, {'min_price': '1000'})
    assert response.status_code == 200
    assert response.json()['count'] == 1
    assert _titles(response) == ['Item Two']
    # Nothing was ranked, so the flag stays false — the UI uses it to decide
    # whether to explain the ordering.
    assert response.json()['fuzzy'] is False


def test_strict_match_does_not_trigger_the_fuzzy_fallback(client):
    store = _store()
    _product(store, 'Ceramic')

    body = client.get(SEARCH, {'q': 'ceramic'}).json()
    assert body['count'] == 1
    assert body['fuzzy'] is False


def test_typo_still_finds_the_product(client):
    """A misspelling the strict pass cannot satisfy falls back to trigrams
    rather than showing the shopper an empty marketplace."""
    store = _store()
    _product(store, 'Ceramic')

    strict = client.get(SEARCH, {'q': 'ceramik'}).json()
    # websearch has no stemming that would bridge 'ceramik' to 'ceramic'.
    assert strict['count'] == 1, 'expected the trigram fallback to rescue this'
    assert strict['fuzzy'] is True
    assert strict['items'][0]['title'] == 'Ceramic'


def test_typo_fallback_still_respects_the_searchable_set(client):
    """Fuzzy rescue widens the *matching*, never the permissions."""
    store = _store()
    _product(store, 'Ceramik Draft', status=Product.Status.DRAFT)

    body = client.get(SEARCH, {'q': 'ceramik'}).json()
    assert body['count'] == 0
    assert body['items'] == []


def test_first_page_of_results_is_paginated_with_a_total(client):
    store = _store()
    for index in range(3):
        _product(store, f'Basket {index}')

    first = client.get(SEARCH, {'q': 'basket', 'page_size': 2}).json()
    assert first['count'] == 3           # count is the total, not the page
    assert len(first['items']) == 2

    second = client.get(SEARCH, {'q': 'basket', 'page_size': 2, 'page': 2}).json()
    assert len(second['items']) == 1
    # Pages must not overlap — a shopper scrolling must never see a repeat.
    assert {i['id'] for i in first['items']}.isdisjoint(
        {i['id'] for i in second['items']}
    )



# --- Permission safety (§18.1 gate: "search remains permission-safe") -------


def test_unpublished_states_and_suspended_stores_are_unreachable(client):
    """Every non-sellable state is invisible to keyword search *and* to the
    facets that describe the same set."""
    live = _store('Live Store')
    _product(live, 'Bamboo Live')
    for status in (
        Product.Status.DRAFT,
        Product.Status.PENDING_REVIEW,
        Product.Status.UNPUBLISHED,
        Product.Status.REJECTED,
        Product.Status.ARCHIVED,
    ):
        _product(live, f'Bamboo {status}', status=status)

    suspended = _store('Suspended Store', status=Store.Status.SUSPENDED)
    _product(suspended, 'Bamboo From Suspended Store')

    body = client.get(SEARCH, {'q': 'bamboo'}).json()
    assert body['count'] == 1
    assert [item['title'] for item in body['items']] == ['Bamboo Live']
    # The facet counts must agree with the list, or the sidebar would advertise
    # products the shopper can never reach.
    assert body['facets']['in_stock']['total'] == 1


def test_suspended_store_is_absent_from_the_stores_strip(client):
    _store('Bamboo Live Store')
    suspended = _store('Bamboo Suspended', status=Store.Status.SUSPENDED)
    _product(suspended, 'Bamboo Thing')

    body = client.get(SEARCH, {'q': 'bamboo'}).json()
    assert [store['name'] for store in body['stores']] == ['Bamboo Live Store']


def test_search_by_store_and_category(client):
    """§18.1's "search by store" / "search by category" — the companion strips."""
    store = _store('Bamboo Craft Store')
    category = Category.objects.create(name='Bamboo Goods')
    _product(store, 'Bamboo Basket', category=category)

    body = client.get(SEARCH, {'q': 'bamboo'}).json()
    assert [s['name'] for s in body['stores']] == ['Bamboo Craft Store']
    # The badge counts only what a shopper can actually reach.
    assert body['stores'][0]['product_count'] == 1
    assert [c['name'] for c in body['categories']] == ['Bamboo Goods']
    assert body['categories'][0]['product_count'] == 1


def test_price_filters_use_the_cheapest_active_variant(client):
    """The shelf price is server-resolved, so a variant edit moves the product
    between bands without anything on the product row changing."""
    store = _store()
    _product(store, 'Cheap', variant_prices=['900.00', '20.00'])
    _product(store, 'Pricey', price='400.00')

    under = client.get(SEARCH, {'max_price': '100'}).json()
    assert [item['title'] for item in under['items']] == ['Cheap']

    over = client.get(SEARCH, {'min_price': '100'}).json()
    assert [item['title'] for item in over['items']] == ['Pricey']


def test_stock_filter_counts_availability_not_a_flag(client):
    store = _store()
    _product(store, 'Stocked Item', stock=4)
    _product(store, 'Sold Out Item', stock=0)

    body = client.get(SEARCH, {'in_stock': '1'}).json()
    assert [item['title'] for item in body['items']] == ['Stocked Item']
    # The stock facet lifts its own filter, so it still reports the sold-out
    # item — that is what lets the shopper undo the filter they just applied.
    assert body['facets']['in_stock'] == {
        'total': 2, 'in_stock': 1, 'out_of_stock': 1,
    }


def test_reserved_stock_does_not_count_as_available(client):
    """A fully reserved shelf is sold out — on_hand alone would lie."""
    store = _store()
    product = _product(store, 'All Reserved', stock=3)
    Inventory.objects.filter(variant__product=product).update(reserved=3)

    body = client.get(SEARCH, {'in_stock': '1'}).json()
    assert body['count'] == 0


def test_rating_filters_exclude_unrated_products(client):
    """Unrated products are outside every bucket — a null rating is not a 5."""
    store = _store()
    _product(store, 'Rated Well', rating='4.50')
    _product(store, 'Rated Poorly', rating='2.00')
    _product(store, 'Never Reviewed')

    body = client.get(SEARCH, {'min_rating': '4'}).json()
    assert [item['title'] for item in body['items']] == ['Rated Well']
    # Counted over the set with the rating filter lifted, and buckets are
    # cumulative ("4★ & up" ⊂ "3★ & up"), so they only ever grow.
    assert body['facets']['ratings'] == [
        {'label': '4★ & up', 'min': 4.0, 'count': 1},
        {'label': '3★ & up', 'min': 3.0, 'count': 1},
        {'label': '2★ & up', 'min': 2.0, 'count': 2},
    ]



# --- Facets (§18.1 gate: "filters work together") ----------------------------


def _facet_counts(body, key='categories'):
    return {row['slug' if 'slug' in row else 'label']: row['count']
            for row in body['facets'][key]}


def test_facet_counts_describe_the_result_set(client):
    store = _store()
    wicker = Category.objects.create(name='Wicker')
    baskets = Category.objects.create(name='Baskets')
    brand = Brand.objects.create(name='Rattan Co')
    _product(store, 'Wicker Chair', category=wicker, price='3000.00')
    _product(store, 'Wicker Basket', category=wicker, brand=brand, price='150.00')
    _product(store, 'Bamboo Basket', category=baskets, price='150.00')

    body = client.get(SEARCH, {}).json()
    assert body['count'] == 3
    assert _facet_counts(body) == {'wicker': 2, 'baskets': 1}
    assert _facet_counts(body, 'brands') == {'rattan-co': 1}
    # Stock totals cover the whole set, so they reconcile with the list.
    assert body['facets']['in_stock']['total'] == 3

    # The price bands partition the set: every product lands in exactly one.
    bands = body['facets']['prices']
    assert sum(band['count'] for band in bands) == 3
    # A band that cannot contain anything is never offered.
    assert all(band['count'] > 0 for band in bands)


def test_selecting_a_facet_does_not_zero_out_its_siblings(client):
    """OR-count, not AND-count: after picking a category the shopper must still
    see how many products the other categories would add, or the sidebar
    dead-ends them."""
    store = _store()
    wicker = Category.objects.create(name='Wicker')
    baskets = Category.objects.create(name='Baskets')
    _product(store, 'Wicker Chair', category=wicker)
    _product(store, 'Wicker Basket', category=wicker)
    _product(store, 'Bamboo Basket', category=baskets)

    body = client.get(SEARCH, {'category': 'wicker'}).json()
    assert body['count'] == 2
    # Baskets is not in the filtered set, yet its count survives — that is the
    # whole point of lifting the facet's own filter.
    assert _facet_counts(body) == {'wicker': 2, 'baskets': 1}

    # And the other direction works too: the count follows the keyword.
    narrowed = client.get(SEARCH, {'q': 'basket', 'category': 'wicker'}).json()
    assert narrowed['count'] == 1
    assert _facet_counts(narrowed)['baskets'] == 1


def test_filters_compose(client):
    """Every candidate matches the keyword, so only the filters can separate
    them — a broken filter cannot hide behind the text search."""
    store = _store()
    other = _store('Other Store')
    wanted = Category.objects.create(name='Wicker')
    brand = Brand.objects.create(name='Rattan Co')
    _product(store, 'Match', category=wanted, brand=brand, price='300.00',
             rating='4.50')
    # One product per disqualifying reason — none may sneak in.
    _product(store, 'Match Wrong Category', brand=brand, price='300.00',
             rating='4.50')
    _product(store, 'Match Wrong Brand', category=wanted, price='300.00',
             rating='4.50')
    _product(store, 'Match Too Expensive', category=wanted, brand=brand,
             price='900.00', rating='4.50')
    _product(store, 'Match Unrated', category=wanted, brand=brand,
             price='300.00')
    _product(store, 'Match Sold Out', category=wanted, brand=brand,
             price='300.00', rating='4.50', stock=0)
    _product(other, 'Match Other Store', category=wanted, brand=brand,
             price='300.00', rating='4.50')

    body = client.get(SEARCH, {
        'q': 'match',
        'category': 'wicker',
        'brand': 'rattan-co',
        'min_price': '100',
        'max_price': '500',
        'min_rating': '4',
        'in_stock': '1',
        'store': store.slug,
    }).json()
    assert body['count'] == 1
    assert [item['title'] for item in body['items']] == ['Match']


def test_price_facet_survives_an_active_price_filter(client):
    """The band the shopper is standing in must stay on the page."""
    store = _store()
    _product(store, 'Cheap', price='50.00')
    _product(store, 'Mid', price='300.00')
    _product(store, 'Dear', price='5000.00')

    body = client.get(SEARCH, {'min_price': '100', 'max_price': '1000'}).json()
    assert body['count'] == 1
    bands = body['facets']['prices']
    # All three products are still described, because the price filter is
    # lifted for the price facet — otherwise "reset this filter" would be
    # invisible to the shopper.
    assert sum(band['count'] for band in bands) == 3


# --- Sorting (§18.1) --------------------------------------------------------


def test_sorts_are_server_side(client):
    store = _store()
    _product(store, 'Alpha Basket', price='300.00', rating='3.00')
    _product(store, 'Beta Basket', price='100.00', rating='5.00')
    _product(store, 'Gamma Basket', price='200.00', rating='4.00')

    ascending = client.get(SEARCH, {'q': 'basket', 'sort': 'price_asc'}).json()
    assert [i['title'] for i in ascending['items']] == [
        'Beta Basket', 'Gamma Basket', 'Alpha Basket',
    ]

    descending = client.get(SEARCH, {'q': 'basket', 'sort': 'price_desc'}).json()
    assert [i['title'] for i in descending['items']] == [
        'Alpha Basket', 'Gamma Basket', 'Beta Basket',
    ]

    by_rating = client.get(SEARCH, {'q': 'basket', 'sort': 'rating'}).json()
    assert [i['title'] for i in by_rating['items']] == [
        'Beta Basket', 'Gamma Basket', 'Alpha Basket',
    ]


def test_unrated_products_sort_last_not_first(client):
    """NULL ratings must not float to the top of a "best rated" list."""
    store = _store()
    _product(store, 'No Reviews Yet')
    _product(store, 'Reviewed', rating='3.00')

    body = client.get(SEARCH, {'sort': 'rating'}).json()
    assert [item['title'] for item in body['items']] == [
        'Reviewed', 'No Reviews Yet',
    ]



# --- Autocomplete (§18.1 "autocomplete", "search suggestions") --------------


def test_suggest_returns_prefix_matches_by_entity(client):
    store = _store('Bamboo Hut')
    category = Category.objects.create(name='Bamboo Goods')
    _product(store, 'Bamboo Basket', category=category)
    _product(store, 'Ceramic Vase')

    body = client.get(SUGGEST, {'q': 'bamboo'}).json()
    assert [p['title'] for p in body['products']] == ['Bamboo Basket']
    # The dropdown payload stays minimal — no cards, no images.
    assert set(body['products'][0]) == {'id', 'slug', 'title', 'store_name'}
    assert [s['name'] for s in body['stores']] == ['Bamboo Hut']
    assert [c['name'] for c in body['categories']] == ['Bamboo Goods']


def test_suggest_is_silent_below_the_minimum_length(client):
    """One character is a shopper mid-word, not an error — and not a scan."""
    store = _store()
    _product(store, 'Bamboo Basket')

    response = client.get(SUGGEST, {'q': 'b'})
    assert response.status_code == 200
    assert response.json() == {
        'query': 'b', 'products': [], 'stores': [], 'categories': [],
    }

    assert client.get(SUGGEST, {'q': ''}).json()['products'] == []


def test_suggest_never_reveals_unreachable_products(client):
    store = _store()
    _product(store, 'Bamboo Draft', status=Product.Status.DRAFT)
    suspended = _store('Bamboo Suspended', status=Store.Status.SUSPENDED)
    _product(suspended, 'Bamboo Suspended Item')

    body = client.get(SUGGEST, {'q': 'bamboo'}).json()
    assert body['products'] == []
    assert body['stores'] == []


def test_suggest_rejects_an_oversized_query(client):
    response = client.get(SUGGEST, {'q': 'x' * 121})
    assert response.status_code == 400
    assert response.json()['error'] == 'query_too_long'


# --- Parameter validation (§8 error envelope) --------------------------------


@pytest.mark.parametrize('params', [
    {'page': 'abc'},
    {'page': '0'},
    {'page_size': 'abc'},
    {'page_size': '101'},
    {'min_price': 'cheap'},
    {'min_price': '-1'},
    {'max_price': '-5'},
    {'min_rating': 'high'},
    {'sort': 'cheapest'},
])
def test_invalid_parameters_are_rejected_with_a_400(client, params):
    response = client.get(SEARCH, params)
    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_parameter'
    assert response.json()['detail']


def test_an_oversized_query_is_rejected(client):
    response = client.get(SEARCH, {'q': 'x' * 121})
    assert response.status_code == 400
    assert response.json()['error'] == 'query_too_long'


def test_zero_is_a_legal_price_bound(client):
    """`min_price=0` means "from free" — a real filter, not a bad request."""
    store = _store()
    _product(store, 'Freebie', price='0.00')
    _product(store, 'Keeper', price='999.00')

    response = client.get(SEARCH, {'min_price': '0', 'max_price': '1'})
    assert response.status_code == 200
    assert [item['title'] for item in response.json()['items']] == ['Freebie']


def test_response_envelope_matches_the_list_convention(client):
    """Products ride the §8 `{count, items}` envelope so the frontend can page
    search exactly like every other list."""
    store = _store()
    _product(store, 'Bamboo Basket')

    body = client.get(SEARCH, {'q': 'bamboo'}).json()
    assert body['query'] == 'bamboo'
    assert body['count'] == 1
    assert set(body) == {
        'query', 'count', 'items', 'fuzzy', 'stores', 'categories', 'facets',
    }
    assert set(body['facets']) == {
        'categories', 'brands', 'prices', 'ratings', 'in_stock',
    }


def test_search_is_public(client):
    """A shopper searches before they have an account."""
    store = _store()
    _product(store, 'Bamboo Basket')

    assert client.get(SEARCH, {'q': 'bamboo'}).status_code == 200
    assert client.get(SUGGEST, {'q': 'bamboo'}).status_code == 200

