from pathlib import Path

from src.conferencerewrite.errors import RewriteError

PROMPT_PATH = Path(__file__).resolve().parent / "conference_rewrite_prompt.txt"


def load_prompt():
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise RewriteError("Rewrite prompt is empty")
    return text
