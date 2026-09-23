"""
JEYVRO URL configuration.

API rules (backend-api): versioned /api/v1/ only, JSON only — handler404 and
handler500 return JSON so HTML error pages never leave Django (§8).
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def json404(request, exception=None):
    return JsonResponse({'error': 'not_found'}, status=404)


def json500(request):
    return JsonResponse({'error': 'server_error'}, status=500)


handler404 = 'config.urls.json404'
handler500 = 'config.urls.json500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.core.urls')),
]
