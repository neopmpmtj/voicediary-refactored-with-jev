import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from src.diary.models import Attachment, Entry
from src.diary.services import (
    AttachmentError,
    entry_payload,
    ingest_audio,
    ingest_files,
    ingest_text,
    list_entries,
    recorder_max_seconds,
    store_attachments,
)
from src.diary.storage import attachment_disk_path, attachment_path_is_allowed
from src.diary.transcription import TranscriptionError

logger = logging.getLogger(__name__)


def _recorder_config(request):
    return {
        "uploadUrl": "/voice/upload/",
        "filesUploadUrl": "/files/upload/",
        "maxDuration": recorder_max_seconds(),
        "maxFileSize": 100 * 1024 * 1024,
        "swipeVoiceUrl": "/voice/",
        "swipeTextUrl": "/text-input/",
    }


def _wants_json(request):
    accept = request.headers.get("Accept", "")
    return "application/json" in accept or request.headers.get("X-Requested-With") == "XMLHttpRequest"


@login_required
@ensure_csrf_cookie
def voice_page(request):
    return render(request, "diary/voice.html", {"recorder_config": _recorder_config(request)})


@login_required
@ensure_csrf_cookie
def text_page(request):
    if request.method == "POST":
        files = request.FILES.getlist("files")
        text = request.POST.get("text", "")
        if not (text or "").strip() and not files:
            return render(request, "diary/text.html", {
                "error": "Enter text or attach a file.",
                "text": text,
            })
        entry = ingest_text(request.user, text, uploads=files)
        if entry.classification_error:
            return render(request, "diary/text.html", {
                "error": "Saved the text. Classification failed.",
                "text": entry.content_text,
            })
        return redirect("diary:list")
    return render(request, "diary/text.html")


@login_required
@require_http_methods(["POST"])
def upload_audio(request):
    upload = request.FILES.get("audio")
    if not upload:
        return JsonResponse({"error": "missing_audio", "message": "No audio uploaded."}, status=400)
    duration = request.POST.get("recording_duration_seconds")
    try:
        entry = ingest_audio(
            request.user,
            upload,
            recording_duration_seconds=duration,
            recording_group_id=request.POST.get("recording_group_id"),
            uploads=request.FILES.getlist("files"),
        )
    except TranscriptionError as exc:
        logger.error("Transcription failed: %s", exc)
        return JsonResponse({"error": "transcription_failed", "message": str(exc)}, status=502)
    except Exception as exc:
        logger.error("Audio ingest failed: %s", exc)
        return JsonResponse({"error": "ingest_failed", "message": "Could not store the recording."}, status=500)
    return JsonResponse(entry_payload(entry))


@login_required
@require_http_methods(["POST"])
def upload_files(request):
    files = request.FILES.getlist("files")
    if not files:
        if _wants_json(request):
            return JsonResponse({"error": "missing_files", "message": "No files uploaded."}, status=400)
        messages.error(request, "Choose at least one file.")
        return redirect("diary:list")
    entry_id = request.POST.get("entry_id")
    try:
        if entry_id:
            entry = get_object_or_404(Entry, pk=entry_id, user=request.user)
            store_attachments(request.user, entry, files)
        else:
            entry = ingest_files(request.user, files)
    except AttachmentError as exc:
        if _wants_json(request):
            return JsonResponse({"error": "missing_files", "message": str(exc)}, status=400)
        messages.error(request, str(exc))
        return redirect("diary:list")
    if _wants_json(request):
        return JsonResponse(entry_payload(entry))
    if entry_id:
        messages.success(request, "Files added to the entry.")
    else:
        messages.success(request, "Files saved.")
    return redirect("diary:list")


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(Attachment, pk=attachment_id, user=request.user)
    if not attachment_path_is_allowed(request.user.pk, attachment.relative_path):
        return JsonResponse({"error": "not_found", "message": "File is not available."}, status=404)
    path = attachment_disk_path(attachment.relative_path)
    return FileResponse(path.open("rb"), as_attachment=True, filename=attachment.original_filename)


@login_required
def entry_list(request):
    return render(request, "diary/list.html", {"entries": list_entries(request.user)})
