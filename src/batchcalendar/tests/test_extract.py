import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError, AuthenticationError

from src.batchcalendar.errors import ExtractError
from src.batchcalendar.extract import extract_batch_events

pytestmark = pytest.mark.unit


def _config_value(key, default=None, cast=None):
    values = {
        "AI_OPENAI_API_KEY": "sk-test",
        "BATCH_CAL_MODEL": "gpt-4.1-mini",
        "BATCH_CAL_TEMPERATURE": 0.3,
        "BATCH_CAL_MAX_TOKENS": 4096,
    }
    value = values.get(key, default)
    return cast(value) if cast else value


def _response(content, input_tokens=4, output_tokens=6):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )


def test_extract_returns_validated_events(monkeypatch):
    payload = {
        "events": [
            {
                "summary": "Physio",
                "start": {"dateTime": "2026-10-01T17:00:00", "timeZone": "Europe/Lisbon"},
                "end": {"dateTime": "2026-10-01T17:30:00", "timeZone": "Europe/Lisbon"},
            },
            {"summary": "skip me"},
        ]
    }
    monkeypatch.setattr("src.batchcalendar.extract.config", _config_value)
    monkeypatch.setattr(
        "src.batchcalendar.extract._request_extract",
        lambda *args, **kwargs: _response(json.dumps(payload)),
    )
    events, error, usage = extract_batch_events("physio at 5")
    assert error is None
    assert len(events) == 1
    assert events[0]["summary"] == "Physio"
    assert usage == {"input": 4, "output": 6, "total": 10}


def test_extract_returns_model_error_without_raising(monkeypatch):
    monkeypatch.setattr("src.batchcalendar.extract.config", _config_value)
    monkeypatch.setattr(
        "src.batchcalendar.extract._request_extract",
        lambda *args, **kwargs: _response(
            json.dumps({"error": "Insufficient information to create calendar events"})
        ),
    )
    events, error, usage = extract_batch_events("hello")
    assert events is None
    assert error == "Insufficient information to create calendar events"
    assert usage["input"] == 4


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr("src.batchcalendar.extract.config", lambda *args, **kwargs: "")
    with pytest.raises(ExtractError, match="AI_OPENAI_API_KEY is not set"):
        extract_batch_events("hello")


def test_auth_refusal_raises(monkeypatch):
    response = MagicMock()
    response.status_code = 401
    response.headers = {}
    response.request = MagicMock()
    monkeypatch.setattr("src.batchcalendar.extract.config", _config_value)
    monkeypatch.setattr(
        "src.batchcalendar.extract._request_extract",
        MagicMock(side_effect=AuthenticationError("invalid api key", response=response, body=None)),
    )
    with pytest.raises(ExtractError, match="OpenAI refused the request"):
        extract_batch_events("hello")


def test_network_failure_after_retry_raises(monkeypatch):
    monkeypatch.setattr("src.batchcalendar.extract.config", _config_value)
    monkeypatch.setattr(
        "src.batchcalendar.extract._request_extract",
        MagicMock(side_effect=APIConnectionError(message="down", request=MagicMock())),
    )
    with pytest.raises(ExtractError, match="Network failure"):
        extract_batch_events("hello")
