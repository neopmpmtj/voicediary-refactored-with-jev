import pytest

from src.diary.services import derive_route, select_prior_entries

pytestmark = pytest.mark.unit


class _Entry:
    def __init__(self, item_type, duration):
        self.item_type = item_type
        self.recording_duration_seconds = duration


def test_prior_context_waits_until_two_entries_exist():
    entries = [_Entry("audio", 30)]
    assert select_prior_entries(entries, count=2, max_seconds=240) == []


def test_prior_context_skips_recordings_at_least_as_long_as_the_cap():
    newest_first = [
        _Entry("audio", 240),
        _Entry("text", None),
        _Entry("audio", 30),
    ]
    chosen = select_prior_entries(newest_first, count=2, max_seconds=240)
    assert [item.recording_duration_seconds for item in chosen] == [30, None]


def test_prior_context_uses_the_configured_count():
    newest_first = [
        _Entry("text", None),
        _Entry("text", None),
        _Entry("text", None),
    ]
    chosen = select_prior_entries(newest_first, count=2, max_seconds=240)
    assert len(chosen) == 2
    assert chosen[0] is newest_first[1]
    assert chosen[1] is newest_first[0]


def test_calendar_route_wins_for_follow_up_even_when_subject_is_diary():
    assert derive_route("follow-up", "diary") == "calendar"


def test_calendar_route_wins_for_an_appointment():
    assert derive_route("freeform", "appointment") == "calendar"


def test_calendar_route_wins_for_reschedule():
    assert derive_route("reschedule", "finance") == "calendar"


def test_other_subjects_keep_their_own_route():
    assert derive_route("freeform", "diary") == "diary"
    assert derive_route("list", "finance") == "finance"
    assert derive_route("todo", "diary") == "diary"
