import pytest

from src.diary.models import Entry, ItemType
from src.diary.services import ingest_text
from src.urls_others.models import Reference

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="pat@example.com", password="pass")


def _answers(reference):
    return {
        "answers": {
            "intent": {"choice": "freeform", "confidence": 0.9},
            "subject": {"choice": "diary", "confidence": 0.8},
            "user_asked_for_diary": {"noul": 0.1},
            "continues_prior": {"noul": 0.1},
            "reference": {"choice": reference, "confidence": 0.95},
        },
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def test_https_link_writes_diary_entry_and_reference_row(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    entry = ingest_text(user, "https://example.com")
    assert entry.item_type == ItemType.TEXT
    assert entry.content_text == "https://example.com"
    assert entry.reference == "url"
    row = Reference.objects.get(entry=entry)
    assert row.kind == "url"
    assert row.value == "https://example.com"
    assert row.note == ""
    assert row.status == "pending"
    assert row.user_id == user.pk


def test_link_plus_instruction_calls_start_process(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    calls = []

    def capture(user_arg, entry, note, references):
        calls.append((user_arg, entry, note, references))

    monkeypatch.setattr("src.urls_others.services.start_process", capture)
    entry = ingest_text(user, "summarize this https://example.com/article")
    assert len(calls) == 1
    called_user, called_entry, called_note, called_refs = calls[0]
    assert called_user == user
    assert called_entry == entry
    assert called_note == "summarize this"
    assert len(called_refs) == 1


def test_bare_url_does_not_call_start_process(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    calls = []
    monkeypatch.setattr(
        "src.urls_others.services.start_process",
        lambda *args, **kwargs: calls.append(args),
    )
    ingest_text(user, "https://example.com")
    assert calls == []


def test_several_links_create_one_row_each(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    entry = ingest_text(user, "https://a.example/x https://b.example/y")
    values = set(Reference.objects.filter(entry=entry).values_list("value", flat=True))
    assert values == {"https://a.example/x", "https://b.example/y"}


def test_none_does_not_create_reference_rows(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("none"))
    entry = ingest_text(user, "https://example.com")
    assert entry.reference == "none"
    assert Reference.objects.filter(entry=entry).count() == 0


def test_url_choice_with_no_parsable_address_creates_no_row(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("url"))
    entry = ingest_text(user, "I will send the link later")
    assert entry.reference == "url"
    assert Entry.objects.filter(pk=entry.id).exists()
    assert Reference.objects.filter(entry=entry).count() == 0


def test_get_path_and_api_path_are_endpoints(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("endpoint"))
    entry = ingest_text(user, "GET /v1/users and /api/users")
    rows = Reference.objects.filter(entry=entry)
    assert {(row.kind, row.value) for row in rows} == {
        ("endpoint", "GET /v1/users"),
        ("endpoint", "/api/users"),
    }


def test_classification_error_does_not_record_references(user, monkeypatch):
    from src.diary.jev import JevError

    monkeypatch.setattr("src.diary.services.decide", lambda state: (_ for _ in ()).throw(JevError("down")))
    entry = ingest_text(user, "https://example.com")
    assert entry.classification_error == "down"
    assert entry.reference == ""
    assert Reference.objects.filter(entry=entry).count() == 0
