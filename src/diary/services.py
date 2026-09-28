import logging
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.utils import timezone
from decouple import config

from src.diary.audio import probe_duration_seconds, strip_silence
from src.diary.jev import JevError, decide
from src.diary.models import Attachment, Entry, ItemType, UsageLog
from src.diary.storage import (
    ATTACHMENTS_SUBDIR,
    MediaPathError,
    allocate_unique_attachment_filename,
    artifacts_dir_for_user,
    attachment_disk_path,
    attachment_path_is_allowed,
    attachments_dir_for_entry,
    resolve_media_file_path,
    sanitize_storage_filename,
)
from src.diary.transcription import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)

CALENDAR_INTENTS = {"follow-up", "reschedule"}
NOUL_YES = 0.5


class AttachmentError(Exception):
    pass


class MediaReleaseError(Exception):
    pass


class EntryLookupError(Exception):
    pass


def recorder_max_seconds():
    return config("RECORDER_MAX_DURATION", default=240, cast=int)


def prior_entry_count():
    return config("PRIOR_ENTRY_COUNT", default=2, cast=int)


def derive_route(intent, subject):
    if intent in CALENDAR_INTENTS or subject == "appointment":
        return "calendar"
    return subject or ""


def select_prior_entries(entries, *, count, max_seconds):
    """Newest-first entries already stored. Context starts once two exist."""
    if len(entries) < 2:
        return []
    chosen = []
    for entry in entries:
        if entry.item_type == ItemType.AUDIO:
            duration = entry.recording_duration_seconds
            if duration is None or duration >= max_seconds:
                continue
        chosen.append(entry)
        if len(chosen) >= count:
            break
    return list(reversed(chosen))


def _noul(answer):
    if not answer or answer.get("noul") is None:
        return False, None
    probability = float(answer["noul"])
    return probability >= NOUL_YES, probability


def _log_usage(user, entry, service, usage_type, amount):
    UsageLog.objects.create(
        user=user,
        entry=entry,
        service=service,
        usage_type=usage_type,
        amount=Decimal(str(amount)),
    )


def _classify(user, text, exclude_id=None):
    existing_qs = Entry.objects.filter(user=user, is_deleted=False)
    if exclude_id is not None:
        existing_qs = existing_qs.exclude(pk=exclude_id)
    existing = list(existing_qs.order_by("-created_at"))
    prior = select_prior_entries(
        existing,
        count=prior_entry_count(),
        max_seconds=recorder_max_seconds(),
    )
    state = {
        "entry": text,
        "prior_entries": [
            {
                "text": item.content_text,
                "recorded_at": item.created_at.isoformat(),
            }
            for item in prior
        ],
    }
    return decide(state)


def _apply_classification(entry, payload):
    answers = payload.get("answers") or {}
    intent_answer = answers.get("intent") or {}
    subject_answer = answers.get("subject") or {}
    reference_answer = answers.get("reference") or {}
    diary_yes, diary_probability = _noul(answers.get("user_asked_for_diary"))
    continues_yes, continues_probability = _noul(answers.get("continues_prior"))
    entry.intent = intent_answer.get("choice") or ""
    entry.subject = subject_answer.get("choice") or ""
    entry.intent_confidence = intent_answer.get("confidence")
    entry.subject_confidence = subject_answer.get("confidence")
    entry.user_asked_for_diary = diary_yes
    entry.user_asked_for_diary_probability = diary_probability
    entry.continues_prior = continues_yes
    entry.continues_prior_probability = continues_probability
    entry.reference = reference_answer.get("choice") or ""
    entry.reference_confidence = reference_answer.get("confidence")
    entry.route = derive_route(entry.intent, entry.subject)
    entry.classification_error = ""
    usage = payload.get("usage") or {}
    _log_usage(entry.user, entry, "jev", "input_tokens", usage.get("input_tokens") or 0)
    _log_usage(entry.user, entry, "jev", "output_tokens", usage.get("output_tokens") or 0)


def _record_references_if_needed(entry):
    if entry.reference not in ("url", "endpoint"):
        return
    from src.urls_others.services import record_references

    record_references(entry.user, entry, entry.content_text)


def _attachment_payload(entry):
    return [
        {
            "id": str(item.id),
            "filename": item.original_filename,
            "uploaded_at": item.uploaded_at.isoformat(),
        }
        for item in entry.attachments.filter(is_deleted=False)
    ]


def entry_payload(entry):
    return {
        "item_id": str(entry.id),
        "status": "complete",
        "content_text": entry.content_text,
        "route": entry.route,
        "intent": entry.intent,
        "subject": entry.subject,
        "classification_error": entry.classification_error,
        "attachments": _attachment_payload(entry),
        "attachment_count": entry.attachments.filter(is_deleted=False).count(),
    }


def store_attachments(user, entry, uploads):
    """Save user files under attachments/ and link them to entry."""
    created = []
    uploads = [item for item in (uploads or []) if item]
    if not uploads:
        return created
    folder = attachments_dir_for_entry(user.pk, entry.id)
    used = set()
    for upload in uploads:
        safe_name = allocate_unique_attachment_filename(
            folder,
            sanitize_storage_filename(getattr(upload, "name", "") or "uploaded_file"),
            used,
        )
        dest = folder / safe_name
        with dest.open("wb") as out:
            for chunk in upload.chunks():
                out.write(chunk)
        created.append(
            Attachment.objects.create(
                user=user,
                entry=entry,
                original_filename=(getattr(upload, "name", "") or safe_name)[:255],
                stored_name=safe_name,
                mime_type=getattr(upload, "content_type", "") or "",
                relative_path=str(Path(ATTACHMENTS_SUBDIR) / str(user.pk) / str(entry.id) / safe_name),
            )
        )
    return created


def ingest_files(user, uploads):
    """Attachment without an ongoing voice/text input becomes its own entry."""
    uploads = [item for item in (uploads or []) if item]
    if not uploads:
        raise AttachmentError("Missing file upload")
    names = [getattr(item, "name", "") or "file" for item in uploads]
    entry = Entry.objects.create(
        user=user,
        item_type=ItemType.FILE,
        content_text=", ".join(names),
    )
    store_attachments(user, entry, uploads)
    return entry


def ingest_text(user, text, uploads=None):
    cleaned = (text or "").strip()
    uploads = [item for item in (uploads or []) if item]
    if not cleaned and uploads:
        return ingest_files(user, uploads)
    entry = Entry.objects.create(
        user=user,
        item_type=ItemType.TEXT,
        content_text=cleaned,
    )
    try:
        _apply_classification(entry, _classify(user, cleaned, exclude_id=entry.id))
        _record_references_if_needed(entry)
    except JevError as exc:
        logger.error("Classification failed for %s: %s", entry.id, exc)
        entry.classification_error = str(exc)
    if uploads:
        store_attachments(user, entry, uploads)
    entry.save()
    return entry


def _store_upload(upload, user_id):
    folder = Path(settings.MEDIA_ROOT) / "recordings" / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.name).suffix or ".webm"
    source = folder / f"{uuid.uuid4()}{suffix}"
    with source.open("wb") as dest:
        for chunk in upload.chunks():
            dest.write(chunk)
    return source


def ingest_audio(user, upload, recording_duration_seconds=None, recording_group_id=None, uploads=None):
    if not isinstance(upload, UploadedFile):
        raise TranscriptionError("Missing audio upload")
    source = _store_upload(upload, user.pk)
    original_duration = probe_duration_seconds(source)
    if recording_duration_seconds not in (None, ""):
        try:
            original_duration = float(recording_duration_seconds)
        except (TypeError, ValueError):
            pass
    processed = artifacts_dir_for_user(user.pk) / f"{source.stem}-processed{source.suffix}"
    audio_for_transcript = source
    processed_duration = original_duration
    if strip_silence(source, processed):
        audio_for_transcript = processed
        processed_duration = probe_duration_seconds(processed)
    transcript = transcribe_audio(audio_for_transcript)
    text = (transcript.get("text") or "").strip()
    group_id = None
    if recording_group_id:
        try:
            group_id = uuid.UUID(str(recording_group_id))
        except ValueError:
            group_id = None
    entry = Entry.objects.create(
        user=user,
        item_type=ItemType.AUDIO,
        content_text=text,
        recording_duration_seconds=int(round(original_duration)) if original_duration is not None else None,
        processed_duration_seconds=processed_duration,
        recording_group_id=group_id,
    )
    minutes = transcript.get("duration")
    if minutes is None and processed_duration is not None:
        minutes = processed_duration
    if minutes is not None:
        _log_usage(user, entry, transcript.get("model") or "transcription", "audio_minutes", float(minutes) / 60.0)
    try:
        _apply_classification(entry, _classify(user, text, exclude_id=entry.id))
        _record_references_if_needed(entry)
    except JevError as exc:
        logger.error("Classification failed for %s: %s", entry.id, exc)
        entry.classification_error = str(exc)
    if uploads:
        store_attachments(user, entry, uploads)
    entry.save()
    return entry


def list_entries(user):
    """Entries for the list page. Missing or soft-deleted files are omitted from links.

    Loading this page does not write. A file that is gone stays in the database until
    media_release soft-deletes that row.
    """
    rows = (
        Entry.objects.filter(user=user, is_deleted=False)
        .prefetch_related("attachments")
        .order_by("-created_at")
    )
    visible = []
    for entry in rows:
        present = [
            item
            for item in entry.attachments.all()
            if not item.is_deleted and attachment_path_is_allowed(user.pk, item.relative_path)
        ]
        entry.present_attachments = present
        visible.append(entry)
    return visible


def _soft_delete(row, now):
    if row.is_deleted:
        return False
    row.is_deleted = True
    row.deleted_at = now
    row.save(update_fields=["is_deleted", "deleted_at"])
    return True


def release_file(path):
    """Delete a file under media/ and soft-delete the row that stored the path."""
    from src.conference.models import Segment

    try:
        resolved, relative = resolve_media_file_path(path)
    except MediaPathError as exc:
        raise MediaReleaseError(str(exc)) from exc
    bytes_freed = 0
    if resolved.is_file():
        bytes_freed = resolved.stat().st_size
        resolved.unlink()
    now = timezone.now()
    attachment_ids = []
    entry_ids = []
    for item in Attachment.objects.filter(relative_path=relative, is_deleted=False).select_related("entry"):
        _soft_delete(item, now)
        attachment_ids.append(str(item.id))
        entry = item.entry
        if entry.item_type == ItemType.FILE and not entry.is_deleted:
            still_active = entry.attachments.filter(is_deleted=False).exists()
            if not still_active:
                _soft_delete(entry, now)
                entry_ids.append(str(entry.id))
    segment_ids = []
    segments = Segment.objects.filter(is_deleted=False).filter(
        Q(relative_path=relative) | Q(processed_relative_path=relative)
    )
    for segment in segments:
        _soft_delete(segment, now)
        segment_ids.append(str(segment.id))
    return {
        "path": str(resolved),
        "relative_path": relative,
        "bytes_freed": bytes_freed,
        "attachments": attachment_ids,
        "entries": entry_ids,
        "segments": segment_ids,
    }


def _unlink_stored_file(relative_path):
    path = attachment_disk_path(relative_path)
    try:
        resolved = path.resolve()
        if resolved.is_file():
            size = resolved.stat().st_size
            resolved.unlink()
            return size
    except OSError:
        return 0
    return 0


def _active_attachments(entry):
    return [item for item in entry.attachments.all() if not item.is_deleted]


def entry_list_item(entry):
    return {
        "id": str(entry.id),
        "item_type": entry.item_type,
        "created_at": entry.created_at.isoformat(),
        "content_text": entry.content_text,
        "route": entry.route,
        "intent": entry.intent,
        "subject": entry.subject,
        "attachment_count": len(_active_attachments(entry)),
    }


def entry_show_item(entry):
    data = entry_list_item(entry)
    data["attachments"] = [item.original_filename for item in _active_attachments(entry)]
    return data


def user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise EntryLookupError("Unknown user.") from exc


def _entry_uuid(entry_id):
    try:
        return uuid.UUID(str(entry_id))
    except (TypeError, ValueError) as exc:
        raise EntryLookupError("Unknown entry.") from exc


def get_active_entry(entry_id, email=None):
    key = _entry_uuid(entry_id)
    rows = Entry.objects.filter(pk=key, is_deleted=False).prefetch_related("attachments")
    if email:
        rows = rows.filter(user=user_by_email(email))
    entry = rows.first()
    if entry is None:
        raise EntryLookupError("Unknown entry.")
    return entry


def entries_for_email(email):
    user = user_by_email(email)
    rows = (
        Entry.objects.filter(user=user, is_deleted=False)
        .prefetch_related("attachments")
        .order_by("-created_at")
    )
    return [entry_list_item(entry) for entry in rows]


def show_entry(entry_id, email=None):
    return entry_show_item(get_active_entry(entry_id, email=email))


def create_entry_for_email(email, text):
    cleaned = (text or "").strip()
    if not cleaned:
        raise EntryLookupError("Missing text.")
    user = user_by_email(email)
    return entry_show_item(ingest_text(user, cleaned))


def update_entry(user, entry, text):
    entry.content_text = text if text is not None else ""
    entry.save(update_fields=["content_text"])
    return entry


def update_entry_by_id(entry_id, text, email=None):
    entry = get_active_entry(entry_id, email=email)
    update_entry(entry.user, entry, text)
    return entry_show_item(entry)


def delete_entry(user, entry):
    now = timezone.now()
    bytes_freed = 0
    attachment_ids = []
    for item in entry.attachments.filter(is_deleted=False):
        bytes_freed += _unlink_stored_file(item.relative_path)
        _soft_delete(item, now)
        attachment_ids.append(str(item.id))
    _soft_delete(entry, now)
    return {
        "id": str(entry.id),
        "attachments": attachment_ids,
        "bytes_freed": bytes_freed,
    }


def delete_entry_by_id(entry_id, email=None):
    entry = get_active_entry(entry_id, email=email)
    return delete_entry(entry.user, entry)
