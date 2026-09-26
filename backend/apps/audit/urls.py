from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'audit'

router = DefaultRouter()
router.register('events', views.StaffAuditLogViewSet, basename='audit-events')

urlpatterns = [
    path('', include(router.urls)),
]
