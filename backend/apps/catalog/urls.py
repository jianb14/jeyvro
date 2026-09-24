from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'catalog'

router = DefaultRouter()
router.register('products', views.PublicProductViewSet, basename='products')
router.register('categories', views.CategoryViewSet, basename='categories')
router.register('brands', views.BrandViewSet, basename='brands')
router.register('my/products', views.SellerProductViewSet, basename='my-products')
router.register('admin/products', views.StaffProductReviewViewSet, basename='admin-products')

urlpatterns = [
    path('my/stock', views.SellerStockView.as_view(), name='my-stock'),
    path(
        'admin/products/<int:pk>/review',
        views.StaffProductReviewActionView.as_view(),
        name='admin-product-review',
    ),
    path('', include(router.urls)),
]