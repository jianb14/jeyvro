from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'stores'

router = DefaultRouter()
router.register(
    'admin/applications', views.StaffApplicationViewSet, basename='admin-applications'
)

urlpatterns = [
    path('apply', views.ApplyView.as_view(), name='apply'),
    path('my/store', views.MyStoreView.as_view(), name='my-store'),
    path('public/<slug:slug>/', views.PublicStoreDetailView.as_view(), name='public-store'),
    path(
        'admin/applications/<int:pk>/review',
        views.ReviewApplicationView.as_view(),
        name='review-application',
    ),
    path('', include(router.urls)),
]