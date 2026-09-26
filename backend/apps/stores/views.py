"""Store API (Phase 4) — thin views: parse → validate → service → serialize.

Endpoints (all under /api/v1/stores/):
- POST apply                      any authenticated customer
- GET/PATCH my/store              seller — own store only
- GET public/                     public — active store directory ({count, items})
- GET public/<slug>/              public — active stores only
- GET admin/applications/         staff — review queue ({count, items})
- POST admin/applications/<id>/review  staff — approve/reject
"""
from django.db import models
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.common.pagination import CountItemsPagination

from . import services
from .models import SellerApplication, Store
from .permissions import IsStoreOwner
from .serializers import (
    PublicStoreSerializer,
    SellerApplicationCreateSerializer,
    SellerApplicationSerializer,
    SellerStoreSerializer,
    StaffStoreSerializer,
)


class ApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if SellerApplication.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'already_applied',
                 'detail': 'You have already applied to become a seller.'},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = SellerApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = services.apply_as_seller(
            request.user, **serializer.validated_data
        )
        return Response(
            SellerApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class MyStoreView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        store = get_object_or_404(Store, user=request.user)
        return Response(SellerStoreSerializer(store).data)

    def patch(self, request):
        store = get_object_or_404(Store, user=request.user)
        serializer = SellerStoreSerializer(
            store, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyStoreDashboardView(APIView):
    """GET /api/v1/stores/my/dashboard — the seller home aggregates (§12.1).

    Read-only API truth scoped to the caller's own store: sales summary,
    order summary, inventory alerts, recent orders (masked customer label),
    and the reviews slot that Phase 14 fills.
    """

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        store = get_object_or_404(Store, user=request.user)
        return Response(services.build_seller_dashboard(store))


class PublicStoreDetailView(APIView):
    """Public storefront — pending/suspended stores never leak (§6 v1.2)."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        store = get_object_or_404(Store, slug=slug, status=Store.Status.ACTIVE)
        return Response(PublicStoreSerializer(store).data)


class PublicStoreListView(APIView):
    """Public store directory (Phase 6 discovery) — active stores only.

    Powers the customer-facing "Featured stores" sections. Same {count,
    items} envelope and pagination as every other list endpoint (§8).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        queryset = Store.objects.filter(
            status=Store.Status.ACTIVE
        ).order_by('name')
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = PublicStoreSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff review queue — staff group members only (§4 group-based)."""

    queryset = SellerApplication.objects.select_related('user', 'store')
    serializer_class = SellerApplicationSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'moderator', 'administrator']

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                models.Q(store_name__icontains=q)
                | models.Q(user__email__icontains=q)
            )
        return queryset


class ReviewApplicationView(APIView):
    """Moderation decisions — moderator/administrator only (§4 matrix)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        application = get_object_or_404(SellerApplication, pk=pk)
        decision = request.data.get('decision')
        reason = request.data.get('reason', '')
        if decision not in (
            SellerApplication.Status.APPROVED,
            SellerApplication.Status.REJECTED,
        ):
            return Response(
                {'error': 'invalid_decision',
                 'detail': "Decision must be 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            services.review_application(
                request.user, application, decision=decision, reason=reason
            )
        except ValueError as exc:
            return Response(

                {'error': 'review_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SellerApplicationSerializer(application).data)


class StaffStoreViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff store oversight (§13.3) — list/detail with search & status filters."""

    queryset = (
        Store.objects.select_related('user')
        .annotate(product_count=Count('products'))
        .order_by('-created_at')
    )
    serializer_class = StaffStoreSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator', 'support', 'operations']
    pagination_class = CountItemsPagination

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(
                models.Q(name__icontains=q)
                | models.Q(user__email__icontains=q)
                | models.Q(slug__icontains=q)
            )
        return qs


class SuspendStoreView(APIView):
    """POST /api/v1/stores/admin/stores/<pk>/suspend — moderator/administrator."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        store = get_object_or_404(Store, pk=pk)
        reason = request.data.get('reason', '')
        try:
            services.suspend_store(request.user, store, reason=reason)
        except ValueError as exc:
            return Response(
                {'error': 'suspend_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StaffStoreSerializer(store).data)


class ActivateStoreView(APIView):
    """POST /api/v1/stores/admin/stores/<pk>/activate — moderator/administrator."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        store = get_object_or_404(Store, pk=pk)
        reason = request.data.get('reason', '')
        try:
            services.activate_store(request.user, store, reason=reason)
        except ValueError as exc:
            return Response(
                {'error': 'activate_failed', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(StaffStoreSerializer(store).data)

