"""Order API (Phase 8) — thin views: validate → service → serialize (§8).

Checkout is signed-in only (§6 v1.7): guest carts merge into the account
cart at login and guests are prompted to sign in — no anonymous orders.
Requests can only choose an address; prices, fees, and totals are always
recomputed and snapshotted server-side.
"""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup
from apps.cart import services as cart_services
from apps.common.pagination import CountItemsPagination

from . import serializers, services
from .models import Order, OrderRequest, SellerOrder, Shipment


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
                'requests__seller_order',
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
        ).select_related('store', 'order', 'order__payment').prefetch_related(
            'items',
            'shipments__items__order_item',
            'shipments__tracking_events',
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        needle = request.query_params.get('q')
        if needle:
            # Order number, customer label, or item title (§12.4 search).
            queryset = queryset.filter(
                Q(order__number__icontains=needle)
                | Q(order__ship_to_name__icontains=needle)
                | Q(items__product_title__icontains=needle)
            ).distinct()

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
            SellerOrder.objects.select_related(
                'store', 'order', 'order__payment'
            ).prefetch_related(
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
            SellerOrder.objects.select_related('store', 'order', 'order__payment'),
            pk=pk,
            store__user=request.user,
        )
        try:
            so = services.mark_seller_order_processing(seller_order, actor=request.user)
        except services.FulfillmentError as exc:
            return _rejected(exc)
        so = SellerOrder.objects.select_related(
            'store', 'order', 'order__payment'
        ).prefetch_related(
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
            SellerOrder.objects.select_related('store', 'order', 'order__payment'),
            pk=pk,
            store__user=request.user,
        )
        try:
            so = services.mark_seller_order_packed(seller_order, actor=request.user)
        except services.FulfillmentError as exc:
            return _rejected(exc)
        so = SellerOrder.objects.select_related(
            'store', 'order', 'order__payment'
        ).prefetch_related(
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
            SellerOrder.objects.select_related(
                'store', 'order', 'order__payment'
            ).prefetch_related('items'),
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


# -----------------------------------------------------------------------------
# Phase 11: Customer Account & Order Management Views (§11.2, §11.3)
# -----------------------------------------------------------------------------

class OrderReorderView(APIView):
    """POST /api/v1/orders/<number>/reorder — buy the order again (§11.2).

    Re-validates every line against live catalog/stock truth; unavailable
    lines come back as `skipped`, never silently dropped.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, number):
        try:
            result = services.reorder_into_cart(request.user, number)
        except Order.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class OrderRequestCreateView(APIView):
    """POST /api/v1/orders/<number>/requests — record a customer request.

    The intake only (§11.3): eligibility is server-verified, the record is
    owner-scoped, and Phase 17 owns what happens to it next.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, number):
        serializer = serializers.CreateOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order_request = services.create_order_request(
                request.user,
                number,
                serializer.validated_data['kind'],
                serializer.validated_data['reason'],
                serializer.validated_data.get('description', ''),
                serializer.validated_data.get('seller_order_id'),
            )
        except Order.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        except services.RequestError as exc:
            return _rejected(exc)
        return Response(
            serializers.serialize_order_request(order_request),
            status=status.HTTP_201_CREATED,
        )


class OrderRequestWithdrawView(APIView):
    """POST /api/v1/orders/<number>/requests/<id>/withdraw — customer withdraw."""

    permission_classes = [IsAuthenticated]

    def post(self, request, number, pk):
        try:
            order_request = services.withdraw_order_request(request.user, number, pk)
        except OrderRequest.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        except services.RequestError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_order_request(order_request))


# -----------------------------------------------------------------------------
# Phase 13.5: Staff oversight views (§4 groups — read-only console)
# -----------------------------------------------------------------------------

class StaffOrderListView(APIView):
    """GET /api/v1/orders/admin/orders/ — order oversight (13.5).

    Support, finance and operations read every order; the console never
    mutates state — cancellation and money movement stay on the existing
    owner/staff services (§4).
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'finance', 'operations', 'administrator']

    def get(self, request):
        queryset = (
            Order.objects.select_related('user', 'payment')
            .prefetch_related('seller_orders__items')
            .order_by('-created_at')
        )
        params = request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(number__icontains=needle)
                | Q(user__email__icontains=needle)
                | Q(ship_to_name__icontains=needle)
            )
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        store = params.get('store')
        if store:
            queryset = (
                queryset.filter(seller_orders__store_id=store)
                if store.isdigit()
                else queryset.filter(seller_orders__store__slug=store)
            ).distinct()
        payment = params.get('payment')
        if payment:
            queryset = queryset.filter(payment__status=payment)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_staff_order_row(order) for order in page]
        )


class StaffOrderDetailView(APIView):
    """GET /api/v1/orders/admin/orders/<number>/ — full snapshot for staff."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'finance', 'operations', 'administrator']

    def get(self, request, number):
        order = get_object_or_404(
            Order.objects.select_related('payment', 'user').prefetch_related(
                'seller_orders__items',
                'seller_orders__shipments__items__order_item',
                'seller_orders__shipments__tracking_events',
                'requests__seller_order',
            ),
            number=number,
        )
        payload = serializers.serialize_order(order)
        payload['customer_email'] = order.user.email
        return Response(payload)


class StaffShipmentListView(APIView):
    """GET /api/v1/orders/admin/shipments/ — parcel oversight (13.5).

    Support oversees shipments and operations reconciles logistics (§4);
    carrier mutations are not part of this slice.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'operations', 'administrator']

    def get(self, request):
        queryset = (
            Shipment.objects.select_related(
                'seller_order__order', 'seller_order__store'
            )
            .annotate(event_count=Count('tracking_events'))
            .order_by('-created_at')
        )
        params = request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(tracking_number__icontains=needle)
                | Q(seller_order__order__number__icontains=needle)
                | Q(seller_order__store__name__icontains=needle)
            )
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        carrier = params.get('carrier')
        if carrier:
            queryset = queryset.filter(carrier=carrier)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_staff_shipment_row(shipment) for shipment in page]
        )


class StaffOrderRequestListView(APIView):
    """GET /api/v1/orders/admin/requests/ — return/refund/dispute intake (13.5).

    Read-only oversight of the Phase 11 intake queue: support reviews it,
    finance watches refunds, operations watches issues — Phase 17 adjudicates.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'finance', 'operations', 'administrator']

    def get(self, request):
        queryset = (
            OrderRequest.objects.select_related('order__user', 'seller_order')
            .order_by('-created_at')
        )
        params = request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(order__number__icontains=needle)
                | Q(order__user__email__icontains=needle)
                | Q(reason__icontains=needle)
            )
        kind = params.get('kind')
        if kind:
            queryset = queryset.filter(kind=kind)
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_staff_request_row(item) for item in page]
        )
