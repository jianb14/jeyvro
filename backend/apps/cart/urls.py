from django.urls import path

from . import views

app_name = 'cart'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/items', views.CartItemsView.as_view(), name='cart-items'),
    path('cart/items/<int:pk>', views.CartItemDetailView.as_view(), name='cart-item'),
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path(
        'wishlist/items/<slug:slug>',
        views.WishlistItemDetailView.as_view(),
        name='wishlist-item',
    ),
]
