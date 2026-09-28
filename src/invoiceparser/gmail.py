import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.accounts.google import GMAIL_SCOPE
from src.accounts.models import UserSecret
from src.accounts.services import google_access_token
from src.invoiceparser.errors import InvoiceError

logger = logging.getLogger(__name__)

GMAIL_MESSAGES_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_MESSAGE_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
GMAIL_ATTACHMENT_URI = (
    "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
    "/attachments/{attachment_id}"
)
GMAIL_LABELS_URI = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
GMAIL_MODIFY_URI = (
    "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify"
)
_PDF_MIME_TYPES = {"application/pdf"}


def user_has_gmail(user):
    secret = UserSecret.objects.filter(user=user).first()
    if not secret:
        return False
    return GMAIL_SCOPE in secret.get_scopes_list()


def _authorized(user, url, method="GET", body=None):
    token = google_access_token(user)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        logger.error("Gmail request failed: %s", detail)
        raise InvoiceError(detail) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Gmail request error: %s", exc)
        raise InvoiceError(str(exc)) from exc


def search_inbox_messages(user, query, max_results=20):
    params = urlencode(
        {
            "q": query,
            "labelIds": "INBOX",
            "maxResults": max_results,
        }
    )
    result = _authorized(user, f"{GMAIL_MESSAGES_URI}?{params}")
    return [item["id"] for item in result.get("messages") or [] if item.get("id")]


def get_message(user, message_id, fmt="full"):
    url = GMAIL_MESSAGE_URI.format(message_id=quote(message_id, safe=""))
    return _authorized(user, f"{url}?format={quote(fmt, safe='')}")


def get_or_create_label(user, name):
    result = _authorized(user, GMAIL_LABELS_URI)
    for label in result.get("labels") or []:
        if label.get("name") == name and label.get("id"):
            return label["id"]
    created = _authorized(
        user,
        GMAIL_LABELS_URI,
        method="POST",
        body={
            "name": name,
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow",
        },
    )
    label_id = created.get("id") or ""
    if not label_id:
        raise InvoiceError("Gmail label create returned no id")
    return label_id


def add_label_to_message(user, message_id, label_id):
    url = GMAIL_MODIFY_URI.format(message_id=quote(message_id, safe=""))
    _authorized(user, url, method="POST", body={"addLabelIds": [label_id]})


def download_attachment(user, message_id, attachment_id):
    url = GMAIL_ATTACHMENT_URI.format(
        message_id=quote(message_id, safe=""),
        attachment_id=quote(attachment_id, safe=""),
    )
    result = _authorized(user, url)
    data = result.get("data") or ""
    if not data:
        raise InvoiceError("Gmail attachment was empty")
    return base64.urlsafe_b64decode(data)


def _is_pdf(part):
    mime = (part.get("mimeType") or "").lower()
    filename = (part.get("filename") or "").lower()
    return mime in _PDF_MIME_TYPES or filename.endswith(".pdf")


def get_pdf_attachments(user, message_id):
    msg = get_message(user, message_id, fmt="full")
    payload = msg.get("payload") or {}
    parts = payload.get("parts") or []
    found = []

    def collect(plist):
        for part in plist:
            if _is_pdf(part) and part.get("filename"):
                body = part.get("body") or {}
                attachment_id = body.get("attachmentId")
                if attachment_id:
                    found.append(
                        {
                            "filename": part["filename"],
                            "data": download_attachment(user, message_id, attachment_id),
                            "mime_type": (part.get("mimeType") or "application/pdf").lower(),
                        }
                    )
            nested = part.get("parts") or []
            if nested:
                collect(nested)
            inner = (part.get("payload") or {}).get("parts") or []
            if inner:
                collect(inner)

    collect(parts)
    return found
