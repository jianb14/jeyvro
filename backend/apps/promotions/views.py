"""Promotion views (Phase 16 — ROADMAP §16.1, §16.2, §16.4) — thin: validate → service → shape."""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.audit.services import log_event
from apps.cart import services as cart_services
from apps.stores.models import Store

from . import serializers, services
from .models import Campaign, Promotion, Voucher


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



class PublicVoucherListView(APIView):
    """GET /api/v1/vouchers/ — active platform/public vouchers for the voucher center."""

    permission_classes = [AllowAny]

    def get(self, request):
        vouchers = Voucher.objects.filter(is_active=True).order_by('-created_at')
        store_slug = request.query_params.get('store')
        if store_slug:
            vouchers = vouchers.filter(store__slug=store_slug)
        else:
            scope = request.query_params.get('scope')
            if scope:
                vouchers = vouchers.filter(scope=scope)
        return Response([serializers.serialize_voucher(v) for v in vouchers[:50]])


class PublicPromotionListView(APIView):
    """GET /api/v1/promotions/ — active public promotions."""

    permission_classes = [AllowAny]

    def get(self, request):
        promos = (
            Promotion.objects.filter(is_active=True, campaign__is_active=True)
            .select_related('campaign', 'campaign__store')
            .order_by('id')
        )
        kind = request.query_params.get('kind') or request.query_params.get('type')
        if kind:
            promos = promos.filter(kind=kind)
        store_slug = request.query_params.get('store')
        if store_slug:
            promos = promos.filter(campaign__store__slug=store_slug)
        return Response([serializers.serialize_promotion(p) for p in promos[:50]])


class PublicCampaignListView(APIView):
    """GET /api/v1/campaigns/ — active marketplace campaigns."""

    permission_classes = [AllowAny]

    def get(self, request):
        campaigns = Campaign.objects.filter(is_active=True).order_by('-id')
        return Response([serializers.serialize_campaign(c) for c in campaigns[:20]])



class SellerPromotionListView(APIView):
    """GET/POST /api/v1/seller/promotions/ — seller-scoped promotion management."""

    permission_classes = [IsAuthenticated, IsSeller]

    def _get_store(self, request):
        return Store.objects.filter(user=request.user).first()

    def get(self, request):
        store = self._get_store(request)
        if not store:
            return Response({'error': 'no_store', 'detail': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        promos = Promotion.objects.filter(campaign__store=store).select_related('campaign').order_by('-id')
        return Response([serializers.serialize_promotion(p) for p in promos])

    def post(self, request):
        store = self._get_store(request)
        if not store:
            return Response({'error': 'no_store', 'detail': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = serializers.PromotionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_type = data.pop('target_type', 'all')
        product_ids = data.pop('product_ids', [])
        category_ids = data.pop('category_ids', [])
        starts_at = data.pop('starts_at', None)
        ends_at = data.pop('ends_at', None)
        name = data.pop('name')

        campaign = Campaign.objects.create(
            scope='seller',
            store=store,
            name=name,
            starts_at=starts_at,
            ends_at=ends_at,
            is_active=data.get('is_active', True),
        )
        label = data.pop('label', '') or name
        promo = Promotion.objects.create(campaign=campaign, label=label, **data)
        if target_type == 'product' and product_ids:
            for pid in product_ids:
                promo.target_rules.create(target_type='product', product_id=pid)
        elif target_type == 'category' and category_ids:
            for cid in category_ids:
                promo.target_rules.create(target_type='category', category_id=cid)

        log_event(
            request.user,
            'promotion.created',
            promo,
            detail={'name': campaign.name, 'kind': promo.kind, 'store_id': store.id},
        )
        return Response(serializers.serialize_promotion(promo), status=status.HTTP_201_CREATED)


class SellerPromotionDetailView(APIView):
    """PATCH/DELETE /api/v1/seller/promotions/<id>/ — store-owner scoped."""

    permission_classes = [IsAuthenticated, IsSeller]

    def _get_promo(self, request, pk):
        store = Store.objects.filter(user=request.user).first()
        if not store:
            return None
        return Promotion.objects.filter(pk=pk, campaign__store=store).select_related('campaign').first()

    def patch(self, request, pk):
        promo = self._get_promo(request, pk)
        if not promo:
            return Response({'error': 'not_found', 'detail': 'Promotion not found.'}, status=status.HTTP_404_NOT_FOUND)
        if 'is_active' in request.data:
            promo.is_active = bool(request.data['is_active'])
            promo.save(update_fields=['is_active'])
            log_event(
                request.user,
                'promotion.toggled',
                promo,
                detail={'is_active': promo.is_active},
            )
        return Response(serializers.serialize_promotion(promo))

    def delete(self, request, pk):
        promo = self._get_promo(request, pk)
        if not promo:
            return Response({'error': 'not_found', 'detail': 'Promotion not found.'}, status=status.HTTP_404_NOT_FOUND)
        promo.is_active = False
        promo.save(update_fields=['is_active'])
        log_event(
            request.user,
            'promotion.deactivated',
            promo,
            detail={},
        )
        return Response({'status': 'deactivated'})


class StaffPromotionListView(APIView):
    """GET /api/v1/staff/promotions/ — platform-wide promotion oversight."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator', 'operations', 'finance']

    def get(self, request):
        promos = Promotion.objects.select_related('campaign', 'campaign__store').order_by('-id')[:100]
        return Response([serializers.serialize_promotion(p) for p in promos])


class StaffCampaignListView(APIView):
    """GET/POST /api/v1/staff/campaigns/ — staff campaign management."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['administrator', 'operations']

    def get(self, request):
        campaigns = Campaign.objects.order_by('-id')[:50]
        return Response([serializers.serialize_campaign(c) for c in campaigns])

    def post(self, request):
        name = request.data.get('name', '').strip()
        starts_at = request.data.get('starts_at')
        ends_at = request.data.get('ends_at')
        if not name:
            return Response({'error': 'invalid', 'detail': 'name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        campaign = Campaign.objects.create(
            name=name,
            scope='platform',
            store=None,
            starts_at=starts_at,
            ends_at=ends_at,
            description=request.data.get('description', ''),
            is_active=bool(request.data.get('is_active', True)),
        )
        log_event(
            request.user,
            'campaign.created',
            campaign,
            detail={'name': campaign.name},
        )
        return Response(serializers.serialize_campaign(campaign), status=status.HTTP_201_CREATED)

