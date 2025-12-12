# pyright: reportArgumentType=false, reportExplicitAny=false
# pyright: reportOptionalMemberAccess=false, reportAny=false
"""Unit tests for the logs _query module."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import polars as pl
import pytest
from hypothesis import given, settings, strategies as st

from oaps.cli._commands._logs._query import (
    _build_column_expr,
    _build_filter_expr,
    _format_compact_entry,
    _parse_numeric,
    _parse_time_filter,
    _parse_where_clause,
)
from oaps.cli._commands._logs._sources import LogSource


class TestParseTimeFilter:
    def test_returns_none_for_none_input(self) -> None:
        result = _parse_time_filter(None)
        assert result is None

    def test_parses_relative_days(self) -> None:
        with patch("oaps.cli._commands._logs._query.datetime") as mock_dt:
            now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat

            result = _parse_time_filter("2d")

            expected = now - timedelta(days=2)
            assert result == expected

    def test_parses_relative_hours(self) -> None:
        with patch("oaps.cli._commands._logs._query.datetime") as mock_dt:
            now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat

            result = _parse_time_filter("6h")

            expected = now - timedelta(hours=6)
            assert result == expected

    def test_parses_relative_minutes(self) -> None:
        with patch("oaps.cli._commands._logs._query.datetime") as mock_dt:
            now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat

            result = _parse_time_filter("30m")

            expected = now - timedelta(minutes=30)
            assert result == expected

    def test_parses_absolute_date(self) -> None:
        result = _parse_time_filter("2025-01-01")

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1
        assert result.tzinfo == UTC

    def test_parses_absolute_datetime(self) -> None:
        result = _parse_time_filter("2025-01-15T10:30:00")

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo == UTC

    def test_parses_absolute_datetime_with_timezone(self) -> None:
        result = _parse_time_filter("2025-01-15T10:30:00+00:00")

        assert result.year == 2025
        assert result.tzinfo is not None

    def test_invalid_format_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Invalid time format"):
            _parse_time_filter("invalid")

    def test_invalid_format_includes_guidance(self) -> None:
        with pytest.raises(ValueError, match=r"relative.*absolute"):
            _parse_time_filter("yesterday")

    @given(st.integers(min_value=1, max_value=999))
    @settings(max_examples=20)
    def test_relative_days_property(self, days: int) -> None:
        result = _parse_time_filter(f"{days}d")
        assert result is not None
        # Result should be in the past
        assert result < datetime.now(UTC)

    @given(st.integers(min_value=1, max_value=999))
    @settings(max_examples=20)
    def test_relative_hours_property(self, hours: int) -> None:
        result = _parse_time_filter(f"{hours}h")
        assert result is not None
        assert result < datetime.now(UTC)

    @given(st.integers(min_value=1, max_value=999))
    @settings(max_examples=20)
    def test_relative_minutes_property(self, minutes: int) -> None:
        result = _parse_time_filter(f"{minutes}m")
        assert result is not None
        assert result < datetime.now(UTC)


class TestParseWhereClause:
    def test_equals_string(self) -> None:
        expr = _parse_where_clause("level = error")

        df = pl.DataFrame({"level": ["info", "error", "warning"]})
        result = df.filter(expr)

        assert result.height == 1
        assert result["level"][0] == "error"

    def test_equals_quoted_string(self) -> None:
        expr = _parse_where_clause("level = 'error'")

        df = pl.DataFrame({"level": ["info", "error", "warning"]})
        result = df.filter(expr)

        assert result.height == 1
        assert result["level"][0] == "error"

    def test_equals_double_quoted_string(self) -> None:
        expr = _parse_where_clause('level = "error"')

        df = pl.DataFrame({"level": ["info", "error", "warning"]})
        result = df.filter(expr)

        assert result.height == 1

    def test_equals_integer(self) -> None:
        expr = _parse_where_clause("count = 5")

        df = pl.DataFrame({"count": [1, 5, 10]})
        result = df.filter(expr)

        assert result.height == 1
        assert result["count"][0] == 5

    def test_equals_float(self) -> None:
        expr = _parse_where_clause("value = 3.14")

        df = pl.DataFrame({"value": [1.0, 3.14, 5.0]})
        result = df.filter(expr)

        assert result.height == 1

    def test_not_equals(self) -> None:
        expr = _parse_where_clause("level != info")

        df = pl.DataFrame({"level": ["info", "error", "warning"]})
        result = df.filter(expr)

        assert result.height == 2
        assert "info" not in result["level"].to_list()

    def test_greater_than(self) -> None:
        expr = _parse_where_clause("count > 5")

        df = pl.DataFrame({"count": [1, 5, 10, 15]})
        result = df.filter(expr)

        assert result.height == 2
        assert all(c > 5 for c in result["count"].to_list())

    def test_less_than(self) -> None:
        expr = _parse_where_clause("count < 10")

        df = pl.DataFrame({"count": [1, 5, 10, 15]})
        result = df.filter(expr)

        assert result.height == 2
        assert all(c < 10 for c in result["count"].to_list())

    def test_greater_than_or_equal(self) -> None:
        expr = _parse_where_clause("count >= 5")

        df = pl.DataFrame({"count": [1, 5, 10]})
        result = df.filter(expr)

        assert result.height == 2
        assert all(c >= 5 for c in result["count"].to_list())

    def test_less_than_or_equal(self) -> None:
        expr = _parse_where_clause("count <= 5")

        df = pl.DataFrame({"count": [1, 5, 10]})
        result = df.filter(expr)

        assert result.height == 2
        assert all(c <= 5 for c in result["count"].to_list())

    def test_regex_match(self) -> None:
        expr = _parse_where_clause("event ~ hook_.*")

        df = pl.DataFrame({"event": ["hook_started", "hook_completed", "other"]})
        result = df.filter(expr)

        assert result.height == 2
        assert all(e.startswith("hook_") for e in result["event"].to_list())

    def test_contains_literal(self) -> None:
        expr = _parse_where_clause("message contains error")

        df = pl.DataFrame(
            {"message": ["an error occurred", "all good", "error in processing"]}
        )
        result = df.filter(expr)

        assert result.height == 2

    def test_dot_notation_nested_field(self) -> None:
        expr = _parse_where_clause("context.exit_code != 0")

        df = pl.DataFrame(
            {"context": [{"exit_code": 0}, {"exit_code": 1}, {"exit_code": 2}]}
        ).cast({"context": pl.Struct({"exit_code": pl.Int64})})
        result = df.filter(expr)

        assert result.height == 2

    def test_invalid_syntax_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Invalid --where syntax"):
            _parse_where_clause("invalid syntax without operator")

    def test_invalid_syntax_provides_guidance(self) -> None:
        with pytest.raises(ValueError, match="Expected: field op value"):
            _parse_where_clause("bad query")


class TestBuildColumnExpr:
    def test_simple_field(self) -> None:
        expr = _build_column_expr("level")

        df = pl.DataFrame({"level": ["info", "error"]})
        result = df.select(expr)

        assert result.height == 2
        assert result.columns == ["level"]

    def test_nested_field_one_level(self) -> None:
        expr = _build_column_expr("context.exit_code")

        df = pl.DataFrame({"context": [{"exit_code": 0}, {"exit_code": 1}]}).cast(
            {"context": pl.Struct({"exit_code": pl.Int64})}
        )

        result = df.select(expr.alias("value"))
        assert result["value"].to_list() == [0, 1]

    def test_nested_field_multiple_levels(self) -> None:
        expr = _build_column_expr("a.b.c")

        df = pl.DataFrame({"a": [{"b": {"c": "value1"}}, {"b": {"c": "value2"}}]}).cast(
            {"a": pl.Struct({"b": pl.Struct({"c": pl.Utf8})})}
        )

        result = df.select(expr.alias("value"))
        assert result["value"].to_list() == ["value1", "value2"]


class TestParseNumeric:
    def test_parses_integer(self) -> None:
        result = _parse_numeric("42")
        assert result == 42
        assert isinstance(result, int)

    def test_parses_float(self) -> None:
        result = _parse_numeric("3.14")
        assert result == 3.14
        assert isinstance(result, float)

    def test_parses_negative_integer(self) -> None:
        result = _parse_numeric("-10")
        assert result == -10

    def test_parses_negative_float(self) -> None:
        result = _parse_numeric("-2.5")
        assert result == -2.5

    def test_invalid_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="could not convert"):
            _parse_numeric("not a number")

    @given(st.integers())
    @settings(max_examples=50)
    def test_integer_roundtrip(self, n: int) -> None:
        result = _parse_numeric(str(n))
        assert result == n

    @given(st.floats(allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_float_roundtrip(self, f: float) -> None:
        result = _parse_numeric(str(f))
        assert abs(result - f) < 1e-10 or result == f


class TestBuildFilterExpr:
    def test_level_filter_info(self) -> None:
        expr = _build_filter_expr(
            level="info",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame({"level": ["debug", "info", "warning", "error"]})
        result = df.filter(expr)

        # info, warning, error should pass; debug should not
        assert result.height == 3
        assert "debug" not in result["level"].to_list()

    def test_level_filter_warning(self) -> None:
        expr = _build_filter_expr(
            level="warning",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame({"level": ["debug", "info", "warning", "error"]})
        result = df.filter(expr)

        # warning, error should pass
        assert result.height == 2
        assert set(result["level"].to_list()) == {"warning", "error"}

    def test_level_filter_error(self) -> None:
        expr = _build_filter_expr(
            level="error",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame({"level": ["debug", "info", "warning", "error"]})
        result = df.filter(expr)

        assert result.height == 1
        assert result["level"][0] == "error"

    def test_level_filter_debug(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame({"level": ["debug", "info", "warning", "error"]})
        result = df.filter(expr)

        # All levels should pass
        assert result.height == 4

    def test_event_filter_single(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=["hook_started"],
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "event": ["hook_started", "hook_completed", "hook_failed"],
                "level": ["info", "info", "error"],
            }
        )
        result = df.filter(expr)

        assert result.height == 1
        assert result["event"][0] == "hook_started"

    def test_event_filter_multiple(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=["hook_started", "hook_completed"],
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "event": ["hook_started", "hook_completed", "hook_failed"],
                "level": ["info", "info", "error"],
            }
        )
        result = df.filter(expr)

        assert result.height == 2

    def test_time_filter_since(self) -> None:
        since_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=since_dt,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "timestamp": [
                    "2025-01-15T09:00:00+00:00",
                    "2025-01-15T10:00:00+00:00",
                    "2025-01-15T11:00:00+00:00",
                ],
                "level": ["info", "info", "info"],
            }
        )
        result = df.filter(expr)

        # Entries at or after 10:00 should pass
        assert result.height == 2

    def test_time_filter_until(self) -> None:
        until_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=until_dt,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "timestamp": [
                    "2025-01-15T09:00:00+00:00",
                    "2025-01-15T10:00:00+00:00",
                    "2025-01-15T11:00:00+00:00",
                ],
                "level": ["info", "info", "info"],
            }
        )
        result = df.filter(expr)

        # Entries at or before 10:00 should pass
        assert result.height == 2

    def test_grep_filter(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern="error",
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "event": ["start", "error_occurred", "done", "start"],
                "level": ["info", "info", "info", "error"],
                "session_id": ["s-1", "s-2", "s-3", "s-4"],
            }
        )
        result = df.filter(expr)

        # Row 2 matches "error" in event, Row 4 matches "error" in level
        assert result.height == 2
        events = result["event"].to_list()
        assert "error_occurred" in events
        assert events.count("start") == 1  # The one with level=error

    def test_session_filter(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter="abc",
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "event": ["hook_started", "hook_started", "hook_started"],
                "level": ["info", "info", "info"],
                "session_id": ["abc-123", "abc-456", "xyz-789"],
            }
        )
        result = df.filter(expr)

        assert result.height == 2
        assert all("abc" in s for s in result["session_id"].to_list())

    def test_rule_id_filter(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter="security",
            tool_name_filter=None,
            where_clauses=None,
        )

        df = pl.DataFrame(
            {
                "event": ["rule_matched", "rule_matched", "rule_matched"],
                "level": ["info", "info", "info"],
                "rule_id": ["security-check", "performance", "security-block"],
            }
        )
        result = df.filter(expr)

        assert result.height == 2

    def test_where_clause_filter(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=["count > 0"],
        )

        df = pl.DataFrame(
            {
                "event": ["hook_completed", "hook_completed", "hook_completed"],
                "level": ["info", "info", "info"],
                "count": [0, 5, 10],
            }
        )
        result = df.filter(expr)

        assert result.height == 2

    def test_multiple_where_clauses(self) -> None:
        expr = _build_filter_expr(
            level="debug",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=["count > 0", "count < 10"],
        )

        df = pl.DataFrame(
            {
                "event": ["a", "b", "c"],
                "level": ["info", "info", "info"],
                "count": [0, 5, 10],
            }
        )
        result = df.filter(expr)

        # Only count=5 matches both conditions
        assert result.height == 1
        assert result["count"][0] == 5

    def test_combined_filters(self) -> None:
        since_dt = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
        expr = _build_filter_expr(
            level="info",
            events=["hook_completed"],
            since_dt=since_dt,
            until_dt=None,
            grep_pattern=None,
            session_filter="abc",
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=["count > 0"],
        )

        df = pl.DataFrame(
            {
                "timestamp": [
                    "2025-01-15T09:00:00+00:00",
                    "2025-01-15T11:00:00+00:00",
                    "2025-01-15T12:00:00+00:00",
                    "2025-01-15T13:00:00+00:00",
                ],
                "event": ["hook_completed", "hook_completed", "hook_started", "done"],
                "level": ["info", "info", "info", "debug"],
                "session_id": ["abc-123", "abc-456", "abc-789", "abc-000"],
                "count": [0, 5, 10, 15],
            }
        )
        result = df.filter(expr)

        # Only the second row matches all conditions
        assert result.height == 1

    def test_returns_none_when_no_filters(self) -> None:
        expr = _build_filter_expr(
            level="invalid_level",
            events=None,
            since_dt=None,
            until_dt=None,
            grep_pattern=None,
            session_filter=None,
            rule_id_filter=None,
            tool_name_filter=None,
            where_clauses=None,
        )

        # Invalid level is not in _LEVEL_ORDER, so no filter is created
        assert expr is None


class TestFormatCompactEntry:
    @pytest.fixture
    def source(self, tmp_path: Path) -> LogSource:
        return LogSource(
            name="hooks",
            paths=(tmp_path / "hooks.log",),
            source_type="hooks",
        )

    def test_basic_formatting(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
        }

        result = _format_compact_entry(row, source)

        assert "10:30:45" in result
        assert "INFO" in result
        assert "hook_started" in result

    def test_includes_source_hint(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
            "hook_event": "session_start",
        }

        result = _format_compact_entry(row, source)

        assert "hooks:session_start" in result

    def test_truncates_long_source_hint(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
            "hook_event": "very_long_hook_event_name_that_exceeds_width",
        }

        result = _format_compact_entry(row, source)

        # Should be truncated with ellipsis
        assert "…" in result

    def test_truncates_long_event_name(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "this_is_a_very_long_event_name_that_should_be_truncated",
            "_source": "hooks",
        }

        result = _format_compact_entry(row, source)

        # Event name should be truncated
        assert len(result) < 200

    def test_includes_session_id_truncated(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
            "session_id": "a39cb323-4567-890a-bcde-fghijklmnopq",
        }

        result = _format_compact_entry(row, source)

        assert "session_id=a39cb323…" in result

    def test_handles_uuid_wrapped_session_id(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
            "session_id": "UUID('a39cb323-4567-890a-bcde-fghijklmnopq')",
        }

        result = _format_compact_entry(row, source)

        assert "session_id=a39cb323…" in result
        assert "UUID(" not in result

    def test_includes_rule_id(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "rule_matched",
            "_source": "hooks",
            "rule_id": "security-check",
        }

        result = _format_compact_entry(row, source)

        assert "rule_id=security-check" in result

    def test_includes_count(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "rules_matched",
            "_source": "hooks",
            "count": 5,
        }

        result = _format_compact_entry(row, source)

        assert "count=5" in result

    def test_includes_reason_truncated(self, source: LogSource) -> None:
        reason = "This is a very long reason that should be truncated"
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "error",
            "event": "hook_blocked",
            "_source": "hooks",
            "reason": reason,
        }

        result = _format_compact_entry(row, source)

        assert "reason=" in result
        assert "…" in result

    def test_handles_missing_timestamp(self, source: LogSource) -> None:
        row: dict[str, Any] = {
            "level": "info",
            "event": "hook_started",
            "_source": "hooks",
        }

        result = _format_compact_entry(row, source)

        # Should not crash
        assert "INFO" in result
        assert "hook_started" in result

    def test_cli_source_with_command(self, tmp_path: Path) -> None:
        source = LogSource(
            name="cli",
            paths=(tmp_path / "cli.log",),
            source_type="cli",
        )
        row: dict[str, Any] = {
            "timestamp": "2025-01-15T10:30:45Z",
            "level": "info",
            "event": "command_started",
            "_source": "cli",
            "command": "config",
        }

        result = _format_compact_entry(row, source)

        assert "cli:config" in result
