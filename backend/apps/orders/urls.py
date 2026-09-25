from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.CheckoutPreviewView.as_view(), name='checkout-preview'),
    path('checkout/orders', views.CheckoutOrderView.as_view(), name='checkout-orders'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<str:number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<str:number>/cancel', views.OrderCancelView.as_view(), name='order-cancel'),
]
