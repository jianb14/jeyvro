from django.contrib import admin
from django.urls import path

from .models import Address, User

admin.site.register(User)
admin.site.register(Address)