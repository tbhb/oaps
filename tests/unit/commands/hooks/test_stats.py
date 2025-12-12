"""Unit tests for the hooks stats command."""

import json
from pathlib import Path

import polars as pl
import pytest

from oaps.cli._commands._hooks._stats import (
    HookStats,
    _compute_event_counts,
    _compute_health_score,
    _compute_hook_event_counts,
    _compute_level_counts,
    _compute_stats,
    _compute_tool_usage,
    _format_json_output,
    _get_health_style,
)
from oaps.cli._shared import parse_log_to_dataframe as _parse_log_to_dataframe


@pytest.fixture
def sample_log_entries() -> list[dict[str, object]]:
    return [
        {
            "hook_event": "session_start",
            "session_id": "abc-123",
            "event": "hook_started",
            "level": "info",
            "timestamp": "2025-01-01T10:00:00Z",
        },
        {
            "hook_event": "session_start",
            "session_id": "abc-123",
            "event": "hook_completed",
            "level": "info",
            "timestamp": "2025-01-01T10:00:01Z",
        },
        {
            "hook_event": "pre_tool_use",
            "session_id": "abc-123",
            "event": "hook_started",
            "level": "info",
            "timestamp": "2025-01-01T10:00:02Z",
        },
        {
            "hook_event": None,
            "session_id": "abc-123",
            "event": "hook_input",
            "level": "info",
            "timestamp": "2025-01-01T10:00:02Z",
            "input": {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "session_id": "abc-123",
            },
        },
        {
            "hook_event": "pre_tool_use",
            "session_id": "abc-123",
            "event": "hook_completed",
            "level": "info",
            "timestamp": "2025-01-01T10:00:03Z",
        },
        {
            "hook_event": "pre_tool_use",
            "session_id": "abc-123",
            "event": "hook_started",
            "level": "info",
            "timestamp": "2025-01-01T10:00:04Z",
        },
        {
            "hook_event": None,
            "session_id": "abc-123",
            "event": "hook_input",
            "level": "info",
            "timestamp": "2025-01-01T10:00:04Z",
            "input": {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "session_id": "abc-123",
            },
        },
        {
            "hook_event": "pre_tool_use",
            "session_id": "abc-123",
            "event": "hook_failed",
            "level": "error",
            "timestamp": "2025-01-01T10:00:05Z",
        },
        {
            "hook_event": "post_tool_use",
            "session_id": "def-456",
            "event": "hook_started",
            "level": "info",
            "timestamp": "2025-01-01T10:00:06Z",
        },
        {
            "hook_event": "post_tool_use",
            "session_id": "def-456",
            "event": "hook_completed",
            "level": "info",
            "timestamp": "2025-01-01T10:00:07Z",
        },
    ]


@pytest.fixture
def sample_log_file(
    tmp_path: Path, sample_log_entries: list[dict[str, object]]
) -> Path:
    log_file = tmp_path / "hooks.log"
    with log_file.open("w") as f:
        for entry in sample_log_entries:
            f.write(json.dumps(entry) + "\n")
    return log_file


@pytest.fixture
def sample_df(sample_log_entries: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(sample_log_entries)


class TestParseLogToDataframe:
    def test_parses_jsonl_file(self, sample_log_file: Path) -> None:
        df = _parse_log_to_dataframe(str(sample_log_file))

        assert df.height == 10
        assert "hook_event" in df.columns
        assert "session_id" in df.columns

    def test_raises_on_invalid_file(self, tmp_path: Path) -> None:
        invalid_file = tmp_path / "invalid.log"
        invalid_file.write_text("not json\n")

        with pytest.raises(pl.exceptions.ComputeError):
            _parse_log_to_dataframe(str(invalid_file))


class TestComputeLevelCounts:
    def test_counts_levels(self, sample_df: pl.DataFrame) -> None:
        counts = _compute_level_counts(sample_df)

        assert counts["info"] == 9
        assert counts["error"] == 1

    def test_empty_when_no_level_column(self) -> None:
        df = pl.DataFrame({"event": ["a", "b"]})
        counts = _compute_level_counts(df)

        assert counts == {}


class TestComputeEventCounts:
    def test_counts_events(self, sample_df: pl.DataFrame) -> None:
        counts = _compute_event_counts(sample_df)

        assert counts["hook_started"] == 4
        assert counts["hook_completed"] == 3  # One hook failed instead of completing
        assert counts["hook_failed"] == 1
        assert counts["hook_input"] == 2

    def test_empty_when_no_event_column(self) -> None:
        df = pl.DataFrame({"level": ["info", "error"]})
        counts = _compute_event_counts(df)

        assert counts == {}


class TestComputeHookEventCounts:
    def test_counts_hook_events(self, sample_df: pl.DataFrame) -> None:
        counts = _compute_hook_event_counts(sample_df)

        # Only non-null hook_events are counted
        assert counts["pre_tool_use"] == 4
        assert counts["post_tool_use"] == 2
        assert counts["session_start"] == 2

    def test_empty_when_no_hook_event_column(self) -> None:
        df = pl.DataFrame({"event": ["a", "b"]})
        counts = _compute_hook_event_counts(df)

        assert counts == {}


class TestComputeToolUsage:
    def test_extracts_tool_usage(self, sample_df: pl.DataFrame) -> None:
        usage = _compute_tool_usage(sample_df)

        assert usage["Read"] == 1
        assert usage["Bash"] == 1

    def test_empty_when_no_input_column(self) -> None:
        df = pl.DataFrame({"event": ["hook_input"], "hook_event": ["pre_tool_use"]})
        usage = _compute_tool_usage(df)

        assert usage == {}


class TestComputeStats:
    def test_computes_all_stats(self, sample_df: pl.DataFrame) -> None:
        stats = _compute_stats(sample_df)

        assert stats.total_entries == 10
        assert stats.total_sessions == 2
        assert stats.error_count == 1
        assert stats.completed_count == 3  # One hook failed instead of completing
        assert stats.failed_count == 1
        assert "pre_tool_use" in stats.entries_by_hook_event
        assert stats.time_range_start is not None
        assert stats.time_range_end is not None

    def test_handles_uuid_wrapped_session_ids(self) -> None:
        df = pl.DataFrame(
            {
                "session_id": ["UUID('abc-123')", "UUID('def-456')", "abc-123"],
                "event": ["hook_started", "hook_started", "hook_started"],
                "level": ["info", "info", "info"],
                "timestamp": ["2025-01-01T10:00:00Z"] * 3,
            }
        )
        stats = _compute_stats(df)

        # abc-123 appears both wrapped and unwrapped, so should be 2 unique
        assert stats.total_sessions == 2


class TestComputeHealthScore:
    def test_perfect_score_with_no_issues(self) -> None:
        stats = HookStats(
            total_entries=100,
            total_sessions=5,
            entries_by_level={"info": 100},
            entries_by_event={"hook_started": 50, "hook_completed": 50},
            entries_by_hook_event={"pre_tool_use": 100},
            error_count=0,
            warning_count=0,
            blocked_count=0,
            failed_count=0,
            completed_count=50,
            avg_hooks_per_session=10.0,
            most_active_sessions=[],
            time_range_start="2025-01-01T00:00:00Z",
            time_range_end="2025-01-01T01:00:00Z",
            tool_usage={},
            top_errors=[],
        )
        score, issues = _compute_health_score(stats)

        assert score == 100
        assert issues == []

    def test_deducts_for_errors(self) -> None:
        stats = HookStats(
            total_entries=100,
            total_sessions=5,
            entries_by_level={"info": 95, "error": 5},
            entries_by_event={"hook_started": 50, "hook_completed": 50},
            entries_by_hook_event={},
            error_count=5,
            warning_count=0,
            blocked_count=0,
            failed_count=0,
            completed_count=50,
            avg_hooks_per_session=10.0,
            most_active_sessions=[],
            time_range_start=None,
            time_range_end=None,
            tool_usage={},
            top_errors=[("ValueError: test error", 5)],
        )
        score, issues = _compute_health_score(stats)

        assert score < 100
        assert any("error" in issue for issue in issues)

    def test_deducts_for_failed_hooks(self) -> None:
        stats = HookStats(
            total_entries=100,
            total_sessions=5,
            entries_by_level={"info": 100},
            entries_by_event={
                "hook_started": 50,
                "hook_completed": 45,
                "hook_failed": 5,
            },
            entries_by_hook_event={},
            error_count=0,
            warning_count=0,
            blocked_count=0,
            failed_count=5,
            completed_count=45,
            avg_hooks_per_session=10.0,
            most_active_sessions=[],
            time_range_start=None,
            time_range_end=None,
            tool_usage={},
            top_errors=[],
        )
        score, issues = _compute_health_score(stats)

        assert score < 100
        assert any("failed" in issue for issue in issues)

    def test_deducts_for_low_completion_rate(self) -> None:
        stats = HookStats(
            total_entries=100,
            total_sessions=5,
            entries_by_level={"info": 100},
            entries_by_event={"hook_started": 100, "hook_completed": 90},
            entries_by_hook_event={},
            error_count=0,
            warning_count=0,
            blocked_count=0,
            failed_count=0,
            completed_count=90,  # 90% completion rate
            avg_hooks_per_session=10.0,
            most_active_sessions=[],
            time_range_start=None,
            time_range_end=None,
            tool_usage={},
            top_errors=[],
        )
        score, issues = _compute_health_score(stats)

        assert score < 100
        assert any("Completion rate" in issue for issue in issues)


class TestGetHealthStyle:
    def test_excellent(self) -> None:
        status, color = _get_health_style(95)
        assert status == "Excellent"
        assert color == "green"

    def test_good(self) -> None:
        status, color = _get_health_style(80)
        assert status == "Good"
        assert color == "blue"

    def test_fair(self) -> None:
        status, color = _get_health_style(60)
        assert status == "Fair"
        assert color == "yellow"

    def test_poor(self) -> None:
        status, color = _get_health_style(40)
        assert status == "Poor"
        assert color == "red"


class TestFormatJsonOutput:
    def test_produces_valid_json(self) -> None:
        stats = HookStats(
            total_entries=100,
            total_sessions=5,
            entries_by_level={"info": 100},
            entries_by_event={"hook_started": 50, "hook_completed": 50},
            entries_by_hook_event={"pre_tool_use": 100},
            error_count=0,
            warning_count=0,
            blocked_count=0,
            failed_count=0,
            completed_count=50,
            avg_hooks_per_session=10.0,
            most_active_sessions=[("session-1", 25), ("session-2", 15)],
            time_range_start="2025-01-01T00:00:00Z",
            time_range_end="2025-01-01T01:00:00Z",
            tool_usage={"Read": 30, "Bash": 20},
            top_errors=[],
        )
        output = _format_json_output(stats)

        # Should be valid JSON
        data = json.loads(output)
        assert data["overview"]["total_entries"] == 100
        assert data["health"]["score"] == 100
        assert len(data["most_active_sessions"]) == 2

    def test_includes_tool_usage(self) -> None:
        stats = HookStats(
            total_entries=10,
            total_sessions=1,
            entries_by_level={},
            entries_by_event={},
            entries_by_hook_event={},
            error_count=0,
            warning_count=0,
            blocked_count=0,
            failed_count=0,
            completed_count=10,
            avg_hooks_per_session=10.0,
            most_active_sessions=[],
            time_range_start=None,
            time_range_end=None,
            tool_usage={"Read": 5, "Edit": 3},
            top_errors=[],
        )
        output = _format_json_output(stats)
        data = json.loads(output)

        assert data["tool_usage"]["Read"] == 5
        assert data["tool_usage"]["Edit"] == 3
