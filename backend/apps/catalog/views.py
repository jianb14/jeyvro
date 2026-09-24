"""Catalog API (Phase 5) — thin views: parse → validate → service → serialize.

Public browse runs server-side search/filter/sort with the {count, items}
envelope (marketplace-catalog rule 3); seller endpoints are store-scoped
(rule 6); staff review is audit-logged; image upload is validated (§8/§10).
"""
from django.core.exceptions import ValidationError
from django.db.models import Min, Q
from django.db.models.functions import Coalesce
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.stores.models import Store

from . import services
from .models import Brand, Category, Product, ProductImage, Variant
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductImageSerializer,
    PublicProductSerializer,
    SellerProductSerializer,
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
        # Display price as a SQL annotation so price filters/sorts hit the
        # same server-resolved value the serializer returns (§6 v1.3).
        queryset = queryset.annotate(
            display_price=Coalesce(
                Min('variants__price', filter=Q(variants__is_active=True)),
                'base_price',
            )
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
        if sort in SORT_MAP:
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


class SellerStockView(APIView):
    """GET/POST /my/stock — seller stock adjust + movement history."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request):
        store = get_seller_store(request)
        variant_id = request.data.get('variant_id')
        try:
            delta = int(request.data.get('delta', 0))
        except (TypeError, ValueError):
            return Response(
                {'error': 'invalid_delta', 'detail': 'delta must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        variant = get_object_or_404(
            Variant, pk=variant_id, product__store=store
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
        return Response(VariantSerializer(variant).data)

    def get(self, request):
        """Movement history for a variant (5.4 stock movement history)."""
        store = get_seller_store(request)
        variant_id = request.query_params.get('variant_id')
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


class StaffProductReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff pending-review queue — group-based access (§4)."""

    queryset = (
        Product.objects.filter(status=Product.Status.PENDING_REVIEW)
        .select_related('store', 'category', 'brand')
        .prefetch_related('variants', 'images')
    )
    serializer_class = SellerProductSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]


class StaffProductReviewActionView(APIView):
    permission_classes = [IsAuthenticated, InStaffGroup]

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