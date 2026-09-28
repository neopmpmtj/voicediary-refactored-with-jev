import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q

from src.diary.models import UsageLog
from src.finance.errors import ExtractError, FinanceLookupError
from src.finance.extract import extract_from_text, parse_amount, parse_transaction_date
from src.finance.models import FinancialItem, FinancialRecord, RecordStatus

logger = logging.getLogger(__name__)


def _to_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    return value


def _log_extract_usage(user, entry, usage):
    if not usage:
        return
    UsageLog.objects.create(
        user=user,
        entry=entry,
        service="finance",
        usage_type="input_tokens",
        amount=Decimal(str(usage.get("input") or 0)),
    )
    UsageLog.objects.create(
        user=user,
        entry=entry,
        service="finance",
        usage_type="output_tokens",
        amount=Decimal(str(usage.get("output") or 0)),
    )


def _store_items(record, items):
    created = []
    for index, item in enumerate(items or []):
        created.append(
            FinancialItem.objects.create(
                financial_record=record,
                item_index=index,
                type=item.get("type") or "expense",
                amount=item["amount"],
                currency=item.get("currency") or "EUR",
                category=item.get("category") or "",
                merchant=item.get("merchant") or "",
                transaction_date=item.get("transaction_date"),
                description=item.get("description") or "",
                payment_method=item.get("payment_method") or "",
            )
        )
    return created


def _store_record(
    user,
    *,
    entry=None,
    record_name="",
    record_context="",
    status,
    error_message="",
    llm_response=None,
    items=None,
    external_id="",
):
    record = FinancialRecord.objects.create(
        user=user,
        entry=entry,
        record_name=record_name or "",
        record_context=record_context or "",
        status=status,
        error_message=error_message or "",
        llm_response=_to_json_safe(llm_response or {}),
        external_id=external_id or "",
    )
    if status == RecordStatus.SUCCESS:
        _store_items(record, items)
    return record


def item_payload(row):
    return {
        "id": str(row.id),
        "type": row.type,
        "amount": str(row.amount),
        "currency": row.currency,
        "category": row.category,
        "merchant": row.merchant,
        "transaction_date": row.transaction_date.isoformat() if row.transaction_date else "",
        "description": row.description,
        "payment_method": row.payment_method,
    }


def record_payload_item(row):
    return {
        "id": str(row.id),
        "record_name": row.record_name,
        "record_context": row.record_context,
        "status": row.status,
        "error_message": row.error_message,
        "items": [item_payload(item) for item in row.items.all()],
    }


def records_for_entry(entry):
    return [record_payload_item(row) for row in entry.finance_records.all()]


def record_list_item(row):
    item = record_payload_item(row)
    item.update(
        {
            "entry_id": str(row.entry_id) if row.entry_id else "",
            "external_id": row.external_id,
            "created_at": row.created_at.isoformat(),
        }
    )
    return item


def extract_financial_items(user, entry):
    if entry.route != "finance":
        return None
    usage = {}
    try:
        record_name, record_context, items, error, usage = extract_from_text(entry.content_text)
    except ExtractError as exc:
        logger.error("Finance extraction failed for %s: %s", entry.id, exc)
        return _store_record(
            user,
            entry=entry,
            status=RecordStatus.FAILED,
            error_message=str(exc),
        )
    finally:
        _log_extract_usage(user, entry, usage)
    if not items:
        return _store_record(
            user,
            entry=entry,
            status=RecordStatus.FAILED,
            error_message=error or "No financial items extracted",
        )
    return _store_record(
        user,
        entry=entry,
        record_name=record_name or "",
        record_context=record_context or "",
        status=RecordStatus.SUCCESS,
        llm_response={
            "record_name": record_name,
            "record_context": record_context,
            "items": items,
        },
        items=items,
    )


def _payable_total(parsed):
    summary = parsed.get("summary") or {}
    for value in (
        parsed.get("total_amount"),
        summary.get("total_to_pay"),
        parsed.get("amount_paid"),
        (parsed.get("payments") or {}).get("total_paid"),
        summary.get("total"),
    ):
        amount = parse_amount(value)
        if amount is not None:
            return amount
    return None


def persist_parsed_invoice(user, parsed, source):
    """Write one finance record from a parsed invoice. PDF and image parsers call this."""
    if not parsed or parsed.get("error"):
        return None
    source = source or {}
    message_id = source.get("message_id") or ""
    filename = source.get("filename") or ""
    if message_id:
        existing = FinancialRecord.objects.filter(
            user=user,
            external_id=message_id,
            is_deleted=False,
            status=RecordStatus.SUCCESS,
        ).first()
        if existing:
            return existing
    vendor_name = (parsed.get("vendor_name") or "Unknown")[:255]
    currency = (parsed.get("currency") or "EUR").strip().upper()[:10] or "EUR"
    invoice_date = parse_transaction_date(parsed.get("invoice_date"))
    invoice_number = parsed.get("invoice_number") or ""
    amount = _payable_total(parsed)
    if amount is None:
        return _store_record(
            user,
            status=RecordStatus.FAILED,
            record_name=vendor_name,
            error_message="No payable total on invoice",
            llm_response=parsed,
        )
    context_parts = []
    if invoice_number:
        context_parts.append(f"Invoice {invoice_number}")
    if invoice_date:
        context_parts.append(f"dated {invoice_date.isoformat()}")
    if filename:
        context_parts.append(filename)
    item = {
        "type": "expense",
        "amount": amount,
        "currency": currency,
        "category": "",
        "merchant": vendor_name,
        "transaction_date": invoice_date,
        "description": invoice_number or filename,
        "payment_method": "",
    }
    return _store_record(
        user,
        record_name=vendor_name,
        record_context=" ".join(context_parts),
        status=RecordStatus.SUCCESS,
        llm_response=parsed,
        items=[item],
        external_id=message_id,
    )


def user_by_email(email):
    User = get_user_model()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise FinanceLookupError("Unknown user.") from exc


def records_for_email(email, *, entry_id=None):
    user = user_by_email(email)
    rows = FinancialRecord.objects.filter(user=user, is_deleted=False).filter(
        Q(entry__isnull=True) | Q(entry__is_deleted=False)
    )
    if entry_id:
        try:
            key = uuid.UUID(str(entry_id))
        except (TypeError, ValueError) as exc:
            raise FinanceLookupError("Unknown entry.") from exc
        rows = rows.filter(entry_id=key)
    rows = rows.prefetch_related("items").order_by("-created_at")
    return [record_list_item(row) for row in rows]
