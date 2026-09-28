import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from src.diary.models import Entry, ItemType

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _classify_ok(_state):
    return {
        "answers": {
            "intent": {"choice": "freeform", "confidence": 0.9},
            "subject": {"choice": "diary", "confidence": 0.8},
            "user_asked_for_diary": {"noul": 0.2},
            "continues_prior": {"noul": 0.1},
        },
        "usage": {"input_tokens": 2, "output_tokens": 1},
    }


def test_entry_audio_creates_audio_entry(user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    source = tmp_path / "clip.webm"
    source.write_bytes(b"audio-bytes")
    with patch("src.diary.services.transcribe_audio", return_value={"text": "hello", "duration": 1, "model": "x"}), \
         patch("src.diary.services.probe_duration_seconds", return_value=1.0), \
         patch("src.diary.services.strip_silence", return_value=False), \
         patch("src.diary.services.decide", side_effect=_classify_ok):
        out = StringIO()
        call_command("entry_audio", str(source), "--email", user.email, "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["content_text"] == "hello"
    assert payload["item_type"] == ItemType.AUDIO
    entry = Entry.objects.get(pk=payload["id"])
    assert entry.user_id == user.pk
    assert entry.recording_duration_seconds == 1
    assert entry.intent == "freeform"


def test_entry_audio_missing_file(user):
    with pytest.raises(CommandError, match="Unknown file"):
        call_command("entry_audio", "/no/such/clip.webm", "--email", user.email)
