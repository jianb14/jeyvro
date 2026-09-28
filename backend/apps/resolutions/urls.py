from django.urls import path

from . import views

app_name = 'resolutions'

urlpatterns = [
    # Customer returns (§17.1)
    path(
        'orders/<str:number>/return-eligibility',
        views.OrderReturnEligibilityView.as_view(),
        name='return-eligibility',
    ),
    path(
        'orders/<str:number>/returns',
        views.OrderReturnApplyView.as_view(),
        name='return-apply',
    ),
    path('returns/', views.CustomerReturnListView.as_view(), name='return-list'),
    path(
        'returns/<str:reference>/',
        views.CustomerReturnDetailView.as_view(),
        name='return-detail',
    ),
    path(
        'returns/<str:reference>/cancel',
        views.CustomerReturnCancelView.as_view(),
        name='return-cancel',
    ),
    # Seller desk (§17.1 seller response, return shipment, restocking)
    path('seller/returns/', views.SellerReturnListView.as_view(), name='seller-return-list'),
    path(
        'seller/returns/<str:reference>/',
        views.SellerReturnDetailView.as_view(),
        name='seller-return-detail',
    ),
    path(
        'seller/returns/<str:reference>/respond',
        views.SellerReturnRespondView.as_view(),
        name='seller-return-respond',
    ),
    path(
        'seller/returns/<str:reference>/shipment',
        views.SellerReturnShipmentView.as_view(),
        name='seller-return-shipment',
    ),
    path(
        'seller/returns/<str:reference>/receive',
        views.SellerReturnReceiveView.as_view(),
        name='seller-return-receive',
    ),
    path(
        'seller/returns/<str:reference>/close',
        views.SellerReturnCloseView.as_view(),
        name='seller-return-close',
    ),
    # Staff intervention (§4 groups, §17.1 admin intervention)
    path('admin/returns/', views.StaffReturnListView.as_view(), name='staff-return-list'),
    path(
        'admin/returns/reference/',
        views.StaffReturnReferenceView.as_view(),
        name='staff-return-reference',
    ),
    path(
        'admin/returns/<str:reference>/decide',
        views.StaffReturnDecideView.as_view(),
        name='staff-return-decide',
    ),
    path(
        'admin/returns/<str:reference>/refund',
        views.StaffReturnPayoutView.as_view(),
        name='staff-return-refund',
    ),
    # Customer disputes (§17.3 buyer escalation)
    path(
        'orders/<str:number>/disputes',
        views.CustomerDisputeCreateView.as_view(),
        name='dispute-create',
    ),
    path('disputes/', views.CustomerDisputeListView.as_view(), name='dispute-list'),
    path(
        'disputes/<str:reference>/',
        views.CustomerDisputeDetailView.as_view(),
        name='dispute-detail',
    ),
    path(
        'disputes/<str:reference>/statements',
        views.CustomerDisputeStatementView.as_view(),
        name='dispute-statement',
    ),
    path(
        'disputes/<str:reference>/evidence',
        views.CustomerDisputeEvidenceView.as_view(),
        name='dispute-evidence',
    ),
    path(
        'disputes/<str:reference>/cancel',
        views.CustomerDisputeCancelView.as_view(),
        name='dispute-cancel',
    ),
    # Seller desk (§17.3 seller statement)
    path(
        'seller/disputes/',
        views.SellerDisputeListView.as_view(),
        name='seller-dispute-list',
    ),
    path(
        'seller/disputes/<str:reference>/',
        views.SellerDisputeDetailView.as_view(),
        name='seller-dispute-detail',
    ),
    path(
        'seller/disputes/<str:reference>/respond',
        views.SellerDisputeRespondView.as_view(),
        name='seller-dispute-respond',
    ),
    # Staff adjudication (§4 groups, §17.3 staff review/resolution)
    path(
        'admin/disputes/',
        views.StaffDisputeListView.as_view(),
        name='staff-dispute-list',
    ),
    path(
        'admin/disputes/<str:reference>/',
        views.StaffDisputeDetailView.as_view(),
        name='staff-dispute-detail',
    ),
    path(
        'admin/disputes/<str:reference>/review',
        views.StaffDisputeReviewView.as_view(),
        name='staff-dispute-review',
    ),
    path(
        'admin/disputes/<str:reference>/resolve',
        views.StaffDisputeResolveView.as_view(),
        name='staff-dispute-resolve',
    ),
    path(
        'admin/disputes/<str:reference>/statements',
        views.StaffDisputeStatementView.as_view(),
        name='staff-dispute-statement',
    ),
]
