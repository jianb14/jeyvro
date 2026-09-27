"""Review endpoints (Phase 14 — backend-api rules 2 & 6).

GET review lists are anonymous; writing a review demands a signed-in
verified buyer — the view never decides eligibility, services do (§6).
Every rejection returns the {error, detail} envelope through
`ReviewError`, mirroring orders/payments views.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.catalog.models import Product
from apps.common.pagination import CountItemsPagination

from . import serializers, services
from .models import Review, ReviewStatus


def _rejected(exc):
    return Response({'error': exc.code, 'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _console_queryset():
    """Everything the staff queue and the seller studio render in one query set."""
    return (
        Review.objects
        .select_related('user', 'product', 'store', 'order', 'moderated_by')
        .prefetch_related('images', 'reports')
        .order_by('-created_at')
    )



class ProductReviewListView(APIView):
    """GET the published reviews of a product / POST the buyer's own review."""

    def get_permissions(self):
        # Anonymous may read; only signed-in buyers may write (backend-api
        # rule 6 — permission stated per endpoint, never UI-only).
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        queryset = services.public_list(product)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializers.ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status=Product.Status.PUBLISHED)
        input = serializers.ReviewWriteSerializer(data=request.data)
        input.is_valid(raise_exception=True)
        try:
            review = services.create_review(
                request.user,
                product=product,
                rating=input.validated_data['rating'],
                title=input.validated_data.get('title', ''),
                body=input.validated_data['body'],
                image_urls=input.validated_data.get('image_urls', []),
            )
        except services.ReviewError as exc:
            return _rejected(exc)
        return Response(
            serializers.ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )


class ProductReviewEligibilityView(APIView):
    """The server's verdict behind the 'Write a review' button (§6)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        return Response(services.eligibility(request.user, product))


class ReviewDetailView(APIView):
    """PATCH — owner edits their own review (14.1 editing rules)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        input = serializers.ReviewWriteSerializer(data=request.data, partial=True)
        input.is_valid(raise_exception=True)
        validated = input.validated_data
        try:
            updated = services.update_review(
                request.user,
                review.pk,
                rating=validated.get('rating'),
                title=validated.get('title'),
                body=validated.get('body'),
            )
        except services.ReviewError as exc:
            return _rejected(exc)
        except Review.DoesNotExist:
            return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializers.ReviewSerializer(updated).data)


class ReviewReportView(APIView):
    """POST — a customer reports a review for moderation (14.3)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        input = serializers.ReviewReportSerializer(data=request.data)
        input.is_valid(raise_exception=True)
        try:
            report = services.report_review(
                request.user,
                review,
                reason=input.validated_data['reason'],
                notes=input.validated_data.get('notes', ''),
            )
        except services.ReviewError as exc:
            return _rejected(exc)
        return Response(
            {'id': report.pk, 'review_id': review.pk, 'status': review.status},
            status=status.HTTP_201_CREATED,
        )


class StaffReviewQueueView(APIView):
    """GET /api/v1/reviews/moderation/ — the staff moderation queue (§6).

    Support reads along; only moderator/administrator can act (the write
    endpoints below state their own groups — backend-api rule 6). Filters:
    `status`, `reported=1` (flagged or carrying open reports), `q`.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'moderator', 'administrator']

    def get(self, request):
        queryset = _console_queryset()
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if request.query_params.get('reported') in ('1', 'true'):
            queryset = queryset.filter(
                status=ReviewStatus.FLAGGED
            ) | queryset.filter(reports__resolved=False)
            # The union can repeat rows when a review carries many reports.
            queryset = queryset.distinct()
        needle = request.query_params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(product__title__icontains=needle)
                | Q(store__name__icontains=needle)
                | Q(user__email__icontains=needle)
                | Q(body__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializers.StaffReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class StaffReviewModerateView(APIView):
    """POST /api/v1/reviews/<pk>/moderate/ — hide/restore (moderator only).

    Hiding demands a reason; the decision and its actor land in the audit
    log through `services.moderate_review` (§4, §6).
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        input = serializers.ReviewModerationSerializer(data=request.data)
        input.is_valid(raise_exception=True)
        try:
            review = services.moderate_review(
                request.user,
                review=review,
                action=input.validated_data['action'],
                reason=input.validated_data.get('reason', ''),
            )
        except services.ReviewError as exc:
            return _rejected(exc)
        return Response(serializers.StaffReviewSerializer(review).data)


class StaffReviewReportsResolveView(APIView):
    """POST /api/v1/reviews/<pk>/reports/resolve/ — close the abuse reports."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        resolved = services.resolve_reports(request.user, review=review)
        return Response({'review_id': review.pk, 'resolved': resolved})


class StoreReviewListView(APIView):
    """GET /api/v1/reviews/store/ — the seller's own store reviews (14.2).

    Sellers read and reply to their own store's reviews only; moderation
    stays staff-only (§6 — sellers cannot hide a review).
    """

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        queryset = _console_queryset().filter(store__user=request.user)
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if request.query_params.get('unanswered') in ('1', 'true'):
            queryset = queryset.filter(seller_reply='')
        needle = request.query_params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(product__title__icontains=needle) | Q(body__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializers.StaffReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ReviewReplyView(APIView):
    """POST /api/v1/reviews/<pk>/reply/ — the store's reply to a review."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        input = serializers.ReviewReplySerializer(data=request.data)
        input.is_valid(raise_exception=True)
        try:
            review = services.reply_to_review(
                seller_user=request.user,
                review=review,
                text=input.validated_data['text'],
            )
        except services.ReviewError as exc:
            return _rejected(exc)
        return Response(serializers.StaffReviewSerializer(review).data)

