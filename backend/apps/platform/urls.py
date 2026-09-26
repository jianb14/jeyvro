"""Platform URLs — mounted at the API root (config/urls.py).

Paths mirror the other staff surfaces: admin settings live under
/api/v1/admin/…, the public subset under /api/v1/platform/….
"""
from django.urls import path

from . import views

app_name = 'platform'

urlpatterns = [
    path(
        'admin/settings/',
        views.StaffSettingsView.as_view(),
        name='staff-settings',
    ),
    path(
        'admin/settings/commission/',
        views.StaffCommissionSettingsView.as_view(),
        name='staff-commission-settings',
    ),
    path(
        'platform/public/',
        views.PublicPlatformInfoView.as_view(),
        name='public-platform-info',
    ),
]
