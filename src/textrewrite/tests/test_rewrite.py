from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError, AuthenticationError

from src.textrewrite.config import load_prompt
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
        "style": "grammar",
        "input_tokens": 10,
        "output_tokens": 4,
    }
    assert "source" not in result
    assert "raw source that must not be stored" not in result.values()
    row = RewriteUsage.objects.get()
    assert row.model_id == "o3-mini"
    assert row.style == "grammar"
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
    assert RewriteUsage.objects.get().style == "grammar"


def test_unknown_style_writes_no_row(monkeypatch):
    mock_request = MagicMock()
    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr("src.textrewrite.responses._request_rewrite", mock_request)
    with pytest.raises(RewriteError, match="Unknown style"):
        rewrite_text("hello", style="bogus")
    mock_request.assert_not_called()
    assert RewriteUsage.objects.count() == 0


def test_named_style_is_the_instruction_sent(monkeypatch):
    captured = {}

    def fake_request(client, model_id, instructions, text):
        captured["instructions"] = instructions
        captured["text"] = text
        return _response("Rewritten.")

    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr("src.textrewrite.responses._request_rewrite", fake_request)
    result = rewrite_text("hello", style="professional")
    assert captured["instructions"] == load_prompt("professional")
    assert captured["text"] == "hello"
    assert result["style"] == "professional"
    assert RewriteUsage.objects.get().style == "professional"


def test_default_call_uses_grammar_prompt(monkeypatch):
    captured = {}

    def fake_request(client, model_id, instructions, text):
        captured["instructions"] = instructions
        return _response("Grouped idea.")

    monkeypatch.setattr("src.textrewrite.responses.config", lambda *args, **kwargs: "sk-test")
    monkeypatch.setattr("src.textrewrite.responses._request_rewrite", fake_request)
    result = rewrite_text("hello")
    assert captured["instructions"] == load_prompt("grammar")
    assert result["style"] == "grammar"
