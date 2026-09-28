import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from src.conference.services import ingest_segment, start_conference

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="conf@example.com", password="pass")


def _audio(name="clip.webm"):
    return SimpleUploadedFile(name, b"audio-bytes", content_type="audio/webm")


def _ingest_two_segments(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    conference = start_conference(user)
    transcripts = iter(["first part", "tail"])

    def transcribe(_path):
        return {"text": next(transcripts), "duration": 1, "model": "test-model"}

    with patch("src.conference.services.probe_duration_seconds", return_value=1.0), \
         patch("src.conference.services.strip_silence", return_value=False), \
         patch("src.conference.services.transcribe_audio", side_effect=transcribe):
        ingest_segment(
            user, conference.id, _audio(), sequence=1, recording_duration_seconds=240, final=False,
        )
        ingest_segment(
            user, conference.id, _audio("tail.webm"), sequence=2, recording_duration_seconds=12, final=True,
        )
    conference.refresh_from_db()
    return conference


def test_conference_list_json_omits_transcript(user, settings, tmp_path):
    conference = _ingest_two_segments(user, settings, tmp_path)
    out = StringIO()
    call_command("conference_list", "--email", user.email, "--json", stdout=out)
    rows = json.loads(out.getvalue())
    assert len(rows) == 1
    item = rows[0]
    assert item["id"] == str(conference.id)
    assert item["status"] == "complete"
    assert item["segment_count"] == 2
    assert item["total_duration_seconds"] == 252
    assert "content_text" not in item
    assert "segments" not in item


def test_conference_show_json_includes_joined_text_and_segments(user, settings, tmp_path):
    conference = _ingest_two_segments(user, settings, tmp_path)
    out = StringIO()
    call_command("conference_show", str(conference.id), "--email", user.email, "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["id"] == str(conference.id)
    assert payload["content_text"] == "first part\n\ntail"
    assert [item["sequence"] for item in payload["segments"]] == [1, 2]
    assert payload["segments"][0]["content_text"] == "first part"
    assert payload["segments"][1]["content_text"] == "tail"
    plain = StringIO()
    call_command("conference_show", str(conference.id), "--email", user.email, stdout=plain)
    assert plain.getvalue().strip() == "first part\n\ntail"


def test_conference_list_unknown_user(user):
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("conference_list", "--email", "missing@example.com")
    out = StringIO()
    call_command("conference_list", "--email", user.email, stdout=out)
    assert out.getvalue().strip() == "no conferences"


def test_conference_show_rejects_another_users_id(user, django_user_model, settings, tmp_path):
    other = django_user_model.objects.create_user(email="other@example.com", password="pass")
    conference = _ingest_two_segments(other, settings, tmp_path)
    with pytest.raises(CommandError, match="Unknown conference"):
        call_command("conference_show", str(conference.id), "--email", user.email)
