import logging
from decimal import Decimal

from django.contrib.auth import get_user_model

from src.accounts.google import GoogleAuthError
from src.diary.models import UsageLog
from src.finance.models import RecordStatus
from src.finance.services import persist_parsed_invoice
from src.invoiceparser.errors import InvoiceError, InvoiceLookupError
from src.invoiceparser.gmail import (
    add_label_to_message,
    get_or_create_label,
    get_pdf_attachments,
    search_inbox_messages,
    user_has_gmail,
)
from src.invoiceparser.parse import parse_pdf_invoice
from src.invoiceparser.prompt import PROCESSED_LABEL_NAME, invoice_search_query

logger = logging.getLogger(__name__)


def _log_parse_usage(user, usage):
    if not usage:
        return
    UsageLog.objects.create(
        user=user,
        entry=None,
        service="invoiceparser",
        usage_type="input_tokens",
        amount=Decimal(str(usage.get("input_tokens") or 0)),
    )
    UsageLog.objects.create(
        user=user,
        entry=None,
        service="invoiceparser",
        usage_type="output_tokens",
        amount=Decimal(str(usage.get("output_tokens") or 0)),
    )


def user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise InvoiceLookupError("Unknown user.") from exc


def process_invoice_messages(user):
    results = []
    errors = []
    if not user_has_gmail(user):
        return {
            "results": [],
            "errors": ["Gmail is not connected."],
            "summary": {
                "messages_found": 0,
                "pdfs_parsed": 0,
                "records_created": 0,
                "records_skipped": 0,
            },
        }
    try:
        label_id = get_or_create_label(user, PROCESSED_LABEL_NAME)
    except (GoogleAuthError, InvoiceError) as exc:
        logger.warning("Could not get or create processed label: %s", exc)
        return {
            "results": [],
            "errors": [f"Label setup failed: {exc}"],
            "summary": {
                "messages_found": 0,
                "pdfs_parsed": 0,
                "records_created": 0,
                "records_skipped": 0,
            },
        }
    query = invoice_search_query()
    try:
        message_ids = search_inbox_messages(user, query, max_results=20)
    except (GoogleAuthError, InvoiceError) as exc:
        logger.error("Gmail search failed: %s", exc)
        return {
            "results": [],
            "errors": [f"Gmail search failed: {exc}"],
            "summary": {
                "messages_found": 0,
                "pdfs_parsed": 0,
                "records_created": 0,
                "records_skipped": 0,
            },
        }
    pdfs_parsed = 0
    records_created = 0
    records_skipped = 0
    for message_id in message_ids:
        try:
            attachments = get_pdf_attachments(user, message_id)
        except (GoogleAuthError, InvoiceError) as exc:
            errors.append(f"Error processing message {message_id}: {exc}")
            continue
        if not attachments:
            continue
        labeled = False
        for attachment in attachments:
            filename = attachment.get("filename") or "invoice.pdf"
            try:
                result = parse_pdf_invoice(attachment["data"], filename)
            except InvoiceError as exc:
                errors.append(f"Parse failed for {filename} (msg {message_id}): {exc}")
                continue
            parsed = result["parsed"]
            usage = result["usage"]
            _log_parse_usage(user, usage)
            pdfs_parsed += 1
            record = None
            if not parsed.get("error"):
                record = persist_parsed_invoice(
                    user,
                    parsed,
                    {"message_id": message_id, "filename": filename},
                )
            results.append(
                {
                    "message_id": message_id,
                    "filename": filename,
                    "parsed": parsed,
                    "usage": usage,
                    "record_id": str(record.id) if record else "",
                    "status": record.status if record else "",
                }
            )
            if record and record.status == RecordStatus.SUCCESS:
                records_created += 1
                if not labeled:
                    try:
                        add_label_to_message(user, message_id, label_id)
                        labeled = True
                    except (GoogleAuthError, InvoiceError) as exc:
                        logger.warning(
                            "Could not add processed label to message %s: %s",
                            message_id,
                            exc,
                        )
            else:
                records_skipped += 1
    return {
        "results": results,
        "errors": errors,
        "summary": {
            "messages_found": len(message_ids),
            "pdfs_parsed": pdfs_parsed,
            "records_created": records_created,
            "records_skipped": records_skipped,
        },
    }


def process_invoices_for_email(email):
    return process_invoice_messages(user_by_email(email))
