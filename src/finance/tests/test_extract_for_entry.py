from decimal import Decimal

import pytest

from src.diary.jev import JevError
from src.diary.models import UsageLog
from src.diary.services import ingest_text
from src.finance.models import FinancialRecord

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="pat@example.com", password="pass")


def _answers(subject="finance", intent="freeform"):
    return {
        "answers": {
            "intent": {"choice": intent, "confidence": 0.9},
            "subject": {"choice": subject, "confidence": 0.9},
            "user_asked_for_diary": {"noul": 0.1},
            "continues_prior": {"noul": 0.1},
            "reference": {"choice": "none", "confidence": 0.9},
        },
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _items():
    return (
        "Despesas de hoje",
        "",
        [
            {
                "type": "expense",
                "amount": Decimal("20.00"),
                "currency": "EUR",
                "category": "Food",
                "merchant": "",
                "transaction_date": None,
                "description": "café",
                "payment_method": "",
            }
        ],
        None,
        {"input": 3, "output": 2},
    )


def test_finance_route_extracts_items(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("finance"))
    monkeypatch.setattr(
        "src.finance.services.extract_from_text",
        lambda text, user_timezone="Europe/Lisbon": _items(),
    )
    entry = ingest_text(user, "gastei 20 no café")
    record = FinancialRecord.objects.get(entry=entry)
    assert record.status == "success"
    assert record.record_name == "Despesas de hoje"
    item = record.items.get()
    assert item.amount == Decimal("20.00")
    assert item.description == "café"
    usage = UsageLog.objects.filter(entry=entry, service="finance")
    assert {row.usage_type for row in usage} == {"input_tokens", "output_tokens"}


def test_calendar_route_does_not_extract_finance(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("calendar"))
    called = []
    monkeypatch.setattr(
        "src.finance.services.extract_from_text",
        lambda *args, **kwargs: called.append("extract") or _items(),
    )
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda *args, **kwargs: ([], "none", {}),
    )
    monkeypatch.setattr(
        "src.batchcalendar.services.check_freebusy",
        lambda *args, **kwargs: (True, []),
    )
    ingest_text(user, "book tomorrow at 5")
    assert called == []
    assert FinancialRecord.objects.count() == 0


def test_diary_route_does_not_extract_finance(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("diary"))
    called = []
    monkeypatch.setattr(
        "src.finance.services.extract_from_text",
        lambda *args, **kwargs: called.append("extract") or _items(),
    )
    ingest_text(user, "a note")
    assert called == []
    assert FinancialRecord.objects.count() == 0


def test_empty_extract_writes_failed_record(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("finance"))
    monkeypatch.setattr(
        "src.finance.services.extract_from_text",
        lambda *args, **kwargs: (
            None,
            None,
            None,
            "No financial information to extract",
            {"input": 2, "output": 1},
        ),
    )
    entry = ingest_text(user, "maybe money later")
    record = FinancialRecord.objects.get(entry=entry)
    assert record.status == "failed"
    assert record.error_message == "No financial information to extract"
    assert record.items.count() == 0
    assert entry.content_text == "maybe money later"


def test_classification_error_does_not_extract(user, monkeypatch):
    monkeypatch.setattr(
        "src.diary.services.decide",
        lambda state: (_ for _ in ()).throw(JevError("down")),
    )
    called = []
    monkeypatch.setattr(
        "src.finance.services.extract_financial_items",
        lambda *args, **kwargs: called.append("extract"),
    )
    entry = ingest_text(user, "gastei 20")
    assert entry.classification_error == "down"
    assert called == []
    assert FinancialRecord.objects.count() == 0


def test_entry_payload_includes_finance(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("finance"))
    monkeypatch.setattr(
        "src.finance.services.extract_from_text",
        lambda *args, **kwargs: _items(),
    )
    from src.diary.services import entry_payload

    entry = ingest_text(user, "gastei 20 no café")
    payload = entry_payload(entry)
    assert len(payload["finance"]) == 1
    assert payload["finance"][0]["status"] == "success"
    assert payload["finance"][0]["items"][0]["amount"] == "20.00"
