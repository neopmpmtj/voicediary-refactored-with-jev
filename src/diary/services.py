import logging
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from decouple import config

from src.diary.audio import probe_duration_seconds, strip_silence
from src.diary.jev import JevError, decide
from src.diary.models import Attachment, Entry, ItemType, UsageLog
from src.diary.storage import (
    ATTACHMENTS_SUBDIR,
    allocate_unique_attachment_filename,
    artifacts_dir_for_user,
    attachments_dir_for_entry,
    sanitize_storage_filename,
)
from src.diary.transcription import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)

CALENDAR_INTENTS = {"follow-up", "reschedule"}
NOUL_YES = 0.5


class AttachmentError(Exception):
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
    existing_qs = Entry.objects.filter(user=user)
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
    entry.route = derive_route(entry.intent, entry.subject)
    entry.classification_error = ""
    usage = payload.get("usage") or {}
    _log_usage(entry.user, entry, "jev", "input_tokens", usage.get("input_tokens") or 0)
    _log_usage(entry.user, entry, "jev", "output_tokens", usage.get("output_tokens") or 0)


def _attachment_payload(entry):
    return [
        {
            "id": str(item.id),
            "filename": item.original_filename,
            "uploaded_at": item.uploaded_at.isoformat(),
        }
        for item in entry.attachments.all()
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
        "attachment_count": entry.attachments.count(),
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
    except JevError as exc:
        logger.error("Classification failed for %s: %s", entry.id, exc)
        entry.classification_error = str(exc)
    if uploads:
        store_attachments(user, entry, uploads)
    entry.save()
    return entry


def list_entries(user):
    return Entry.objects.filter(user=user).prefetch_related("attachments").order_by("-created_at")
