import pytest

from src.urls_others.parse import parse_references

pytestmark = [pytest.mark.unit]


def test_https_link_is_a_url_with_empty_note():
    matches, note = parse_references("https://example.com")
    assert matches == [("url", "https://example.com")]
    assert note == ""


def test_link_plus_instruction_keeps_leftover_as_note():
    matches, note = parse_references("watch later https://youtube.com/watch?v=abc")
    assert matches == [("url", "https://youtube.com/watch?v=abc")]
    assert note == "watch later"


def test_several_links_each_become_a_row():
    matches, note = parse_references("https://a.example/x and https://b.example/y")
    assert matches == [
        ("url", "https://a.example/x"),
        ("url", "https://b.example/y"),
    ]
    assert note == "and"


def test_trailing_punctuation_is_stripped():
    matches, note = parse_references("see https://example.com.")
    assert matches == [("url", "https://example.com")]
    assert note == "see"


def test_https_api_address_is_still_a_url():
    matches, note = parse_references("https://api.example.com/v1/users")
    assert matches == [("url", "https://api.example.com/v1/users")]
    assert note == ""


def test_get_path_is_an_endpoint():
    matches, note = parse_references("GET /v1/users")
    assert matches == [("endpoint", "GET /v1/users")]
    assert note == ""


def test_api_path_is_an_endpoint():
    matches, note = parse_references("/api/users")
    assert matches == [("endpoint", "/api/users")]
    assert note == ""


def test_method_path_is_one_endpoint_not_also_a_bare_path():
    matches, note = parse_references("try GET /api/users later")
    assert matches == [("endpoint", "GET /api/users")]
    assert note == "try later"


def test_plain_text_has_no_matches():
    matches, note = parse_references("just a diary note")
    assert matches == []
    assert note == "just a diary note"
