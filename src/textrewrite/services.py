from src.textrewrite.catalog import select_model
from src.textrewrite.config import load_prompt
from src.textrewrite.errors import RewriteError
from src.textrewrite.models import RewriteUsage
from src.textrewrite.responses import create_rewrite


def rewrite_text(text, model_id=None):
    source = (text or "").strip()
    if not source:
        raise RewriteError("Missing text")
    model = select_model(model_id)
    result = create_rewrite(model["model_id"], load_prompt(), source)
    RewriteUsage.objects.create(
        model_id=model["model_id"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
    )
    return {
        "text": result["text"],
        "model_id": model["model_id"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }
