import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from src.diary.models import UsageLog
from src.diary.services import ingest_text

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


def test_usage_list_json_after_classify(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        entry = ingest_text(user, "Logged")
    out = StringIO()
    call_command("usage_list", "--email", user.email, "--json", stdout=out)
    rows = json.loads(out.getvalue())
    assert {item["usage_type"] for item in rows} == {"input_tokens", "output_tokens"}
    assert all(item["entry_id"] == str(entry.id) for item in rows)
    assert all(item["service"] == "jev" for item in rows)


def test_usage_list_filters_by_entry_and_limit(user):
    with patch("src.diary.services.decide", side_effect=_classify_ok):
        first = ingest_text(user, "First")
        ingest_text(user, "Second")
    out = StringIO()
    call_command(
        "usage_list",
        "--email",
        user.email,
        "--entry",
        str(first.id),
        "--limit",
        "1",
        "--json",
        stdout=out,
    )
    rows = json.loads(out.getvalue())
    assert len(rows) == 1
    assert rows[0]["entry_id"] == str(first.id)


def test_usage_list_unknown_entry(user):
    with pytest.raises(CommandError, match="Unknown entry"):
        call_command("usage_list", "--email", user.email, "--entry", "not-a-uuid")


def test_usage_list_empty(user):
    out = StringIO()
    call_command("usage_list", "--email", user.email, stdout=out)
    assert out.getvalue().strip() == "no usage"
    assert UsageLog.objects.filter(user=user).count() == 0
