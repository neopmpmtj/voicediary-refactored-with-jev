import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

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


def test_entries_page_hides_edit_until_checkbox(auth_client, user):
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
    assert "rewrite-entry-modal" not in html
    assert 'id="edit-enable"' in html
    assert "checked" not in html.split('id="edit-enable"', 1)[1].split(">", 1)[0]
    assert "entry-edit-btn hidden" in html
    assert "entry-rewrite-btn" not in html
    assert "Grammar" in html
    assert "Professional" in html
    assert "/entries/rewrite/" in html


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
    created = timezone.now() - timedelta(minutes=2)
    Entry.objects.filter(pk=entry.pk).update(created_at=created, updated_at=created)
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
    assert entry.updated_at > entry.created_at
    assert entry.was_modified()
    assert b"Revised note" in response.content
    assert b"Entry saved." in response.content
    assert b"modified" in response.content


def test_blank_entry_still_has_hidden_edit_button(auth_client, user):
    Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="")
    listing = auth_client.get("/entries/")
    assert listing.status_code == 200
    html = listing.content.decode()
    assert "entry-edit-btn hidden" in html
    assert "entry-rewrite-btn" not in html
    assert 'id="edit-enable"' in html


def test_rewrite_preview_returns_text_and_leaves_entry(auth_client, user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Original")
    with patch("src.diary.views.rewrite_text") as mock_rewrite:
        mock_rewrite.return_value = {
            "text": "Polished note",
            "model_id": "o3-mini",
            "style": "grammar",
            "input_tokens": 2,
            "output_tokens": 1,
        }
        response = auth_client.post(
            "/entries/rewrite/",
            data=json.dumps({"text": "Original", "style": "grammar"}),
            content_type="application/json",
        )
    assert response.status_code == 200
    assert response.json() == {"text": "Polished note", "style": "grammar"}
    mock_rewrite.assert_called_once_with("Original", style="grammar")
    entry.refresh_from_db()
    assert entry.content_text == "Original"
    assert entry.intent == "freeform"
    assert entry.subject == "diary"


def test_rewrite_preview_rejects_empty_text(auth_client):
    response = auth_client.post(
        "/entries/rewrite/",
        data=json.dumps({"text": "   ", "style": "grammar"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "rewrite_failed"


def test_rewrite_preview_requires_login(client):
    response = client.post(
        "/entries/rewrite/",
        data=json.dumps({"text": "hello", "style": "grammar"}),
        content_type="application/json",
    )
    assert response.status_code == 302
