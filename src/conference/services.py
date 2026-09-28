import logging
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.utils import timezone

from src.conference.models import Conference, ConferenceStatus, Segment
from src.diary.audio import probe_duration_seconds, strip_silence
from src.diary.models import UsageLog
from src.diary.transcription import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)


class ConferenceError(Exception):
    pass


def start_conference(user):
    return Conference.objects.create(user=user, status=ConferenceStatus.OPEN)


def conference_for_user(user, conference_id):
    try:
        key = uuid.UUID(str(conference_id))
    except (TypeError, ValueError) as exc:
        raise ConferenceError("Unknown conference") from exc
    try:
        return Conference.objects.get(pk=key, user=user)
    except Conference.DoesNotExist as exc:
        raise ConferenceError("Unknown conference") from exc


def refresh_conference(conference):
    segments = list(conference.segments.filter(is_deleted=False).order_by("sequence"))
    texts = [(item.content_text or "").strip() for item in segments]
    conference.content_text = "\n\n".join(text for text in texts if text)
    durations = [item.recording_duration_seconds for item in segments if item.recording_duration_seconds is not None]
    conference.total_duration_seconds = sum(durations) if durations else None
    return conference


def close_conference(user, conference_id):
    conference = conference_for_user(user, conference_id)
    if conference.status != ConferenceStatus.COMPLETE:
        conference.status = ConferenceStatus.COMPLETE
        conference.ended_at = timezone.now()
    refresh_conference(conference)
    conference.save()
    return conference


def _store_segment_file(upload, user_id, conference_id, sequence):
    folder = Path(settings.MEDIA_ROOT) / "conferences" / str(user_id) / str(conference_id)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.name).suffix or ".webm"
    source = folder / f"{int(sequence):04d}{suffix}"
    with source.open("wb") as dest:
        for chunk in upload.chunks():
            dest.write(chunk)
    return source


def _relative(path):
    root = Path(settings.MEDIA_ROOT).resolve()
    return path.resolve().relative_to(root).as_posix()


def _duration_seconds(source, reported):
    duration = probe_duration_seconds(source)
    if reported not in (None, ""):
        try:
            duration = float(reported)
        except (TypeError, ValueError):
            pass
    if duration is None:
        return None
    return int(round(duration))


def ingest_segment(user, conference_id, upload, *, sequence, recording_duration_seconds=None, final=False):
    if not isinstance(upload, UploadedFile):
        raise ConferenceError("Missing audio upload")
    try:
        sequence = int(sequence)
    except (TypeError, ValueError) as exc:
        raise ConferenceError("Segment sequence is required") from exc
    if sequence < 1:
        raise ConferenceError("Segment sequence is required")

    conference = conference_for_user(user, conference_id)
    source = _store_segment_file(upload, user.pk, conference.id, sequence)
    original_duration = _duration_seconds(source, recording_duration_seconds)
    processed = source.with_name(f"{source.stem}-processed{source.suffix}")
    audio_for_transcript = source
    processed_duration = original_duration
    processed_relative = ""
    if strip_silence(source, processed):
        audio_for_transcript = processed
        processed_duration = probe_duration_seconds(processed)
        processed_relative = _relative(processed)

    text = ""
    error = ""
    transcript = {}
    try:
        transcript = transcribe_audio(audio_for_transcript)
        text = (transcript.get("text") or "").strip()
    except TranscriptionError as exc:
        logger.error("Conference transcription failed for %s segment %s: %s", conference.id, sequence, exc)
        error = str(exc)

    try:
        with transaction.atomic():
            segment = Segment.objects.create(
                conference=conference,
                sequence=sequence,
                content_text=text,
                transcription_error=error,
                recording_duration_seconds=original_duration,
                processed_duration_seconds=processed_duration,
                relative_path=_relative(source),
                processed_relative_path=processed_relative,
            )
            locked = Conference.objects.select_for_update().get(pk=conference.pk)
            if final and locked.status != ConferenceStatus.COMPLETE:
                locked.status = ConferenceStatus.COMPLETE
                locked.ended_at = timezone.now()
            refresh_conference(locked)
            locked.save()
    except IntegrityError as exc:
        raise ConferenceError("That segment was already saved") from exc

    minutes = transcript.get("duration") if transcript else None
    if minutes is None and processed_duration is not None:
        minutes = processed_duration
    if text and minutes is not None:
        UsageLog.objects.create(
            user=user,
            entry=None,
            service=transcript.get("model") or "transcription",
            usage_type="audio_minutes",
            amount=Decimal(str(float(minutes) / 60.0)),
        )
    conference.refresh_from_db()
    return conference, segment


def list_conferences(user):
    return (
        Conference.objects.filter(user=user)
        .prefetch_related(
            Prefetch(
                "segments",
                queryset=Segment.objects.filter(is_deleted=False).order_by("sequence"),
            )
        )
        .order_by("-started_at")
    )


def conference_payload(conference):
    conference.refresh_from_db()
    return {
        "conference_id": str(conference.id),
        "status": conference.status,
        "content_text": conference.content_text,
        "total_duration_seconds": conference.total_duration_seconds,
        "segment_count": conference.segments.filter(is_deleted=False).count(),
    }
