"""Tests for usage analysis."""

from pathlib import Path

import pendulum
import pytest

from oaps.cli._commands._analyze._transcript import TranscriptDirectory
from oaps.cli._commands._analyze._usage import (
    DailyUsage,
    SessionUsage,
    UsageAnalysis,
    WeeklyUsage,
    parse_since_filter,
)


class TestSessionUsage:
    def test_cache_efficiency_with_data(self):
        session = SessionUsage(
            session_id="test",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T01:00:00Z",
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=20,
            cache_read_tokens=80,
            total_tokens=150,
            models_used=frozenset({"claude-3-5-sonnet"}),
            tools_used=frozenset({"Read"}),
            tool_invocations=5,
        )

        # cache_efficiency = cache_read / (cache_read + cache_creation + input)
        # = 80 / (80 + 20 + 100) = 80 / 200 = 0.4
        assert session.cache_efficiency == 0.4

    def test_cache_efficiency_with_no_input(self):
        session = SessionUsage(
            session_id="test",
            start_time=None,
            end_time=None,
            input_tokens=0,
            output_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            total_tokens=0,
            models_used=frozenset(),
            tools_used=frozenset(),
            tool_invocations=0,
        )

        assert session.cache_efficiency == 0.0


class TestDailyUsage:
    def test_cache_efficiency(self):
        daily = DailyUsage(
            date="2024-01-01",
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=10,
            cache_read_tokens=90,
            total_tokens=150,
            session_count=5,
            models_used=frozenset({"claude-3-5-sonnet"}),
        )

        # cache_efficiency = 90 / (90 + 10 + 100) = 90 / 200 = 0.45
        assert daily.cache_efficiency == 0.45


class TestWeeklyUsage:
    def test_cache_efficiency(self):
        weekly = WeeklyUsage(
            week_start="2024-01-01",
            week_end="2024-01-07",
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=400,
            total_tokens=1500,
            session_count=10,
            day_count=5,
            models_used=frozenset({"claude-3-5-sonnet"}),
        )

        # cache_efficiency = 400 / (400 + 100 + 1000) = 400 / 1500 = 0.267
        assert abs(weekly.cache_efficiency - 0.267) < 0.001


class TestUsageAnalysis:
    def test_total_tokens_property(self, tmp_path: Path):
        td = TranscriptDirectory(
            path=tmp_path,
            project_path=tmp_path,
            main_sessions=[],
            agent_transcripts=[],
        )
        analysis = UsageAnalysis(
            transcript_dir=td,
            total_input_tokens=100,
            total_output_tokens=50,
        )

        assert analysis.total_tokens == 150

    def test_overall_cache_efficiency_property(self, tmp_path: Path):
        td = TranscriptDirectory(
            path=tmp_path,
            project_path=tmp_path,
            main_sessions=[],
            agent_transcripts=[],
        )
        analysis = UsageAnalysis(
            transcript_dir=td,
            total_input_tokens=100,
            total_output_tokens=50,
            total_cache_creation=10,
            total_cache_read=90,
        )

        # cache_efficiency = 90 / (90 + 10 + 100) = 90 / 200 = 0.45
        assert analysis.overall_cache_efficiency == 0.45


class TestParseSinceFilter:
    def test_parses_days(self):
        result = parse_since_filter("7d")
        expected = pendulum.now("UTC").subtract(days=7)

        # Allow small time difference due to execution time
        assert abs((result - expected).total_seconds()) < 1

    def test_parses_weeks(self):
        result = parse_since_filter("2w")
        expected = pendulum.now("UTC").subtract(weeks=2)

        assert abs((result - expected).total_seconds()) < 1

    def test_parses_months(self):
        result = parse_since_filter("1m")
        expected = pendulum.now("UTC").subtract(months=1)

        assert abs((result - expected).total_seconds()) < 1

    def test_parses_date_string(self):
        result = parse_since_filter("2024-12-01")

        assert result.year == 2024
        assert result.month == 12
        assert result.day == 1

    def test_raises_on_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid --since value"):
            parse_since_filter("invalid")

    def test_handles_uppercase(self):
        result = parse_since_filter("7D")
        expected = pendulum.now("UTC").subtract(days=7)

        assert abs((result - expected).total_seconds()) < 1
