from decimal import Decimal

import pytest

from src.finance.models import FinancialRecord
from src.finance.services import persist_parsed_invoice

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _parsed(**kwargs):
    payload = {
        "vendor_name": "Pingo Doce",
        "invoice_number": "FT 1",
        "invoice_date": "2026-09-17",
        "currency": "EUR",
        "total_amount": 24.08,
        "line_items": [
            {"description": "pão", "quantity": 5, "unit_price": 0.17, "total": 0.85},
            {"description": "leite", "quantity": 1, "unit_price": 1.29, "total": 1.29},
        ],
        "summary": {"total": 28.98, "total_to_pay": 24.08},
    }
    payload.update(kwargs)
    return payload


def test_persist_uses_vendor_and_payable_total(user):
    record = persist_parsed_invoice(
        user,
        _parsed(),
        {"message_id": "msg-1", "filename": "invoice.pdf"},
    )
    assert record.status == "success"
    assert record.record_name == "Pingo Doce"
    assert record.entry_id is None
    assert record.external_id == "msg-1"
    assert record.llm_response["line_items"][0]["description"] == "pão"
    item = record.items.get()
    assert item.amount == Decimal("24.08")
    assert item.merchant == "Pingo Doce"
    assert item.type == "expense"


def test_persist_skips_error_payload(user):
    assert persist_parsed_invoice(user, {"error": "No invoice data found"}, {}) is None
    assert FinancialRecord.objects.count() == 0


def test_persist_does_not_insert_the_same_gmail_message_twice(user):
    first = persist_parsed_invoice(user, _parsed(), {"message_id": "msg-1", "filename": "a.pdf"})
    second = persist_parsed_invoice(user, _parsed(), {"message_id": "msg-1", "filename": "b.pdf"})
    assert first.id == second.id
    assert FinancialRecord.objects.filter(user=user).count() == 1
