from decouple import config
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from src.textrewrite.errors import RewriteError

_NETWORK_ERRORS = (APIConnectionError, APITimeoutError)
_REFUSAL_ERRORS = (AuthenticationError, PermissionDeniedError, RateLimitError)


def _request_rewrite(client, model_id, instructions, text):
    return client.responses.create(
        model=model_id,
        instructions=instructions,
        input=text,
    )


def _output_text(response):
    return (getattr(response, "output_text", None) or "").strip()


def _token_counts(response):
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
    }


def create_rewrite(model_id, instructions, text):
    api_key = config("AI_OPENAI_API_KEY", default="")
    if not api_key:
        raise RewriteError("AI_OPENAI_API_KEY is not set")
    client = OpenAI(api_key=api_key, timeout=120.0)
    try:
        response = _request_rewrite(client, model_id, instructions, text)
    except _NETWORK_ERRORS:
        try:
            response = _request_rewrite(client, model_id, instructions, text)
        except _NETWORK_ERRORS as exc:
            raise RewriteError("Network failure") from exc
        except _REFUSAL_ERRORS as exc:
            raise RewriteError("OpenAI refused the request") from exc
        except Exception as exc:
            raise RewriteError("Rewrite failed") from exc
    except _REFUSAL_ERRORS as exc:
        raise RewriteError("OpenAI refused the request") from exc
    except Exception as exc:
        raise RewriteError("Rewrite failed") from exc
    rewritten = _output_text(response)
    if not rewritten:
        raise RewriteError("Empty rewrite")
    tokens = _token_counts(response)
    return {
        "text": rewritten,
        "input_tokens": tokens["input_tokens"],
        "output_tokens": tokens["output_tokens"],
    }
