"""Order API (Phase 8) — thin views: validate → service → serialize (§8).

Checkout is signed-in only (§6 v1.7): guest carts merge into the account
cart at login and guests are prompted to sign in — no anonymous orders.
Requests can only choose an address; prices, fees, and totals are always
recomputed and snapshotted server-side.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart import services as cart_services
from apps.common.pagination import CountItemsPagination

from . import serializers, services
from .models import Order


def _rejected(exc):
    return Response(
        {'error': exc.code, 'detail': str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


class CheckoutPreviewView(APIView):
    """GET /api/v1/checkout/ — cart truth + per-store shipping + totals."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = cart_services.get_or_create_cart(request)
        return Response(serializers.build_checkout_preview(cart, request))


class CheckoutOrderView(APIView):
    """POST /api/v1/checkout/orders — place the order (address + method)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = serializers.CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = services.create_order(
                request.user,
                serializer.validated_data['address_id'],
                serializer.validated_data['payment_method'],
            )
        except services.CheckoutError as exc:
            return _rejected(exc)
        order = Order.objects.select_related('payment').prefetch_related(
            'seller_orders__items'
        ).get(pk=order.pk)
        return Response(
            serializers.serialize_order(order), status=status.HTTP_201_CREATED
        )


class OrderListView(APIView):
    """GET /api/v1/orders/ — the customer's own orders only (§4 IDOR)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Order.objects.filter(user=request.user).prefetch_related(
            'seller_orders__items'
        )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_order_summary(order) for order in page]
        )


class OrderDetailView(APIView):
    """GET /api/v1/orders/<number>/ — owner-scoped order snapshot."""

    permission_classes = [IsAuthenticated]

    def get(self, request, number):
        order = get_object_or_404(
            Order.objects.select_related('payment').prefetch_related(
                'seller_orders__items'
            ),
            number=number,
            user=request.user,
        )
        return Response(serializers.serialize_order(order))


class OrderCancelView(APIView):
    """POST /api/v1/orders/<number>/cancel — releases reservations (§6)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, number):
        try:
            order = services.cancel_order(request.user, number)
        except Order.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        except services.CheckoutError as exc:
            return _rejected(exc)
        order = Order.objects.select_related('payment').prefetch_related(
            'seller_orders__items'
        ).get(pk=order.pk)
        return Response(serializers.serialize_order(order))
