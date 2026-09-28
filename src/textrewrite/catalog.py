import json
from pathlib import Path

from src.textrewrite.errors import RewriteError

CATALOG_PATH = Path(__file__).resolve().parent / "openai_models.json"
RESPONSES_KIND = "responses"


def load_models():
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return payload.get("models") or []


def select_model(model_id=None):
    models = load_models()
    if model_id:
        match = next((item for item in models if item.get("model_id") == model_id), None)
        if match is None:
            raise RewriteError(f"Unknown model {model_id}")
        if match.get("endpoint_kind") != RESPONSES_KIND:
            raise RewriteError(f"Model {model_id} is not a Responses model")
        return match
    defaults = [item for item in models if item.get("is_default")]
    if len(defaults) != 1:
        raise RewriteError("Catalog must have exactly one default model")
    chosen = defaults[0]
    if chosen.get("endpoint_kind") != RESPONSES_KIND:
        raise RewriteError(f"Model {chosen.get('model_id')} is not a Responses model")
    return chosen
