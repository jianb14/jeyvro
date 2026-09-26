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

    # Phase 11: Customer account & order management (§11.2, §11.3)
    path('orders/<str:number>/reorder', views.OrderReorderView.as_view(), name='order-reorder'),
    path('orders/<str:number>/requests', views.OrderRequestCreateView.as_view(), name='order-request-create'),
    path('orders/<str:number>/requests/<int:pk>/withdraw', views.OrderRequestWithdrawView.as_view(), name='order-request-withdraw'),

    # Phase 13.5: staff order/shipment/request oversight (§4 groups).
    path('admin/orders/', views.StaffOrderListView.as_view(), name='staff-order-list'),
    path('admin/orders/<str:number>/', views.StaffOrderDetailView.as_view(), name='staff-order-detail'),
    path('admin/shipments/', views.StaffShipmentListView.as_view(), name='staff-shipment-list'),
    path('admin/requests/', views.StaffOrderRequestListView.as_view(), name='staff-order-request-list'),

]
