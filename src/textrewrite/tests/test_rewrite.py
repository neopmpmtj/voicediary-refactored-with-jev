from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError, AuthenticationError

from src.textrewrite.errors import RewriteError
from src.textrewrite.models import RewriteUsage
from src.textrewrite.services import rewrite_text

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _response(text, input_tokens=10, output_tokens=4):
    return SimpleNamespace(
        output_text=text,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _auth_error():
    response = MagicMock()
    response.status_code = 401
    response.headers = {}
    response.request = MagicMock()
    return AuthenticationError("invalid api key", response=response, body=None)


def _network_error():
    return APIConnectionError(message="down", request=MagicMock())


def test_rewrite_text_returns_rewrite_and_writes_usage(monkeypatch):
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr(
        "src.textrewrite.responses._request_rewrite",
        lambda *args, **kwargs: _response("Grouped idea."),
    )
    result = rewrite_text("raw source that must not be stored")
    assert result == {
        "text": "Grouped idea.",
        "model_id": "o3-mini",
        "input_tokens": 10,
        "output_tokens": 4,
    }
    assert "source" not in result
    assert "raw source that must not be stored" not in result.values()
    row = RewriteUsage.objects.get()
    assert row.model_id == "o3-mini"
    assert row.input_tokens == 10
    assert row.output_tokens == 4


def test_missing_api_key_writes_no_row(monkeypatch):
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "")
    with pytest.raises(RewriteError, match="AI_OPENAI_API_KEY is not set"):
        rewrite_text("hello")
    assert RewriteUsage.objects.count() == 0


def test_auth_refusal_writes_no_row(monkeypatch):
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr(
        "src.textrewrite.responses._request_rewrite",
        MagicMock(side_effect=_auth_error()),
    )
    with pytest.raises(RewriteError, match="OpenAI refused the request"):
        rewrite_text("hello")
    assert RewriteUsage.objects.count() == 0


def test_empty_reply_writes_no_row(monkeypatch):
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr(
        "src.textrewrite.responses._request_rewrite",
        lambda *args, **kwargs: _response("  "),
    )
    with pytest.raises(RewriteError, match="Empty rewrite"):
        rewrite_text("hello")
    assert RewriteUsage.objects.count() == 0


def test_network_failure_retries_then_writes_usage(monkeypatch):
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    mock_request = MagicMock(side_effect=[_network_error(), _response("Grouped idea.")])
    monkeypatch.setattr("src.textrewrite.responses._request_rewrite", mock_request)
    result = rewrite_text("hello")
    assert result["text"] == "Grouped idea."
    assert mock_request.call_count == 2
    assert RewriteUsage.objects.count() == 1
