from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.batchcalendar.errors import CalendarError
from src.batchcalendar.models import CalendarBooking
from src.diary.jev import JevError
from src.diary.models import UsageLog
from src.diary.services import ingest_text

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

LISBON = ZoneInfo("Europe/Lisbon")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="pat@example.com", password="pass")


def _answers(subject="calendar", intent="freeform"):
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


def _event(summary, hour):
    start = datetime(2026, 10, 1, hour, 0, tzinfo=LISBON)
    end = datetime(2026, 10, 1, hour, 30, tzinfo=LISBON)
    return {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": "Europe/Lisbon"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Europe/Lisbon"},
    }


def test_free_slot_inserts_and_reports_taken_without_inserting_busy(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("calendar"))
    events = [_event("Physio", 17), _event("Call", 11)]
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda text, user_timezone="Europe/Lisbon": (events, None, {"input": 3, "output": 2}),
    )
    inserts = []

    def fake_freebusy(user_arg, start_dt, end_dt, calendar_id="primary"):
        if start_dt.hour == 17:
            return False, [{"start": "2026-10-01T17:00:00+01:00", "end": "2026-10-01T17:30:00+01:00"}]
        return True, []

    def fake_insert(user_arg, body, calendar_id="primary"):
        inserts.append(body)
        return {"id": "gcal-call"}

    monkeypatch.setattr("src.batchcalendar.services.check_freebusy", fake_freebusy)
    monkeypatch.setattr("src.batchcalendar.services.insert_event", fake_insert)
    entry = ingest_text(user, "Physio at 5pm and a call at 11")
    rows = list(CalendarBooking.objects.filter(entry=entry).order_by("event_index"))
    assert [row.status for row in rows] == ["taken", "inserted"]
    assert rows[0].google_event_id == ""
    assert "Slot taken" in rows[0].problem
    assert rows[1].google_event_id == "gcal-call"
    assert len(inserts) == 1
    assert inserts[0]["summary"] == "Call"
    usage = UsageLog.objects.filter(entry=entry, service="batchcalendar")
    assert {item.usage_type for item in usage} == {"input_tokens", "output_tokens"}


def test_one_freebusy_failure_does_not_block_the_next_event(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("appointment"))
    events = [_event("A", 10), _event("B", 11)]
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda text, user_timezone="Europe/Lisbon": (events, None, {"input": 1, "output": 1}),
    )
    inserts = []

    def fake_freebusy(user_arg, start_dt, end_dt, calendar_id="primary"):
        if start_dt.hour == 10:
            raise CalendarError("freebusy down")
        return True, []

    monkeypatch.setattr("src.batchcalendar.services.check_freebusy", fake_freebusy)
    monkeypatch.setattr(
        "src.batchcalendar.services.insert_event",
        lambda user_arg, body, calendar_id="primary": inserts.append(body) or {"id": "gcal-b"},
    )
    entry = ingest_text(user, "Two bookings")
    rows = list(CalendarBooking.objects.filter(entry=entry).order_by("event_index"))
    assert [row.status for row in rows] == ["failed", "inserted"]
    assert rows[0].problem == "freebusy down"
    assert rows[1].google_event_id == "gcal-b"
    assert len(inserts) == 1


def test_extractor_with_no_events_writes_one_failed_row(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("calendar"))
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda text, user_timezone="Europe/Lisbon": (
            None,
            "Insufficient information to create calendar events",
            {"input": 2, "output": 1},
        ),
    )
    called = []
    monkeypatch.setattr(
        "src.batchcalendar.services.check_freebusy",
        lambda *args, **kwargs: called.append("freebusy"),
    )
    monkeypatch.setattr(
        "src.batchcalendar.services.insert_event",
        lambda *args, **kwargs: called.append("insert"),
    )
    entry = ingest_text(user, "maybe later")
    row = CalendarBooking.objects.get(entry=entry)
    assert row.status == "failed"
    assert row.problem == "Insufficient information to create calendar events"
    assert called == []


def test_diary_route_does_not_extract_or_book(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("diary"))
    called = []
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda *args, **kwargs: called.append("extract") or ([], "x", {}),
    )
    ingest_text(user, "a note")
    assert called == []
    assert CalendarBooking.objects.count() == 0


def test_classification_error_does_not_book(user, monkeypatch):
    monkeypatch.setattr(
        "src.diary.services.decide",
        lambda state: (_ for _ in ()).throw(JevError("down")),
    )
    called = []
    monkeypatch.setattr(
        "src.batchcalendar.services.book_calendar_events",
        lambda *args, **kwargs: called.append("book"),
    )
    entry = ingest_text(user, "book tomorrow at 5")
    assert entry.classification_error == "down"
    assert called == []
    assert CalendarBooking.objects.count() == 0


def test_entry_payload_includes_bookings(user, monkeypatch):
    monkeypatch.setattr("src.diary.services.decide", lambda state: _answers("calendar"))
    monkeypatch.setattr(
        "src.batchcalendar.services.extract_batch_events",
        lambda text, user_timezone="Europe/Lisbon": (
            [_event("Physio", 17)],
            None,
            {"input": 1, "output": 1},
        ),
    )
    monkeypatch.setattr(
        "src.batchcalendar.services.check_freebusy",
        lambda *args, **kwargs: (False, [{"start": "a", "end": "b"}]),
    )
    monkeypatch.setattr(
        "src.batchcalendar.services.insert_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not insert")),
    )
    from src.diary.services import entry_payload

    entry = ingest_text(user, "Physio at 5")
    payload = entry_payload(entry)
    assert len(payload["bookings"]) == 1
    assert payload["bookings"][0]["status"] == "taken"
    assert payload["bookings"][0]["summary"] == "Physio"
    assert "Slot taken" in payload["bookings"][0]["problem"]
