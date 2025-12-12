from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from pendulum import DateTime

    from oaps.session import Session


class TestSessionGet:
    def test_get_returns_value_when_exists(self, session: Session) -> None:
        session.store.set("key", "value")

        result = session.get("key")

        assert result == "value"

    def test_get_returns_none_when_missing(self, session: Session) -> None:
        result = session.get("nonexistent")

        assert result is None

    def test_get_returns_int_value(self, session: Session) -> None:
        session.store.set("count", 42)

        result = session.get("count")

        assert result == 42

    def test_get_returns_none_value_when_stored(self, session: Session) -> None:
        session.store.set("null_key", None)

        result = session.get("null_key")

        assert result is None


class TestSessionSet:
    def test_set_stores_value(self, session: Session) -> None:
        session.set("key", "value")

        assert session.store["key"] == "value"

    def test_set_uses_oaps_hooks_author(self, session: Session) -> None:
        session.set("key", "value")

        entry = session.store.get_entry("key")
        assert entry is not None
        assert entry.created_by == "oaps.hooks"
        assert entry.updated_by == "oaps.hooks"

    def test_set_stores_int_value(self, session: Session) -> None:
        session.set("count", 100)

        assert session.store["count"] == 100

    def test_set_overwrites_existing(self, session: Session) -> None:
        session.set("key", "original")
        session.set("key", "updated")

        assert session.store["key"] == "updated"


class TestSessionIncrement:
    def test_increment_initializes_to_amount_when_key_missing(
        self, session: Session
    ) -> None:
        result = session.increment("counter")

        assert result == 1
        assert session.store["counter"] == 1

    def test_increment_adds_to_existing_int(self, session: Session) -> None:
        session.set("counter", 5)

        result = session.increment("counter")

        assert result == 6
        assert session.store["counter"] == 6

    def test_increment_with_custom_amount(self, session: Session) -> None:
        session.set("counter", 10)

        result = session.increment("counter", amount=5)

        assert result == 15

    def test_increment_handles_float_value(self, session: Session) -> None:
        session.store.set("counter", 3.7)

        result = session.increment("counter")

        assert result == 4  # int(3.7) + 1

    def test_increment_handles_str_numeric_value(self, session: Session) -> None:
        session.store.set("counter", "42")

        result = session.increment("counter")

        # Strings are not numeric per SQLite typeof(), so treated as 0
        assert result == 1

    def test_increment_handles_str_non_numeric_value(self, session: Session) -> None:
        session.store.set("counter", "not a number")

        result = session.increment("counter")

        assert result == 1  # Treats as 0

    def test_increment_handles_bytes_value(self, session: Session) -> None:
        session.store.set("counter", b"\x00\x01")

        result = session.increment("counter")

        assert result == 1  # Treats as 0

    def test_increment_handles_none_value(self, session: Session) -> None:
        session.store.set("counter", None)

        result = session.increment("counter")

        assert result == 1  # Treats as 0


class TestSessionSetIfAbsent:
    def test_set_if_absent_sets_when_key_missing(self, session: Session) -> None:
        result = session.set_if_absent("key", "value")

        assert result is True
        assert session.store["key"] == "value"

    def test_set_if_absent_returns_false_when_key_exists(
        self, session: Session
    ) -> None:
        session.set("key", "original")

        result = session.set_if_absent("key", "new value")

        assert result is False
        assert session.store["key"] == "original"

    def test_set_if_absent_uses_oaps_hooks_author(self, session: Session) -> None:
        session.set_if_absent("key", "value")

        entry = session.store.get_entry("key")
        assert entry is not None
        assert entry.created_by == "oaps.hooks"


class TestSessionSetTimestamp:
    def test_set_timestamp_stores_iso8601_string(
        self,
        session: Session,
        freeze_time: Callable[[int, int, int, int, int, int], DateTime],
    ) -> None:
        freeze_time(2025, 12, 16, 10, 30, 0)

        result = session.set_timestamp("timestamp_key")

        # Accept both +00:00 and Z suffix for UTC timezone
        assert result in ("2025-12-16T10:30:00+00:00", "2025-12-16T10:30:00Z")
        assert session.store["timestamp_key"] == result

    def test_set_timestamp_returns_timestamp(
        self,
        session: Session,
        freeze_time: Callable[[int, int, int, int, int, int], DateTime],
    ) -> None:
        freeze_time(2025, 1, 1, 0, 0, 0)

        result = session.set_timestamp("key")

        # Accept both +00:00 and Z suffix for UTC timezone
        assert result in ("2025-01-01T00:00:00+00:00", "2025-01-01T00:00:00Z")

    def test_set_timestamp_overwrites_existing(
        self,
        session: Session,
        freeze_time: Callable[[int, int, int, int, int, int], DateTime],
    ) -> None:
        session.set("key", "old_value")
        freeze_time(2025, 6, 15, 12, 0, 0)

        session.set_timestamp("key")

        # Accept both +00:00 and Z suffix for UTC timezone
        assert session.store["key"] in (
            "2025-06-15T12:00:00+00:00",
            "2025-06-15T12:00:00Z",
        )


class TestSessionSetTimestampIfAbsent:
    def test_set_timestamp_if_absent_sets_when_missing(
        self,
        session: Session,
        freeze_time: Callable[[int, int, int, int, int, int], DateTime],
    ) -> None:
        freeze_time(2025, 12, 16, 10, 30, 0)

        result = session.set_timestamp_if_absent("timestamp_key")

        # Accept both +00:00 and Z suffix for UTC timezone
        assert result in ("2025-12-16T10:30:00+00:00", "2025-12-16T10:30:00Z")
        assert session.store["timestamp_key"] == result

    def test_set_timestamp_if_absent_returns_none_when_exists(
        self, session: Session
    ) -> None:
        session.set("key", "existing_value")

        result = session.set_timestamp_if_absent("key")

        assert result is None
        assert session.store["key"] == "existing_value"

    def test_set_timestamp_if_absent_does_not_overwrite(
        self,
        session: Session,
        freeze_time: Callable[[int, int, int, int, int, int], DateTime],
    ) -> None:
        session.set("key", "original_timestamp")
        freeze_time(2025, 6, 15, 12, 0, 0)

        session.set_timestamp_if_absent("key")

        assert session.store["key"] == "original_timestamp"
