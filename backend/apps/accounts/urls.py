from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'accounts'

router = DefaultRouter()
router.register('addresses', views.AddressViewSet, basename='address')
# Phase 13.1/13.2 staff administration (group-gated inside the views).
router.register('admin/users', views.AdminUserViewSet, basename='admin-user')
router.register('admin/staff', views.StaffMemberViewSet, basename='admin-staff')

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
    path('admin/users/<int:pk>/suspend', views.SuspendUserView.as_view(), name='admin-user-suspend'),
    path('admin/users/<int:pk>/reactivate', views.ReactivateUserView.as_view(), name='admin-user-reactivate'),
    path('admin/staff/<int:pk>/roles/assign', views.AssignStaffRoleView.as_view(), name='admin-staff-role-assign'),
    path('admin/staff/<int:pk>/roles/remove', views.RemoveStaffRoleView.as_view(), name='admin-staff-role-remove'),
    path('', include(router.urls)),
]
