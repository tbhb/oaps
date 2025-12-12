from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pendulum import DateTime

    from oaps.hooks._statistics import SessionStatistics


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if Path(item.path).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def session() -> Session:
    """Create a Session with MockStateStore for testing."""
    from oaps.session import Session
    from oaps.utils import MockStateStore

    store = MockStateStore()
    return Session(id="test-session", store=store)


FreezeTimeFunc = Callable[[int, int, int, int, int, int], "DateTime"]


@pytest.fixture
def freeze_time(monkeypatch: pytest.MonkeyPatch) -> FreezeTimeFunc:
    """Return a function to freeze pendulum.now() to a fixed time."""
    import pendulum

    def _freeze(
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> DateTime:
        fixed = pendulum.datetime(year, month, day, hour, minute, second, tz="UTC")

        def mock_now(tz: str) -> DateTime:
            return fixed if tz == "UTC" else pendulum.now(tz)

        monkeypatch.setattr("pendulum.now", mock_now)
        return fixed

    return _freeze


@pytest.fixture
def make_session_statistics() -> Callable[..., SessionStatistics]:
    """Return a factory function to create SessionStatistics with defaults."""
    from oaps.hooks._statistics import SessionStatistics

    def _make(**overrides: object) -> SessionStatistics:
        defaults: dict[str, object] = {
            "started_at": None,
            "ended_at": None,
            "source": None,
            "prompt_count": 0,
            "first_prompt_at": None,
            "last_prompt_at": None,
            "total_tool_count": 0,
            "last_tool": None,
            "last_tool_at": None,
            "tool_counts": {},
            "permission_request_count": 0,
            "last_permission_tool": None,
            "notification_count": 0,
            "notification_counts": {},
            "stop_count": 0,
            "compaction_count": 0,
            "subagent_spawn_count": 0,
            "subagent_stop_count": 0,
        }
        defaults.update(overrides)
        return SessionStatistics(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


# Re-export Session for type hints
from oaps.session import Session  # noqa: E402
