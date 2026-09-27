"""Promotion views (Phase 16 — ROADMAP §16.1) — thin: validate → service → shape."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart import services as cart_services

from . import serializers, services


class VoucherValidateView(APIView):
    """POST /api/v1/vouchers/validate/ — is this code usable on MY cart?

    The cart is read server-side (the client sends only the code) and the
    verdict — eligibility, discount math, refusal reason — comes from the
    same service checkout uses, so the preview can never disagree with the
    order that follows. 400 carries the customer-safe reason.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = serializers.VoucherValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = cart_services.get_or_create_cart(request)
        store_lines = services.build_store_lines(
            cart.items.select_related(
                'variant__product__store', 'variant__product__category'
            )
        )
        try:
            plan = services.evaluate_voucher(
                serializer.validated_data['code'], request.user, store_lines
            )
        except services.VoucherError as exc:
            return Response(
                {'error': exc.code, 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serializers.serialize_voucher_preview(plan))
