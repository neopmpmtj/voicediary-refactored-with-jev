from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("google/login/", views.GoogleLoginView.as_view(), name="google_login"),
    path("google/callback/", views.GoogleCallbackView.as_view(), name="google_callback"),
    path("google/link-confirm/", views.GoogleLinkConfirmView.as_view(), name="google_link_confirm"),
    path("google/connect/", views.GoogleConnectView.as_view(), name="google_connect"),
    path("google/connect/callback/", views.GoogleConnectCallbackView.as_view(), name="google_connect_callback"),
    path("google/disconnect/", views.GoogleDisconnectView.as_view(), name="google_disconnect"),
]
