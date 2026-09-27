from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('conversations/', views.CustomerConversationListView.as_view(), name='customer-conversations'),
    path('conversations/unread-count/', views.TotalUnreadCountView.as_view(), name='conversations-unread-count'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:pk>/messages/', views.SendMessageView.as_view(), name='conversation-send-message'),
    path('conversations/<int:pk>/read/', views.MarkConversationReadView.as_view(), name='conversation-mark-read'),
    path('conversations/<int:pk>/report/', views.ReportConversationView.as_view(), name='conversation-report'),
    path('seller/conversations/', views.SellerConversationListView.as_view(), name='seller-conversations'),
]
