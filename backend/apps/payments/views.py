"""Payment API (Phase 9) — thin views: validate → service → serialize (§8).

The webhook endpoint is public by design: gateways authenticate with their
signature, not a session — verification happens inside the service before
any state changes. Staff endpoints confirm cash-on-delivery collections and
issue refunds; Phase 10 / Phase 13 wire their flows into these same
services instead of duplicating money logic.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup
from apps.common.pagination import CountItemsPagination

from . import serializers, services
from .models import Payment, PaymentMethod, Refund, WebhookStatus


def _rejected(exc):
    return Response(
        {'error': exc.code, 'detail': str(exc)},
        status=status.HTTP_400_BAD_REQUEST,
    )


class PaymentDetailView(APIView):
    """GET /api/v1/payments/<reference>/ — owner-scoped payment state."""

    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        payment = get_object_or_404(
            Payment.objects.select_related('order'),
            reference=reference,
            order__user=request.user,
        )
        return Response(serializers.serialize_payment_detail(payment))


class CodCollectedView(APIView):
    """POST /api/v1/payments/<reference>/cod-collected — staff cash confirm.

    The delivery-flow entry point (§9.2): Phase 10 calls the same service
    from its delivery confirmation instead of this endpoint. Duplicate
    confirmations are safe — the second call returns the unchanged payment.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]

    def post(self, request, reference):
        payment = get_object_or_404(
            Payment.objects.select_related('order'), reference=reference
        )
        if payment.method != PaymentMethod.COD:
            return Response(
                {
                    'error': 'not_cod',
                    'detail': 'Only cash-on-delivery payments are collected this way.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payment = services.mark_paid(
                payment, source='cod_collection', actor=request.user
            )
        except services.PaymentError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_payment_detail(payment))


class RefundView(APIView):
    """POST /api/v1/payments/<reference>/refunds — staff-issued refund (§9.4).

    Finance/administrator only (§4): support reads payments but never moves
    money — the group gate is the least-privilege check, the balance check
    stays inside the service.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['finance', 'administrator']

    def post(self, request, reference):
        payment = get_object_or_404(
            Payment.objects.select_related('order'), reference=reference
        )
        serializer = serializers.CreateRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = services.refund(
                payment,
                serializer.validated_data['amount'],
                reason=serializer.validated_data.get('reason', ''),
                actor=request.user,
            )
        except services.PaymentError as exc:
            return _rejected(exc)
        if refund.status == Refund.Status.FAILED:
            return Response(
                {
                    'error': 'refund_failed',
                    'detail': 'The gateway refused the refund.',
                    'refund': serializers.serialize_refund(refund),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            serializers.serialize_refund(refund),
            status=(
                status.HTTP_201_CREATED
                if refund.status == Refund.Status.SUCCEEDED
                else status.HTTP_202_ACCEPTED
            ),
        )


class PaymentWebhookView(APIView):
    """POST /api/v1/payments/webhooks/<provider>/ — gateways only (§9.3).

    No session auth and no CSRF: the HMAC signature over the raw body is the
    credential, and it is verified before anything is read or written.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, provider):
        try:
            event, duplicate = services.process_webhook(
                provider=provider,
                body=request.body,
                signature=request.headers.get('X-Payments-Signature', ''),
            )
        except services.WebhookRejected as exc:
            return Response(
                {'error': exc.code, 'detail': str(exc)},
                status=exc.status_code,
            )
        if duplicate:
            return Response({'status': 'duplicate', 'event_id': event.event_id})
        if event.status == WebhookStatus.FAILED:
            return Response(
                {'status': 'failed', 'error': event.error},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'status': event.status, 'event_id': event.event_id})


# -----------------------------------------------------------------------------
# Phase 13.5: Staff payment oversight views (§4 groups — read-only console)
# -----------------------------------------------------------------------------

class StaffPaymentListView(APIView):
    """GET /api/v1/payments/admin/payments/ — payment oversight (13.5).

    Support has read-only payment oversight and finance sees its settlement
    queue (§4); issuing a refund stays on the gated endpoint above.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'finance', 'administrator']

    def get(self, request):
        queryset = Payment.objects.select_related(
            'order', 'order__user'
        ).order_by('-created_at')
        params = request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(order__number__icontains=needle)
                | Q(order__user__email__icontains=needle)
            )
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        method = params.get('method')
        if method:
            queryset = queryset.filter(method=method)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_staff_payment_row(payment) for payment in page]
        )


class StaffRefundListView(APIView):
    """GET /api/v1/payments/admin/refunds/ — refund oversight (13.5).

    Finance settles refunds and support reads the same trail for customer
    cases (§4); every row carries the issuing staff member.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'finance', 'administrator']

    def get(self, request):
        queryset = Refund.objects.select_related(
            'payment', 'payment__order', 'payment__order__user', 'actor'
        ).order_by('-created_at')
        params = request.query_params
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(payment__reference__icontains=needle)
                | Q(payment__order__number__icontains=needle)
            )
        status_param = params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_staff_refund_row(refund) for refund in page]
        )
