import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

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


def test_media_release_soft_deletes_an_attachment_and_leaves_the_text_entry(auth_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Keep this note", uploads=[_pdf("gone.pdf")])
    attachment = entry.attachments.get()
    path = tmp_path / attachment.relative_path
    assert path.is_file()
    out = StringIO()
    call_command("media_release", str(path), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["bytes_freed"] > 0
    assert payload["attachments"] == [str(attachment.id)]
    assert payload["entries"] == []
    assert not path.exists()
    attachment.refresh_from_db()
    assert attachment.is_deleted is True
    assert attachment.deleted_at is not None
    entry.refresh_from_db()
    assert entry.is_deleted is False
    assert entry.content_text == "Keep this note"
    listing = auth_client.get("/entries/")
    assert b"Keep this note" in listing.content
    assert b"gone.pdf" not in listing.content


def test_media_release_soft_deletes_a_file_only_entry(auth_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files
    entry = ingest_files(user, [_pdf("solo.pdf")])
    attachment = entry.attachments.get()
    path = tmp_path / attachment.relative_path
    out = StringIO()
    call_command("media_release", str(path), stdout=out)
    assert str(entry.id) in out.getvalue()
    attachment.refresh_from_db()
    assert attachment.is_deleted is True
    entry.refresh_from_db()
    assert entry.is_deleted is True
    assert Entry.objects.filter(pk=entry.id).exists()
    listing = auth_client.get("/entries/")
    assert b"solo.pdf" not in listing.content
    assert b"No entries yet." in listing.content


def test_media_release_refuses_a_path_outside_media(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir()
    from src.diary.services import ingest_files
    entry = ingest_files(user, [_pdf("kept.pdf")])
    attachment = entry.attachments.get()
    stored = tmp_path / "media" / attachment.relative_path
    outsider = tmp_path / "outside.pdf"
    outsider.write_bytes(b"nope")
    with pytest.raises(CommandError, match="outside media"):
        call_command("media_release", str(outsider))
    assert outsider.is_file()
    attachment.refresh_from_db()
    assert attachment.is_deleted is False
    assert stored.is_file()


def test_media_release_refuses_a_directory(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files
    entry = ingest_files(user, [_pdf("kept.pdf")])
    attachment = entry.attachments.get()
    folder = (tmp_path / attachment.relative_path).parent
    with pytest.raises(CommandError, match="directory"):
        call_command("media_release", str(folder))
    attachment.refresh_from_db()
    assert attachment.is_deleted is False
    assert (tmp_path / attachment.relative_path).is_file()
