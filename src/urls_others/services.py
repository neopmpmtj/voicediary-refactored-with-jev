import logging

from django.contrib.auth import get_user_model

from src.urls_others.models import Reference, ReferenceKind
from src.urls_others.parse import parse_references

logger = logging.getLogger(__name__)

RECORDABLE = {ReferenceKind.URL, ReferenceKind.ENDPOINT}


class ReferenceLookupError(Exception):
    pass


def start_process(user, entry, note, references):
    """Stub: leftover note on a URL or endpoint. Replace with the LLM start-process call."""
    print("what do you want me to do")
    logger.info("what do you want me to do")


def record_references(user, entry, text):
    """Parse addresses from text and store a row per match when JEV said url or endpoint."""
    if entry.reference not in RECORDABLE:
        return []
    matches, note = parse_references(text)
    created = []
    for kind, value in matches:
        created.append(
            Reference.objects.create(
                user=user,
                entry=entry,
                kind=kind,
                value=value,
                note=note,
            )
        )
    if note and created:
        start_process(user, entry, note, created)
    return created


def reference_list_item(row):
    return {
        "id": str(row.id),
        "kind": row.kind,
        "created_at": row.created_at.isoformat(),
        "value": row.value,
        "note": row.note,
        "entry_id": str(row.entry_id),
        "status": row.status,
    }


def user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise ReferenceLookupError("Unknown user.") from exc


def references_for_email(email, *, kind=None, limit=None):
    user = user_by_email(email)
    rows = Reference.objects.filter(user=user)
    if kind:
        rows = rows.filter(kind=kind)
    rows = rows.order_by("-created_at")
    if limit is not None:
        rows = rows[:limit]
    return [reference_list_item(row) for row in rows]
