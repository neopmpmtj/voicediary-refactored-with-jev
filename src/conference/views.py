import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from src.conference.services import (
    ConferenceError,
    close_conference,
    conference_payload,
    ingest_segment,
    list_conferences,
    start_conference,
)
from src.diary.services import recorder_max_seconds

logger = logging.getLogger(__name__)


def _page_config():
    return {
        "startUrl": reverse("conference:start"),
        "segmentUrl": reverse("conference:segment"),
        "stopUrl": reverse("conference:stop"),
        "maxDuration": recorder_max_seconds(),
        "maxFileSize": 100 * 1024 * 1024,
    }


@login_required
@ensure_csrf_cookie
def conference_page(request):
    return render(request, "conference/record.html", {"recorder_config": _page_config()})


@login_required
def conference_list(request):
    return render(request, "conference/list.html", {"conferences": list_conferences(request.user)})


@login_required
@require_http_methods(["POST"])
def start(request):
    conference = start_conference(request.user)
    return JsonResponse(conference_payload(conference))


@login_required
@require_http_methods(["POST"])
def upload_segment(request):
    upload = request.FILES.get("audio")
    if not upload:
        return JsonResponse({"error": "missing_audio", "message": "No audio uploaded."}, status=400)
    final = request.POST.get("final") in {"1", "true", "True"}
    try:
        conference, segment = ingest_segment(
            request.user,
            request.POST.get("conference_id"),
            upload,
            sequence=request.POST.get("sequence"),
            recording_duration_seconds=request.POST.get("recording_duration_seconds"),
            final=final,
        )
    except ConferenceError as exc:
        logger.error("Conference segment rejected: %s", exc)
        status = 409 if "already saved" in str(exc) else 404 if "Unknown" in str(exc) else 400
        return JsonResponse({"error": "segment_rejected", "message": str(exc)}, status=status)
    payload = conference_payload(conference)
    payload["sequence"] = segment.sequence
    payload["segment_text"] = segment.content_text
    payload["transcription_error"] = segment.transcription_error
    return JsonResponse(payload)


@login_required
@require_http_methods(["POST"])
def stop(request):
    try:
        conference = close_conference(request.user, request.POST.get("conference_id"))
    except ConferenceError as exc:
        return JsonResponse({"error": "unknown_conference", "message": str(exc)}, status=404)
    return JsonResponse(conference_payload(conference))
