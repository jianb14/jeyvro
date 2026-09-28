"""Resolution views (Phase 17 — ROADMAP §17.1) — thin: validate → service → shape.

Three audiences, three prefixes, each with its own permission class and its
own query scope (§4):

* the customer under `/orders/<number>/…` and `/returns/…` — owner-scoped;
* the seller under `/seller/returns/…` — store-scoped, so another store's case
  is simply not found;
* staff under `/admin/returns/…` — group-gated adjudication of any case,
  including whole-order ones.
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup, IsSeller
from apps.common.pagination import CountItemsPagination
from apps.orders.models import Order
from apps.payments import services as payment_services

from . import serializers, services
from .models import Dispute, ReturnCase, ReturnStatus

STAFF_GROUPS = ['support', 'operations', 'administrator']


def _rejected(exc):
    """Service rejection → 400 with the customer-safe code (§8)."""
    return Response(
        {'error': exc.code, 'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST
    )


def _not_found():
    return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)


def _case_queryset():
    return ReturnCase.objects.select_related(
        'order', 'order__user', 'seller_order__store', 'requested_by'
    ).prefetch_related('items__order_item', 'events__actor')


class OrderReturnEligibilityView(APIView):
    """GET /api/v1/orders/<number>/return-eligibility — can this be returned?

    The return button's verdict is a server one (§17.1 eligibility/window),
    with the same per-line remaining quantities the filing endpoint enforces,
    so the form can never offer a quantity the apply will refuse.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, number):
        order = Order.objects.filter(number=number, user=request.user).first()
        if order is None:
            return _not_found()
        verdict = services.evaluate_return_eligibility(
            order, request.query_params.get('seller_order')
        )
        return Response(serializers.serialize_eligibility(verdict))


class OrderReturnApplyView(APIView):
    """POST /api/v1/orders/<number>/returns — file a return (§17.1)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, number):
        serializer = serializers.ReturnApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            case = services.apply_return(
                request.user,
                number,
                reason=data['reason'],
                note=data.get('note', ''),
                seller_order_id=data.get('seller_order_id'),
                lines=data['lines'],
                request_id=data.get('request_id'),
            )
        except Order.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(
            serializers.serialize_return_case(case), status=status.HTTP_201_CREATED
        )


class CustomerReturnListView(APIView):
    """GET /api/v1/returns/ — the customer's own returns, newest first."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = _case_queryset().filter(requested_by=request.user)
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_return_row(case) for case in page]
        )


class CustomerReturnDetailView(APIView):
    """GET /api/v1/returns/<reference>/ — one case with its timeline."""

    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        case = (
            _case_queryset()
            .filter(reference=reference, requested_by=request.user)
            .first()
        )
        if case is None:
            return _not_found()
        return Response(serializers.serialize_return_case(case))


class CustomerReturnCancelView(APIView):
    """POST /api/v1/returns/<reference>/cancel — withdraw before goods move."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        note = request.data.get('note', '') if hasattr(request.data, 'get') else ''
        try:
            case = services.cancel_return(request.user, reference, note=note)
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_case(case))


class SellerReturnListView(APIView):
    """GET /api/v1/seller/returns/ — this store's return queue (§17.1)."""

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        queryset = _case_queryset().filter(seller_order__store__user=request.user)
        params = request.query_params
        status_param = params.get('status')
        if status_param == 'open':
            queryset = queryset.filter(status__in=services.OPEN_RETURN_STATUSES)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(order__number__icontains=needle)
                | Q(requested_by__email__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_return_row(case) for case in page]
        )


class SellerReturnDetailView(APIView):
    """GET /api/v1/seller/returns/<reference>/ — the case and its timeline."""

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request, reference):
        case = (
            _case_queryset()
            .filter(reference=reference, seller_order__store__user=request.user)
            .first()
        )
        if case is None:
            return _not_found()
        return Response(serializers.serialize_return_case(case))


class SellerReturnRespondView(APIView):
    """POST /api/v1/seller/returns/<reference>/respond — approve or reject."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, reference):
        serializer = serializers.ReturnDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = services.respond_to_return(
                request.user,
                reference,
                decision=serializer.validated_data['decision'],
                reason=serializer.validated_data.get('reason', ''),
                note=serializer.validated_data.get('note', ''),
            )
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_case(case))


class SellerReturnShipmentView(APIView):
    """POST /api/v1/seller/returns/<reference>/shipment — book the return leg."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, reference):
        serializer = serializers.ReturnShipmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shipment = services.register_return_shipment(
                request.user, reference, **serializer.validated_data
            )
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_shipment(shipment))


class SellerReturnReceiveView(APIView):
    """POST /api/v1/seller/returns/<reference>/receive — goods back, restock."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, reference):
        serializer = serializers.ReturnReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = services.receive_return(
                request.user,
                reference,
                note=serializer.validated_data.get('note', ''),
                restock_overrides=serializer.validated_data.get('restock_overrides'),
            )
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_case(case))


class SellerReturnCloseView(APIView):
    """POST /api/v1/seller/returns/<reference>/close — settle and close."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, reference):
        note = request.data.get('note', '') if hasattr(request.data, 'get') else ''
        try:
            case = services.close_return(request.user, reference, note=note)
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_case(case))


class StaffReturnListView(APIView):
    """GET /api/v1/admin/returns/ — every return case, staff-filtered (§4)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def get(self, request):
        queryset = _case_queryset()
        params = request.query_params
        status_param = params.get('status')
        if status_param == 'open':
            queryset = queryset.filter(status__in=services.OPEN_RETURN_STATUSES)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        reason = params.get('reason')
        if reason:
            queryset = queryset.filter(reason=reason)
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(order__number__icontains=needle)
                | Q(seller_order__store_name__icontains=needle)
                | Q(requested_by__email__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_return_row(case) for case in page]
        )


class StaffReturnDecideView(APIView):
    """POST /api/v1/admin/returns/<reference>/decide — staff intervention (§17.1).

    The only path for whole-order cases, and the way a seller ruling is
    re-decided — always with a reason, always recorded as an override.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def post(self, request, reference):
        serializer = serializers.ReturnDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            case = services.decide_return(
                request.user,
                reference,
                decision=serializer.validated_data['decision'],
                reason=serializer.validated_data.get('reason', ''),
                note=serializer.validated_data.get('note', ''),
            )
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_return_case(case))


class StaffReturnPayoutView(APIView):
    """POST /api/v1/admin/returns/<reference>/refund — pay the case out (§17.2).

    Finance or administrator only, matching the Phase 13.4 rule that only
    those groups may issue a refund anywhere in the product: a return is the
    seller's ruling, but the money is the platform's. The amount is optional
    (defaults to everything the case still owes) and is re-capped by the
    service against the case and the payment.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['finance', 'administrator']

    def post(self, request, reference):
        serializer = serializers.ReturnPayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = services.issue_refund(
                request.user,
                reference,
                amount=serializer.validated_data.get('amount'),
                reason=serializer.validated_data.get('reason', ''),
            )
        except ReturnCase.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        except payment_services.PaymentError as exc:
            # The ledger's own balance check refused it (e.g. the payment is
            # already fully refunded) — same 400 + code contract.
            return _rejected(exc)
        return Response(
            serializers.serialize_refund(refund), status=status.HTTP_201_CREATED
        )


class StaffReturnReferenceView(APIView):
    """GET /api/v1/admin/returns/reference/ — the case vocabularies (§17.1)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def get(self, request):
        return Response({
            'statuses': [
                {'value': value, 'label': label}
                for value, label in ReturnStatus.choices
            ],
            'reasons': [
                {'value': value, 'label': label}
                for value, label in ReturnCase.Reason.choices
            ],
        })


# -----------------------------------------------------------------------------
# §17.3 disputes — three audiences, three prefixes (like the return desk)
# -----------------------------------------------------------------------------

def _dispute_queryset():
    return Dispute.objects.select_related(
        'order', 'order__user', 'seller_order__store', 'requested_by',
        'return_case', 'resolved_by',
    ).prefetch_related(
        'statements__author', 'evidence__added_by', 'events__actor'
    )


class CustomerDisputeCreateView(APIView):
    """POST /api/v1/orders/<number>/disputes — open a buyer escalation (§17.3).

    Owner-scoped at the query level: an order that is not the caller's does
    not exist here, and everything about eligibility (slice, duplicates,
    intake/return links) is decided by the service.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, number):
        serializer = serializers.DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            dispute = services.open_dispute(
                request.user,
                number,
                reason=data['reason'],
                statement=data['statement'],
                seller_order_id=data.get('seller_order_id'),
                request_id=data.get('request_id'),
                return_reference=data.get('return_reference') or None,
            )
        except Order.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(
            serializers.serialize_dispute(dispute), status=status.HTTP_201_CREATED
        )


class CustomerDisputeListView(APIView):
    """GET /api/v1/disputes/ — the buyer's own escalations, newest first."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = _dispute_queryset().filter(requested_by=request.user)
        status_param = request.query_params.get('status')
        if status_param == 'open':
            queryset = queryset.filter(status__in=services.OPEN_DISPUTE_STATUSES)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_dispute_row(d) for d in page]
        )


class CustomerDisputeDetailView(APIView):
    """GET /api/v1/disputes/<reference>/ — one dispute with its timeline."""

    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        dispute = (
            _dispute_queryset()
            .filter(reference=reference, requested_by=request.user)
            .first()
        )
        if dispute is None:
            return _not_found()
        return Response(serializers.serialize_dispute(dispute))


class CustomerDisputeStatementView(APIView):
    """POST /api/v1/disputes/<reference>/statements — the customer statement."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        serializer = serializers.DisputeStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dispute = services.add_dispute_statement(
                request.user, reference, body=serializer.validated_data['body']
            )
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class CustomerDisputeEvidenceView(APIView):
    """POST /api/v1/disputes/<reference>/evidence — one evidence row."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        serializer = serializers.DisputeEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            dispute = services.add_dispute_evidence(
                request.user,
                reference,
                url=data['url'],
                caption=data.get('caption', ''),
            )
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class CustomerDisputeCancelView(APIView):
    """POST /api/v1/disputes/<reference>/cancel — withdraw while undecided."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reference):
        try:
            dispute = services.cancel_dispute(request.user, reference)
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class SellerDisputeListView(APIView):
    """GET /api/v1/seller/disputes/ — this store's dispute queue (§17.3)."""

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request):
        queryset = _dispute_queryset().filter(
            seller_order__store__user=request.user
        )
        params = request.query_params
        status_param = params.get('status')
        if status_param == 'open':
            queryset = queryset.filter(status__in=services.OPEN_DISPUTE_STATUSES)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(order__number__icontains=needle)
                | Q(requested_by__email__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_dispute_row(d) for d in page]
        )


class SellerDisputeDetailView(APIView):
    """GET /api/v1/seller/disputes/<reference>/ — the dispute and timeline."""

    permission_classes = [IsAuthenticated, IsSeller]

    def get(self, request, reference):
        dispute = (
            _dispute_queryset()
            .filter(reference=reference, seller_order__store__user=request.user)
            .first()
        )
        if dispute is None:
            return _not_found()
        return Response(serializers.serialize_dispute(dispute))


class SellerDisputeRespondView(APIView):
    """POST /api/v1/seller/disputes/<reference>/respond — seller statement."""

    permission_classes = [IsAuthenticated, IsSeller]

    def post(self, request, reference):
        serializer = serializers.DisputeRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            dispute = services.respond_to_dispute(
                request.user,
                reference,
                statement=data['statement'],
                evidence=data.get('evidence') or [],
            )
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class StaffDisputeListView(APIView):
    """GET /api/v1/admin/disputes/ — every dispute, staff-filtered (§4)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def get(self, request):
        queryset = _dispute_queryset()
        params = request.query_params
        status_param = params.get('status')
        if status_param == 'open':
            queryset = queryset.filter(status__in=services.OPEN_DISPUTE_STATUSES)
        elif status_param:
            queryset = queryset.filter(status=status_param)
        reason = params.get('reason')
        if reason:
            queryset = queryset.filter(reason=reason)
        needle = params.get('q')
        if needle:
            queryset = queryset.filter(
                Q(reference__icontains=needle)
                | Q(order__number__icontains=needle)
                | Q(seller_order__store_name__icontains=needle)
                | Q(requested_by__email__icontains=needle)
            )
        paginator = CountItemsPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            [serializers.serialize_dispute_row(d) for d in page]
        )


class StaffDisputeDetailView(APIView):
    """GET /api/v1/admin/disputes/<reference>/ — the full dispute record."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def get(self, request, reference):
        dispute = _dispute_queryset().filter(reference=reference).first()
        if dispute is None:
            return _not_found()
        return Response(serializers.serialize_dispute(dispute))


class StaffDisputeReviewView(APIView):
    """POST /api/v1/admin/disputes/<reference>/review — claim for review (§17.3)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def post(self, request, reference):
        try:
            dispute = services.review_dispute(request.user, reference)
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class StaffDisputeResolveView(APIView):
    """POST /api/v1/admin/disputes/<reference>/resolve — the staff ruling.

    Resolution and reason are mandatory and recorded on the case, in the
    timeline and in the audit trail (§17.3 resolution/reason/audit trail).
    Money still never moves here — a buyer win is settled through the
    finance-gated §17.2 payout.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def post(self, request, reference):
        serializer = serializers.DisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            dispute = services.resolve_dispute(
                request.user,
                reference,
                resolution=data['resolution'],
                reason=data.get('reason', ''),
            )
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))


class StaffDisputeStatementView(APIView):
    """POST /api/v1/admin/disputes/<reference>/statements — a support note."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = STAFF_GROUPS

    def post(self, request, reference):
        serializer = serializers.DisputeStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dispute = services.add_dispute_statement(
                request.user, reference, body=serializer.validated_data['body']
            )
        except Dispute.DoesNotExist:
            return _not_found()
        except services.ReturnError as exc:
            return _rejected(exc)
        return Response(serializers.serialize_dispute(dispute))
