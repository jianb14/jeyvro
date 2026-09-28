from django.urls import path

from . import views

app_name = 'promotions'

urlpatterns = [
    # Public buyer endpoints (§16.1, §16.2, §16.4)
    path('vouchers/', views.PublicVoucherListView.as_view(), name='voucher-list'),
    path('vouchers/validate/', views.VoucherValidateView.as_view(), name='voucher-validate'),
    path('promotions/', views.PublicPromotionListView.as_view(), name='promotion-list'),
    path('campaigns/', views.PublicCampaignListView.as_view(), name='campaign-list'),
    # Seller promotion management (§16.4)
    path('seller/promotions/', views.SellerPromotionListView.as_view(), name='seller-promotion-list'),
    path('seller/promotions/<int:pk>/', views.SellerPromotionDetailView.as_view(), name='seller-promotion-detail'),
    # Staff promotion & campaign consoles (§16.4)
    path('staff/promotions/', views.StaffPromotionListView.as_view(), name='staff-promotion-list'),
    path('staff/campaigns/', views.StaffCampaignListView.as_view(), name='staff-campaign-list'),
]
