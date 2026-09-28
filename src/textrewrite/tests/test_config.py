import pytest

from src.textrewrite.config import load_prompt

pytestmark = [pytest.mark.unit]


def test_load_prompt_is_non_empty():
    text = load_prompt()
    assert text
