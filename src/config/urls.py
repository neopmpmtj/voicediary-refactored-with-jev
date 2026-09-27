from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from src.accounts.views import GoogleCallbackView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="diary:voice")),
    path("admin/", admin.site.urls),
    path("accounts/", include("src.accounts.urls")),
    path("conference/", include("src.conference.urls")),
    path("src.accounts/google/callback/", GoogleCallbackView.as_view()),
    path("", include("src.diary.urls")),
]
