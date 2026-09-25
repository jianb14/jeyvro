from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    # Gateway callbacks — registered before the detail route on purpose.
    path(
        'webhooks/<str:provider>/',
        views.PaymentWebhookView.as_view(),
        name='webhook',
    ),
    path(
        '<str:reference>/',
        views.PaymentDetailView.as_view(),
        name='payment-detail',
    ),
    path(
        '<str:reference>/cod-collected',
        views.CodCollectedView.as_view(),
        name='cod-collected',
    ),
    path(
        '<str:reference>/refunds',
        views.RefundView.as_view(),
        name='refund-create',
    ),
]
