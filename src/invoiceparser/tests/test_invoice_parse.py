import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(email="ada@example.com", password="pass")


def test_invoice_parse_json_and_human_output(user, monkeypatch):
    payload = {
        "results": [
            {
                "message_id": "msg-1",
                "filename": "invoice.pdf",
                "parsed": {"vendor_name": "Pingo Doce"},
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                "record_id": "rec-1",
                "status": "success",
            }
        ],
        "errors": [],
        "summary": {
            "messages_found": 1,
            "pdfs_parsed": 1,
            "records_created": 1,
            "records_skipped": 0,
        },
    }
    monkeypatch.setattr(
        "src.invoiceparser.services.process_invoice_messages",
        lambda u: payload,
    )
    json_out = StringIO()
    call_command("invoice_parse", "--email", user.email, "--json", stdout=json_out)
    assert json.loads(json_out.getvalue()) == payload
    plain = StringIO()
    call_command("invoice_parse", "--email", user.email, stdout=plain)
    line = plain.getvalue()
    assert "messages=1" in line
    assert "pdfs=1" in line
    assert "created=1" in line


def test_invoice_parse_unknown_user():
    with pytest.raises(CommandError, match="Unknown user"):
        call_command("invoice_parse", "--email", "missing@example.com")
