"""Store API (Phase 4) — thin views: parse → validate → service → serialize.

Endpoints (all under /api/v1/stores/):
- POST apply                      any authenticated customer
- GET/PATCH my/store              seller — own store only
- GET public/<slug>/              public — active stores only
- GET admin/applications/         staff — review queue ({count, items})
- POST admin/applications/<id>/review  staff — approve/reject
"""
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller

from . import services
from .models import SellerApplication, Store
from .permissions import IsStoreOwner
from .serializers import (
    PublicStoreSerializer,
    SellerApplicationCreateSerializer,
    SellerApplicationSerializer,
    SellerStoreSerializer,
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


class PublicStoreDetailView(APIView):
    """Public storefront — pending/suspended stores never leak (§6 v1.2)."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        store = get_object_or_404(Store, slug=slug, status=Store.Status.ACTIVE)
        return Response(PublicStoreSerializer(store).data)


class StaffApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff review queue — staff group members only (§4 group-based)."""

    queryset = SellerApplication.objects.select_related('user', 'store')
    serializer_class = SellerApplicationSerializer
    permission_classes = [IsAuthenticated, InStaffGroup]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class ReviewApplicationView(APIView):
    permission_classes = [IsAuthenticated, InStaffGroup]

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