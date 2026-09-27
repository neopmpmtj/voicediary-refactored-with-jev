from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.diary.models import Attachment, Entry

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


def test_entries_page_includes_delete_edit_and_copy(auth_client, user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        ingest_text(user, "A note")
    listing = auth_client.get("/entries/")
    assert listing.status_code == 200
    html = listing.content.decode()
    assert "Delete" in html
    assert "Edit" in html
    assert "Copy" in html
    assert "vd-btn-destructive" in html
    assert "entry-copy-btn" in html
    assert "edit-entry-modal" in html


def test_delete_post_soft_deletes_entry_and_attachment(auth_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Keep transcript", uploads=[_pdf("gone.pdf")])
    attachment = entry.attachments.get()
    path = tmp_path / attachment.relative_path
    assert path.is_file()
    response = auth_client.post(
        f"/entries/{entry.id}/delete/",
        HTTP_ACCEPT="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(entry.id)
    assert data["attachments"] == [str(attachment.id)]
    assert not path.exists()
    entry.refresh_from_db()
    assert entry.is_deleted is True
    assert entry.content_text == "Keep transcript"
    attachment.refresh_from_db()
    assert attachment.is_deleted is True
    listing = auth_client.get("/entries/")
    assert b"Keep transcript" not in listing.content


def test_delete_post_is_404_for_another_user(auth_client, user, django_user_model):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Private")
    other = django_user_model.objects.create_user(email="other@example.com", password="pass")
    auth_client.force_login(other)
    response = auth_client.post(f"/entries/{entry.id}/delete/")
    assert response.status_code == 404
    entry.refresh_from_db()
    assert entry.is_deleted is False


def test_edit_post_changes_text_and_leaves_classification(auth_client, user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Original")
    assert entry.intent == "freeform"
    assert entry.subject == "diary"
    response = auth_client.post(
        f"/entries/{entry.id}/edit/",
        {"content_text": "Revised note"},
        follow=True,
    )
    assert response.status_code == 200
    entry.refresh_from_db()
    assert entry.content_text == "Revised note"
    assert entry.intent == "freeform"
    assert entry.subject == "diary"
    assert b"Revised note" in response.content
    assert b"Entry saved." in response.content
