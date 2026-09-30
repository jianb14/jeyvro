"""Moderation staff API (§20.2 — the queue the automatic rules feed).

Two endpoints and no more: a worklist and a decision. The worklist is
readable by the groups that oversee trust (support, moderator, administrator)
while the *decision* is narrower — resolving a flag hides or restores a
customer's review, which is the moderator/administrator power §4 already
grants over reviews. Support may look; only a moderator may act (§4).
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import InStaffGroup

from . import services
from .models import ContentFlag
from .serializers import ContentFlagSerializer, ResolveFlagSerializer


class ContentFlagListView(APIView):
    """The staff worklist — `?status=open|dismissed|confirmed|all`."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['support', 'moderator', 'administrator']

    def get(self, request):
        raw = (request.query_params.get('status') or ContentFlag.Status.OPEN).strip()
        status_filter = '' if raw in ('all', '') else raw
        if status_filter and status_filter not in ContentFlag.Status.values:
            return Response(
                {'error': 'Unknown status filter.'}, status=status.HTTP_400_BAD_REQUEST
            )
        kind = (request.query_params.get('kind') or '').strip()
        if kind and kind not in ContentFlag.Kind.values:
            return Response(
                {'error': 'Unknown kind filter.'}, status=status.HTTP_400_BAD_REQUEST
            )

        # `services.queue` reads a blank status as "no filter", so `all` is passed
        # straight through — defaulting a blank back to OPEN here would make the
        # documented `?status=all` silently return the open pile again.
        flags = services.queue(
            status=status_filter,
            kind=kind,
        )
        serializer = ContentFlagSerializer(flags, many=True)
        return Response({
            'count': len(serializer.data),
            'open_count': services.open_flag_count(),
            'items': serializer.data,
        })


class ContentFlagResolveView(APIView):
    """Dismiss (the rule misfired) or confirm (it was abuse)."""

    permission_classes = [IsAuthenticated, InStaffGroup]
    required_groups = ['moderator', 'administrator']

    def post(self, request, pk):
        serializer = ResolveFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flag = ContentFlag.objects.filter(pk=pk).first()
        if flag is None:
            return Response(
                {'error': 'Flag not found.'}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            services.resolve_flag(
                request.user,
                flag,
                action=serializer.validated_data['action'],
                note=serializer.validated_data.get('note', ''),
            )
        except services.ModerationError as exc:
            return Response(
                {'error': str(exc), 'code': exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        flag.refresh_from_db()
        return Response(ContentFlagSerializer(flag).data)
