import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.accounts.services import google_access_token
from src.batchcalendar.errors import CalendarError

logger = logging.getLogger(__name__)

FREEBUSY_URI = "https://www.googleapis.com/calendar/v3/freeBusy"
EVENTS_URI = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"


def _iso(value):
    text = value.isoformat()
    if value.tzinfo is None and not text.endswith("Z"):
        return text + "Z"
    return text


def _authorized_json(user, url, body):
    token = google_access_token(user)
    req = Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Calendar request failed: %s", detail)
        raise CalendarError(detail) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Calendar request error: %s", exc)
        raise CalendarError(str(exc)) from exc


def check_freebusy(user, start_datetime, end_datetime, calendar_id="primary"):
    result = _authorized_json(
        user,
        FREEBUSY_URI,
        {
            "timeMin": _iso(start_datetime),
            "timeMax": _iso(end_datetime),
            "items": [{"id": calendar_id}],
        },
    )
    calendar = (result.get("calendars") or {}).get(calendar_id) or {}
    errors = calendar.get("errors") or []
    if errors:
        raise CalendarError(json.dumps(errors))
    busy_periods = calendar.get("busy") or []
    return len(busy_periods) == 0, busy_periods


def insert_event(user, event_data, calendar_id="primary"):
    url = EVENTS_URI.format(calendar_id=quote(calendar_id, safe=""))
    return _authorized_json(user, url, event_data)
