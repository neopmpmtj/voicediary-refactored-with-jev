from pathlib import Path

from src.textrewrite.errors import RewriteError

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
DEFAULT_STYLE = "grammar"
STYLES = (
    {"id": "grammar", "label": "Grammar"},
    {"id": "professional", "label": "Professional"},
    {"id": "casual", "label": "Casual"},
    {"id": "llm-friendly", "label": "LLM-Friendly"},
    {"id": "story", "label": "Story"},
    {"id": "fairy-tale", "label": "Fairy Tale"},
)
_STYLE_IDS = {item["id"] for item in STYLES}


def list_styles():
    return [dict(item) for item in STYLES]


def resolve_style(style=None):
    chosen = DEFAULT_STYLE if style is None else style
    if chosen not in _STYLE_IDS:
        raise RewriteError(f"Unknown style {style}")
    return chosen


def load_prompt(style=None):
    chosen = resolve_style(style)
    path = PROMPTS_DIR / f"{chosen}.txt"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RewriteError("Rewrite prompt is empty")
    return text
