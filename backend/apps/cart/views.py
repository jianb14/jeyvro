"""Cart & wishlist API (Phase 7) — thin views: validate → service → serialize.

Guest carts are session-keyed server carts (§6): every endpoint resolves
the requester's cart (user or session) through the service, so ownership
is never trusted from the client. Every mutation returns the freshly
recomputed cart payload — the client never patches local state by hand.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product, Variant
from apps.common.pagination import CountItemsPagination
from apps.stores.models import Store

from . import serializers, services
from .models import CartItem, WishlistItem


def _rejected(exc):
    return Response(
        {'error': 'cart_item_rejected', 'detail': str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


class CartView(APIView):
    """GET /api/v1/cart/ · DELETE /api/v1/cart/ (clear, keeps the cart)."""

    permission_classes = [AllowAny]

    def get(self, request):
        cart = services.get_or_create_cart(request)
        return Response(serializers.build_cart_payload(cart, request))

    def delete(self, request):
        cart = services.get_or_create_cart(request)
        services.clear_cart(cart)
        return Response(serializers.build_cart_payload(cart, request))


class CartItemsView(APIView):
    """POST /api/v1/cart/items — add a variant (increments an existing line)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = serializers.AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = get_object_or_404(
            Variant.objects.select_related(
                'product', 'product__store', 'inventory'
            ),
            pk=serializer.validated_data['variant_id'],
        )
        cart = services.get_or_create_cart(request)
        try:
            services.add_item(cart, variant, serializer.validated_data['quantity'])
        except ValueError as exc:
            return _rejected(exc)
        return Response(serializers.build_cart_payload(cart, request))


class CartItemDetailView(APIView):
    """PATCH (set quantity) · DELETE (remove) /api/v1/cart/items/<pk>."""

    permission_classes = [AllowAny]

    def patch(self, request, pk):
        serializer = serializers.SetCartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = services.get_or_create_cart(request)
        try:
            services.set_item_quantity(
                cart, pk, serializer.validated_data['quantity']
            )
        except CartItem.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return _rejected(exc)
        return Response(serializers.build_cart_payload(cart, request))

    def delete(self, request, pk):
        cart = services.get_or_create_cart(request)
        try:
            services.remove_item(cart, pk)
        except CartItem.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializers.build_cart_payload(cart, request))


class WishlistView(APIView):
    """GET (list) · POST (save) /api/v1/wishlist/ — private per customer."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            WishlistItem.objects.filter(user=request.user)
            .select_related('product', 'product__store', 'product__category')
            .prefetch_related('product__variants__inventory', 'product__images')
        )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializers.WishlistItemSerializer(
            page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = serializers.AddWishlistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(
            Product.objects.select_related('store'),
            slug=serializer.validated_data['product_id'],
            status=Product.Status.PUBLISHED,
            store__status=Store.Status.ACTIVE,
        )
        item, created = services.add_to_wishlist(request.user, product)
        item = (
            WishlistItem.objects.filter(pk=item.pk)
            .select_related('product', 'product__store', 'product__category')
            .prefetch_related('product__variants__inventory', 'product__images')
            .get()
        )
        payload = serializers.WishlistItemSerializer(
            item, context={'request': request}
        ).data
        response_status = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return Response(payload, status=response_status)


class WishlistItemDetailView(APIView):
    """DELETE /api/v1/wishlist/items/<slug> — removes only the owner's row."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        services.remove_from_wishlist(request.user, product)
        count = WishlistItem.objects.filter(user=request.user).count()
        return Response({'detail': 'removed', 'count': count})
