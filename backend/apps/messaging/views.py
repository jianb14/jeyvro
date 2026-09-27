"""Messaging API views (Phase 15 — ROADMAP §15.1, §12.6)."""
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.orders.models import Order
from apps.stores.models import Store
from . import services
from .models import Conversation, ConversationStatus, ConversationType, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
    ReportConversationSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)


class CustomerConversationListView(APIView):
    """Customer-facing conversations list and conversation starter."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(customer=request.user).select_related(
            'store', 'order', 'product', 'customer'
        ).prefetch_related('messages')

        serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
        unread_count = sum(item['unread_count'] for item in serializer.data)
        return Response({
            'count': conversations.count(),
            'unread_count': unread_count,
            'items': serializer.data,
        })

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        store = None
        if data.get('store_id'):
            try:
                store = Store.objects.get(pk=data['store_id'])
            except Store.DoesNotExist:
                return Response({'error': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

        order = None
        if data.get('order_id'):
            try:
                order = Order.objects.get(pk=data['order_id'], user=request.user)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        product = None
        if data.get('product_id'):
            try:
                product = Product.objects.get(pk=data['product_id'])
                if not store and product.store:
                    store = product.store
            except Product.DoesNotExist:
                return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            conversation, created = services.start_or_get_conversation(
                request.user,
                store=store,
                order=order,
                product=product,
                conversation_type=data.get('type', ConversationType.SELLER),
                subject=data.get('subject', ''),
                initial_message=data.get('message', ''),
            )
        except (ValidationError, PermissionDenied) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        detail_serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)



class SellerConversationListView(APIView):
    """Seller-facing conversations list for their own store (§12.6)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        seller_stores = Store.objects.filter(user=request.user)
        if not seller_stores.exists():
            return Response({'error': 'You do not own a store.'}, status=status.HTTP_403_FORBIDDEN)

        conversations = Conversation.objects.filter(
            store__in=seller_stores
        ).select_related('store', 'order', 'product', 'customer').prefetch_related('messages')

        serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
        unread_count = sum(item['unread_count'] for item in serializer.data)
        return Response({
            'count': conversations.count(),
            'unread_count': unread_count,
            'items': serializer.data,
        })


class ConversationDetailView(APIView):
    """View conversation thread and messages."""
    permission_classes = [IsAuthenticated]

    def get_conversation(self, pk, user):
        try:
            conv = Conversation.objects.select_related(
                'store', 'order', 'product', 'customer'
            ).prefetch_related('messages__sender').get(pk=pk)
        except Conversation.DoesNotExist:
            return None
        if not services.can_access_conversation(conv, user):
            raise PermissionDenied('You do not have access to this conversation.')
        return conv

    def get(self, request, pk):
        try:
            conversation = self.get_conversation(pk, request.user)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        if not conversation:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        services.mark_conversation_as_read(conversation, request.user)
        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(serializer.data)


class SendMessageView(APIView):
    """Send a message to a conversation."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            message = services.send_message(
                conv,
                request.user,
                body=data.get('body', ''),
                attachment_url=data.get('attachment_url', ''),
            )
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)


class MarkConversationReadView(APIView):
    """Explicit endpoint to mark conversation messages as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
            services.mark_conversation_as_read(conv, request.user)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response({'success': True})


class ReportConversationView(APIView):
    """Report conversation for moderation review."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReportConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            services.report_conversation(
                conv,
                request.user,
                reason=data['reason'],
                details=data.get('details', ''),
            )
        except PermissionDenied as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response({'success': True, 'status': ConversationStatus.REPORTED})


class TotalUnreadCountView(APIView):
    """Combined unread messages count for navbar/badges."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = services.get_total_unread_messages(request.user)
        return Response({'unread_count': count})

