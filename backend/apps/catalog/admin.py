from django.contrib import admin

from .models import Brand, Category, Product, ProductImage, Variant

admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Product)
admin.site.register(Variant)
admin.site.register(ProductImage)