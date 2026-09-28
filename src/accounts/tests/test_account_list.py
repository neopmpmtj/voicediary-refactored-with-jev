import json
from io import StringIO

import pytest
from django.core.management import call_command

from src.accounts.models import UserSecret

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_account_list_json_email_and_google_flag_only(django_user_model):
    google = django_user_model.objects.create_user(email="ada@example.com", password="pass")
    google.is_google_account = True
    google.save(update_fields=["is_google_account"])
    django_user_model.objects.create_user(email="bob@example.com", password="pass")
    UserSecret.objects.create(user=google, encrypted_google_access_token="secret-token")
    out = StringIO()
    call_command("account_list", "--json", stdout=out)
    rows = json.loads(out.getvalue())
    assert rows == [
        {"email": "ada@example.com", "is_google_account": True},
        {"email": "bob@example.com", "is_google_account": False},
    ]
    dumped = out.getvalue()
    assert "secret-token" not in dumped
    assert "encrypted" not in dumped


def test_account_list_empty(django_user_model):
    out = StringIO()
    call_command("account_list", stdout=out)
    assert out.getvalue().strip() == "no accounts"
    json_out = StringIO()
    call_command("account_list", "--json", stdout=json_out)
    assert json.loads(json_out.getvalue()) == []
