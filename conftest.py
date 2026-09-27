import pytest


def pytest_collection_modifyitems(config, items):
    missing = []
    for item in items:
        if item.name.startswith("test_") and not (
            item.get_closest_marker("unit") or item.get_closest_marker("integration")
        ):
            missing.append(item.nodeid)
    if missing:
        raise pytest.UsageError(
            "Every test must be marked unit or integration. Missing: " + ", ".join(missing)
        )
