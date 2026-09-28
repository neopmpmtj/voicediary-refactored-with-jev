from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from src.conference.models import ConferenceStatus, Segment
from src.conference.services import close_conference, ingest_segment, start_conference
from src.diary.models import Entry

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="conf@example.com", password="pass")


def _audio(name="clip.webm"):
    return SimpleUploadedFile(name, b"audio-bytes", content_type="audio/webm")


def test_segments_join_in_sequence_and_a_short_tail_completes_the_conference(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    conference = start_conference(user)
    transcripts = iter(["first part", "tail"])

    def transcribe(_path):
        return {"text": next(transcripts), "duration": 1, "model": "test-model"}

    with patch("src.conference.services.probe_duration_seconds", return_value=1.0), \
         patch("src.conference.services.strip_silence", return_value=False), \
         patch("src.conference.services.transcribe_audio", side_effect=transcribe), \
         patch("src.diary.jev.decide") as decide:
        first, _segment = ingest_segment(
            user, conference.id, _audio(), sequence=1, recording_duration_seconds=240, final=False,
        )
        assert first.status == ConferenceStatus.OPEN
        finished, tail = ingest_segment(
            user, conference.id, _audio("tail.webm"), sequence=2, recording_duration_seconds=12, final=True,
        )
    decide.assert_not_called()
    assert Entry.objects.count() == 0
    assert finished.status == ConferenceStatus.COMPLETE
    assert finished.content_text == "first part\n\ntail"
    assert finished.total_duration_seconds == 252
    assert tail.recording_duration_seconds == 12
    assert tail.relative_path.startswith(f"conferences/{user.pk}/{conference.id}/")
    assert "artifacts" not in tail.relative_path
    assert "attachments" not in tail.relative_path
    assert (tmp_path / tail.relative_path).is_file()


def test_late_segment_keeps_sequence_order(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    conference = start_conference(user)
    texts = {"2": "second", "1": "first"}

    def transcribe(path):
        name = str(path)
        key = "2" if "0002" in name else "1"
        return {"text": texts[key], "duration": 1, "model": "test-model"}

    with patch("src.conference.services.probe_duration_seconds", return_value=1.0), \
         patch("src.conference.services.strip_silence", return_value=False), \
         patch("src.conference.services.transcribe_audio", side_effect=transcribe):
        ingest_segment(user, conference.id, _audio(), sequence=2, recording_duration_seconds=240, final=False)
        finished, _segment = ingest_segment(
            user, conference.id, _audio(), sequence=1, recording_duration_seconds=200, final=True,
        )
    assert finished.content_text == "first\n\nsecond"
    assert list(finished.segments.order_by("sequence").values_list("sequence", flat=True)) == [1, 2]


def test_close_conference_omits_soft_deleted_segments(user):
    conference = start_conference(user)
    Segment.objects.create(
        conference=conference,
        sequence=1,
        content_text="keep",
        recording_duration_seconds=10,
        relative_path="conferences/x/0001.webm",
    )
    Segment.objects.create(
        conference=conference,
        sequence=2,
        content_text="drop",
        recording_duration_seconds=20,
        relative_path="conferences/x/0002.webm",
        is_deleted=True,
    )
    closed = close_conference(user, conference.id)
    assert closed.content_text == "keep"
    assert closed.total_duration_seconds == 10
    assert closed.segments.filter(is_deleted=False).count() == 1
