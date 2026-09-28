import json
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from src.batchcalendar.models import CalendarBooking
from src.diary.models import Entry, ItemType

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _booking(user, entry, **kwargs):
    defaults = {
        "user": user,
        "entry": entry,
        "event_index": 0,
        "summary": "Physio",
        "start_datetime": datetime(2026, 10, 1, 17, 0, tzinfo=ZoneInfo("Europe/Lisbon")),
        "end_datetime": datetime(2026, 10, 1, 17, 30, tzinfo=ZoneInfo("Europe/Lisbon")),
        "timezone": "Europe/Lisbon",
        "status": "inserted",
        "problem": "",
        "google_event_id": "gcal-1",
    }
    defaults.update(kwargs)
    return CalendarBooking.objects.create(**defaults)


def test_calendar_list_json_and_human_output(user):
    entry = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="book")
    row = _booking(user, entry, problem="")
    row.refresh_from_db()
    json_out = StringIO()
    call_command("calendar_list", "--email", user.email, "--json", stdout=json_out)
    payload = json.loads(json_out.getvalue())
    assert payload == [
        {
            "id": str(row.id),
            "summary": "Physio",
            "start": row.start_datetime.isoformat(),
            "end": row.end_datetime.isoformat(),
            "status": "inserted",
            "problem": "",
            "entry_id": str(entry.id),
            "event_index": 0,
            "timezone": "Europe/Lisbon",
            "google_event_id": "gcal-1",
            "created_at": row.created_at.isoformat(),
        }
    ]
    plain = StringIO()
    call_command("calendar_list", "--email", user.email, stdout=plain)
    line = plain.getvalue().strip()
    assert str(row.id) in line
    assert "inserted" in line
    assert "Physio" in line


def test_calendar_list_empty_for_unknown_user(user):
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("calendar_list", "--email", "missing@example.com")
    out = StringIO()
    call_command("calendar_list", "--email", user.email, stdout=out)
    assert out.getvalue().strip() == "no bookings"


def test_calendar_list_entry_filter(user):
    first = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="one")
    second = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="two")
    _booking(user, first, summary="A")
    kept = _booking(user, second, summary="B", event_index=1)
    out = StringIO()
    call_command("calendar_list", "--email", user.email, "--entry", str(second.id), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert len(payload) == 1
    assert payload[0]["id"] == str(kept.id)
    assert payload[0]["summary"] == "B"


def test_calendar_list_omits_rows_of_soft_deleted_entries(user):
    entry = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="book")
    _booking(user, entry)
    entry.is_deleted = True
    entry.deleted_at = timezone.now()
    entry.save(update_fields=["is_deleted", "deleted_at"])
    out = StringIO()
    call_command("calendar_list", "--email", user.email, "--json", stdout=out)
    assert json.loads(out.getvalue()) == []
