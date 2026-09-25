from django.contrib import admin

from .models import Order, OrderItem, SellerOrder

admin.site.register(Order)
admin.site.register(SellerOrder)
admin.site.register(OrderItem)
