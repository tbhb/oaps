"""Tests for HistoryManager operations."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.exceptions import SpecNotFoundError
from oaps.spec import HistoryEntry, HistoryManager, SpecManager, SpecType


@pytest.fixture
def spec_manager(tmp_path: Path) -> SpecManager:
    """Create an initialized SpecManager with a test spec."""
    manager = SpecManager(tmp_path)
    # Create a test spec
    manager.create_spec(
        slug="test-spec",
        title="Test Specification",
        spec_type=SpecType.FEATURE,
        actor="test-user",
    )
    return manager


@pytest.fixture
def history_manager(spec_manager: SpecManager) -> HistoryManager:
    """Create a HistoryManager with the test SpecManager."""
    return HistoryManager(spec_manager)


class TestHistoryManagerInit:
    def test_accepts_spec_manager(self, spec_manager: SpecManager) -> None:
        manager = HistoryManager(spec_manager)
        assert manager._spec_manager is spec_manager


class TestHistoryPath:
    def test_returns_path_to_history_file(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        # Get spec to find ID
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        path = history_manager._history_path(spec_id)

        assert path.name == "history.jsonl"
        assert spec_id in str(path.parent)

    def test_raises_for_nonexistent_spec(self, history_manager: HistoryManager) -> None:
        with pytest.raises(SpecNotFoundError):
            history_manager._history_path("SPEC-9999")


class TestRecordEvent:
    def test_creates_history_entry(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        entry = history_manager.record_event(
            spec_id=spec_id,
            event="spec_created",
            actor="test-user",
        )

        assert entry.event == "spec_created"
        assert entry.actor == "test-user"
        assert entry.timestamp is not None

    def test_includes_optional_details(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        entry = history_manager.record_event(
            spec_id=spec_id,
            event="requirement_added",
            actor="developer",
            id="REQ-0001",
            target="test-spec",
            from_value="draft",
            to_value="approved",
            result="pass",
            reason="Initial requirement",
            command="spec req add",
        )

        assert entry.id == "REQ-0001"
        assert entry.target == "test-spec"
        assert entry.from_value == "draft"
        assert entry.to_value == "approved"
        assert entry.result is not None
        assert entry.result.value == "pass"
        assert entry.reason == "Initial requirement"
        assert entry.command == "spec req add"

    def test_appends_to_history_file(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "event_1", "user1")
        history_manager.record_event(spec_id, "event_2", "user2")

        history_path = history_manager._history_path(spec_id)
        content = history_path.read_text()
        lines = [line for line in content.strip().split("\n") if line]

        assert len(lines) == 2

    def test_raises_for_nonexistent_spec(self, history_manager: HistoryManager) -> None:
        with pytest.raises(SpecNotFoundError):
            history_manager.record_event(
                spec_id="SPEC-9999",
                event="test_event",
                actor="test-user",
            )


class TestGet:
    def test_returns_empty_list_for_missing_history(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        entries = history_manager.get(spec_id)

        assert entries == []

    def test_returns_history_entries(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "event_1", "user1")
        history_manager.record_event(spec_id, "event_2", "user2")

        entries = history_manager.get(spec_id)

        assert len(entries) == 2

    def test_sorts_newest_first(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "first_event", "user1")
        history_manager.record_event(spec_id, "second_event", "user2")

        entries = history_manager.get(spec_id)

        # Second event should be first (newest)
        assert entries[0].event == "second_event"
        assert entries[1].event == "first_event"

    def test_respects_limit(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        for i in range(10):
            history_manager.record_event(spec_id, f"event_{i}", "user")

        entries = history_manager.get(spec_id, limit=5)

        assert len(entries) == 5

    def test_default_limit_is_50(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        for i in range(60):
            history_manager.record_event(spec_id, f"event_{i}", "user")

        entries = history_manager.get(spec_id)

        assert len(entries) == 50

    def test_raises_for_limit_less_than_one(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        with pytest.raises(ValueError, match="limit must be >= 1"):
            history_manager.get(spec_id, limit=0)

        with pytest.raises(ValueError, match="limit must be >= 1"):
            history_manager.get(spec_id, limit=-1)

    def test_raises_for_nonexistent_spec(self, history_manager: HistoryManager) -> None:
        with pytest.raises(SpecNotFoundError):
            history_manager.get("SPEC-9999")


class TestGetWithSinceFilter:
    def test_filters_entries_since_timestamp(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        # Record events
        history_manager.record_event(spec_id, "old_event", "user")
        cutoff = datetime.now(UTC)
        history_manager.record_event(spec_id, "new_event", "user")

        entries = history_manager.get(spec_id, since=cutoff)

        # Should only get the new event (timestamp >= cutoff)
        assert len(entries) >= 1
        assert all(e.timestamp >= cutoff for e in entries)


class TestGetWithUntilFilter:
    def test_filters_entries_until_timestamp(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        # Record events
        history_manager.record_event(spec_id, "old_event", "user")
        cutoff = datetime.now(UTC)
        history_manager.record_event(spec_id, "new_event", "user")

        entries = history_manager.get(spec_id, until=cutoff)

        # Should only get the old event (timestamp <= cutoff)
        assert len(entries) >= 1
        assert all(e.timestamp <= cutoff for e in entries)


class TestGetWithEventFilter:
    def test_filters_by_event_substring(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "spec_created", "user")
        history_manager.record_event(spec_id, "requirement_added", "user")
        history_manager.record_event(spec_id, "requirement_updated", "user")
        history_manager.record_event(spec_id, "test_added", "user")

        entries = history_manager.get(spec_id, event_filter="requirement")

        assert len(entries) == 2
        assert all("requirement" in e.event for e in entries)

    def test_event_filter_is_substring_match(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "requirement_added", "user")
        history_manager.record_event(spec_id, "test_requirement_verified", "user")

        entries = history_manager.get(spec_id, event_filter="req")

        # Both contain "req"
        assert len(entries) == 2


class TestGetWithActorFilter:
    def test_filters_by_exact_actor(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "event_1", "alice")
        history_manager.record_event(spec_id, "event_2", "bob")
        history_manager.record_event(spec_id, "event_3", "alice")

        entries = history_manager.get(spec_id, actor_filter="alice")

        assert len(entries) == 2
        assert all(e.actor == "alice" for e in entries)

    def test_actor_filter_is_exact_match(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "event_1", "alice")
        history_manager.record_event(spec_id, "event_2", "alice-bot")

        entries = history_manager.get(spec_id, actor_filter="alice")

        # Only exact match
        assert len(entries) == 1
        assert entries[0].actor == "alice"


class TestGetWithCombinedFilters:
    def test_combines_all_filters(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        # Record various events
        history_manager.record_event(spec_id, "spec_created", "alice")
        history_manager.record_event(spec_id, "requirement_added", "bob")
        history_manager.record_event(spec_id, "requirement_updated", "alice")
        history_manager.record_event(spec_id, "test_added", "alice")

        entries = history_manager.get(
            spec_id,
            event_filter="requirement",
            actor_filter="alice",
        )

        # Only requirement_updated by alice
        assert len(entries) == 1
        assert entries[0].event == "requirement_updated"
        assert entries[0].actor == "alice"


class TestParseEntry:
    def test_parses_minimal_entry(self, history_manager: HistoryManager) -> None:
        raw = {
            "timestamp": "2024-01-15T10:30:00+00:00",
            "event": "test_event",
            "actor": "test_user",
        }

        entry = history_manager._parse_entry(raw)

        assert isinstance(entry, HistoryEntry)
        assert entry.event == "test_event"
        assert entry.actor == "test_user"
        assert entry.timestamp.year == 2024

    def test_parses_full_entry(self, history_manager: HistoryManager) -> None:
        raw = {
            "timestamp": "2024-01-15T10:30:00+00:00",
            "event": "test_run",
            "actor": "ci-bot",
            "command": "spec test run",
            "id": "TST-0001",
            "target": "test-spec",
            "from_value": "pending",
            "to_value": "passing",
            "result": "pass",
            "reason": "All checks passed",
        }

        entry = history_manager._parse_entry(raw)

        assert entry.command == "spec test run"
        assert entry.id == "TST-0001"
        assert entry.target == "test-spec"
        assert entry.from_value == "pending"
        assert entry.to_value == "passing"
        assert entry.result is not None
        assert entry.result.value == "pass"
        assert entry.reason == "All checks passed"

    def test_handles_datetime_object(self, history_manager: HistoryManager) -> None:
        timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        raw = {
            "timestamp": timestamp,
            "event": "test_event",
            "actor": "test_user",
        }

        entry = history_manager._parse_entry(raw)

        assert entry.timestamp == timestamp


class TestMatchesFilters:
    def test_matches_with_no_filters(self, history_manager: HistoryManager) -> None:
        entry = HistoryEntry(
            timestamp=datetime.now(UTC),
            event="test_event",
            actor="test_user",
        )

        result = history_manager._matches_filters(entry, None, None, None, None)

        assert result is True

    def test_filters_by_since(self, history_manager: HistoryManager) -> None:
        old_entry = HistoryEntry(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            event="old_event",
            actor="user",
        )
        new_entry = HistoryEntry(
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            event="new_event",
            actor="user",
        )
        cutoff = datetime(2024, 3, 1, tzinfo=UTC)

        assert (
            history_manager._matches_filters(old_entry, cutoff, None, None, None)
            is False
        )
        assert (
            history_manager._matches_filters(new_entry, cutoff, None, None, None)
            is True
        )

    def test_filters_by_until(self, history_manager: HistoryManager) -> None:
        old_entry = HistoryEntry(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            event="old_event",
            actor="user",
        )
        new_entry = HistoryEntry(
            timestamp=datetime(2024, 6, 1, tzinfo=UTC),
            event="new_event",
            actor="user",
        )
        cutoff = datetime(2024, 3, 1, tzinfo=UTC)

        assert (
            history_manager._matches_filters(old_entry, None, cutoff, None, None)
            is True
        )
        assert (
            history_manager._matches_filters(new_entry, None, cutoff, None, None)
            is False
        )

    def test_filters_by_event_substring(self, history_manager: HistoryManager) -> None:
        entry = HistoryEntry(
            timestamp=datetime.now(UTC),
            event="requirement_added",
            actor="user",
        )

        assert (
            history_manager._matches_filters(entry, None, None, "requirement", None)
            is True
        )
        assert (
            history_manager._matches_filters(entry, None, None, "test", None) is False
        )

    def test_filters_by_exact_actor(self, history_manager: HistoryManager) -> None:
        entry = HistoryEntry(
            timestamp=datetime.now(UTC),
            event="event",
            actor="alice",
        )

        assert (
            history_manager._matches_filters(entry, None, None, None, "alice") is True
        )
        assert history_manager._matches_filters(entry, None, None, None, "bob") is False
        assert (
            history_manager._matches_filters(entry, None, None, None, "alic") is False
        )


class TestEventTypes:
    def test_supports_spec_events(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        events = ["spec_created", "spec_updated", "spec_status_changed"]
        for event in events:
            entry = history_manager.record_event(spec_id, event, "user")
            assert entry.event == event

    def test_supports_requirement_events(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        events = ["requirement_added", "requirement_updated", "requirement_removed"]
        for event in events:
            entry = history_manager.record_event(spec_id, event, "user")
            assert entry.event == event

    def test_supports_test_events(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        events = ["test_added", "test_updated", "test_removed", "test_run"]
        for event in events:
            entry = history_manager.record_event(spec_id, event, "user")
            assert entry.event == event

    def test_supports_artifact_events(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        events = ["artifact_added", "artifact_updated", "artifact_removed"]
        for event in events:
            entry = history_manager.record_event(spec_id, event, "user")
            assert entry.event == event

    def test_supports_link_events(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        events = ["link_added", "link_removed"]
        for event in events:
            entry = history_manager.record_event(spec_id, event, "user")
            assert entry.event == event


class TestTimestampValidation:
    def test_raises_for_naive_timestamp(self, history_manager: HistoryManager) -> None:
        raw = {
            "timestamp": "2024-01-15T10:30:00",  # Missing timezone
            "event": "test_event",
            "actor": "test_user",
        }

        with pytest.raises(ValueError, match="Timestamp must include timezone"):
            history_manager._parse_entry(raw)

    def test_accepts_timezone_aware_timestamp(
        self, history_manager: HistoryManager
    ) -> None:
        raw = {
            "timestamp": "2024-01-15T10:30:00+00:00",  # With timezone
            "event": "test_event",
            "actor": "test_user",
        }

        entry = history_manager._parse_entry(raw)

        assert entry.timestamp.tzinfo is not None


class TestISO8601Compliance:
    def test_writes_iso8601_with_timezone(
        self, history_manager: HistoryManager, spec_manager: SpecManager
    ) -> None:
        import re

        specs = spec_manager.list_specs()
        spec_id = specs[0].id

        history_manager.record_event(spec_id, "test_event", "user")

        # Read raw file content
        history_path = history_manager._history_path(spec_id)
        content = history_path.read_text()

        # Verify ISO 8601 format with timezone (UTC offset or Z)
        iso8601_pattern = (
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)"
        )
        assert re.search(iso8601_pattern, content), (
            f"No ISO 8601 timestamp found in: {content}"
        )
