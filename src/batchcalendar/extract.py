import json
import logging
from datetime import datetime
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

from src.batchcalendar.errors import ExtractError
from src.batchcalendar.prompt import DEFAULT_TIMEZONE, extraction_prompt

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


def _parse_events(response_text):
    parsed = json.loads(_strip_markdown_json_fences(response_text))
    if "error" in parsed:
        return None, parsed["error"]
    events = parsed.get("events")
    if not events or not isinstance(events, list):
        return None, "No events extracted from text"
    validated = []
    for item in events:
        if not isinstance(item, dict):
            continue
        if "summary" not in item or "start" not in item or "end" not in item:
            continue
        validated.append(item)
    if not validated:
        return None, "No valid events extracted"
    return validated, None


def extract_batch_events(content_text, user_timezone=DEFAULT_TIMEZONE):
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
    model = config("BATCH_CAL_MODEL", default="gpt-4.1-mini")
    temperature = config("BATCH_CAL_TEMPERATURE", default=0.3, cast=float)
    max_tokens = config("BATCH_CAL_MAX_TOKENS", default=4096, cast=int)
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
        events, error = _parse_events(response_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse calendar extraction JSON: %s", exc)
        return None, f"Invalid JSON response: {exc}", usage
    return events, error, usage
