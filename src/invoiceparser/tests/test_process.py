from decimal import Decimal

import pytest

from src.diary.models import UsageLog
from src.finance.models import FinancialRecord
from src.invoiceparser.services import process_invoice_messages

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _parsed():
    return {
        "vendor_name": "Pingo Doce",
        "invoice_number": "FT 1",
        "invoice_date": "2026-09-17",
        "currency": "EUR",
        "total_amount": 12.5,
        "line_items": [{"description": "pão", "total": 12.5}],
        "summary": {"total_to_pay": 12.5},
    }


def test_process_persists_pdf_and_labels_message(user, monkeypatch):
    labeled = []
    monkeypatch.setattr("src.invoiceparser.services.user_has_gmail", lambda u: True)
    monkeypatch.setattr(
        "src.invoiceparser.services.get_or_create_label",
        lambda u, name: "label-1",
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.search_inbox_messages",
        lambda u, query, max_results=20: ["msg-1"],
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.get_pdf_attachments",
        lambda u, message_id: [{"filename": "invoice.pdf", "data": b"%PDF-1.4"}],
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.parse_pdf_invoice",
        lambda data, filename: {
            "parsed": _parsed(),
            "usage": {"input_tokens": 5, "output_tokens": 3, "total_tokens": 8},
            "model": "gpt-4o",
        },
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.add_label_to_message",
        lambda u, message_id, label_id: labeled.append((message_id, label_id)),
    )
    payload = process_invoice_messages(user)
    assert payload["summary"]["messages_found"] == 1
    assert payload["summary"]["pdfs_parsed"] == 1
    assert payload["summary"]["records_created"] == 1
    record = FinancialRecord.objects.get(external_id="msg-1")
    assert record.record_name == "Pingo Doce"
    assert record.items.get().amount == Decimal("12.50")
    assert labeled == [("msg-1", "label-1")]
    usage = UsageLog.objects.filter(user=user, service="invoiceparser")
    assert {row.usage_type for row in usage} == {"input_tokens", "output_tokens"}


def test_process_skips_when_gmail_is_missing(user, monkeypatch):
    monkeypatch.setattr("src.invoiceparser.services.user_has_gmail", lambda u: False)
    payload = process_invoice_messages(user)
    assert payload["errors"] == ["Gmail is not connected."]
    assert payload["summary"]["messages_found"] == 0
    assert FinancialRecord.objects.count() == 0


def test_parse_error_does_not_label(user, monkeypatch):
    labeled = []
    monkeypatch.setattr("src.invoiceparser.services.user_has_gmail", lambda u: True)
    monkeypatch.setattr(
        "src.invoiceparser.services.get_or_create_label",
        lambda u, name: "label-1",
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.search_inbox_messages",
        lambda u, query, max_results=20: ["msg-1"],
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.get_pdf_attachments",
        lambda u, message_id: [{"filename": "invoice.pdf", "data": b"%PDF-1.4"}],
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.parse_pdf_invoice",
        lambda data, filename: {
            "parsed": {"error": "No invoice data found"},
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            "model": "gpt-4o",
        },
    )
    monkeypatch.setattr(
        "src.invoiceparser.services.add_label_to_message",
        lambda u, message_id, label_id: labeled.append(message_id),
    )
    payload = process_invoice_messages(user)
    assert labeled == []
    assert FinancialRecord.objects.count() == 0
    assert payload["summary"]["records_skipped"] == 1
