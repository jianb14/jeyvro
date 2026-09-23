from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'accounts'

router = DefaultRouter()
router.register('addresses', views.AddressViewSet, basename='address')

urlpatterns = [
    path('csrf', views.CsrfView.as_view(), name='csrf'),
    path('register', views.RegisterView.as_view(), name='register'),
    path('login', views.LoginView.as_view(), name='login'),
    path('logout', views.LogoutView.as_view(), name='logout'),
    path('me', views.MeView.as_view(), name='me'),
    path('change-password', views.ChangePasswordView.as_view(), name='change-password'),
    path('verify-email', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification', views.ResendVerificationView.as_view(), name='resend-verification'),
    path('password-reset', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('notification-preferences', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('', include(router.urls)),
]
