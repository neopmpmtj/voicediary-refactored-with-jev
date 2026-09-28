import pytest

from src.textrewrite.config import load_prompt, list_styles
from src.textrewrite.errors import RewriteError

pytestmark = [pytest.mark.unit]


def test_load_prompt_is_non_empty():
    text = load_prompt()
    assert text


def test_every_style_prompt_is_non_empty():
    for item in list_styles():
        assert load_prompt(item["id"])


def test_load_prompt_default_is_grammar():
    assert load_prompt() == load_prompt("grammar")


def test_unknown_style_raises():
    with pytest.raises(RewriteError, match="Unknown style"):
        load_prompt("bogus")


def test_list_styles_ids_and_labels():
    assert list_styles() == [
        {"id": "grammar", "label": "Grammar"},
        {"id": "professional", "label": "Professional"},
        {"id": "casual", "label": "Casual"},
        {"id": "llm-friendly", "label": "LLM-Friendly"},
        {"id": "story", "label": "Story"},
        {"id": "fairy-tale", "label": "Fairy Tale"},
    ]
