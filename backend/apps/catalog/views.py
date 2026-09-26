"""Catalog API (Phase 5) — thin views: parse → validate → service → serialize.

Public browse runs server-side search/filter/sort with the {count, items}
envelope (marketplace-catalog rule 3); seller endpoints are store-scoped
(rule 6); staff review is audit-logged; image upload is validated (§8/§10).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, ExpressionWrapper, F, FloatField, Min, Q
from django.db.models.functions import Coalesce, NullIf
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.common.pagination import CountItemsPagination
from apps.stores.models import Store

from . import services
from .models import Brand, Category, Product, ProductImage, Variant
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductImageSerializer,
    PublicProductSerializer,
    SellerProductSerializer,
    SellerVariantSerializer,
    StaffBrandSerializer,
    StaffCategorySerializer,
    StaffProductListSerializer,
    StaffProductSerializer,
    VariantSerializer,
)

SORT_MAP = {
    'newest': '-created_at',
    'price': 'display_price',
    '-price': '-display_price',
    'title': 'title',
}


def get_seller_store(request):
    """The requesting seller's store — 404 when they have none (scoping)."""
    return get_object_or_404(Store, user=request.user)


class PublicProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalog browse — published products from active stores only.

    Detail lookup is by slug (public-facing identifier, CONVENTIONS.md).
    """

    serializer_class = PublicProductSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = Product.objects.filter(
            status=Product.Status.PUBLISHED,
            store__status=Store.Status.ACTIVE,
        ).select_related('store', 'category').prefetch_related(
            'variants__inventory', 'images'
        )
        # Display price + real discount as SQL annotations so price filters
        # and sorts hit the same server-resolved values the serializer
        # returns (§6 v1.3). discount_score is null when there is no
        # reference price — those sort last under sort=discount (Phase 6
        # customer discovery: Trending / deals ordering).
        display_price = Coalesce(
            Min('variants__price', filter=Q(variants__is_active=True)),
            'base_price',
        )
        queryset = queryset.annotate(
            display_price=display_price,
            discount_score=ExpressionWrapper(
                (F('compare_at_price') - display_price)
                / NullIf(F('compare_at_price'), Decimal('0')),
                output_field=FloatField(),
            ),
        )
        params = self.request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(title__icontains=needle) | Q(description__icontains=needle)
            )
        category = params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        store = params.get('store')
        if store:
            queryset = queryset.filter(store__slug=store)
        min_price = params.get('min_price')
        if min_price:
            queryset = queryset.filter(display_price__gte=min_price)
        max_price = params.get('max_price')
        if max_price:
            queryset = queryset.filter(display_price__lte=max_price)
        sort = params.get('sort')
        if sort == 'discount':
            # Biggest real discount first; products with no reference price
            # sort last (never a fake "deal" at the top).
            queryset = queryset.order_by(
                F('discount_score').desc(nulls_last=True), '-created_at'
            )
        elif sort in SORT_MAP:
            queryset = queryset.order_by(SORT_MAP[sort], '-created_at')
        else:
            # Stable default order — pagination must never be ambiguous.
            queryset = queryset.order_by('-created_at')
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Single product — 404 keeps the JSON error envelope (§8)."""
        instance = self.get_object()
        return Response(self.get_serializer(instance).data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Category tree source — the frontend never hardcodes categories."""

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


# --- Seller endpoints (store-scoped: only their own products) ---

class SellerProductViewSet(viewsets.ModelViewSet):
    """Seller product management — scoping enforced by queryset + service.

    Lifecycle: sellers create drafts and move them through
    submit/unpublish/archive via dedicated actions; status edits by
    payload are ignored (read-only), all transitions run in services.
    """

    serializer_class = SellerProductSerializer
    permission_classes = [IsAuthenticated, IsSeller]

    def get_queryset(self):
        return (
            Product.objects.filter(store__user=self.request.user)
            .select_related('category', 'brand')
            .prefetch_related('variants__inventory', 'images')
        )

    def get_store(self):
        return get_seller_store(self.request)

    def create(self, request, *args, **kwargs):
        """Creates the product via the service and serializes the INSTANCE
        (validated_data dicts are never echoed back)."""
        serializer = SellerProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = services.create_product(
            request.user, store=self.get_store(), **serializer.validated_data
        )
        return Response(
            self.get_serializer(product).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """PATCH/PUT — editable fields only (§12.2).

        Status transitions never ride along: the serializer keeps status
        read-only and edits run through the service (which also blocks
        archived products).
        """
        product = self.get_object()
        serializer = SellerProductSerializer(
            product, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            product = services.update_product(
                request.user, product.pk, **serializer.validated_data
            )
        except (ValueError, PermissionError) as exc:
            return Response(
                {'error': 'not_editable', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        product = self.get_queryset().get(pk=product.pk)
        return Response(self.get_serializer(product).data)

    def destroy(self, request, *args, **kwargs):
        """DELETE — hard-delete when never ordered, archive otherwise (§12.2).

        Both answers are success: the seller asked to remove the product
        from their store, and order history (PROTECT) decides which action
        actually happens.
        """
        product = self.get_object()
        action, _ = services.delete_product(request.user, product.pk)
        if action == 'archived':
            product = self.get_queryset().get(pk=kwargs['pk'])
            return Response({
                'action': 'archived',
                'detail': 'Product archived — past orders keep their history.',
                'product': self.get_serializer(product).data,
            })
        return Response({
            'action': 'deleted',
            'detail': 'Product deleted.',
        })

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """Bulk lifecycle actions over the seller's own products (§12.2).

        Each id is attempted independently and reported per id — one bad
        row never blocks the batch (bulk operations where appropriate).
        """
        action_name = request.data.get('action')
        transitions = {
            'submit': services.submit_for_review,
            'unpublish': services.unpublish_product,
            'archive': services.archive_product,
        }
        if action_name not in transitions:
            return Response(
                {'error': 'invalid_action',
                 'detail': "action must be 'submit', 'unpublish', or 'archive'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ids = request.data.get('ids')
        if not isinstance(ids, list) or not ids:
            return Response(
                {'error': 'ids_required',
                 'detail': 'Attach a non-empty list of product ids.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        transition = transitions[action_name]
        results = []
        for product_id in ids[:100]:
            try:
                transition(request.user, int(product_id))
            except Product.DoesNotExist:
                results.append({
                    'id': product_id, 'ok': False,
                    'detail': 'Product not found in your store.',
                })
            except (TypeError, ValueError) as exc:
                results.append({'id': product_id, 'ok': False, 'detail': str(exc)})
            else:
                results.append({'id': product_id, 'ok': True})
        return Response({'action': action_name, 'results': results})

    def _transition(self, request, pk, transition):
        try:
            product = transition(request.user, int(pk))
        except Product.DoesNotExist:
            # Another store's product (or nonexistent) — same answer, no
            # existence leak (§10): 404 for everything outside their scope.
            return Response(
                {'error': 'not_found',
                 'detail': 'Product not found in your store.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(product).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        return self._transition(request, pk, services.submit_for_review)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        return self._transition(request, pk, services.unpublish_product)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        return self._transition(request, pk, services.archive_product)

    @action(detail=True, methods=['post'])
    def images(self, request, pk=None):
        """Validated image upload for the seller's product (§8 media)."""
        product = self.get_object()
        if product.status == Product.Status.ARCHIVED:
            return Response(
                {'error': 'not_editable',
                 'detail': 'Archived products cannot receive images.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        upload = request.FILES.get('image')
        if upload is None:
            return Response(
                {'error': 'image_required', 'detail': 'Attach an image file.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.validate_image_file(upload)
        except ValidationError as exc:
            return Response(
                {'error': 'invalid_image', 'detail': exc.message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        image = ProductImage.objects.create(
            product=product,
            image=upload,
            alt_text=str(request.data.get('alt_text', ''))[:180],
            position=int(request.data.get('position', 0) or 0),
        )
        return Response(
            ProductImageSerializer(image).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'])
    def remove_image(self, request, pk=None):
        image_id = request.data.get('image_id') or request.query_params.get('image_id')
        image = get_object_or_404(
            ProductImage, pk=image_id, product__store__user=request.user
        )
        image.image.delete(save=False)
        image.delete()
        return Response({'detail': 'image removed'})

    @action(detail=True, methods=['post'])
    def variants(self, request, pk=None):
        """Adds a variant (+ its inventory row) to the seller's product."""
        product = self.get_object()
        if product.status == Product.Status.ARCHIVED:
            return Response(
                {'error': 'not_editable',
                 'detail': 'Archived products cannot receive variants.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = VariantSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        initial = data.pop('initial_stock', None)
        with transaction.atomic():
            variant = Variant.objects.create(
                product=product,
                price=data['price'],
                name=data.get('name') or '',
                is_default=not product.variants.exists(),
                attributes=data.get('attributes') or {},
            )
            services.ensure_inventory(
                variant,
                initial_on_hand=initial or 0,
                actor=request.user,
                note='variant created',
            )
        return Response(
            VariantSerializer(variant).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True, methods=['patch', 'delete'],
        url_path='variants/(?P<variant_pk>[0-9]+)',
    )
    def variant_detail(self, request, pk=None, variant_pk=None):
        """PATCH/DELETE one variant of the seller's own product (§12.2).

        Delete resolves to deactivation when the variant appears in order
        history (OrderItem.variant is PROTECT) — the action field in the
        response says which happened.
        """
        product = self.get_object()  # 404 outside the seller's store (§10)
        variant = get_object_or_404(Variant, pk=variant_pk, product=product)
        if request.method == 'DELETE':
            action, variant = services.delete_variant(
                request.user, product.pk, variant.pk
            )
            if action == 'deleted':
                return Response({'action': 'deleted',
                                 'detail': 'Variant deleted.'})
            return Response({
                'action': 'deactivated',
                'detail': 'Variant deactivated — past orders keep their history.',
                'variant': SellerVariantSerializer(variant).data,
            })
        payload = SellerVariantSerializer(
            variant, data=request.data, partial=True
        )
        payload.is_valid(raise_exception=True)
        try:
            variant = services.update_variant(
                request.user, product.pk, variant.pk, **payload.validated_data
            )
        except (ValueError, PermissionError) as exc:
            return Response(
                {'error': 'not_editable', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SellerVariantSerializer(variant).data)


class SellerStockView(APIView):
    """GET/POST /my/stock — inventory list, adjustments, movement history.

    - GET  ?variant_id=…  → that variant's movement history (5.4)
    - GET  (no params)    → the store's inventory rows ({count, items}),
      searchable, `low_stock=1` narrows to at/below-threshold rows (§12.3)
    - POST {variant_id, delta, note}  → row-locked adjustment + movement
    - POST {variant_id, threshold}    → low-stock alert level (§12.3)
    """

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request):
        store = get_seller_store(request)
        variant_id = request.data.get('variant_id')
        variant = get_object_or_404(
            Variant, pk=variant_id, product__store=store
        )
        if 'threshold' in request.data:
            try:
                threshold = int(request.data['threshold'])
            except (TypeError, ValueError):
                return Response(
                    {'error': 'invalid_threshold',
                     'detail': 'threshold must be a non-negative integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                services.set_low_stock_threshold(
                    request.user, variant, threshold=threshold
                )
            except ValueError as exc:
                return Response(
                    {'error': 'invalid_threshold', 'detail': str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(SellerVariantSerializer(variant).data)
        try:
            delta = int(request.data.get('delta', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'invalid_delta', 'detail': 'delta must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        note = str(request.data.get('note', ''))[:255]
        try:
            services.adjust_stock(
                request.user,
                variant,
                delta=delta,
                reason=services.StockMovement.Reason.RESTOCK if delta > 0
                else services.StockMovement.Reason.ADJUSTMENT,
                note=note,
            )
        except ValueError as exc:
            return Response(
                {'error': 'stock_adjustment_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant.refresh_from_db()
        return Response(SellerVariantSerializer(variant).data)

    def get(self, request):
        """Inventory list (§12.3) or one variant's movement history (5.4)."""
        store = get_seller_store(request)
        variant_id = request.query_params.get('variant_id')
        if variant_id:
            variant = get_object_or_404(
                Variant, pk=variant_id, product__store=store
            )
            movements = variant.stock_movements.all()[:50]
            data = [
                {
                    'id': movement.id,
                    'reason': movement.reason,
                    'quantity_delta': movement.quantity_delta,
                    'resulting_on_hand': movement.resulting_on_hand,
                    'note': movement.note,
                    'created_at': movement.created_at,
                }
                for movement in movements
            ]
            return Response({'count': len(data), 'items': data})

        queryset = (
            Variant.objects.filter(product__store=store)
            .select_related('product', 'inventory')
            .order_by('product__title', 'price')
        )
        needle = request.query_params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(product__title__icontains=needle)
                | Q(sku__icontains=needle)
                | Q(name__icontains=needle)
            )
        if request.query_params.get('low_stock') in ('1', 'true', 'True'):
            # available (on_hand − reserved) at or below the threshold
            queryset = queryset.filter(
                inventory__on_hand__lte=(
                    F('inventory__low_stock_threshold') + F('inventory__reserved')
                )
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [self._inventory_row(variant) for variant in page]
        )

    @staticmethod
    def _inventory_row(variant):
        """One inventory row — variant identity + live stock numbers."""
        inventory = getattr(variant, 'inventory', None)
        return {
            'variant_id': variant.id,
            'product_id': variant.product_id,
            'product_title': variant.product.title,
            'product_slug': variant.product.slug,
            'product_status': variant.product.status,
            'sku': variant.sku,
            'name': variant.name,
            'price': float(variant.price),
            'is_active': variant.is_active,
            'inventory': (
                {
                    'on_hand': inventory.on_hand,
                    'reserved': inventory.reserved,
                    'available': inventory.available,
                    'low_stock_threshold': inventory.low_stock_threshold,
                    'low_stock': inventory.available <= inventory.low_stock_threshold,
                }
                if inventory is not None
                else None
            ),
        }


class StaffProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff product console (13.4) — every status, server-filtered.

    Moderator/administrator only (§4 matrix). The list shape is light
    (store identity + status + counts); retrieve returns the full seller
    shape so staff can inspect variants/images without leaving the console.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        display_price = Coalesce(
            Min('variants__price', filter=Q(variants__is_active=True)),
            'base_price',
        )
        queryset = (
            Product.objects.select_related(
                'store', 'store__user', 'category', 'brand'
            )
            .annotate(
                display_price=display_price,
                variant_count=Count('variants', distinct=True),
                image_count=Count('images', distinct=True),
            )
            .prefetch_related('variants__inventory', 'images')
            .order_by('-created_at')
        )
        params = self.request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(title__icontains=needle)
                | Q(description__icontains=needle)
                | Q(slug__icontains=needle)
                | Q(store__name__icontains=needle)
                | Q(store__user__email__icontains=needle)
            )
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        category = params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        store = params.get('store')
        if store:
            if store.isdigit():
                queryset = queryset.filter(store_id=store)
            else:
                queryset = queryset.filter(store__slug=store)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return StaffProductListSerializer
        return StaffProductSerializer


class StaffProductReviewActionView(APIView):
    """POST /api/v1/catalog/admin/products/<pk>/review — publish/reject.

    Completes the Phase 5 review loop; moderator/administrator only (§4).
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        decision = request.data.get('decision')
        reason = request.data.get('reason', '')
        try:
            product = services.review_product(
                request.user, pk, decision=decision, reason=reason
            )
        except ValueError as exc:
            return Response(
                {'error': 'review_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SellerProductSerializer(product).data)


class StaffProductUnpublishView(APIView):
    """POST /api/v1/catalog/admin/products/<pk>/unpublish — takedown.

    Reason required; the seller sees it on their product and the decision
    is audit-logged (moderator/administrator only, §4).
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        reason = request.data.get('reason', '')
        try:
            services.staff_unpublish_product(request.user, product, reason=reason)
        except ValueError as exc:
            return Response(
                {'error': 'unpublish_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StaffProductSerializer(product).data)


class StaffCategoryViewSet(viewsets.ModelViewSet):
    """Category management (13.4) — operations/administrator (§4 matrix).

    Reads are {count, items}; writes run through the audited catalog
    services (thin views, §13) so cycles, non-empty deletes, and every
    create/update/delete are enforced and logged server-side.
    """

    serializer_class = StaffCategorySerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['operations', 'administrator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        queryset = (
            Category.objects.select_related('parent')
            .annotate(product_count=Count('products'))
            .order_by('position', 'name')
        )
        needle = self.request.query_params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(name__icontains=needle) | Q(slug__icontains=needle)
            )
        return queryset

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.create_category(
                request.user, **serializer.validated_data
            )
        except ValueError as exc:
            return Response(
                {'error': 'create_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(category).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(
            category, data=request.data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        try:
            category = services.update_category(
                request.user, category, changes=serializer.validated_data
            )
        except ValueError as exc:
            return Response(
                {'error': 'update_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(category).data)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        try:
            services.delete_category(request.user, category)
        except ValueError as exc:
            return Response(
                {'error': 'delete_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffBrandViewSet(viewsets.ModelViewSet):
    """Brand management (13.4) — operations/administrator (§4 matrix).

    Deleting a brand only removes the label (products detach via SET_NULL);
    every write is audit-logged through the catalog services.
    """

    serializer_class = StaffBrandSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['operations', 'administrator']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        queryset = Brand.objects.annotate(
            product_count=Count('products')
        ).order_by('name')
        needle = self.request.query_params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(name__icontains=needle) | Q(slug__icontains=needle)
            )
        return queryset

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            brand = services.create_brand(request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response(
                {'error': 'create_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.get_serializer(brand).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        brand = self.get_object()
        serializer = self.get_serializer(
            brand, data=request.data, partial=kwargs.pop('partial', False)
        )
        serializer.is_valid(raise_exception=True)
        try:
            brand = services.update_brand(
                request.user, brand, **serializer.validated_data
            )
        except ValueError as exc:
            return Response(
                {'error': 'update_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.get_serializer(brand).data)

    def destroy(self, request, *args, **kwargs):
        brand = self.get_object()
        try:
            services.delete_brand(request.user, brand)
        except ValueError as exc:
            return Response(
                {'error': 'delete_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)