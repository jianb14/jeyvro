from django.contrib import admin

from .models import SellerApplication, Store

admin.site.register(Store)
admin.site.register(SellerApplication)