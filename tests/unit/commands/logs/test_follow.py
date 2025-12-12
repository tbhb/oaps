# pyright: reportArgumentType=false, reportExplicitAny=false, reportAny=false
"""Unit tests for the logs _follow module."""

import json
from pathlib import Path

import polars as pl
import pytest
from hypothesis import given, settings, strategies as st

from oaps.cli._commands._logs._follow import (
    _apply_polars_filter,
    _format_entry,
    _infer_source_hint,
    _matches_level,
    _read_new_entries,
)
from oaps.cli._commands._logs._sources import LogSource


class TestMatchesLevel:
    def test_debug_matches_debug(self) -> None:
        assert _matches_level("debug", "debug") is True

    def test_info_matches_debug(self) -> None:
        assert _matches_level("info", "debug") is True

    def test_warning_matches_debug(self) -> None:
        assert _matches_level("warning", "debug") is True

    def test_error_matches_debug(self) -> None:
        assert _matches_level("error", "debug") is True

    def test_debug_does_not_match_info(self) -> None:
        assert _matches_level("debug", "info") is False

    def test_debug_does_not_match_warning(self) -> None:
        assert _matches_level("debug", "warning") is False

    def test_debug_does_not_match_error(self) -> None:
        assert _matches_level("debug", "error") is False

    def test_info_matches_info(self) -> None:
        assert _matches_level("info", "info") is True

    def test_info_does_not_match_warning(self) -> None:
        assert _matches_level("info", "warning") is False

    def test_warning_matches_warning(self) -> None:
        assert _matches_level("warning", "warning") is True

    def test_warning_does_not_match_error(self) -> None:
        assert _matches_level("warning", "error") is False

    def test_error_matches_error(self) -> None:
        assert _matches_level("error", "error") is True

    def test_case_insensitive_entry_level(self) -> None:
        assert _matches_level("INFO", "info") is True
        assert _matches_level("WARNING", "warning") is True
        assert _matches_level("Error", "error") is True

    def test_case_insensitive_min_level(self) -> None:
        assert _matches_level("info", "INFO") is True
        assert _matches_level("warning", "WARNING") is True

    def test_unknown_entry_level_matches(self) -> None:
        # Unknown levels should be shown
        assert _matches_level("trace", "debug") is True
        assert _matches_level("unknown", "info") is True

    def test_unknown_min_level_matches(self) -> None:
        # If min_level is unknown, show everything
        assert _matches_level("debug", "unknown") is True
        assert _matches_level("info", "trace") is True

    @given(st.sampled_from(["debug", "info", "warning", "error"]))
    @settings(max_examples=20)
    def test_level_matches_itself(self, level: str) -> None:
        assert _matches_level(level, level) is True

    @given(
        st.sampled_from(["debug", "info", "warning", "error"]),
        st.sampled_from(["debug", "info", "warning", "error"]),
    )
    @settings(max_examples=50)
    def test_ordering_property(self, entry_level: str, min_level: str) -> None:
        level_order = ["debug", "info", "warning", "error"]
        entry_idx = level_order.index(entry_level)
        min_idx = level_order.index(min_level)

        result = _matches_level(entry_level, min_level)
        expected = entry_idx >= min_idx

        assert result == expected


class TestFormatEntry:
    def test_basic_formatting(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
        }

        result = _format_entry(entry, "hooks")

        assert "10:30:45" in result
        assert "INFO" in result
        assert "hook_started" in result
        assert "hooks" in result

    def test_extracts_time_from_timestamp(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T23:59:59+00:00",
            "level": "info",
            "event": "test",
        }

        result = _format_entry(entry, "hooks")

        assert "23:59:59" in result

    def test_handles_timestamp_without_t_separator(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "10:30:45",
            "level": "info",
            "event": "test",
        }

        result = _format_entry(entry, "hooks")

        assert "10:30:45" in result

    def test_appends_hook_event_to_hooks_source(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "hook_event": "session_start",
        }

        result = _format_entry(entry, "hooks")

        assert "hooks:session_start" in result

    def test_appends_command_to_cli_source(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "command_started",
            "command": "config",
        }

        result = _format_entry(entry, "cli")

        assert "cli:config" in result

    def test_truncates_long_source_hint(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "test",
            "hook_event": "very_long_event_name_that_exceeds_width_limit",
        }

        result = _format_entry(entry, "hooks")

        # Source hint should be truncated with ellipsis
        assert "…" in result

    def test_truncates_long_event_name(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "this_is_a_very_long_event_name_that_exceeds_limit",
        }

        result = _format_entry(entry, "hooks")

        # Should contain ellipsis for truncated event
        assert len(result) < 200

    def test_includes_session_id_truncated(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "session_id": "a39cb323-4567-890a-bcde-fghijklmnopq",
        }

        result = _format_entry(entry, "hooks")

        assert "session_id=a39cb323…" in result

    def test_unwraps_uuid_session_id(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "session_id": "UUID('a39cb323-4567-890a-bcde-fghijklmnopq')",
        }

        result = _format_entry(entry, "hooks")

        assert "session_id=a39cb323…" in result
        assert "UUID(" not in result

    def test_includes_rule_id(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "rule_matched",
            "rule_id": "security-check",
        }

        result = _format_entry(entry, "hooks")

        assert "rule_id=security-check" in result

    def test_includes_count(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "rules_matched",
            "count": 5,
        }

        result = _format_entry(entry, "hooks")

        assert "count=5" in result

    def test_includes_reason_truncated(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "error",
            "event": "hook_blocked",
            "reason": "This is a very long reason message that should be truncated",
        }

        result = _format_entry(entry, "hooks")

        assert "reason=" in result
        assert "…" in result

    def test_handles_missing_fields(self) -> None:
        entry: dict[str, object] = {}

        result = _format_entry(entry, "hooks")

        # Should not crash with empty entry
        assert "hooks" in result

    def test_uppercase_level(self) -> None:
        entry: dict[str, object] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "warning",
            "event": "test",
        }

        result = _format_entry(entry, "hooks")

        assert "WARNI" in result  # Truncated to 5 chars


class TestInferSourceHint:
    def test_hooks_log(self) -> None:
        path = Path("/some/path/to/hooks.log")
        assert _infer_source_hint(path) == "hooks"

    def test_cli_log(self) -> None:
        path = Path("/some/path/to/cli.log")
        assert _infer_source_hint(path) == "cli"

    def test_session_log(self) -> None:
        path = Path("/some/path/to/a39cb323-4567-890a-bcde.log")
        assert _infer_source_hint(path) == "sess:a39cb323"

    def test_session_log_with_short_id(self) -> None:
        path = Path("/some/path/to/abc.log")
        assert _infer_source_hint(path) == "sess:abc"


class TestApplyPolarsFilter:
    def test_no_filter_passes_all(self) -> None:
        entry: dict[str, object] = {"level": "info", "event": "test"}

        result = _apply_polars_filter(entry, None)

        assert result is True

    def test_matching_filter_passes(self) -> None:
        entry: dict[str, object] = {"level": "error", "event": "test"}
        filter_expr = pl.col("level") == "error"

        result = _apply_polars_filter(entry, filter_expr)

        assert result is True

    def test_non_matching_filter_fails(self) -> None:
        entry: dict[str, object] = {"level": "info", "event": "test"}
        filter_expr = pl.col("level") == "error"

        result = _apply_polars_filter(entry, filter_expr)

        assert result is False

    def test_missing_column_passes(self) -> None:
        # If filter references column that doesn't exist, include the entry
        entry: dict[str, object] = {"level": "info"}
        filter_expr = pl.col("nonexistent") == "value"

        result = _apply_polars_filter(entry, filter_expr)

        # Should include entries that can't be filtered
        assert result is True

    def test_complex_filter(self) -> None:
        entry: dict[str, object] = {"level": "error", "count": 5}
        filter_expr = (pl.col("level") == "error") & (pl.col("count") > 0)

        result = _apply_polars_filter(entry, filter_expr)

        assert result is True

    def test_complex_filter_partial_match(self) -> None:
        entry: dict[str, object] = {"level": "info", "count": 5}
        filter_expr = (pl.col("level") == "error") & (pl.col("count") > 0)

        result = _apply_polars_filter(entry, filter_expr)

        assert result is False


class TestReadNewEntries:
    @pytest.fixture
    def log_dir(self, tmp_path: Path) -> Path:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        return logs_dir

    def _write_jsonl(self, path: Path, entries: list[dict[str, object]]) -> None:
        with path.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def _append_jsonl(self, path: Path, entries: list[dict[str, object]]) -> None:
        with path.open("a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_reads_new_entries_from_single_file(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "test1"},
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "test2"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 2
        assert new_entries[0][0]["event"] == "test1"
        assert new_entries[1][0]["event"] == "test2"
        assert new_entries[0][1] == "hooks"

    def test_tracks_position_correctly(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        initial_entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "initial"},
        ]
        self._write_jsonl(log_file, initial_entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        # First read
        _read_new_entries(source, positions, None, "debug")

        # Add more entries
        new_entries_data = [
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "new1"},
            {"timestamp": "2025-01-15T10:00:02Z", "level": "info", "event": "new2"},
        ]
        self._append_jsonl(log_file, new_entries_data)

        # Second read should only get new entries
        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 2
        assert new_entries[0][0]["event"] == "new1"
        assert new_entries[1][0]["event"] == "new2"

    def test_handles_file_truncation(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "old1"},
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "old2"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        # First read sets position
        _read_new_entries(source, positions, None, "debug")
        old_position = positions[log_file]

        # Truncate file (simulate log rotation)
        new_entries_data = [
            {"timestamp": "2025-01-15T11:00:00Z", "level": "info", "event": "new"},
        ]
        self._write_jsonl(log_file, new_entries_data)

        # File is now smaller than old position
        assert log_file.stat().st_size < old_position

        # Should reset position and read from beginning
        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 1
        assert new_entries[0][0]["event"] == "new"

    def test_filters_by_level(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "debug", "event": "dbg"},
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "inf"},
            {"timestamp": "2025-01-15T10:00:02Z", "level": "error", "event": "err"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        # Filter to warning and above
        new_entries = _read_new_entries(source, positions, None, "warning")

        # Only error should pass
        assert len(new_entries) == 1
        assert new_entries[0][0]["level"] == "error"

    def test_applies_polars_filter(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "started"},
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "done"},
            {"timestamp": "2025-01-15T10:00:02Z", "level": "info", "event": "failed"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}
        filter_expr = pl.col("event").str.contains("done")

        new_entries = _read_new_entries(source, positions, filter_expr, "debug")

        assert len(new_entries) == 1
        assert new_entries[0][0]["event"] == "done"

    def test_handles_missing_file(self, log_dir: Path) -> None:
        missing_file = log_dir / "missing.log"

        source = LogSource(name="hooks", paths=(missing_file,), source_type="hooks")
        positions: dict[Path, int] = {}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 0

    def test_handles_invalid_json_lines(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        content = (
            '{"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "a"}\n'
            "this is not valid json\n"
            '{"timestamp": "2025-01-15T10:00:02Z", "level": "info", "event": "b"}\n'
        )
        log_file.write_text(content)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        # Should skip invalid line and return valid entries
        assert len(new_entries) == 2

    def test_handles_empty_lines(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        content = (
            '{"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "t"}\n'
            "\n"
            "   \n"
        )
        log_file.write_text(content)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 1

    def test_reads_from_multiple_files(self, log_dir: Path) -> None:
        hooks_log = log_dir / "hooks.log"
        cli_log = log_dir / "cli.log"

        hooks_entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "h_evt"},
        ]
        cli_entries = [
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "c_evt"},
        ]

        self._write_jsonl(hooks_log, hooks_entries)
        self._write_jsonl(cli_log, cli_entries)

        source = LogSource(name="all", paths=(hooks_log, cli_log), source_type="all")
        positions: dict[Path, int] = {hooks_log: 0, cli_log: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 2
        # Should be sorted by timestamp
        assert new_entries[0][0]["event"] == "h_evt"
        assert new_entries[1][0]["event"] == "c_evt"

    def test_sorts_entries_by_timestamp(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        # Write entries out of order
        entries = [
            {"timestamp": "2025-01-15T10:00:02Z", "level": "info", "event": "third"},
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "first"},
            {"timestamp": "2025-01-15T10:00:01Z", "level": "info", "event": "second"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 3
        assert new_entries[0][0]["event"] == "first"
        assert new_entries[1][0]["event"] == "second"
        assert new_entries[2][0]["event"] == "third"

    def test_infers_source_hint_for_session_log(self, log_dir: Path) -> None:
        session_log = log_dir / "a39cb323-4567-890a-bcde.log"
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "level": "info", "event": "test"},
        ]
        self._write_jsonl(session_log, entries)

        source = LogSource(
            name="sess:a39cb323",
            paths=(session_log,),
            source_type="session",
        )
        positions: dict[Path, int] = {session_log: 0}

        new_entries = _read_new_entries(source, positions, None, "debug")

        assert len(new_entries) == 1
        assert new_entries[0][1] == "sess:a39cb323"

    def test_defaults_level_to_info_when_missing(self, log_dir: Path) -> None:
        log_file = log_dir / "hooks.log"
        # Entry without level field
        entries = [
            {"timestamp": "2025-01-15T10:00:00Z", "event": "test"},
        ]
        self._write_jsonl(log_file, entries)

        source = LogSource(name="hooks", paths=(log_file,), source_type="hooks")
        positions: dict[Path, int] = {log_file: 0}

        # With min_level=info, entry should pass (defaults to info)
        new_entries = _read_new_entries(source, positions, None, "info")

        assert len(new_entries) == 1

        # With min_level=warning, entry should fail
        positions = {log_file: 0}
        new_entries = _read_new_entries(source, positions, None, "warning")

        assert len(new_entries) == 0
