from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.diary.models import Attachment, Entry, ItemType

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


def _pdf(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-fake", content_type="application/pdf")


def _audio():
    return SimpleUploadedFile("clip.webm", b"audio-bytes", content_type="audio/webm")


def _classify_ok(_state):
    return {
        "answers": {
            "intent": {"choice": "freeform", "confidence": 0.9},
            "subject": {"choice": "diary", "confidence": 0.8},
            "user_asked_for_diary": {"noul": 0.2},
            "continues_prior": {"noul": 0.1},
        },
        "usage": {"input_tokens": 2, "output_tokens": 1},
    }


def test_text_post_with_file_links_attachment(auth_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        response = auth_client.post(
            "/text-input/",
            {"text": "Receipt", "files": _pdf("receipt.pdf")},
        )
    assert response.status_code == 302
    entry = Entry.objects.get()
    assert entry.item_type == ItemType.TEXT
    attached = Attachment.objects.get(entry=entry)
    assert attached.original_filename == "receipt.pdf"
    assert attached.uploaded_at is not None


def test_text_post_without_file_creates_no_attachment(auth_client):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        response = auth_client.post("/text-input/", {"text": "No file"})
    assert response.status_code == 302
    assert Attachment.objects.count() == 0


def test_files_only_text_post_is_a_standalone_entry(auth_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    response = auth_client.post("/text-input/", {"text": "", "files": _pdf("solo.png")})
    assert response.status_code == 302
    entry = Entry.objects.get()
    assert entry.item_type == ItemType.FILE
    assert entry.attachments.get().original_filename == "solo.png"


def test_standalone_file_upload_creates_file_entry(auth_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    response = auth_client.post(
        "/files/upload/",
        {"files": _pdf("alone.pdf")},
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["attachment_count"] == 1
    entry = Entry.objects.get(pk=data["item_id"])
    assert entry.item_type == ItemType.FILE
    assert Attachment.objects.filter(entry=entry).count() == 1


def test_add_files_to_existing_entry(auth_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Existing")
    response = auth_client.post(
        "/files/upload/",
        {"entry_id": str(entry.id), "files": _pdf("extra.pdf")},
    )
    assert response.status_code == 302
    assert entry.attachments.get().original_filename == "extra.pdf"


@patch("src.diary.services.transcribe_audio", return_value={"text": "hello", "duration": 1, "model": "x"})
@patch("src.diary.services.probe_duration_seconds", return_value=1.0)
@patch("src.diary.services.strip_silence", return_value=False)
def test_audio_upload_with_files_links_them(mock_strip, mock_probe, mock_transcribe, auth_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        response = auth_client.post(
            "/voice/upload/",
            {"audio": _audio(), "files": _pdf("with-voice.pdf"), "recording_duration_seconds": "1"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["attachment_count"] == 1
    entry = Entry.objects.get(pk=data["item_id"])
    assert entry.item_type == ItemType.AUDIO
    assert entry.attachments.get().original_filename == "with-voice.pdf"


def test_download_attachment_is_limited_to_owner(auth_client, user, django_user_model, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files
    entry = ingest_files(user, [_pdf("mine.pdf")])
    attachment = entry.attachments.get()
    response = auth_client.get(f"/files/{attachment.id}/")
    assert response.status_code == 200
    other = django_user_model.objects.create_user(email="other@example.com", password="pass")
    auth_client.force_login(other)
    denied = auth_client.get(f"/files/{attachment.id}/")
    assert denied.status_code == 404
