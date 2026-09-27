from django.urls import path

from . import views

app_name = 'promotions'

urlpatterns = [
    path('vouchers/validate/', views.VoucherValidateView.as_view(), name='voucher-validate'),
]
