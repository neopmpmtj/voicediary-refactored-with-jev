import json

import pytest

from src.textrewrite.catalog import select_model
from src.textrewrite.errors import RewriteError

pytestmark = [pytest.mark.unit]


def test_select_model_default_is_o3_mini():
    model = select_model()
    assert model["model_id"] == "o3-mini"
    assert model["endpoint_kind"] == "responses"


def test_select_model_named_responses_model():
    model = select_model("gpt-5.6-sol")
    assert model["model_id"] == "gpt-5.6-sol"


def test_select_model_unknown_raises():
    with pytest.raises(RewriteError, match="Unknown model"):
        select_model("not-a-model")


def test_select_model_rejects_chat_completions(tmp_path, monkeypatch):
    path = tmp_path / "openai_models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "model_id": "gpt-4o-mini",
                        "endpoint_kind": "chat_completions",
                        "is_default": False,
                    }
                ]
            }
        )
    )
    monkeypatch.setattr("src.textrewrite.catalog.CATALOG_PATH", path)
    with pytest.raises(RewriteError, match="not a Responses model"):
        select_model("gpt-4o-mini")


def test_select_model_zero_defaults_raises(tmp_path, monkeypatch):
    path = tmp_path / "openai_models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "model_id": "o3-mini",
                        "endpoint_kind": "responses",
                        "is_default": False,
                    }
                ]
            }
        )
    )
    monkeypatch.setattr("src.textrewrite.catalog.CATALOG_PATH", path)
    with pytest.raises(RewriteError, match="exactly one default"):
        select_model()


def test_select_model_many_defaults_raises(tmp_path, monkeypatch):
    path = tmp_path / "openai_models.json"
    path.write_text(
        json.dumps(
            {
                "models": [
                    {"model_id": "a", "endpoint_kind": "responses", "is_default": True},
                    {"model_id": "b", "endpoint_kind": "responses", "is_default": True},
                ]
            }
        )
    )
    monkeypatch.setattr("src.textrewrite.catalog.CATALOG_PATH", path)
    with pytest.raises(RewriteError, match="exactly one default"):
        select_model()
