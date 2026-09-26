"""Phase 13.6 — platform settings console endpoints (§4 matrix).

Reads are open to administrator/finance/operations; edits narrow per
path: the general PATCH is administrator-only, the commission PATCH is
finance/administrator (§4 — finance owns commission adjustments). The
public endpoint serves only the name + support contact for the storefront
chrome. Business rules live in services (backend-api rule 4).
"""
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup

from . import services
from .serializers import (
    CommissionSettingsSerializer,
    PlatformSettingsSerializer,
    PublicPlatformInfoSerializer,
)

READ_GROUPS = ['administrator', 'finance', 'operations']
GENERAL_WRITE_GROUPS = ['administrator']
COMMISSION_WRITE_GROUPS = ['finance', 'administrator']


class StaffSettingsView(APIView):
    """GET the whole row; PATCH general fields (administrator only)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = READ_GROUPS

    def get_permissions(self):
        # Reads are broader than writes: every non-GET method narrows to
        # the groups that own the fields (§4). The view is instantiated
        # per request, so this swap never leaks across requests.
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            self.required_groups = GENERAL_WRITE_GROUPS
        return super().get_permissions()

    def get(self, request):
        return Response(PlatformSettingsSerializer(services.get_settings()).data)

    def patch(self, request):
        serializer = PlatformSettingsSerializer(
            services.get_settings(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = services.apply_update(
            request.user, changes=serializer.validated_data, scope='general'
        )
        return Response(PlatformSettingsSerializer(updated).data)


class StaffCommissionSettingsView(APIView):
    """PATCH the commission rate (finance or administrator, §4).

    The full row still arrives on the main GET — this path exists so the
    finance group can adjust exactly one field and nothing else.
    """

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = COMMISSION_WRITE_GROUPS

    def patch(self, request):
        serializer = CommissionSettingsSerializer(
            services.get_settings(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated = services.apply_update(
            request.user, changes=serializer.validated_data, scope='commission'
        )
        return Response(PlatformSettingsSerializer(updated).data)


class PublicPlatformInfoView(APIView):
    """Anonymous storefront chrome info — name + support contact only."""

    permission_classes = [AllowAny]

    def get(self, request):
        current = services.get_settings()
        payload = PublicPlatformInfoSerializer({
            'platform_name': current.platform_name,
            'support_email': current.support_email,
        }).data
        return Response(payload)
