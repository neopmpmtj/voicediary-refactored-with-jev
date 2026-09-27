from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.conference.models import Conference, ConferenceStatus
from src.diary.models import Entry

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


def _audio():
    return SimpleUploadedFile("clip.webm", b"audio-bytes", content_type="audio/webm")


def _transcribe(text):
    return {"text": text, "duration": 1, "model": "test-model"}


def test_conference_page_is_linked_from_diary_voice(auth_client):
    voice = auth_client.get("/voice/")
    assert voice.status_code == 200
    assert b'href="/conference/"' in voice.content
    page = auth_client.get("/conference/")
    assert page.status_code == 200
    assert b"Record" in page.content
    assert b"Continuing" in page.content or b"keeps going until you stop" in page.content


@patch("src.conference.services.probe_duration_seconds", return_value=1.0)
@patch("src.conference.services.strip_silence", return_value=False)
@patch("src.conference.services.transcribe_audio", side_effect=lambda _path: _transcribe("part"))
def test_http_segments_stay_one_conference_until_stop(mock_transcribe, mock_strip, mock_probe, auth_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    started = auth_client.post("/conference/start/")
    assert started.status_code == 200
    conference_id = started.json()["conference_id"]
    assert started.json()["status"] == "open"

    first = auth_client.post("/conference/segment/", {
        "conference_id": conference_id,
        "sequence": "1",
        "final": "0",
        "recording_duration_seconds": "240",
        "audio": _audio(),
    })
    assert first.status_code == 200
    assert first.json()["status"] == "open"
    assert Conference.objects.get(pk=conference_id).status == ConferenceStatus.OPEN

    tail = auth_client.post("/conference/segment/", {
        "conference_id": conference_id,
        "sequence": "2",
        "final": "1",
        "recording_duration_seconds": "12",
        "audio": _audio(),
    })
    assert tail.status_code == 200
    body = tail.json()
    assert body["status"] == "complete"
    assert body["content_text"] == "part\n\npart"
    assert body["segment_count"] == 2
    assert Entry.objects.count() == 0

    listing = auth_client.get("/conference/list/")
    assert listing.status_code == 200
    assert b"part" in listing.content


def test_stop_without_audio_closes_the_conference(auth_client):
    started = auth_client.post("/conference/start/")
    conference_id = started.json()["conference_id"]
    closed = auth_client.post("/conference/stop/", {"conference_id": conference_id})
    assert closed.status_code == 200
    assert closed.json()["status"] == "complete"
    assert Conference.objects.get(pk=conference_id).ended_at is not None


def test_another_user_cannot_add_a_segment(auth_client, user, django_user_model, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    started = auth_client.post("/conference/start/")
    conference_id = started.json()["conference_id"]
    other = django_user_model.objects.create_user(email="other@example.com", password="pass")
    auth_client.force_login(other)
    with patch("src.conference.services.transcribe_audio", return_value=_transcribe("nope")):
        response = auth_client.post("/conference/segment/", {
            "conference_id": conference_id,
            "sequence": "1",
            "final": "1",
            "audio": _audio(),
        })
    assert response.status_code == 404
    assert Conference.objects.get(pk=conference_id, user=user).segments.count() == 0
