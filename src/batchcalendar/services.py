import copy
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model

from src.accounts.google import GoogleAuthError
from src.batchcalendar.errors import CalendarError, CalendarLookupError, ExtractError
from src.batchcalendar.extract import extract_batch_events
from src.batchcalendar.google_calendar import check_freebusy, insert_event
from src.batchcalendar.models import BookingStatus, CalendarBooking
from src.batchcalendar.prompt import DEFAULT_TIMEZONE
from src.diary.models import UsageLog

logger = logging.getLogger(__name__)


def event_data_to_google_format(event_data, start_dt, end_dt, tz_str):
    body = copy.deepcopy(event_data)
    body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz_str}
    body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz_str}
    return body


def parse_event_datetime(value, tz_str):
    if not value:
        raise CalendarError("Missing dateTime")
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CalendarError("Could not parse start or end") from exc
    try:
        tz = ZoneInfo(tz_str or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        tz_str = DEFAULT_TIMEZONE
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed, tz_str


def parse_event_bounds(event_data):
    start = event_data.get("start") or {}
    end = event_data.get("end") or {}
    tz_str = start.get("timeZone") or end.get("timeZone") or DEFAULT_TIMEZONE
    start_dt, tz_str = parse_event_datetime(start.get("dateTime"), tz_str)
    end_dt, tz_str = parse_event_datetime(end.get("dateTime"), tz_str)
    return start_dt, end_dt, tz_str


def _busy_problem(busy_periods):
    parts = []
    for period in busy_periods or []:
        start = period.get("start") or ""
        end = period.get("end") or ""
        if start or end:
            parts.append(f"{start}–{end}")
    if parts:
        return "Slot taken: " + ", ".join(parts)
    return "Slot taken"


def _log_extract_usage(user, entry, usage):
    if not usage:
        return
    UsageLog.objects.create(
        user=user,
        entry=entry,
        service="batchcalendar",
        usage_type="input_tokens",
        amount=Decimal(str(usage.get("input") or 0)),
    )
    UsageLog.objects.create(
        user=user,
        entry=entry,
        service="batchcalendar",
        usage_type="output_tokens",
        amount=Decimal(str(usage.get("output") or 0)),
    )


def _store_booking(
    user,
    entry,
    event_index,
    *,
    summary="",
    start_datetime=None,
    end_datetime=None,
    timezone=DEFAULT_TIMEZONE,
    status,
    problem="",
    google_event_id="",
):
    return CalendarBooking.objects.create(
        user=user,
        entry=entry,
        event_index=event_index,
        summary=summary or "",
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        timezone=timezone or DEFAULT_TIMEZONE,
        status=status,
        problem=problem or "",
        google_event_id=google_event_id or "",
    )


def booking_payload_item(row):
    return {
        "id": str(row.id),
        "summary": row.summary,
        "start": row.start_datetime.isoformat() if row.start_datetime else "",
        "end": row.end_datetime.isoformat() if row.end_datetime else "",
        "status": row.status,
        "problem": row.problem,
    }


def bookings_for_entry(entry):
    return [booking_payload_item(row) for row in entry.calendar_bookings.all()]


def booking_list_item(row):
    item = booking_payload_item(row)
    item.update(
        {
            "entry_id": str(row.entry_id),
            "event_index": row.event_index,
            "timezone": row.timezone,
            "google_event_id": row.google_event_id,
            "created_at": row.created_at.isoformat(),
        }
    )
    return item


def book_calendar_events(user, entry):
    if entry.route != "calendar":
        return []
    usage = {}
    try:
        events, error, usage = extract_batch_events(entry.content_text)
    except ExtractError as exc:
        logger.error("Calendar extraction failed for %s: %s", entry.id, exc)
        return [
            _store_booking(
                user,
                entry,
                0,
                status=BookingStatus.FAILED,
                problem=str(exc),
            )
        ]
    finally:
        _log_extract_usage(user, entry, usage)
    if not events:
        return [
            _store_booking(
                user,
                entry,
                0,
                status=BookingStatus.FAILED,
                problem=error or "No events extracted",
            )
        ]
    created = []
    for index, event_data in enumerate(events):
        summary = event_data.get("summary") or ""
        try:
            start_dt, end_dt, tz_str = parse_event_bounds(event_data)
        except CalendarError as exc:
            created.append(
                _store_booking(
                    user,
                    entry,
                    index,
                    summary=summary,
                    status=BookingStatus.FAILED,
                    problem=str(exc),
                )
            )
            continue
        body = event_data_to_google_format(event_data, start_dt, end_dt, tz_str)
        try:
            available, busy = check_freebusy(user, start_dt, end_dt)
        except (GoogleAuthError, CalendarError) as exc:
            created.append(
                _store_booking(
                    user,
                    entry,
                    index,
                    summary=summary,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone=tz_str,
                    status=BookingStatus.FAILED,
                    problem=str(exc),
                )
            )
            continue
        if not available:
            created.append(
                _store_booking(
                    user,
                    entry,
                    index,
                    summary=summary,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone=tz_str,
                    status=BookingStatus.TAKEN,
                    problem=_busy_problem(busy),
                )
            )
            continue
        try:
            api_resp = insert_event(user, body)
        except (GoogleAuthError, CalendarError) as exc:
            created.append(
                _store_booking(
                    user,
                    entry,
                    index,
                    summary=summary,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone=tz_str,
                    status=BookingStatus.FAILED,
                    problem=str(exc),
                )
            )
            continue
        event_id = (api_resp or {}).get("id") or ""
        if not event_id:
            created.append(
                _store_booking(
                    user,
                    entry,
                    index,
                    summary=summary,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    timezone=tz_str,
                    status=BookingStatus.FAILED,
                    problem="Calendar insert returned no event id",
                )
            )
            continue
        created.append(
            _store_booking(
                user,
                entry,
                index,
                summary=summary,
                start_datetime=start_dt,
                end_datetime=end_dt,
                timezone=tz_str,
                status=BookingStatus.INSERTED,
                google_event_id=event_id,
            )
        )
    return created


def user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise CalendarLookupError("Unknown user.") from exc


def bookings_for_email(email, *, entry_id=None):
    user = user_by_email(email)
    rows = CalendarBooking.objects.filter(user=user, entry__is_deleted=False)
    if entry_id:
        try:
            key = uuid.UUID(str(entry_id))
        except (TypeError, ValueError) as exc:
            raise CalendarLookupError("Unknown entry.") from exc
        rows = rows.filter(entry_id=key)
    rows = rows.order_by("-created_at", "event_index")
    return [booking_list_item(row) for row in rows]
