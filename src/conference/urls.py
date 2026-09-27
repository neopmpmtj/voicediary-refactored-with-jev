from django.urls import path

from src.conference import views

app_name = "conference"

urlpatterns = [
    path("", views.conference_page, name="record"),
    path("list/", views.conference_list, name="list"),
    path("start/", views.start, name="start"),
    path("segment/", views.upload_segment, name="segment"),
    path("stop/", views.stop, name="stop"),
]
