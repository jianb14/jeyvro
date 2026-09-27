"""Notification views (Phase 15 — ROADMAP §15.2)."""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        category = request.query_params.get('category')
        if category:
            notifications = notifications.filter(category=category)
        
        unread_only = request.query_params.get('unread')
        if unread_only in ('1', 'true', 'True'):
            notifications = notifications.filter(is_read=False)

        serializer = NotificationSerializer(notifications[:50], many=True)
        unread_count = services.get_unread_notification_count(request.user)
        return Response({
            'count': notifications.count(),
            'unread_count': unread_count,
            'items': serializer.data,
        })


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = services.get_unread_notification_count(request.user)
        return Response({'unread_count': count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = services.mark_notification_as_read(pk, request.user)
        except ObjectDoesNotExist:
            return Response(
                {'error': 'Notification not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = services.mark_all_notifications_as_read(request.user)
        return Response({'updated': updated_count, 'unread_count': 0})
