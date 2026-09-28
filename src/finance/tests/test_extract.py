import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import APIConnectionError, AuthenticationError

from src.finance.errors import ExtractError
from src.finance.extract import extract_from_text, normalize_item, parse_amount

pytestmark = pytest.mark.unit


def _config_value(key, default=None, cast=None):
    values = {
        "AI_OPENAI_API_KEY": "sk-test",
        "FINANCE_MODEL": "gpt-4.1-mini",
        "FINANCE_TEMPERATURE": 0.1,
        "FINANCE_MAX_TOKENS": 4096,
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


def test_parse_amount_accepts_comma_decimal():
    assert parse_amount("12,50") == Decimal("12.50")
    assert parse_amount(0) is None
    assert parse_amount("nope") is None


def test_normalize_item_defaults_and_skips_invalid():
    assert normalize_item("x") is None
    assert normalize_item({"amount": 0}) is None
    item = normalize_item(
        {
            "type": "INCOME",
            "amount": "20",
            "currency": "eur",
            "transaction_date": "2026-09-28",
            "category": "Food",
        }
    )
    assert item["type"] == "income"
    assert item["amount"] == Decimal("20")
    assert item["currency"] == "EUR"
    assert item["transaction_date"] == date(2026, 9, 28)
    assert item["category"] == "Food"


def test_extract_returns_validated_items(monkeypatch):
    payload = {
        "record_name": "Despesas de hoje",
        "record_context": "viagem",
        "items": [
            {"type": "expense", "amount": 20, "currency": "EUR", "description": "café"},
            {"type": "expense", "amount": 0, "description": "skip"},
        ],
    }
    monkeypatch.setattr("src.finance.extract.config", _config_value)
    monkeypatch.setattr(
        "src.finance.extract._request_extract",
        lambda *args, **kwargs: _response(json.dumps(payload)),
    )
    name, context, items, error, usage = extract_from_text("gastei 20 no café")
    assert error is None
    assert name == "Despesas de hoje"
    assert context == "viagem"
    assert len(items) == 1
    assert items[0]["description"] == "café"
    assert usage == {"input": 4, "output": 6, "total": 10}


def test_extract_returns_model_error_without_raising(monkeypatch):
    monkeypatch.setattr("src.finance.extract.config", _config_value)
    monkeypatch.setattr(
        "src.finance.extract._request_extract",
        lambda *args, **kwargs: _response(
            json.dumps({"error": "No financial information to extract"})
        ),
    )
    name, context, items, error, usage = extract_from_text("hello")
    assert name is None
    assert context is None
    assert items is None
    assert error == "No financial information to extract"
    assert usage["input"] == 4


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr("src.finance.extract.config", lambda *args, **kwargs: "")
    with pytest.raises(ExtractError, match="AI_OPENAI_API_KEY is not set"):
        extract_from_text("hello")


def test_auth_refusal_raises(monkeypatch):
    response = MagicMock()
    response.status_code = 401
    response.headers = {}
    response.request = MagicMock()
    monkeypatch.setattr("src.finance.extract.config", _config_value)
    monkeypatch.setattr(
        "src.finance.extract._request_extract",
        MagicMock(side_effect=AuthenticationError("invalid api key", response=response, body=None)),
    )
    with pytest.raises(ExtractError, match="OpenAI refused the request"):
        extract_from_text("hello")


def test_network_failure_after_retry_raises(monkeypatch):
    monkeypatch.setattr("src.finance.extract.config", _config_value)
    monkeypatch.setattr(
        "src.finance.extract._request_extract",
        MagicMock(side_effect=APIConnectionError(message="down", request=MagicMock())),
    )
    with pytest.raises(ExtractError, match="Network failure"):
        extract_from_text("hello")
