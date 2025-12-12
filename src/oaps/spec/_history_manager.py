# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""History manager for per-spec history log operations.

This module provides the HistoryManager class for querying and recording
events to per-spec history.jsonl files within specification directories.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

from oaps.spec._io import append_jsonl, read_jsonl
from oaps.spec._models import HistoryEntry, TestResult

if TYPE_CHECKING:
    from pathlib import Path

    from oaps.spec._spec_manager import SpecManager

__all__ = ["HistoryManager"]


class HistoryManager:
    """Manager for per-spec history log operations.

    The HistoryManager provides methods for querying and recording events
    to per-spec history.jsonl files. Each specification has its own history
    file located at `{spec_dir}/history.jsonl`.

    Attributes:
        _spec_manager: Reference to the SpecManager for spec validation.
    """

    __slots__: Final = ("_spec_manager",)

    _spec_manager: SpecManager

    def __init__(self, spec_manager: SpecManager) -> None:
        """Initialize the history manager.

        Args:
            spec_manager: Reference to the SpecManager for spec validation
                and path resolution.
        """
        self._spec_manager = spec_manager

    def _history_path(self, spec_id: str) -> Path:
        """Get the path to the per-spec history.jsonl file.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the history.jsonl file within the spec directory.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get spec metadata to validate existence and get slug
        metadata = self._spec_manager.get_spec(spec_id)
        spec_dir = self._spec_manager.base_path / f"{spec_id}-{metadata.slug}"
        return spec_dir / "history.jsonl"

    def _parse_entry(self, raw: dict[str, Any]) -> HistoryEntry:
        """Convert a raw dictionary to a HistoryEntry.

        Args:
            raw: Dictionary from JSONL file.

        Returns:
            HistoryEntry instance.

        Raises:
            ValueError: If timestamp is not timezone-aware.
        """
        timestamp = raw["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Ensure timestamp is timezone-aware to prevent comparison bugs
        if timestamp.tzinfo is None:
            msg = f"Timestamp must include timezone information: {timestamp}"
            raise ValueError(msg)

        # Parse result if present
        result_value = raw.get("result")
        result: TestResult | None = None
        if result_value is not None:
            result = TestResult(result_value)

        return HistoryEntry(
            timestamp=timestamp,
            event=raw["event"],
            actor=raw["actor"],
            command=raw.get("command"),
            id=raw.get("id"),
            target=raw.get("target"),
            from_value=raw.get("from_value"),
            to_value=raw.get("to_value"),
            result=result,
            reason=raw.get("reason"),
        )

    def _matches_filters(
        self,
        entry: HistoryEntry,
        since: datetime | None,
        until: datetime | None,
        event_filter: str | None,
        actor_filter: str | None,
    ) -> bool:
        """Check if an entry matches the specified filters.

        Args:
            entry: The history entry to check.
            since: Only include entries at or after this timestamp.
            until: Only include entries at or before this timestamp.
            event_filter: Only include entries with event containing this substring.
            actor_filter: Only include entries with this exact actor.

        Returns:
            True if the entry matches all specified filters.
        """
        # Check since filter (>=)
        if since is not None and entry.timestamp < since:
            return False

        # Check until filter (<=)
        if until is not None and entry.timestamp > until:
            return False

        # Check event filter (substring match)
        if event_filter is not None and event_filter not in entry.event:
            return False

        # Check actor filter (exact match)
        return not (actor_filter is not None and entry.actor != actor_filter)

    def get(  # noqa: PLR0913
        self,
        spec_id: str,
        since: datetime | None = None,
        until: datetime | None = None,
        event_filter: str | None = None,
        actor_filter: str | None = None,
        limit: int = 50,
    ) -> list[HistoryEntry]:
        """Query history entries for a specification.

        Args:
            spec_id: The specification ID.
            since: Only include entries at or after this timestamp.
            until: Only include entries at or before this timestamp.
            event_filter: Only include entries with event containing this substring.
            actor_filter: Only include entries with this exact actor.
            limit: Maximum number of entries to return. Must be >= 1.

        Returns:
            List of matching history entries, sorted newest-first.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            ValueError: If limit is less than 1.
        """
        if limit < 1:
            msg = f"limit must be >= 1, got {limit}"
            raise ValueError(msg)

        # Get history path (validates spec exists)
        history_path = self._history_path(spec_id)

        # Read history file (returns empty list if missing)
        raw_entries = read_jsonl(history_path)

        # Parse and filter entries
        entries: list[HistoryEntry] = []
        for raw in raw_entries:
            entry = self._parse_entry(raw)
            if self._matches_filters(entry, since, until, event_filter, actor_filter):
                entries.append(entry)

        # Sort newest-first (by timestamp descending)
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        return entries[:limit]

    def record_event(
        self,
        spec_id: str,
        event: str,
        actor: str,
        **details: str | None,
    ) -> HistoryEntry:
        """Record an event to the per-spec history log.

        Args:
            spec_id: The specification ID.
            event: The event type (e.g., "spec_created", "requirement_added").
            actor: The actor who performed the action.
            **details: Optional event details. Supported keys:
                - id: ID of the affected entity.
                - target: Target of the action.
                - from_value: Previous value (for status changes).
                - to_value: New value (for status changes).
                - result: Test result (for test runs).
                - reason: Reason for the action.
                - command: Command that triggered the event.

        Returns:
            The created HistoryEntry.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get history path (validates spec exists)
        history_path = self._history_path(spec_id)

        # Generate timestamp
        timestamp = datetime.now(UTC)

        # Build entry dictionary
        entry_dict: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "event": event,
            "actor": actor,
        }

        # Add optional details if provided
        for key in (
            "id",
            "target",
            "from_value",
            "to_value",
            "result",
            "reason",
            "command",
        ):
            value = details.get(key)
            if value is not None:
                entry_dict[key] = value

        # Append to history file
        append_jsonl(history_path, entry_dict)

        # Parse result if present
        result_value = details.get("result")
        result: TestResult | None = None
        if result_value is not None:
            result = TestResult(result_value)

        # Return the created entry
        return HistoryEntry(
            timestamp=timestamp,
            event=event,
            actor=actor,
            command=details.get("command"),
            id=details.get("id"),
            target=details.get("target"),
            from_value=details.get("from_value"),
            to_value=details.get("to_value"),
            result=result,
            reason=details.get("reason"),
        )
