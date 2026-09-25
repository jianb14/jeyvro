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
from .models import Order, SellerOrder, Shipment


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
                'seller_orders__items',
                'seller_orders__shipments__items__order_item',
                'seller_orders__shipments__tracking_events',
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


# -----------------------------------------------------------------------------
# Phase 10: Fulfillment Views (§10.1, §10.2, §10.3)
# -----------------------------------------------------------------------------

class SellerOrderListView(APIView):
    """GET /api/v1/seller/orders/ — lists seller orders for the caller's store(s)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, 'is_seller', False):
            return Response(
                {'error': 'forbidden', 'detail': 'Seller account required.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = SellerOrder.objects.filter(
            store__user=request.user
        ).select_related('store', 'order').prefetch_related(
            'items',
            'shipments__items__order_item',
            'shipments__tracking_events',
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_seller_order(so) for so in page]
        )


class SellerOrderDetailView(APIView):
    """GET /api/v1/seller/orders/<id>/ — seller order detail for caller's store."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        seller_order = get_object_or_404(
            SellerOrder.objects.select_related('store', 'order').prefetch_related(
                'items',
                'shipments__items__order_item',
                'shipments__tracking_events',
            ),
            pk=pk,
            store__user=request.user,
        )
        return Response(serializers.serialize_seller_order(seller_order))


class SellerOrderProcessView(APIView):
    """POST /api/v1/seller/orders/<id>/process — transition to processing."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        seller_order = get_object_or_404(
            SellerOrder.objects.select_related('store', 'order'),
            pk=pk,
            store__user=request.user,
        )
        try:
            so = services.mark_seller_order_processing(seller_order, actor=request.user)
        except services.FulfillmentError as exc:
            return _rejected(exc)
        so = SellerOrder.objects.select_related('store', 'order').prefetch_related(
            'items',
            'shipments__items__order_item',
            'shipments__tracking_events',
        ).get(pk=so.pk)
        return Response(serializers.serialize_seller_order(so))


class SellerOrderPackView(APIView):
    """POST /api/v1/seller/orders/<id>/pack — transition to packed."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        seller_order = get_object_or_404(
            SellerOrder.objects.select_related('store', 'order'),
            pk=pk,
            store__user=request.user,
        )
        try:
            so = services.mark_seller_order_packed(seller_order, actor=request.user)
        except services.FulfillmentError as exc:
            return _rejected(exc)
        so = SellerOrder.objects.select_related('store', 'order').prefetch_related(
            'items',
            'shipments__items__order_item',
            'shipments__tracking_events',
        ).get(pk=so.pk)
        return Response(serializers.serialize_seller_order(so))


class SellerOrderShipView(APIView):
    """POST /api/v1/seller/orders/<id>/ship — create parcel shipment."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        seller_order = get_object_or_404(
            SellerOrder.objects.select_related('store', 'order').prefetch_related('items'),
            pk=pk,
            store__user=request.user,
        )
        serializer = serializers.CreateShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shipment = services.create_shipment(
                seller_order,
                items_data=serializer.validated_data.get('items'),
                carrier_code=serializer.validated_data.get('carrier', 'manual'),
                package_notes=serializer.validated_data.get('package_notes', ''),
                package_weight_grams=serializer.validated_data.get('package_weight_grams'),
                actor=request.user,
            )
        except services.FulfillmentError as exc:
            return _rejected(exc)

        shipment = Shipment.objects.prefetch_related(
            'items__order_item', 'tracking_events'
        ).get(pk=shipment.pk)
        return Response(
            serializers.serialize_shipment(shipment),
            status=status.HTTP_201_CREATED,
        )


class ShipmentTrackView(APIView):
    """GET /api/v1/shipments/track/<tracking_number>/ — public tracking status."""

    def get(self, request, tracking_number):
        shipment = get_object_or_404(
            Shipment.objects.prefetch_related(
                'items__order_item', 'tracking_events'
            ),
            tracking_number=tracking_number,
        )
        return Response(serializers.serialize_shipment(shipment))


class ShipmentEventUpdateView(APIView):
    """POST /api/v1/shipments/<tracking_number>/events — update shipment status & log event."""

    permission_classes = [IsAuthenticated]

    def post(self, request, tracking_number):
        shipment = get_object_or_404(
            Shipment.objects.select_related('seller_order__store', 'seller_order__order'),
            tracking_number=tracking_number,
        )
        is_store_owner = shipment.seller_order.store.user_id == request.user.id
        is_staff = request.user.is_staff or request.user.is_superuser
        if not (is_store_owner or is_staff):
            return Response(
                {'error': 'forbidden', 'detail': 'Only the fulfilling seller or staff may update shipments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = serializers.UpdateShipmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            s = services.update_shipment_status(
                shipment,
                serializer.validated_data['status'],
                location=serializer.validated_data.get('location', ''),
                description=serializer.validated_data.get('description', ''),
                actor=request.user,
            )
        except services.FulfillmentError as exc:
            return _rejected(exc)

        s = Shipment.objects.prefetch_related(
            'items__order_item', 'tracking_events'
        ).get(pk=s.pk)
        return Response(serializers.serialize_shipment(s))
