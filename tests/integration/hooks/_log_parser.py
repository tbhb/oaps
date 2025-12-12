"""Hook log parser for integration tests.

This module provides the HookLogParser class for parsing JSONL-formatted
hook log files produced by the OAPS hook runner.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True, slots=True)
class HookLogEntry:
    """A single parsed hook log entry.

    Attributes:
        timestamp: ISO-formatted timestamp of the log entry.
        level: Log level (debug, info, warning, error).
        event: The event name (e.g., hook_started, hook_completed).
        session_id: Claude session ID if present.
        hook_event: Hook event type if present (e.g., session_start).
        data: Full parsed log entry data.
    """

    timestamp: str
    level: str
    event: str
    session_id: str | None
    hook_event: str | None
    data: dict[str, object]


@dataclass(frozen=True, slots=True)
class HookLogParser:
    """Parser for hook log files.

    This class parses JSONL-formatted hook log files and provides
    filtering capabilities for integration test assertions.

    Attributes:
        log_path: Path to the hooks.log file.
    """

    log_path: Path

    def parse(self) -> list[HookLogEntry]:
        """Parse the log file into a list of entries.

        Parses each line as JSON and creates HookLogEntry objects.
        Malformed lines are skipped gracefully.

        Returns:
            List of parsed log entries in order.
        """
        if not self.log_path.exists():
            return []

        entries: list[HookLogEntry] = []
        content = self.log_path.read_text()

        for line in content.strip().split("\n"):
            if not line.strip():
                continue

            try:
                data = cast(dict[str, object], json.loads(line))
                entry = self._parse_entry(data)
                entries.append(entry)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

        return entries

    def _parse_entry(self, data: dict[str, object]) -> HookLogEntry:
        """Parse a single log entry from JSON data.

        Args:
            data: Parsed JSON dictionary.

        Returns:
            HookLogEntry with extracted fields.
        """
        # Extract standard fields with safe defaults
        timestamp = str(data.get("timestamp", ""))
        level = str(data.get("level", ""))
        event = str(data.get("event", ""))

        # Extract optional fields
        session_id = data.get("session_id")
        session_id_str = str(session_id) if session_id is not None else None

        hook_event = data.get("hook_event")
        hook_event_str = str(hook_event) if hook_event is not None else None

        return HookLogEntry(
            timestamp=timestamp,
            level=level,
            event=event,
            session_id=session_id_str,
            hook_event=hook_event_str,
            data=data,
        )

    def filter_by_event(self, event_name: str) -> list[HookLogEntry]:
        """Filter entries where entry.event matches the given name.

        Args:
            event_name: Event name to filter by (e.g., "hook_started").

        Returns:
            List of matching log entries.
        """
        entries = self.parse()
        return [e for e in entries if e.event == event_name]

    def filter_by_hook_event(self, hook_event: str) -> list[HookLogEntry]:
        """Filter entries where entry.hook_event matches the given type.

        Args:
            hook_event: Hook event type to filter by (e.g., "session_start").

        Returns:
            List of matching log entries.
        """
        entries = self.parse()
        return [e for e in entries if e.hook_event == hook_event]

    def filter_by_level(self, level: str) -> list[HookLogEntry]:
        """Filter entries by log level.

        Args:
            level: Log level to filter by (e.g., "warning", "error").

        Returns:
            List of matching log entries.
        """
        entries = self.parse()
        return [e for e in entries if e.level == level]

    def get_errors(self) -> list[HookLogEntry]:
        """Get all error-level log entries.

        Returns:
            List of error log entries.
        """
        return self.filter_by_level("error")

    def get_warnings(self) -> list[HookLogEntry]:
        """Get all warning-level log entries.

        Returns:
            List of warning log entries.
        """
        return self.filter_by_level("warning")
