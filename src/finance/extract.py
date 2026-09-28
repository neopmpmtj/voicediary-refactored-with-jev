import json
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from decouple import config
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from src.finance.errors import ExtractError
from src.finance.prompt import DEFAULT_TIMEZONE, extraction_prompt

logger = logging.getLogger(__name__)

_NETWORK_ERRORS = (APIConnectionError, APITimeoutError)
_REFUSAL_ERRORS = (AuthenticationError, PermissionDeniedError, RateLimitError)


def _strip_markdown_json_fences(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


def _request_extract(client, model, prompt, temperature, max_tokens):
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _usage_dict(response):
    usage = getattr(response, "usage", None)
    return {
        "input": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total": getattr(usage, "total_tokens", 0) if usage else 0,
    }


def parse_amount(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value if value > 0 else None
    if isinstance(value, (int, float)) and value > 0:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            parsed = Decimal(value.strip().replace(",", "."))
            return parsed if parsed > 0 else None
        except (InvalidOperation, ValueError):
            return None
    return None


def parse_transaction_date(value):
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def normalize_item(item_dict):
    if not isinstance(item_dict, dict):
        return None
    amount = parse_amount(item_dict.get("amount"))
    if amount is None:
        return None
    item_type = (item_dict.get("type") or "expense").strip().lower()
    if item_type not in ("expense", "income"):
        item_type = "expense"
    currency = (item_dict.get("currency") or "EUR").strip().upper()[:10] or "EUR"
    return {
        "type": item_type,
        "amount": amount,
        "currency": currency,
        "category": (item_dict.get("category") or "")[:100],
        "merchant": (item_dict.get("merchant") or "")[:255],
        "transaction_date": parse_transaction_date(item_dict.get("transaction_date")),
        "description": item_dict.get("description") or "",
        "payment_method": (item_dict.get("payment_method") or "")[:50],
    }


def _parse_payload(response_text):
    parsed = json.loads(_strip_markdown_json_fences(response_text))
    if "error" in parsed:
        return None, None, None, parsed["error"]
    items = parsed.get("items")
    if not items or not isinstance(items, list):
        return None, None, None, "No financial items extracted from text"
    validated = []
    for item in items:
        normalized = normalize_item(item)
        if normalized is not None:
            validated.append(normalized)
    if not validated:
        return None, None, None, "No valid financial items extracted"
    record_name = (parsed.get("record_name") or "Despesas")[:255]
    record_context = parsed.get("record_context") or ""
    return record_name, record_context, validated, None


def extract_from_text(content_text, user_timezone=DEFAULT_TIMEZONE):
    api_key = config("AI_OPENAI_API_KEY", default="")
    if not api_key:
        raise ExtractError("AI_OPENAI_API_KEY is not set")
    try:
        tz = ZoneInfo(user_timezone)
        effective_timezone = user_timezone
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        effective_timezone = DEFAULT_TIMEZONE
    now = datetime.now(tz=tz)
    prompt = extraction_prompt(
        content_text,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        timezone=effective_timezone,
    )
    client = OpenAI(api_key=api_key, timeout=60.0)
    model = config("FINANCE_MODEL", default="gpt-4.1-mini")
    temperature = config("FINANCE_TEMPERATURE", default=0.1, cast=float)
    max_tokens = config("FINANCE_MAX_TOKENS", default=4096, cast=int)
    try:
        response = _request_extract(client, model, prompt, temperature, max_tokens)
    except _NETWORK_ERRORS:
        try:
            response = _request_extract(client, model, prompt, temperature, max_tokens)
        except _NETWORK_ERRORS as exc:
            raise ExtractError("Network failure") from exc
        except _REFUSAL_ERRORS as exc:
            raise ExtractError("OpenAI refused the request") from exc
        except Exception as exc:
            raise ExtractError("Extraction failed") from exc
    except _REFUSAL_ERRORS as exc:
        raise ExtractError("OpenAI refused the request") from exc
    except Exception as exc:
        raise ExtractError("Extraction failed") from exc
    usage = _usage_dict(response)
    response_text = ((response.choices[0].message.content) if response.choices else "") or ""
    try:
        record_name, record_context, items, error = _parse_payload(response_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse finance extraction JSON: %s", exc)
        return None, None, None, f"Invalid JSON response: {exc}", usage
    return record_name, record_context, items, error, usage
