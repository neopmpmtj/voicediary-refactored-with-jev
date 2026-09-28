import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from src.diary.models import Entry, ItemType
from src.urls_others.models import Reference

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _answers(reference="url"):
    return {
        "answers": {
            "intent": {"choice": "freeform", "confidence": 0.9},
            "subject": {"choice": "diary", "confidence": 0.8},
            "user_asked_for_diary": {"noul": 0.2},
            "continues_prior": {"noul": 0.1},
            "reference": {"choice": reference, "confidence": 0.9},
        },
        "usage": {"input_tokens": 2, "output_tokens": 1},
    }


def test_url_list_json_and_human_output(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    from src.diary.services import ingest_text

    entry = ingest_text(user, "keep https://example.com")
    row = Reference.objects.get(entry=entry)
    json_out = StringIO()
    call_command("url_list", "--email", user.email, "--json", stdout=json_out)
    payload = json.loads(json_out.getvalue())
    assert payload == [
        {
            "id": str(row.id),
            "kind": "url",
            "created_at": row.created_at.isoformat(),
            "value": "https://example.com",
            "note": "keep",
            "entry_id": str(entry.id),
            "status": "pending",
        }
    ]
    plain = StringIO()
    call_command("url_list", "--email", user.email, stdout=plain)
    line = plain.getvalue().strip()
    assert str(row.id) in line
    assert "url" in line
    assert "https://example.com" in line
    assert "keep" in line


def test_url_list_empty_for_unknown_user(user):
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("url_list", "--email", "missing@example.com")
    out = StringIO()
    call_command("url_list", "--email", user.email, stdout=out)
    assert out.getvalue().strip() == "no urls"


def _stamp(row, when):
    row.created_at = when
    row.save(update_fields=["created_at"])
    return row


def _seed_url_and_endpoint(user):
    now = timezone.now()
    entry = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="refs")
    older_url = _stamp(
        Reference.objects.create(
            user=user, entry=entry, kind="url", value="https://old.example"
        ),
        now - timedelta(minutes=2),
    )
    endpoint = _stamp(
        Reference.objects.create(
            user=user, entry=entry, kind="endpoint", value="GET /v1/users"
        ),
        now - timedelta(minutes=1),
    )
    newest_url = _stamp(
        Reference.objects.create(
            user=user, entry=entry, kind="url", value="https://new.example"
        ),
        now,
    )
    return older_url, endpoint, newest_url


def test_url_list_kind_url_omits_endpoints(user):
    _seed_url_and_endpoint(user)
    out = StringIO()
    call_command("url_list", "--email", user.email, "--kind", "url", "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert [item["kind"] for item in payload] == ["url", "url"]
    assert [item["value"] for item in payload] == ["https://new.example", "https://old.example"]


def test_url_list_limit_returns_newest_row(user):
    _seed_url_and_endpoint(user)
    out = StringIO()
    call_command("url_list", "--email", user.email, "--limit", "1", "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert len(payload) == 1
    assert payload[0]["value"] == "https://new.example"


def test_url_list_kind_and_limit_together(user):
    _seed_url_and_endpoint(user)
    out = StringIO()
    call_command(
        "url_list",
        "--email",
        user.email,
        "--kind",
        "url",
        "--limit",
        "1",
        "--json",
        stdout=out,
    )
    payload = json.loads(out.getvalue())
    assert len(payload) == 1
    assert payload[0]["kind"] == "url"
    assert payload[0]["value"] == "https://new.example"


def test_url_list_rejects_unknown_kind(user):
    with pytest.raises(CommandError):
        call_command("url_list", "--email", user.email, "--kind", "bogus")


def test_url_list_omits_rows_of_soft_deleted_entries_and_restore_shows_them(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    from src.diary.services import ingest_text

    entry = ingest_text(user, "keep https://example.com")
    call_command("entry_delete_last", "--email", user.email)
    hidden = StringIO()
    call_command("url_list", "--email", user.email, "--json", stdout=hidden)
    assert json.loads(hidden.getvalue()) == []
    assert Reference.objects.filter(entry=entry).exists()
    call_command("entry_restore", "--email", user.email)
    shown = StringIO()
    call_command("url_list", "--email", user.email, "--json", stdout=shown)
    payload = json.loads(shown.getvalue())
    assert len(payload) == 1
    assert payload[0]["value"] == "https://example.com"
    assert payload[0]["entry_id"] == str(entry.id)
