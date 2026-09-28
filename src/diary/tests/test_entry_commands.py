import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from src.diary.models import Entry
from src.urls_others.models import Reference

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


def test_entry_list_json_includes_active_and_omits_soft_deleted(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import delete_entry, ingest_text
        kept = ingest_text(user, "Visible")
        gone = ingest_text(user, "Hidden")
    delete_entry(user, gone)
    out = StringIO()
    call_command("entry_list", "--email", user.email, "--json", stdout=out)
    rows = json.loads(out.getvalue())
    ids = [item["id"] for item in rows]
    assert str(kept.id) in ids
    assert str(gone.id) not in ids
    visible = next(item for item in rows if item["id"] == str(kept.id))
    assert visible["content_text"] == "Visible"
    assert visible["item_type"] == "text"


def test_entry_show_prints_content_text(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Show me")
    out = StringIO()
    call_command("entry_show", str(entry.id), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["content_text"] == "Show me"
    assert payload["id"] == str(entry.id)
    plain = StringIO()
    call_command("entry_show", str(entry.id), stdout=plain)
    assert plain.getvalue().strip() == "Show me"


def test_entry_update_changes_text(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "Before")
    out = StringIO()
    call_command("entry_update", str(entry.id), "--text", "After", "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["content_text"] == "After"
    entry.refresh_from_db()
    assert entry.content_text == "After"
    assert entry.intent == "freeform"


def test_entry_delete_soft_deletes_and_second_call_fails(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files
    entry = ingest_files(user, [_pdf("solo.pdf")])
    attachment = entry.attachments.get()
    path = tmp_path / attachment.relative_path
    out = StringIO()
    call_command("entry_delete", str(entry.id), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["id"] == str(entry.id)
    assert not path.exists()
    entry.refresh_from_db()
    assert entry.is_deleted is True
    with pytest.raises(CommandError, match="Unknown entry"):
        call_command("entry_delete", str(entry.id))
    assert Entry.objects.filter(pk=entry.id).exists()


def test_entry_show_with_email_rejects_another_users_id(user, django_user_model):
    other = django_user_model.objects.create_user(email="other@example.com", password="pass")
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(other, "Not yours")
    with pytest.raises(CommandError, match="Unknown entry"):
        call_command("entry_show", str(entry.id), "--email", user.email)
    out = StringIO()
    call_command("entry_list", "--email", user.email, "--json", stdout=out)
    assert json.loads(out.getvalue()) == []


def test_entry_create_json_and_human_output(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        json_out = StringIO()
        call_command(
            "entry_create",
            "--email",
            user.email,
            "--text",
            "a note",
            "--json",
            stdout=json_out,
        )
    payload = json.loads(json_out.getvalue())
    assert payload["content_text"] == "a note"
    assert payload["item_type"] == "text"
    assert payload["id"]
    entry = Entry.objects.get(pk=payload["id"])
    assert entry.user_id == user.pk
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        plain = StringIO()
        call_command(
            "entry_create",
            "--email",
            user.email,
            "--text",
            "second",
            stdout=plain,
        )
    line = plain.getvalue().strip()
    assert line.endswith(" second")
    created_id = line.split(" ", 1)[0]
    assert Entry.objects.filter(pk=created_id, content_text="second").exists()


def test_entry_create_unknown_email_errors(user):
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("entry_create", "--email", "missing@example.com", "--text", "nope")


def test_entry_create_blank_text_errors(user):
    with pytest.raises(CommandError, match="Missing text"):
        call_command("entry_create", "--email", user.email, "--text", "   ")


def test_entry_list_filters_and_limit(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        ingest_text(user, "alpha note")
        later = ingest_text(user, "beta note")
    later.intent = "todo"
    later.subject = "finance"
    later.route = "finance"
    later.save(update_fields=["intent", "subject", "route"])
    q_out = StringIO()
    call_command("entry_list", "--email", user.email, "--q", "beta", "--json", stdout=q_out)
    q_rows = json.loads(q_out.getvalue())
    assert [item["content_text"] for item in q_rows] == ["beta note"]
    intent_out = StringIO()
    call_command("entry_list", "--email", user.email, "--intent", "todo", "--json", stdout=intent_out)
    assert [item["id"] for item in json.loads(intent_out.getvalue())] == [str(later.id)]
    type_out = StringIO()
    call_command("entry_list", "--email", user.email, "--item-type", "text", "--limit", "1", "--json", stdout=type_out)
    type_rows = json.loads(type_out.getvalue())
    assert len(type_rows) == 1
    assert type_rows[0]["content_text"] == "beta note"


def test_entry_delete_last_leaves_files_and_restore_brings_them_back(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files

    older = ingest_files(user, [_pdf("older.pdf")])
    newest = ingest_files(user, [_pdf("newest.pdf")])
    attachment = newest.attachments.get()
    path = tmp_path / attachment.relative_path
    out = StringIO()
    call_command("entry_delete_last", "--email", user.email, "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["id"] == str(newest.id)
    newest.refresh_from_db()
    attachment.refresh_from_db()
    assert newest.is_deleted is True
    assert attachment.is_deleted is False
    assert path.exists()
    list_out = StringIO()
    call_command("entry_list", "--email", user.email, "--json", stdout=list_out)
    ids = [item["id"] for item in json.loads(list_out.getvalue())]
    assert str(newest.id) not in ids
    assert str(older.id) in ids
    restore_out = StringIO()
    call_command("entry_restore", "--email", user.email, "--json", stdout=restore_out)
    restored = json.loads(restore_out.getvalue())
    assert restored["id"] == str(newest.id)
    assert restored["attachment_count"] == 1
    newest.refresh_from_db()
    assert newest.is_deleted is False
    assert path.exists()


def test_entry_restore_by_id_after_entry_delete_returns_text_without_files(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    from src.diary.services import ingest_files

    entry = ingest_files(user, [_pdf("gone.pdf")])
    attachment = entry.attachments.get()
    path = tmp_path / attachment.relative_path
    call_command("entry_delete", str(entry.id))
    assert not path.exists()
    out = StringIO()
    call_command("entry_restore", "--email", user.email, "--id", str(entry.id), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["id"] == str(entry.id)
    assert payload["attachment_count"] == 0
    entry.refresh_from_db()
    assert entry.is_deleted is False
    attachment.refresh_from_db()
    assert attachment.is_deleted is True


def test_entry_restore_active_id_errors(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        from src.diary.services import ingest_text
        entry = ingest_text(user, "still here")
    with pytest.raises(CommandError, match="Unknown entry"):
        call_command("entry_restore", "--email", user.email, "--id", str(entry.id))


def test_entry_delete_last_empty(user):
    with pytest.raises(CommandError, match="Unknown entry"):
        call_command("entry_delete_last", "--email", user.email)


def test_entry_create_url_plus_instruction_writes_reference(user):
    answers = {
        "answers": {
            "intent": {"choice": "freeform", "confidence": 0.9},
            "subject": {"choice": "diary", "confidence": 0.8},
            "user_asked_for_diary": {"noul": 0.2},
            "continues_prior": {"noul": 0.1},
            "reference": {"choice": "url", "confidence": 0.9},
        },
        "usage": {"input_tokens": 2, "output_tokens": 1},
    }
    with patch("src.diary.services.decide", return_value=answers):
        out = StringIO()
        call_command(
            "entry_create",
            "--email",
            user.email,
            "--text",
            "summarize this https://example.com",
            "--json",
            stdout=out,
        )
    payload = json.loads(out.getvalue())
    row = Reference.objects.get(entry_id=payload["id"])
    assert row.value == "https://example.com"
    assert row.note == "summarize this"
