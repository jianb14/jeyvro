from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'stores'

router = DefaultRouter()
router.register(
    'admin/applications', views.StaffApplicationViewSet, basename='admin-applications'
)
router.register(
    'admin/stores', views.StaffStoreViewSet, basename='admin-stores'
)

urlpatterns = [
    path('apply', views.ApplyView.as_view(), name='apply'),
    path('my/store', views.MyStoreView.as_view(), name='my-store'),
    path('my/dashboard', views.MyStoreDashboardView.as_view(), name='my-dashboard'),
    path('public/', views.PublicStoreListView.as_view(), name='public-stores'),
    path('public/<slug:slug>/', views.PublicStoreDetailView.as_view(), name='public-store'),
    path(
        'admin/applications/<int:pk>/review',
        views.ReviewApplicationView.as_view(),
        name='review-application',
    ),
    path(
        'admin/stores/<int:pk>/suspend',
        views.SuspendStoreView.as_view(),
        name='admin-store-suspend',
    ),
    path(
        'admin/stores/<int:pk>/activate',
        views.ActivateStoreView.as_view(),
        name='admin-store-activate',
    ),
    path('', include(router.urls)),
]
