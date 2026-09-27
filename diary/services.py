import logging
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from decouple import config

from diary.audio import probe_duration_seconds, strip_silence
from diary.jev import JevError, decide
from diary.models import Entry, ItemType, UsageLog
from diary.transcription import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)

CALENDAR_INTENTS = {"follow-up", "reschedule"}
NOUL_YES = 0.5


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


def _entry_payload(entry):
    return {
        "item_id": str(entry.id),
        "status": "complete",
        "content_text": entry.content_text,
        "route": entry.route,
        "intent": entry.intent,
        "subject": entry.subject,
        "classification_error": entry.classification_error,
    }


def ingest_text(user, text):
    cleaned = (text or "").strip()
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


def ingest_audio(user, upload, recording_duration_seconds=None, recording_group_id=None):
    if not isinstance(upload, UploadedFile):
        raise TranscriptionError("Missing audio upload")
    source = _store_upload(upload, user.pk)
    original_duration = probe_duration_seconds(source)
    if recording_duration_seconds not in (None, ""):
        try:
            original_duration = float(recording_duration_seconds)
        except (TypeError, ValueError):
            pass
    processed = source.with_name(f"{source.stem}-processed{source.suffix}")
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
    entry.save()
    return entry


def list_entries(user):
    return Entry.objects.filter(user=user).order_by("-created_at")
