"""Catalog serializers — declared fields only (backend-api rule 2).

The public product shape mirrors the data-layer contract (id/title/price/
originalPrice/discount/rating/sold/stock/store/verified/isNew/category)
so the Phase 6 mock→API swap stays trivial. `rating` and `sold` stay at
their placeholders until orders/reviews exist (Phases 8/14).
"""
from rest_framework import serializers

from .models import Brand, Category, Inventory, Product, ProductImage, Variant
from . import services


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'parent', 'name', 'slug', 'description', 'position', 'is_active']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'position', 'created_at']


class InventorySerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = ['on_hand', 'reserved', 'available', 'low_stock_threshold', 'low_stock']

    def get_low_stock(self, obj):
        return obj.available <= obj.low_stock_threshold


class VariantSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)
    initial_stock = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=0,
        help_text='Sets the starting on-hand inventory for a new variant.',
    )

    class Meta:
        model = Variant
        fields = [
            'id', 'sku', 'name', 'price', 'is_default', 'is_active',
            'attributes', 'inventory', 'initial_stock',
        ]
        read_only_fields = ['id', 'sku', 'is_default', 'is_active', 'inventory']


class SellerVariantSerializer(serializers.ModelSerializer):
    """Seller variant edits (§12.2) — price/name/active; stock stays out.

    Stock changes run through the stock endpoints so every change is
    transactional and appended to the movement history (§12.3).
    """

    inventory = InventorySerializer(read_only=True)

    class Meta:
        model = Variant
        fields = [
            'id', 'sku', 'name', 'price', 'is_default', 'is_active',
            'attributes', 'inventory',
        ]
        read_only_fields = ['id', 'sku', 'is_default', 'inventory']


class SellerProductSerializer(serializers.ModelSerializer):
    """Seller-facing shape — full lifecycle control on their own products."""

    variants = VariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    display_price = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'status',
            'rejection_reason', 'base_price', 'compare_at_price',
            'display_price', 'discount_percent', 'attributes',
            'category', 'brand', 'variants', 'images',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'status', 'rejection_reason',
            'created_at', 'updated_at',
        ]

    def get_display_price(self, obj):
        return services.resolve_display_price(obj)

    def get_discount_percent(self, obj):
        return services.compute_discount_percent(
            services.resolve_display_price(obj), obj.compare_at_price
        )


class PublicProductSerializer(serializers.ModelSerializer):
    """Catalog/browse shape — published products from active stores only."""

    store_slug = serializers.SlugField(source='store.slug', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_verified = serializers.BooleanField(source='store.user.is_seller', read_only=True)
    primary_image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = VariantSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()
    originalPrice = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    sold = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    isNew = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    category_slug = serializers.SlugField(source='category.slug', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'slug', 'title', 'description',
            'price', 'originalPrice', 'discount', 'rating', 'sold',
            'stock', 'isNew', 'category', 'category_slug',
            'store_name', 'store_slug', 'store_verified',
            'primary_image', 'images', 'variants', 'created_at',
        ]

    # --- server-resolved display values (§6 v1.3) ---
    # Money is Decimal in the DB (C6); the JSON display shape is numeric —
    # the frontend never does math on these, it only renders them.

    def get_price(self, obj):
        return float(services.resolve_display_price(obj))

    def get_originalPrice(self, obj):
        price = services.resolve_display_price(obj)
        if obj.compare_at_price and obj.compare_at_price > price:
            return float(obj.compare_at_price)
        return None

    def get_discount(self, obj):
        return self.get_discount_percent(obj)

    def get_discount_percent(self, obj):
        return services.compute_discount_percent(
            services.resolve_display_price(obj), obj.compare_at_price
        )

    def get_rating(self, obj):
        return None  # reviews arrive with Phase 14

    def get_sold(self, obj):
        return 0  # order events arrive with Phase 8

    def get_stock(self, obj):
        total = 0
        for variant in obj.variants.all():
            inventory = getattr(variant, 'inventory', None)
            if inventory is not None and variant.is_active:
                total += inventory.available
        return total

    def get_isNew(self, obj):
        # Seed data carries the explicit flag (contract parity with the
        # frontend mock); live products derive it from recency (§6 v1.3).
        flag = (obj.attributes or {}).get('isNew')
        if flag is not None:
            return bool(flag)
        from django.utils import timezone
        import datetime
        return obj.created_at >= timezone.now() - datetime.timedelta(days=14)

    def get_category(self, obj):
        return obj.category.name if obj.category else None

    def get_primary_image(self, obj):
        image = obj.images.order_by('position', 'created_at').first()
        request = self.context.get('request')
        if image:
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


# --- Staff shapes (13.4 — catalog console & taxonomy management) -----------

class StaffProductListSerializer(serializers.ModelSerializer):
    """Staff console row: store identity + status + counts, no payloads.

    Light on purpose (marketplace-admin rule 5) — variants/images open in
    the seller too, so the console only carries what the table renders.
    """

    display_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.SlugField(source='store.slug', read_only=True)
    store_owner_email = serializers.EmailField(
        source='store.user.email', read_only=True
    )
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    variant_count = serializers.IntegerField(read_only=True)
    image_count = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'status', 'rejection_reason',
            'base_price', 'compare_at_price', 'display_price',
            'store_name', 'store_slug', 'store_owner_email',
            'category_name', 'category_slug', 'brand_name',
            'variant_count', 'image_count', 'primary_image',
            'created_at', 'updated_at',
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_category_slug(self, obj):
        return obj.category.slug if obj.category else None

    def get_brand_name(self, obj):
        return obj.brand.name if obj.brand else None

    def get_primary_image(self, obj):
        image = next(iter(obj.images.all()), None)
        if image is None:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class StaffProductSerializer(SellerProductSerializer):
    """Full seller shape + store identity — staff detail inspection."""

    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.SlugField(source='store.slug', read_only=True)
    store_owner_email = serializers.EmailField(
        source='store.user.email', read_only=True
    )

    class Meta(SellerProductSerializer.Meta):
        fields = SellerProductSerializer.Meta.fields + [
            'store_name', 'store_slug', 'store_owner_email',
        ]


class StaffCategorySerializer(serializers.ModelSerializer):
    """Taxonomy management row — slug, ids, and counts stay read-only."""

    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'parent', 'name', 'slug', 'description', 'position',
            'is_active', 'product_count',
        ]
        read_only_fields = ['id', 'slug', 'product_count']

    def get_product_count(self, obj):
        annotated = getattr(obj, 'product_count', None)
        return annotated if annotated is not None else obj.products.count()


class StaffBrandSerializer(serializers.ModelSerializer):
    """Taxonomy management row — name is unique, slug stays read-only."""

    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'product_count']
        read_only_fields = ['id', 'slug', 'product_count']

    def get_product_count(self, obj):
        annotated = getattr(obj, 'product_count', None)
        return annotated if annotated is not None else obj.products.count()