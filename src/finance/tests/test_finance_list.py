import json
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from src.diary.models import Entry, ItemType
from src.finance.models import FinancialItem, FinancialRecord

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def _record(user, entry=None, **kwargs):
    defaults = {
        "user": user,
        "entry": entry,
        "record_name": "Despesas",
        "record_context": "",
        "status": "success",
        "error_message": "",
        "llm_response": {},
        "external_id": "",
    }
    defaults.update(kwargs)
    record = FinancialRecord.objects.create(**defaults)
    FinancialItem.objects.create(
        financial_record=record,
        item_index=0,
        type="expense",
        amount=Decimal("20.00"),
        currency="EUR",
        description="café",
    )
    return record


def test_finance_list_json_and_human_output(user):
    entry = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="gastei")
    row = _record(user, entry)
    row.refresh_from_db()
    json_out = StringIO()
    call_command("finance_list", "--email", user.email, "--json", stdout=json_out)
    payload = json.loads(json_out.getvalue())
    assert payload == [
        {
            "id": str(row.id),
            "record_name": "Despesas",
            "record_context": "",
            "status": "success",
            "error_message": "",
            "items": [
                {
                    "id": str(row.items.get().id),
                    "type": "expense",
                    "amount": "20.00",
                    "currency": "EUR",
                    "category": "",
                    "merchant": "",
                    "transaction_date": "",
                    "description": "café",
                    "payment_method": "",
                }
            ],
            "entry_id": str(entry.id),
            "external_id": "",
            "created_at": row.created_at.isoformat(),
        }
    ]
    plain = StringIO()
    call_command("finance_list", "--email", user.email, stdout=plain)
    line = plain.getvalue()
    assert str(row.id) in line
    assert "success" in line
    assert "Despesas" in line
    assert "20.00" in line


def test_finance_list_empty_for_unknown_user(user):
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("finance_list", "--email", "missing@example.com")
    out = StringIO()
    call_command("finance_list", "--email", user.email, stdout=out)
    assert out.getvalue().strip() == "no records"


def test_finance_list_entry_filter(user):
    first = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="one")
    second = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="two")
    _record(user, first, record_name="A")
    kept = _record(user, second, record_name="B")
    out = StringIO()
    call_command("finance_list", "--email", user.email, "--entry", str(second.id), "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert len(payload) == 1
    assert payload[0]["id"] == str(kept.id)
    assert payload[0]["record_name"] == "B"


def test_finance_list_omits_rows_of_soft_deleted_entries(user):
    entry = Entry.objects.create(user=user, item_type=ItemType.TEXT, content_text="gastei")
    _record(user, entry)
    entry.is_deleted = True
    entry.deleted_at = timezone.now()
    entry.save(update_fields=["is_deleted", "deleted_at"])
    out = StringIO()
    call_command("finance_list", "--email", user.email, "--json", stdout=out)
    assert json.loads(out.getvalue()) == []


def test_finance_list_includes_invoice_records_without_an_entry(user):
    row = _record(user, None, record_name="Pingo Doce", external_id="msg-1")
    out = StringIO()
    call_command("finance_list", "--email", user.email, "--json", stdout=out)
    payload = json.loads(out.getvalue())
    assert len(payload) == 1
    assert payload[0]["id"] == str(row.id)
    assert payload[0]["entry_id"] == ""
    assert payload[0]["external_id"] == "msg-1"
