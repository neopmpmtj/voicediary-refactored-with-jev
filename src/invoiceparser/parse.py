import base64
import json
import logging

from decouple import config
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from src.invoiceparser.errors import InvoiceError
from src.invoiceparser.prompt import PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

_NETWORK_ERRORS = (APIConnectionError, APITimeoutError)
_REFUSAL_ERRORS = (AuthenticationError, PermissionDeniedError, RateLimitError)


def _strip_markdown_json_fences(text):
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines)
    return stripped.strip()


def _request_parse(client, model, pdf_data, filename, temperature, max_tokens):
    encoded = base64.standard_b64encode(pdf_data).decode("utf-8")
    return client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": filename,
                        "file_data": f"data:application/pdf;base64,{encoded}",
                    },
                    {
                        "type": "input_text",
                        "text": PROMPT_TEMPLATE,
                    },
                ],
            },
        ],
        temperature=temperature,
        max_output_tokens=max_tokens,
    )


def _usage_dict(response):
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
    }


def parse_pdf_invoice(pdf_data, filename):
    api_key = config("AI_OPENAI_API_KEY", default="")
    if not api_key:
        raise InvoiceError("AI_OPENAI_API_KEY is not set")
    client = OpenAI(api_key=api_key, timeout=120.0)
    model = config("INVOICE_PARSER_MODEL", default="gpt-4o")
    temperature = config("INVOICE_PARSER_TEMPERATURE", default=0.0, cast=float)
    max_tokens = config("INVOICE_PARSER_MAX_TOKENS", default=4096, cast=int)
    try:
        response = _request_parse(
            client, model, pdf_data, filename, temperature, max_tokens
        )
    except _NETWORK_ERRORS:
        try:
            response = _request_parse(
                client, model, pdf_data, filename, temperature, max_tokens
            )
        except _NETWORK_ERRORS as exc:
            raise InvoiceError("Network failure") from exc
        except _REFUSAL_ERRORS as exc:
            raise InvoiceError("OpenAI refused the request") from exc
        except Exception as exc:
            raise InvoiceError("Invoice parse failed") from exc
    except _REFUSAL_ERRORS as exc:
        raise InvoiceError("OpenAI refused the request") from exc
    except Exception as exc:
        raise InvoiceError("Invoice parse failed") from exc
    usage = _usage_dict(response)
    raw_text = (getattr(response, "output_text", None) or "").strip()
    try:
        parsed = json.loads(_strip_markdown_json_fences(raw_text))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse invoice JSON for %s: %s", filename, exc)
        parsed = {"error": "LLM returned invalid JSON"}
    return {"parsed": parsed, "usage": usage, "model": model}
