"""Phase 18 §18.3 gate tests — discovery shelves.

The slice claims five rankings plus a personalization foundation, so the
tests are organised around what each one actually promises:

- *trending / popular* — the order rows really are the ranking, recent units
  win "trending" while all-time units win "popular", a cancelled order never
  counts as a sale, and a marketplace that has sold nothing still gets a
  shelf instead of an empty homepage.
- *related / similar* — a shelf is built from the seed's own neighbourhood
  (category first, words second) and never returns the seed, nor pads itself
  with a product that contradicts its own label.
- *personalized* — history scopes the ranking, travels with the request, and
  never becomes a server-side profile.
- *permission-safe* — the claim that made §18.1 honest still holds for every
  kind, including the ones whose ranking comes from order rows.

Fixtures are built with the ORM directly, as everywhere else: the checkout
flow itself is proven in `test_orders.py`, so repeating it here would only
slow the suite down.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Brand, Category, Inventory, Product, Variant
from apps.orders.models import Order, OrderItem, SellerOrder
from apps.stores.models import Store

pytestmark = pytest.mark.django_db

RECOMMENDATIONS = '/api/v1/search/recommendations/'
SEARCH = '/api/v1/search/'
CATALOG = '/api/v1/catalog/products/'
PASSWORD = 'Str0ng!Passw0rd'

_seller_counter = 0
_buyer_counter = 0
_order_counter = 0


def _store(name='Discovery Store', *, status=Store.Status.ACTIVE):
    """A store with its own seller — one user owns exactly one store (§4)."""
    global _seller_counter
    _seller_counter += 1
    seller = User.objects.create_user(
        email=f'seller{_seller_counter}@example.com',
        password=PASSWORD,
        is_seller=True,
    )
    return Store.objects.create(user=seller, name=name, status=status)


def _buyer():
    global _buyer_counter
    _buyer_counter += 1
    return User.objects.create_user(
        email=f'buyer{_buyer_counter}@example.com', password=PASSWORD
    )


def _product(store, title, *, price='100.00', status=Product.Status.PUBLISHED,
             category=None, brand=None, description='', rating=None):
    """A product with one stocked, active variant."""
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
    variant = Variant.objects.create(
        product=product, name='Default', price=Decimal(price), is_default=True
    )
    Inventory.objects.create(variant=variant, on_hand=20, reserved=0)
    return product


def _sell(product, quantity, *, days_ago=0, status='placed'):
    """One sale line, optionally aged out of the §18.3 trending window.

    `created_at` is `auto_now_add`, so backdating is a follow-up `update()`
    rather than an argument — the field the trending window reads is the one
    being moved.
    """
    global _order_counter
    _order_counter += 1

    variant = product.variants.first()
    line_total = variant.price * quantity
    order = Order.objects.create(
        number=f'JV-DISC-{_order_counter:06d}',
        user=_buyer(),
        status=status,
        ship_to_name='Maria Santos',
        ship_to_phone='09171234567',
        shipping_line1='12 Mabini Street',
        shipping_city='Quezon City',
        shipping_province='Metro Manila',
        shipping_postal_code='1100',
        subtotal=line_total,
        shipping_total=Decimal('0.00'),
        savings_total=Decimal('0.00'),
        tax_total=Decimal('0.00'),
        grand_total=line_total,
    )
    seller_order = SellerOrder.objects.create(
        order=order,
        store=product.store,
        store_name=product.store.name,
        status=status,
        subtotal=line_total,
        shipping_fee=Decimal('0.00'),
        total=line_total,
    )
    item = OrderItem.objects.create(
        seller_order=seller_order,
        product=product,
        variant=variant,
        product_title=product.title,
        product_slug=product.slug,
        sku=f'GEN-{_order_counter:06d}',
        unit_price=variant.price,
        quantity=quantity,
        line_total=line_total,
    )
    if days_ago:
        OrderItem.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago)
        )
    return item


def _titles(response):
    return [item['title'] for item in response.json()['items']]


def _two_sellers_with_sales():
    """One long-selling product and one that only just started selling.

    The same pair answers both sales kinds with opposite leaders, which is
    the point: if trending and popular ever agree on *every* input, one of
    them has quietly stopped being what its name claims.
    """
    store = _store()
    evergreen = _product(store, 'Evergreen Seller')
    flash = _product(store, 'Flash In The Pan')
    _sell(evergreen, 40, days_ago=60)
    _sell(flash, 2, days_ago=1)
    return evergreen, flash


# --- Trending / popular (§18.3 "trending products", "popular products") -------


def test_trending_ranks_recent_sales_above_stale_ones(client):
    """Trending answers "what is moving *now*". Forty units two months ago
    is popular, not trending."""
    _two_sellers_with_sales()

    response = client.get(RECOMMENDATIONS, {'kind': 'trending'})

    assert response.status_code == 200
    assert response.json()['kind'] == 'trending'
    assert _titles(response)[0] == 'Flash In The Pan'


def test_popular_ranks_units_above_recency(client):
    """Popular answers "what has sold most", so a flash-in-the-pan launch
    must not overtake the long seller."""
    _two_sellers_with_sales()

    response = client.get(RECOMMENDATIONS, {'kind': 'popular'})

    assert response.status_code == 200
    assert _titles(response)[0] == 'Evergreen Seller'


def test_cancelled_orders_never_count_as_a_sale(client):
    """A cancelled or refunded order made nobody a best seller — the same
    exclusion list the seller dashboard uses (§12.1), so the product card
    and the seller's own numbers cannot disagree."""
    store = _store()
    returned = _product(store, 'Returned A Lot')
    bought = _product(store, 'Actually Bought')
    _sell(returned, 40, status='cancelled')
    _sell(bought, 2, status='placed')

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'popular'}))

    assert titles[0] == 'Actually Bought'


def test_sales_shelves_degrade_to_newest_when_nothing_has_sold(client):
    """The normal state of a young marketplace: no orders at all. The shelf
    must still be a shelf — an empty homepage is a failed homepage."""
    store = _store()
    _product(store, 'First Thing')
    _product(store, 'Second Thing')

    for kind in ('trending', 'popular'):
        response = client.get(RECOMMENDATIONS, {'kind': kind})
        assert response.status_code == 200
        assert response.json()['count'] == 2
        assert _titles(response) == ['Second Thing', 'First Thing']


def test_sales_shelves_never_surface_a_draft_despite_its_units(client):
    """The ranking is built from order rows, which is exactly why it needs
    the permission filter: 99 sold units must not buy a draft a listing."""
    store = _store()
    live = _product(store, 'Live Thing')
    draft = _product(store, 'Draft Thing', status=Product.Status.DRAFT)
    _sell(draft, 99)
    _sell(live, 1)

    for kind in ('trending', 'popular'):
        titles = _titles(client.get(RECOMMENDATIONS, {'kind': kind}))
        assert 'Draft Thing' not in titles


# --- Related (§18.3 "related products") --------------------------------------


def test_related_stays_inside_the_seeds_category(client):
    store = _store()
    baskets = Category.objects.create(name='Baskets')
    kitchen = Category.objects.create(name='Kitchen')

    seed = _product(store, 'Seed Basket', category=baskets)
    _product(store, 'Peer Basket', category=baskets, rating=4.5)
    _product(store, 'Unrelated Pan', category=kitchen)

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'related', 'seed': seed.slug}))

    # The seed never recommends itself, and — unlike a *ranking* — the shelf
    # is not padded with a stranger just to reach its limit.
    assert titles == ['Peer Basket']


def test_related_falls_back_to_brand_when_the_seed_has_no_category(client):
    """Filing is optional, so brand is the next honest neighbourhood."""
    store = _store()
    kawa = Brand.objects.create(name='Kawa')
    iba = Brand.objects.create(name='Iba Pa')

    seed = _product(store, 'Unfiled Seed', brand=kawa)
    _product(store, 'Unfiled Peer', brand=kawa)
    _product(store, 'Different Brand', brand=iba)

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'related', 'seed': seed.slug}))

    assert titles == ['Unfiled Peer']


def test_related_for_a_product_with_no_neighbourhood_falls_back_to_newest(client):
    store = _store()
    seed = _product(store, 'Totally Unfiled')
    _product(store, 'Also Unfiled')

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'related', 'seed': seed.slug}))

    assert titles == ['Also Unfiled']


def test_a_draft_cannot_be_used_as_a_seed(client):
    """404 rather than 200-with-nothing: recommending "products like this"
    would confirm to anyone who guessed the slug that the draft exists."""
    store = _store()
    draft = _product(store, 'Draft Seed', status=Product.Status.DRAFT)

    response = client.get(RECOMMENDATIONS, {'kind': 'related', 'seed': draft.slug})

    assert response.status_code == 404
    assert response.json()['error'] == 'not_found'


# --- Similar (§18.3 "similar products") --------------------------------------


def test_similar_ranks_shared_words_first_and_never_the_seed(client):
    """`similar` is the same `pg_trgm` machinery the typo rescue runs, so the
    closest text wins — not whichever product happened to be added last."""
    store = _store()
    seed = _product(store, 'Woven Banana Basket', description='Handwoven')
    _product(store, 'Banana Bowl')          # shares words with the seed
    _product(store, 'Steel Wok')            # created last, so "newest" would lead

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'similar', 'seed': seed.slug}))

    assert titles[0] == 'Banana Bowl'
    assert 'Woven Banana Basket' not in titles


def test_similar_never_pads_the_shelf_with_an_unrelated_product(client):
    """A shelf labelled "similar" that shows a stranger is worse than one
    that shows less — neighbourhood shelves stay short rather than padded."""
    store = _store()
    seed = _product(store, 'Woven Banana Basket')
    _product(store, 'Banana Bowl')
    _product(store, 'Titanium Laptop Stand Pro')

    titles = _titles(client.get(RECOMMENDATIONS, {'kind': 'similar', 'seed': seed.slug}))

    assert 'Titanium Laptop Stand Pro' not in titles


# --- Personalized (§18.3 "personalized recommendations foundation") -----------


def test_personalized_scopes_to_the_categories_the_shopper_viewed(client):
    """History travels with the request and only narrows the ranking — no
    account, no stored profile, nothing that could leak later."""
    store = _store()
    baskets = Category.objects.create(name='Baskets')
    kitchen = Category.objects.create(name='Kitchen')

    viewed = _product(store, 'Viewed Basket', category=baskets)
    _product(store, 'Basket Peer', category=baskets, rating=4.5)
    _product(store, 'Unrelated Pan', category=kitchen, rating=5)

    titles = _titles(
        client.get(RECOMMENDATIONS, {'kind': 'personalized', 'seen': viewed.slug})
    )

    # The viewed product itself is excluded: recommending what you are
    # already looking at is not a recommendation.
    assert titles == ['Basket Peer']


def test_personalized_never_echoes_back_the_seen_products(client):
    store = _store()
    baskets = Category.objects.create(name='Baskets')
    viewed = _product(store, 'Viewed Basket', category=baskets)
    _sell(viewed, 50)                      # the best seller in its category
    _product(store, 'Basket Peer', category=baskets)

    titles = _titles(
        client.get(RECOMMENDATIONS, {'kind': 'personalized', 'seen': viewed.slug})
    )

    assert 'Viewed Basket' not in titles


def test_personalized_ranks_the_scoped_products_by_popularity(client):
    store = _store()
    baskets = Category.objects.create(name='Baskets')
    viewed = _product(store, 'Viewed Basket', category=baskets)
    loved = _product(store, 'Loved Peer', category=baskets)
    _product(store, 'Quiet Peer', category=baskets)
    _sell(loved, 12)
    _sell(viewed, 99)

    titles = _titles(
        client.get(RECOMMENDATIONS, {'kind': 'personalized', 'seen': viewed.slug})
    )

    assert titles[0] == 'Loved Peer'


# --- Permission safety (§18.3 gate: "search remains permission-safe") --------


def test_no_kind_can_reach_a_draft_or_a_suspended_store(client):
    """§18.1's chokepoint still holds for every §18.3 ranking — including the
    kinds whose ranking is built from order rows, which is exactly where a
    leak would otherwise hide."""
    live = _store('Live Discovery Store')
    shared = Category.objects.create(name='Shared')
    seed = _product(live, 'Shared Seed', category=shared)
    _product(live, 'Shared Control', category=shared)

    draft = _product(live, 'Shared Draft', category=shared, status=Product.Status.DRAFT)
    suspended = _store('Suspended Discovery Store', status=Store.Status.SUSPENDED)
    stranded = _product(suspended, 'Shared Stranded', category=shared)

    # Give the non-sellable products sales too: a ranking sourced from order
    # rows must not be able to smuggle them back in.
    _sell(draft, 99)
    _sell(stranded, 99)

    forbidden = {'Shared Draft', 'Shared Stranded'}
    for params in (
        {'kind': 'trending'},
        {'kind': 'popular'},
        {'kind': 'related', 'seed': seed.slug},
        {'kind': 'similar', 'seed': seed.slug},
        {'kind': 'personalized', 'seen': seed.slug},
    ):
        titles = {item['title'] for item in
                  client.get(RECOMMENDATIONS, params).json()['items']}
        assert not (titles & forbidden), f'{params} leaked {titles & forbidden}'

    # Positive control: this is not passing merely because every shelf came
    # back empty — the reachable product really is recommended.
    related = {item['title'] for item in client.get(
        RECOMMENDATIONS, {'kind': 'related', 'seed': seed.slug}
    ).json()['items']}
    assert related == {'Shared Control'}


# --- Parameter validation (§8 envelope) --------------------------------------


def test_unknown_kind_is_rejected(client):
    response = client.get(RECOMMENDATIONS, {'kind': 'astrology'})

    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_parameter'


def test_a_kind_that_needs_a_subject_names_the_missing_one(client):
    for kind in ('related', 'similar', 'personalized'):
        response = client.get(RECOMMENDATIONS, {'kind': kind})
        assert response.status_code == 400, kind
        assert response.json()['error'] == 'missing_parameter'


def test_limit_is_bounded_server_side(client):
    for limit in ('0', 'abc', '999'):
        response = client.get(RECOMMENDATIONS, {'limit': limit})
        assert response.status_code == 400, limit
        assert response.json()['error'] == 'invalid_parameter'


def test_an_unknown_seed_is_a_404(client):
    response = client.get(RECOMMENDATIONS, {'kind': 'related', 'seed': 'nope'})

    assert response.status_code == 404
    assert response.json()['error'] == 'not_found'


# --- The "sold" figure a product card renders (§18.3 "popular") --------------


def test_product_detail_reports_real_units_sold(client):
    """The serializer used to answer 0 with a note that "order events arrive
    with Phase 8" — they arrived long ago, and a Popular shelf whose detail
    pages all say "0 sold" is a lie the shopper can see."""
    store = _store()
    lived = _product(store, 'Well Lived')
    untouched = _product(store, 'Untouched')
    _sell(lived, 3)
    _sell(lived, 4)

    assert client.get(f'{CATALOG}{lived.slug}/').json()['sold'] == 7
    assert client.get(f'{CATALOG}{untouched.slug}/').json()['sold'] == 0


def test_units_sold_ignores_cancelled_orders(client):
    store = _store()
    product = _product(store, 'Partly Returned')
    _sell(product, 9, status='cancelled')
    _sell(product, 2)

    assert client.get(f'{CATALOG}{product.slug}/').json()['sold'] == 2


# --- The new §18.3 sort keys -------------------------------------------------


def test_best_selling_and_trending_sorts_disagree_on_purpose(client):
    """Both count units over the same rows — the window is the only
    difference, so on this input they must disagree, or one of them has
    stopped being what its name claims."""
    _two_sellers_with_sales()

    best_selling = _titles(client.get(SEARCH, {'sort': 'best_selling'}))
    trending = _titles(client.get(SEARCH, {'sort': 'trending'}))

    assert best_selling[0] == 'Evergreen Seller'
    assert trending[0] == 'Flash In The Pan'


def test_a_sort_changes_the_order_but_never_the_result_set(client):
    """A sort is an ordering, not a filter: unsold products sort last, they
    do not disappear."""
    store = _store()
    _product(store, 'Never Sold')
    sold = _product(store, 'Sold Once')
    _sell(sold, 1)

    for sort in ('best_selling', 'trending'):
        body = client.get(SEARCH, {'sort': sort}).json()
        assert body['count'] == 2, sort
        titles = [item['title'] for item in body['items']]
        assert titles == ['Sold Once', 'Never Sold'], sort


def test_an_unknown_sort_is_still_rejected(client):
    response = client.get(SEARCH, {'sort': 'most_expensive'})

    assert response.status_code == 400
    assert response.json()['error'] == 'invalid_parameter'
