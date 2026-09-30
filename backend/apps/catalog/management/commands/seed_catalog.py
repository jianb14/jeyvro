"""Seed catalog data (Phase 5.6) — mirrors the frontend contract shapes.

Run: python manage.py seed_catalog
Creates categories/brands/stores (idempotent) and the 8 mock products
with variants + inventory so the Phase 6 accessor swap is shape-identical.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog import services
from apps.catalog.models import Brand, Category, Product, Variant
from apps.stores.models import Store

User = get_user_model()

STORES = [
    ('Kalinga Crafts', 'kalinga@example.com', 'Handwoven crafts from the Cordilleras.'),
    ('Batangas Brew Co.', 'batangas@example.com', 'Single-origin coffee from Batangas.'),
    ('Mugna Pottery', 'mugna@example.com', 'Minimal stoneware, hand-thrown.'),
    ('Bicol Weavers', 'bicol@example.com', 'Abaca bags and loom-woven textiles.'),
    ('Cebu Delights', 'cebu@example.com', 'Dried mangoes and Cebuano treats.'),
    ('Ilocos Weavers', 'ilocos@example.com', 'Inabel blankets and home textiles.'),
    ('Davao Cacao House', 'davao@example.com', 'Tablea and single-origin cacao.'),
    ('Kadaugan Gadgets', 'kadaugan@example.com', 'Everyday tech, honestly priced.'),
    ('Sampaguita Beauty', 'sampaguita@example.com', 'Small-batch skincare from the Philippines.'),
]

# (name, position) — position drives the storefront rail order (Category.Meta
# orders by ['position', 'name']). Lower sorts first; the numbers are spaced so
# staff can slot a new category between two existing ones at /staff/taxonomy
# without renumbering the rest. The live category tree stays a database fact
# that staff edit — the frontend never hardcodes this list (catalog rule 7).
CATEGORIES = [
    ('Fashion', 10),
    ('Electronics', 20),
    ('Home & Living', 30),
    ('Food', 40),
    ('Beauty', 50),
    ('Accessories', 60),
]

BRANDS = [
    'Kalinga Crafts', 'Batangas Brew', 'Mugna', 'Bicol Weavers',
    'Cebu Delights', 'Ilocos Weavers', 'Davao Cacao', 'Kadaugan',
    'Sampaguita',
]

# (store, category, brand, title, base_price, compare_at_price, stock,
#  is_new, description) — mirrors frontend/src/data/products.js exactly.
PRODUCTS = [
    ('Kalinga Crafts', 'Home & Living', 'Kalinga Crafts',
     'Handwoven Bamboo Storage Basket - Large', '349.00', '499.00', 24, True,
     'Handwoven bamboo storage basket, large. Woven by Kalinga artisans.'),
    ('Batangas Brew Co.', 'Food', 'Batangas Brew',
     'Organic Barako Coffee Beans 500g', '425.00', None, 8, False,
     'Single-origin Barako beans, medium roast, 500g.'),
    ('Mugna Pottery', 'Home & Living', 'Mugna',
     'Minimal Ceramic Dinner Plates (Set of 4)', '899.00', '1200.00', 0, False,
     'Set of 4 hand-thrown stoneware plates, matte glaze.'),
    ('Bicol Weavers', 'Fashion', 'Bicol Weavers',
     'Abaca Tote Bag - Natural Dye', '550.00', None, 15, True,
     'Abaca tote with natural dye, roomy and hardwearing.'),
    ('Cebu Delights', 'Food', 'Cebu Delights',
     'Air-dried Mango 200g Pack of 3', '380.00', '450.00', 42, False,
     'Air-dried Cebu mangoes, three 200g packs.'),
    ('Kalinga Crafts', 'Home & Living', 'Kalinga Crafts',
     'Capiz Shell Wall Decor', '1250.00', None, 5, False,
     'Capiz shell wall decor, hand-assembled.'),
    ('Ilocos Weavers', 'Home & Living', 'Ilocos Weavers',
     'Inabel Woven Throw Blanket', '1450.00', '1899.00', 12, True,
     'Traditional inabel weave, cotton throw blanket.'),
    ('Davao Cacao House', 'Food', 'Davao Cacao',
     'Tsokolate Tablea (Pack of 12)', '280.00', None, 30, False,
     'Tablea tablets for hot tsokolate, pack of 12.'),
    # The rows below give every seeded category at least one product, so the
    # storefront category cards always have a real photo to show. A category
    # with no products renders the branded fallback panel instead.
    ('Kadaugan Gadgets', 'Electronics', 'Kadaugan',
     'Wireless Earbuds with Charging Case', '1290.00', '1690.00', 26, True,
     'True-wireless earbuds, 24h total playback, USB-C case.'),
    ('Kadaugan Gadgets', 'Electronics', 'Kadaugan',
     'Compact Bluetooth Speaker', '890.00', None, 18, False,
     'Pocket-sized speaker, 12h playtime, water-resistant.'),
    ('Kadaugan Gadgets', 'Accessories', 'Kadaugan',
     'Braided USB-C Charging Cable (2m)', '190.00', '260.00', 60, False,
     'Two-metre braided cable, 60W fast charge.'),
    ('Sampaguita Beauty', 'Beauty', 'Sampaguita',
     'Cold-Pressed Virgin Coconut Oil 100ml', '340.00', None, 22, True,
     'Unrefined coconut oil, cold-pressed and unperfumed.'),
    ('Sampaguita Beauty', 'Beauty', 'Sampaguita',
     'Gentle Castile Soap Bar', '180.00', '230.00', 40, False,
     'Olive-oil soap bar, fragrance-free, handmade.'),
    ('Bicol Weavers', 'Accessories', 'Bicol Weavers',
     'Woven Straw Sun Hat', '420.00', None, 14, False,
     'Handwoven straw hat with an adjustable band.'),
    ('Ilocos Weavers', 'Fashion', 'Ilocos Weavers',
     'Inabel Woven Sundress', '1650.00', '2100.00', 7, True,
     'Inabel cotton sundress, handwoven in Ilocos.'),
]


class Command(BaseCommand):
    help = 'Seed categories, brands, stores, products, variants, inventory (Phase 5.6).'

    def handle(self, *args, **options):
        with transaction.atomic():
            # get_or_create keyed on name: re-running the seed is idempotent and
            # never renames, reorders, or removes a row staff has since edited.
            categories = {
                name: Category.objects.get_or_create(
                    name=name, defaults={'position': position}
                )[0]
                for name, position in CATEGORIES
            }
            brands = {
                name: Brand.objects.get_or_create(name=name)[0]
                for name in BRANDS
            }
            stores = {}
            for store_name, email, description in STORES:
                user = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': store_name.split()[0],
                        'last_name': 'Seller',
                        'is_seller': True,
                    },
                )[0]
                if not user.is_seller:
                    user.is_seller = True
                    user.save(update_fields=['is_seller', 'updated_at'])
                store = Store.objects.filter(user=user).first()
                if store is None:
                    store = Store.objects.create(
                        user=user,
                        name=store_name,
                        description=description,
                        contact_email=email,
                        status=Store.Status.ACTIVE,
                    )
                stores[store_name] = store

            created = 0
            for row in PRODUCTS:
                (store_name, category_name, brand_name, title,
                 base_price, compare_at_price, stock, is_new, description) = row
                if Product.objects.filter(title=title).exists():
                    continue
                product = Product.objects.create(
                    store=stores[store_name],
                    category=categories[category_name],
                    brand=brands[brand_name],
                    title=title,
                    description=description,
                    base_price=Decimal(base_price),
                    compare_at_price=(
                        Decimal(compare_at_price) if compare_at_price else None
                    ),
                    status=Product.Status.PUBLISHED,
                    attributes={'isNew': is_new},
                )
                variant = Variant.objects.create(
                    product=product,
                    name='Default',
                    price=Decimal(base_price),
                    is_default=True,
                )
                services.ensure_inventory(
                    variant,
                    initial_on_hand=stock,
                    note='seed data',
                )
                created += 1

        self.stdout.write(
            f'Seeded: {len(categories)} categories, {len(brands)} brands, '
            f'{len(stores)} stores, {created} new products '
            f'({Product.objects.count()} total).'
        )
