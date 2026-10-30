from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/2fa/setup/", views.TwoFactorSetupView.as_view(), name="auth-2fa-setup"),
    path("auth/2fa/confirm/", views.TwoFactorConfirmView.as_view(), name="auth-2fa-confirm"),
    path("auth/password-reset/", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("auth/password-change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path("me/", views.MeView.as_view(), name="me"),
]
