"""Moderation URLs — staff trust & safety under the API root."""
from django.urls import path

from . import views

app_name = 'moderation'

urlpatterns = [
    path(
        'admin/moderation/flags/',
        views.ContentFlagListView.as_view(),
        name='content-flag-list',
    ),
    path(
        'admin/moderation/flags/<int:pk>/resolve/',
        views.ContentFlagResolveView.as_view(),
        name='content-flag-resolve',
    ),
]
