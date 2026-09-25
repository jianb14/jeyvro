from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.CheckoutPreviewView.as_view(), name='checkout-preview'),
    path('checkout/orders', views.CheckoutOrderView.as_view(), name='checkout-orders'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<str:number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<str:number>/cancel', views.OrderCancelView.as_view(), name='order-cancel'),

    # Phase 10: Fulfillment endpoints (§10.1, §10.2, §10.3)
    path('seller/orders/', views.SellerOrderListView.as_view(), name='seller-order-list'),
    path('seller/orders/<int:pk>/', views.SellerOrderDetailView.as_view(), name='seller-order-detail'),
    path('seller/orders/<int:pk>/process', views.SellerOrderProcessView.as_view(), name='seller-order-process'),
    path('seller/orders/<int:pk>/pack', views.SellerOrderPackView.as_view(), name='seller-order-pack'),
    path('seller/orders/<int:pk>/ship', views.SellerOrderShipView.as_view(), name='seller-order-ship'),
    path('shipments/track/<str:tracking_number>/', views.ShipmentTrackView.as_view(), name='shipment-track'),
    path('shipments/<str:tracking_number>/events', views.ShipmentEventUpdateView.as_view(), name='shipment-event-update'),

]
