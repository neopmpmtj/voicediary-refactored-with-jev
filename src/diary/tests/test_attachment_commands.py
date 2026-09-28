import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from src.diary.models import Entry, ItemType
from src.diary.services import ingest_files, ingest_text

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


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


def test_attachment_list_json_includes_relative_path(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    entry = ingest_files(user, [_pdf("note.pdf")])
    attachment = entry.attachments.get()
    out = StringIO()
    call_command("attachment_list", "--email", user.email, "--json", stdout=out)
    rows = json.loads(out.getvalue())
    assert len(rows) == 1
    item = rows[0]
    assert item["id"] == str(attachment.id)
    assert item["entry_id"] == str(entry.id)
    assert item["original_filename"] == "note.pdf"
    assert item["relative_path"] == attachment.relative_path


def test_attachment_list_filters_by_entry(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    first = ingest_files(user, [_pdf("one.pdf")])
    ingest_files(user, [_pdf("two.pdf")])
    out = StringIO()
    call_command(
        "attachment_list",
        "--email",
        user.email,
        "--entry",
        str(first.id),
        "--json",
        stdout=out,
    )
    rows = json.loads(out.getvalue())
    assert len(rows) == 1
    assert rows[0]["original_filename"] == "one.pdf"


def test_attachment_add_creates_file_entry(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    source = tmp_path / "clip.pdf"
    source.write_bytes(b"%PDF-cli")
    out = StringIO()
    call_command(
        "attachment_add",
        str(source),
        "--email",
        user.email,
        "--json",
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    entry = Entry.objects.get(pk=payload["id"])
    assert entry.item_type == ItemType.FILE
    assert entry.content_text == "clip.pdf"
    assert entry.attachments.get().original_filename == "clip.pdf"


def test_attachment_add_links_to_existing_entry(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        entry = ingest_text(user, "Keep this note")
    source = tmp_path / "extra.pdf"
    source.write_bytes(b"%PDF-extra")
    out = StringIO()
    call_command(
        "attachment_add",
        str(source),
        "--email",
        user.email,
        "--entry",
        str(entry.id),
        "--json",
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    assert payload["id"] == str(entry.id)
    assert payload["content_text"] == "Keep this note"
    assert payload["attachment_count"] == 1
    entry.refresh_from_db()
    assert entry.item_type == ItemType.TEXT
    assert entry.attachments.get().original_filename == "extra.pdf"


def test_attachment_add_missing_file(user):
    with pytest.raises(CommandError, match="Unknown file"):
        call_command("attachment_add", "/no/such/file.pdf", "--email", user.email)
