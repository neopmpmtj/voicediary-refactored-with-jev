import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from diary.services import ingest_audio, ingest_text, list_entries, recorder_max_seconds
from diary.transcription import TranscriptionError

logger = logging.getLogger(__name__)


def _recorder_config(request):
    return {
        "uploadUrl": "/voice/upload/",
        "maxDuration": recorder_max_seconds(),
        "maxFileSize": 100 * 1024 * 1024,
        "swipeVoiceUrl": "/voice/",
        "swipeTextUrl": "/text-input/",
    }


@login_required
@ensure_csrf_cookie
def voice_page(request):
    return render(request, "diary/voice.html", {"recorder_config": _recorder_config(request)})


@login_required
@ensure_csrf_cookie
def text_page(request):
    if request.method == "POST":
        entry = ingest_text(request.user, request.POST.get("text", ""))
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
        )
    except TranscriptionError as exc:
        logger.error("Transcription failed: %s", exc)
        return JsonResponse({"error": "transcription_failed", "message": str(exc)}, status=502)
    except Exception as exc:
        logger.error("Audio ingest failed: %s", exc)
        return JsonResponse({"error": "ingest_failed", "message": "Could not store the recording."}, status=500)
    return JsonResponse({
        "item_id": str(entry.id),
        "status": "complete",
        "content_text": entry.content_text,
        "route": entry.route,
        "intent": entry.intent,
        "subject": entry.subject,
        "classification_error": entry.classification_error,
    })


@login_required
def entry_list(request):
    return render(request, "diary/list.html", {"entries": list_entries(request.user)})
