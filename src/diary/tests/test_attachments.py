from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.diary.models import Attachment, Entry, ItemType
from src.diary.services import ingest_files, ingest_text, store_attachments
from src.diary.storage import (
    ATTACHMENTS_SUBDIR,
    ARTIFACTS_SUBDIR,
    allocate_unique_attachment_filename,
    artifacts_dir_for_user,
    sanitize_storage_filename,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_sanitize_storage_filename_strips_unsafe_characters():
    assert sanitize_storage_filename("inv@ice#.pdf") == "invice.pdf"
    assert sanitize_storage_filename("") == "uploaded_file"


def test_allocate_unique_attachment_filename_avoids_collisions(tmp_path):
    used = set()
    first = allocate_unique_attachment_filename(tmp_path, "doc.pdf", used)
    (tmp_path / first).write_bytes(b"a")
    second = allocate_unique_attachment_filename(tmp_path, "doc.pdf", used)
    assert first == "doc.pdf"
    assert second == "doc_1.pdf"


def test_artifacts_live_in_a_separate_folder(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    folder = artifacts_dir_for_user(9)
    assert folder == tmp_path / ARTIFACTS_SUBDIR / "9"
    assert folder.is_dir()
    assert folder.parts[-2] == ARTIFACTS_SUBDIR


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="pat@example.com", password="pass")


def _pdf(name="note.pdf", body=b"%PDF-1.4"):
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def test_files_without_a_conversation_become_their_own_entry(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    entry = ingest_files(user, [_pdf("photo.jpg", b"img"), _pdf("scan.pdf")])
    assert entry.item_type == ItemType.FILE
    files = list(entry.attachments.all())
    assert [item.original_filename for item in files] == ["photo.jpg", "scan.pdf"]
    assert all(item.uploaded_at is not None for item in files)
    for item in files:
        path = tmp_path / item.relative_path
        assert path.is_file()
        assert ATTACHMENTS_SUBDIR in Path(item.relative_path).parts
        assert ARTIFACTS_SUBDIR not in Path(item.relative_path).parts


def test_text_input_with_files_links_attachments_to_that_entry(user, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path

    def fake_decide(state):
        return {
            "answers": {
                "intent": {"choice": "freeform", "confidence": 0.9},
                "subject": {"choice": "diary", "confidence": 0.8},
                "user_asked_for_diary": {"noul": 0.1},
                "continues_prior": {"noul": 0.1},
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }

    monkeypatch.setattr("src.diary.services.decide", fake_decide)
    entry = ingest_text(user, "Fridge photo", uploads=[_pdf()])
    assert entry.item_type == ItemType.TEXT
    assert entry.content_text == "Fridge photo"
    attached = Attachment.objects.get(entry=entry)
    assert attached.original_filename == "note.pdf"
    assert attached.entry_id == entry.id


def test_text_without_files_has_no_attachment_rows(user, monkeypatch):
    monkeypatch.setattr(
        "src.diary.services.decide",
        lambda state: {
            "answers": {
                "intent": {"choice": "freeform", "confidence": 1},
                "subject": {"choice": "diary", "confidence": 1},
            },
            "usage": {},
        },
    )
    entry = ingest_text(user, "Just text")
    assert entry.attachments.count() == 0


def test_files_can_be_added_to_an_existing_entry(user, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr(
        "src.diary.services.decide",
        lambda state: {"answers": {}, "usage": {}},
    )
    entry = ingest_text(user, "Later attach")
    store_attachments(user, entry, [_pdf("later.pdf")])
    attached = Attachment.objects.get(entry=entry)
    assert attached.original_filename == "later.pdf"
    assert attached.uploaded_at is not None
