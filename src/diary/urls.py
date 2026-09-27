from django.urls import path

from src.diary import views

app_name = "diary"

urlpatterns = [
    path("voice/", views.voice_page, name="voice"),
    path("voice/upload/", views.upload_audio, name="upload"),
    path("text-input/", views.text_page, name="text"),
    path("entries/", views.entry_list, name="list"),
    path("files/upload/", views.upload_files, name="upload_files"),
    path("files/<uuid:attachment_id>/", views.download_attachment, name="download"),
]
