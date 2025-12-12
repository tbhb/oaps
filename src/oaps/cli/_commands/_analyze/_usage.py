# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportImplicitStringConcatenation=false
# pyright: reportImportCycles=false
# ruff: noqa: A002, BLE001, E501, PERF401, PLR0912, PLR0913, PLR0915, PLR2004
# ruff: noqa: TC003, TRY004, TRY300, TRY301
"""Usage analysis subcommand for analyze - analyze Claude Code token usage."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import pendulum
import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.table import Table

from oaps.utils import get_oaps_dir, get_worktree_root

from ._app import app
from ._exit_codes import (
    EXIT_LOAD_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OUTPUT_ERROR,
    EXIT_SUCCESS,
)
from ._transcript import (
    TranscriptDirectory,
    discover_transcript_directory,
    load_tool_data,
    load_usage_data,
)

# Model display name mappings
MODEL_DISPLAY_NAMES: dict[str, str] = {
    "claude-opus-4-5-20251101": "Opus 4.5",
    "claude-sonnet-4-20250514": "Sonnet 4",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
    "claude-3-5-sonnet-20241022": "Sonnet 3.5",
    "claude-3-5-haiku-20241022": "Haiku 3.5",
}


@dataclass(frozen=True, slots=True)
class SessionUsage:
    """Token usage statistics for a single session.

    Attributes:
        session_id: Unique session identifier.
        start_time: Session start timestamp.
        end_time: Session end timestamp.
        input_tokens: Total input tokens.
        output_tokens: Total output tokens.
        cache_creation_tokens: Tokens used for cache creation.
        cache_read_tokens: Tokens read from cache.
        total_tokens: Total tokens (input + output).
        models_used: Set of model names used in session.
        tools_used: Set of tool names used in session.
        tool_invocations: Total number of tool invocations.
    """

    session_id: str
    start_time: str | None
    end_time: str | None
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    models_used: frozenset[str]
    tools_used: frozenset[str]
    tool_invocations: int

    @property
    def cache_efficiency(self) -> float:
        """Calculate cache efficiency as ratio of cache reads to total input.

        Returns:
            Cache efficiency ratio (0.0 to 1.0), or 0.0 if no input tokens.
        """
        total_input = (
            self.cache_read_tokens + self.cache_creation_tokens + self.input_tokens
        )
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input


@dataclass(frozen=True, slots=True)
class DailyUsage:
    """Token usage statistics aggregated by day (UTC).

    Attributes:
        date: Date string (YYYY-MM-DD) in UTC.
        input_tokens: Total input tokens for the day.
        output_tokens: Total output tokens for the day.
        cache_creation_tokens: Total cache creation tokens.
        cache_read_tokens: Total cache read tokens.
        total_tokens: Total tokens (input + output).
        session_count: Number of sessions.
        models_used: Set of model names used.
    """

    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    session_count: int
    models_used: frozenset[str]

    @property
    def cache_efficiency(self) -> float:
        """Calculate cache efficiency."""
        total_input = (
            self.cache_read_tokens + self.cache_creation_tokens + self.input_tokens
        )
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input


@dataclass(frozen=True, slots=True)
class WeeklyUsage:
    """Token usage statistics aggregated by week (UTC Monday boundaries).

    Attributes:
        week_start: Week start date string (YYYY-MM-DD, Monday) in UTC.
        week_end: Week end date string (YYYY-MM-DD, Sunday) in UTC.
        input_tokens: Total input tokens for the week.
        output_tokens: Total output tokens for the week.
        cache_creation_tokens: Total cache creation tokens.
        cache_read_tokens: Total cache read tokens.
        total_tokens: Total tokens (input + output).
        session_count: Number of sessions.
        day_count: Number of active days.
        models_used: Set of model names used.
    """

    week_start: str
    week_end: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    session_count: int
    day_count: int
    models_used: frozenset[str]

    @property
    def cache_efficiency(self) -> float:
        """Calculate cache efficiency."""
        total_input = (
            self.cache_read_tokens + self.cache_creation_tokens + self.input_tokens
        )
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input


@dataclass(frozen=True, slots=True)
class ToolStats:
    """Statistics for a single tool.

    Attributes:
        invocations: Number of times the tool was invoked.
        output_tokens: Output tokens used to generate tool calls.
    """

    invocations: int
    output_tokens: int


@dataclass(slots=True)
class UsageAnalysis:
    """Complete usage analysis results.

    Attributes:
        transcript_dir: Source transcript directory info.
        sessions: Per-session usage statistics.
        daily: Daily aggregated usage.
        weekly: Weekly aggregated usage.
        model_breakdown: Token usage by model.
        tool_breakdown: Invocation counts and token usage by tool.
        bash_breakdown: Breakdown of Bash tool by command.
        file_breakdown: Breakdown of file tools (Read/Write/Edit) by path.
        agent_breakdown: Breakdown of Task tool by agent type.
        hourly_distribution: Token usage by hour of day (0-23 UTC).
        total_input_tokens: Grand total input tokens.
        total_output_tokens: Grand total output tokens.
        total_cache_creation: Grand total cache creation tokens.
        total_cache_read: Grand total cache read tokens.
        time_range_start: Earliest timestamp.
        time_range_end: Latest timestamp.
    """

    transcript_dir: TranscriptDirectory
    sessions: list[SessionUsage] = field(default_factory=list)
    daily: list[DailyUsage] = field(default_factory=list)
    weekly: list[WeeklyUsage] = field(default_factory=list)
    model_breakdown: dict[str, int] = field(default_factory=dict)
    tool_breakdown: dict[str, ToolStats] = field(default_factory=dict)
    bash_breakdown: dict[str, ToolStats] = field(default_factory=dict)
    file_breakdown: dict[str, ToolStats] = field(default_factory=dict)
    agent_breakdown: dict[str, ToolStats] = field(default_factory=dict)
    hourly_distribution: dict[int, int] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation: int = 0
    total_cache_read: int = 0
    time_range_start: str | None = None
    time_range_end: str | None = None

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def overall_cache_efficiency(self) -> float:
        """Overall cache efficiency."""
        total_input = (
            self.total_cache_read + self.total_cache_creation + self.total_input_tokens
        )
        if total_input == 0:
            return 0.0
        return self.total_cache_read / total_input


def parse_since_filter(since: str) -> pendulum.DateTime:
    """Parse a --since filter value into a datetime.

    Supports:
    - Relative: 7d, 30d, 1w, 2w, 1m
    - Absolute: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS

    Args:
        since: Filter string.

    Returns:
        DateTime in UTC.

    Raises:
        ValueError: If the filter string is invalid.
    """
    original_since = since
    since = since.strip().lower()

    # Relative time patterns
    try:
        if since.endswith("d"):
            days = int(since[:-1])
            return pendulum.now("UTC").subtract(days=days)
        if since.endswith("w"):
            weeks = int(since[:-1])
            return pendulum.now("UTC").subtract(weeks=weeks)
        if since.endswith("m"):
            months = int(since[:-1])
            return pendulum.now("UTC").subtract(months=months)
    except ValueError:
        msg = f"Invalid --since value: {original_since}. Use 7d, 2w, 1m or YYYY-MM-DD format."
        raise ValueError(msg) from None

    # Absolute date/datetime
    try:
        dt = pendulum.parse(since, tz="UTC")
        if not isinstance(dt, pendulum.DateTime):
            msg = f"Invalid date format: {since}"
            raise ValueError(msg)
        return dt
    except Exception as e:
        msg = f"Invalid --since value: {original_since}. Use 7d, 2w, 1m or YYYY-MM-DD format."
        raise ValueError(msg) from e


def analyze_usage(
    transcript_dir: TranscriptDirectory,
    *,
    since: pendulum.DateTime | None = None,
) -> UsageAnalysis:
    """Analyze token usage from transcript files.

    Args:
        transcript_dir: Discovered transcript directory.
        since: Optional filter to only include sessions since this time.

    Returns:
        Complete usage analysis results.
    """
    analysis = UsageAnalysis(transcript_dir=transcript_dir)

    # Load usage data (extracts from each file individually to avoid schema conflicts)
    usage_df = load_usage_data(transcript_dir, include_agents=True)
    if usage_df.height == 0:
        return analysis

    # Apply time filter if specified
    if since is not None:
        since_str = since.to_iso8601_string()
        usage_df = usage_df.filter(pl.col("timestamp") >= since_str)
        if usage_df.height == 0:
            return analysis

    # Load tool usage data
    tool_df = load_tool_data(transcript_dir, include_agents=True)
    if since is not None and tool_df.height > 0:
        since_str = since.to_iso8601_string()
        tool_df = tool_df.filter(pl.col("timestamp") >= since_str)

    # Compute per-session statistics
    analysis.sessions = _compute_session_stats(usage_df, tool_df)

    # Compute daily aggregates
    analysis.daily = _compute_daily_stats(usage_df)

    # Compute weekly aggregates
    analysis.weekly = _compute_weekly_stats(usage_df)

    # Compute model breakdown
    analysis.model_breakdown = _compute_model_breakdown(usage_df)

    # Compute tool breakdown
    if tool_df.height > 0:
        analysis.tool_breakdown = _compute_tool_breakdown(tool_df)
        analysis.bash_breakdown = _compute_detail_breakdown(tool_df, "Bash")
        analysis.file_breakdown = _compute_detail_breakdown(
            tool_df, ("Read", "Write", "Edit")
        )
        analysis.agent_breakdown = _compute_detail_breakdown(tool_df, "Task")

    # Compute hourly distribution
    analysis.hourly_distribution = _compute_hourly_distribution(usage_df)

    # Compute totals
    analysis.total_input_tokens = int(usage_df["input_tokens"].sum() or 0)
    analysis.total_output_tokens = int(usage_df["output_tokens"].sum() or 0)
    analysis.total_cache_creation = int(
        usage_df["cache_creation_input_tokens"].sum() or 0
    )
    analysis.total_cache_read = int(usage_df["cache_read_input_tokens"].sum() or 0)

    # Time range
    timestamps = usage_df.select("timestamp").to_series()
    if timestamps.len() > 0:
        analysis.time_range_start = str(timestamps.min())
        analysis.time_range_end = str(timestamps.max())

    return analysis


def _compute_session_stats(
    usage_df: pl.DataFrame,
    tool_df: pl.DataFrame,
) -> list[SessionUsage]:
    """Compute per-session statistics."""
    if "session_id" not in usage_df.columns:
        return []

    sessions: list[SessionUsage] = []

    # Group by session
    session_groups = usage_df.group_by("session_id").agg(
        [
            pl.col("timestamp").min().alias("start_time"),
            pl.col("timestamp").max().alias("end_time"),
            pl.col("input_tokens").sum().alias("input_tokens"),
            pl.col("output_tokens").sum().alias("output_tokens"),
            pl.col("cache_creation_input_tokens").sum().alias("cache_creation_tokens"),
            pl.col("cache_read_input_tokens").sum().alias("cache_read_tokens"),
            pl.col("model").drop_nulls().unique().alias("models_used"),
        ]
    )

    # Get tool usage per session if available
    tool_by_session: dict[str, tuple[set[str], int]] = {}
    if tool_df.height > 0 and "session_id" in tool_df.columns:
        tool_groups = tool_df.group_by("session_id").agg(
            [
                pl.col("tool_name").drop_nulls().unique().alias("tools_used"),
                pl.col("tool_name").count().alias("tool_invocations"),
            ]
        )
        for row in tool_groups.iter_rows(named=True):
            sid = str(row["session_id"])
            tools = set(row["tools_used"]) if row["tools_used"] else set()
            count = int(row["tool_invocations"]) if row["tool_invocations"] else 0
            tool_by_session[sid] = (tools, count)

    for row in session_groups.iter_rows(named=True):
        session_id = str(row["session_id"])
        tools_used, tool_invocations = tool_by_session.get(session_id, (set(), 0))
        models = set(row["models_used"]) if row["models_used"] else set()

        input_tokens = int(row["input_tokens"] or 0)
        output_tokens = int(row["output_tokens"] or 0)

        sessions.append(
            SessionUsage(
                session_id=session_id,
                start_time=str(row["start_time"]) if row["start_time"] else None,
                end_time=str(row["end_time"]) if row["end_time"] else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=int(row["cache_creation_tokens"] or 0),
                cache_read_tokens=int(row["cache_read_tokens"] or 0),
                total_tokens=input_tokens + output_tokens,
                models_used=frozenset(models),
                tools_used=frozenset(tools_used),
                tool_invocations=tool_invocations,
            )
        )

    # Sort by start time (most recent first)
    sessions.sort(key=lambda s: s.start_time or "", reverse=True)
    return sessions


def _compute_daily_stats(usage_df: pl.DataFrame) -> list[DailyUsage]:
    """Compute daily aggregated statistics."""
    if "timestamp" not in usage_df.columns:
        return []

    # Add date column (UTC)
    df_with_date = usage_df.with_columns(
        pl.col("timestamp").str.slice(0, 10).alias("date")
    )

    daily_groups = df_with_date.group_by("date").agg(
        [
            pl.col("input_tokens").sum().alias("input_tokens"),
            pl.col("output_tokens").sum().alias("output_tokens"),
            pl.col("cache_creation_input_tokens").sum().alias("cache_creation_tokens"),
            pl.col("cache_read_input_tokens").sum().alias("cache_read_tokens"),
            pl.col("session_id").n_unique().alias("session_count"),
            pl.col("model").drop_nulls().unique().alias("models_used"),
        ]
    )

    daily: list[DailyUsage] = []
    for row in daily_groups.iter_rows(named=True):
        input_tokens = int(row["input_tokens"] or 0)
        output_tokens = int(row["output_tokens"] or 0)
        models = set(row["models_used"]) if row["models_used"] else set()

        daily.append(
            DailyUsage(
                date=str(row["date"]),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=int(row["cache_creation_tokens"] or 0),
                cache_read_tokens=int(row["cache_read_tokens"] or 0),
                total_tokens=input_tokens + output_tokens,
                session_count=int(row["session_count"] or 0),
                models_used=frozenset(models),
            )
        )

    # Sort by date (most recent first)
    daily.sort(key=lambda d: d.date, reverse=True)
    return daily


def _compute_weekly_stats(usage_df: pl.DataFrame) -> list[WeeklyUsage]:
    """Compute weekly aggregated statistics (UTC Monday boundaries)."""
    if "timestamp" not in usage_df.columns:
        return []

    # Parse timestamp and compute week start (Monday)
    # ISO week starts on Monday
    # Use format string with %+" for ISO 8601 with timezone
    df_with_week = usage_df.with_columns(
        [
            pl.col("timestamp").str.slice(0, 10).alias("date"),
            pl.col("timestamp")
            .str.to_datetime(format="%+", time_zone="UTC")
            .dt.truncate("1w")
            .dt.strftime("%Y-%m-%d")
            .alias("week_start"),
        ]
    )

    weekly_groups = df_with_week.group_by("week_start").agg(
        [
            pl.col("input_tokens").sum().alias("input_tokens"),
            pl.col("output_tokens").sum().alias("output_tokens"),
            pl.col("cache_creation_input_tokens").sum().alias("cache_creation_tokens"),
            pl.col("cache_read_input_tokens").sum().alias("cache_read_tokens"),
            pl.col("session_id").n_unique().alias("session_count"),
            pl.col("date").n_unique().alias("day_count"),
            pl.col("model").drop_nulls().unique().alias("models_used"),
        ]
    )

    weekly: list[WeeklyUsage] = []
    for row in weekly_groups.iter_rows(named=True):
        input_tokens = int(row["input_tokens"] or 0)
        output_tokens = int(row["output_tokens"] or 0)
        models = set(row["models_used"]) if row["models_used"] else set()
        week_start = str(row["week_start"])

        # Compute week end (Sunday = week_start + 6 days)
        week_start_dt = pendulum.parse(week_start)
        if isinstance(week_start_dt, pendulum.DateTime):
            week_end = week_start_dt.add(days=6).format("YYYY-MM-DD")
        else:
            week_end = week_start

        weekly.append(
            WeeklyUsage(
                week_start=week_start,
                week_end=week_end,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=int(row["cache_creation_tokens"] or 0),
                cache_read_tokens=int(row["cache_read_tokens"] or 0),
                total_tokens=input_tokens + output_tokens,
                session_count=int(row["session_count"] or 0),
                day_count=int(row["day_count"] or 0),
                models_used=frozenset(models),
            )
        )

    # Sort by week start (most recent first)
    weekly.sort(key=lambda w: w.week_start, reverse=True)
    return weekly


def _compute_model_breakdown(usage_df: pl.DataFrame) -> dict[str, int]:
    """Compute token usage breakdown by model."""
    if "model" not in usage_df.columns:
        return {}

    model_groups = (
        usage_df.filter(pl.col("model").is_not_null())
        .group_by("model")
        .agg(
            (pl.col("input_tokens") + pl.col("output_tokens"))
            .sum()
            .alias("total_tokens")
        )
        .sort("total_tokens", descending=True)
    )

    return {
        str(row["model"]): int(row["total_tokens"] or 0)
        for row in model_groups.iter_rows(named=True)
    }


def _compute_tool_breakdown(tool_df: pl.DataFrame) -> dict[str, ToolStats]:
    """Compute tool invocation counts and token usage."""
    if "tool_name" not in tool_df.columns:
        return {}

    # Check if output_tokens column exists
    has_tokens = "output_tokens" in tool_df.columns

    if has_tokens:
        tool_groups = (
            tool_df.filter(pl.col("tool_name").is_not_null())
            .group_by("tool_name")
            .agg(
                [
                    pl.len().alias("invocations"),
                    pl.col("output_tokens").sum().alias("output_tokens"),
                ]
            )
            .sort("output_tokens", descending=True)
        )

        return {
            str(row["tool_name"]): ToolStats(
                invocations=int(row["invocations"]),
                output_tokens=int(row["output_tokens"] or 0),
            )
            for row in tool_groups.iter_rows(named=True)
        }

    # Fallback: just count invocations
    tool_groups = (
        tool_df.filter(pl.col("tool_name").is_not_null())
        .group_by("tool_name")
        .len()
        .sort("len", descending=True)
    )

    return {
        str(row["tool_name"]): ToolStats(invocations=int(row["len"]), output_tokens=0)
        for row in tool_groups.iter_rows(named=True)
    }


def _compute_detail_breakdown(
    tool_df: pl.DataFrame,
    tool_filter: str | tuple[str, ...],
) -> dict[str, ToolStats]:
    """Compute breakdown by tool_detail for specific tools.

    Args:
        tool_df: DataFrame with tool usage data (must have tool_detail column).
        tool_filter: Tool name(s) to filter by.

    Returns:
        Dictionary mapping detail values to their stats.
    """
    if "tool_name" not in tool_df.columns or "tool_detail" not in tool_df.columns:
        return {}

    # Filter to the specified tool(s)
    if isinstance(tool_filter, str):
        filtered = tool_df.filter(pl.col("tool_name") == tool_filter)
    else:
        filtered = tool_df.filter(pl.col("tool_name").is_in(list(tool_filter)))

    # Further filter to rows with detail
    filtered = filtered.filter(pl.col("tool_detail").is_not_null())

    if filtered.height == 0:
        return {}

    has_tokens = "output_tokens" in filtered.columns

    if has_tokens:
        groups = (
            filtered.group_by("tool_detail")
            .agg(
                [
                    pl.len().alias("invocations"),
                    pl.col("output_tokens").sum().alias("output_tokens"),
                ]
            )
            .sort("output_tokens", descending=True)
        )

        return {
            str(row["tool_detail"]): ToolStats(
                invocations=int(row["invocations"]),
                output_tokens=int(row["output_tokens"] or 0),
            )
            for row in groups.iter_rows(named=True)
        }

    groups = filtered.group_by("tool_detail").len().sort("len", descending=True)

    return {
        str(row["tool_detail"]): ToolStats(invocations=int(row["len"]), output_tokens=0)
        for row in groups.iter_rows(named=True)
    }


def _compute_hourly_distribution(usage_df: pl.DataFrame) -> dict[int, int]:
    """Compute token usage by hour of day (0-23 UTC)."""
    if "timestamp" not in usage_df.columns:
        return {}

    df_with_hour = usage_df.with_columns(
        pl.col("timestamp").str.slice(11, 2).cast(pl.Int64).alias("hour")
    )

    hourly_groups = df_with_hour.group_by("hour").agg(
        (pl.col("input_tokens") + pl.col("output_tokens")).sum().alias("total_tokens")
    )

    result: dict[int, int] = {}
    for row in hourly_groups.iter_rows(named=True):
        if row["hour"] is not None:
            result[int(row["hour"])] = int(row["total_tokens"] or 0)

    return result


def _format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def _render_rich_output(analysis: UsageAnalysis, console: Console) -> None:
    """Render analysis results using Rich for terminal output."""
    console.print()
    console.print("[bold blue]Claude Code Usage Analysis[/bold blue]")
    console.print()

    # Overview
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", width=24)
    table.add_column("Value", justify="right")

    if analysis.time_range_start and analysis.time_range_end:
        table.add_row("Time Range", analysis.time_range_start[:10])
        table.add_row("", f"to {analysis.time_range_end[:10]}")
        table.add_row("", "")

    table.add_row("[bold cyan]Token Usage[/bold cyan]", "")
    table.add_row("  Input Tokens", _format_tokens(analysis.total_input_tokens))
    table.add_row("  Output Tokens", _format_tokens(analysis.total_output_tokens))
    table.add_row(
        "  [bold]Total Tokens[/bold]",
        f"[bold]{_format_tokens(analysis.total_tokens)}[/bold]",
    )
    table.add_row("", "")

    table.add_row("[bold cyan]Cache Performance[/bold cyan]", "")
    table.add_row("  Cache Creation", _format_tokens(analysis.total_cache_creation))
    table.add_row("  Cache Read", _format_tokens(analysis.total_cache_read))
    efficiency_pct = analysis.overall_cache_efficiency * 100
    efficiency_color = (
        "green" if efficiency_pct >= 50 else "yellow" if efficiency_pct >= 25 else "red"
    )
    table.add_row(
        "  Cache Efficiency",
        f"[{efficiency_color}]{efficiency_pct:.1f}%[/{efficiency_color}]",
    )
    table.add_row("", "")

    table.add_row("[bold cyan]Sessions[/bold cyan]", "")
    table.add_row("  Total Sessions", str(len(analysis.sessions)))
    table.add_row("  Days Active", str(len(analysis.daily)))
    table.add_row("  Weeks Active", str(len(analysis.weekly)))

    console.print(table)
    console.print()

    # Model breakdown
    if analysis.model_breakdown:
        console.print("[bold cyan]Token Usage by Model[/bold cyan]")
        model_table = Table(show_header=True, box=None, padding=(0, 2))
        model_table.add_column("Model", width=30)
        model_table.add_column("Tokens", justify="right")
        model_table.add_column("Share", justify="right")

        total = analysis.total_tokens or 1
        for model, tokens in list(analysis.model_breakdown.items())[:10]:
            display_name = MODEL_DISPLAY_NAMES.get(model, model)
            share = (tokens / total) * 100
            model_table.add_row(display_name, _format_tokens(tokens), f"{share:.1f}%")

        console.print(model_table)
        console.print()

    # Tool breakdown
    if analysis.tool_breakdown:
        console.print("[bold cyan]Tool Usage (Top 10)[/bold cyan]")
        tool_table = Table(show_header=True, box=None, padding=(0, 2))
        tool_table.add_column("Tool", width=30)
        tool_table.add_column("Invocations", justify="right")
        tool_table.add_column("Tokens", justify="right")

        for tool, stats in list(analysis.tool_breakdown.items())[:10]:
            tool_table.add_row(
                tool, f"{stats.invocations:,}", _format_tokens(stats.output_tokens)
            )

        console.print(tool_table)
        console.print()

    # Bash command breakdown
    if analysis.bash_breakdown:
        console.print("[bold cyan]Bash Commands (Top 10)[/bold cyan]")
        bash_table = Table(show_header=True, box=None, padding=(0, 2))
        bash_table.add_column("Command", width=30)
        bash_table.add_column("Invocations", justify="right")
        bash_table.add_column("Tokens", justify="right")

        for cmd, stats in list(analysis.bash_breakdown.items())[:10]:
            bash_table.add_row(
                cmd, f"{stats.invocations:,}", _format_tokens(stats.output_tokens)
            )

        console.print(bash_table)
        console.print()

    # File operations breakdown
    if analysis.file_breakdown:
        console.print("[bold cyan]File Operations (Top 10)[/bold cyan]")
        file_table = Table(show_header=True, box=None, padding=(0, 2))
        file_table.add_column("Path", width=50)
        file_table.add_column("Ops", justify="right")
        file_table.add_column("Tokens", justify="right")

        for path, stats in list(analysis.file_breakdown.items())[:10]:
            # Truncate long paths
            display_path = path if len(path) <= 50 else "..." + path[-47:]
            file_table.add_row(
                display_path,
                f"{stats.invocations:,}",
                _format_tokens(stats.output_tokens),
            )

        console.print(file_table)
        console.print()

    # Agent breakdown
    if analysis.agent_breakdown:
        console.print("[bold cyan]Agent Usage (Task Tool)[/bold cyan]")
        agent_table = Table(show_header=True, box=None, padding=(0, 2))
        agent_table.add_column("Agent Type", width=40)
        agent_table.add_column("Invocations", justify="right")
        agent_table.add_column("Tokens", justify="right")

        for agent, stats in list(analysis.agent_breakdown.items())[:10]:
            agent_table.add_row(
                agent, f"{stats.invocations:,}", _format_tokens(stats.output_tokens)
            )

        console.print(agent_table)
        console.print()

    # Weekly summary
    if analysis.weekly:
        console.print("[bold cyan]Weekly Summary (Recent)[/bold cyan]")
        weekly_table = Table(show_header=True, box=None, padding=(0, 2))
        weekly_table.add_column("Week", width=24)
        weekly_table.add_column("Tokens", justify="right")
        weekly_table.add_column("Sessions", justify="right")
        weekly_table.add_column("Days", justify="right")

        for week in analysis.weekly[:4]:
            weekly_table.add_row(
                f"{week.week_start} to {week.week_end}",
                _format_tokens(week.total_tokens),
                str(week.session_count),
                str(week.day_count),
            )

        console.print(weekly_table)
        console.print()


def _write_markdown_report(
    analysis: UsageAnalysis,
    output_dir: Path,
    *,
    chart_format: str = "png",
    has_charts: bool = True,
    has_dashboard: bool = True,
) -> Path:
    """Write markdown report to output directory.

    Args:
        analysis: Usage analysis results.
        output_dir: Output directory path.
        chart_format: Chart image format (png or svg).
        has_charts: Whether static charts were generated.
        has_dashboard: Whether interactive dashboard was generated.

    Returns:
        Path to the generated index.md file.
    """
    report_lines: list[str] = []

    # Generate title with date range for unique nav entries
    generated_at = pendulum.now("UTC")
    if analysis.time_range_start and analysis.time_range_end:
        date_range = (
            f"{analysis.time_range_start[:10]} to {analysis.time_range_end[:10]}"
        )
        title = f"Usage Report: {date_range}"
    else:
        title = f"Usage Report: {generated_at.format('YYYY-MM-DD')}"

    # YAML frontmatter for zensical nav
    report_lines.append("---")
    report_lines.append(f"title: {title}")
    report_lines.append(f"generated: {generated_at.to_iso8601_string()}")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append(f"# {title}")
    report_lines.append("")
    report_lines.append(f"Generated: {generated_at.to_iso8601_string()}")
    report_lines.append("")

    # Summary
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(f"- **Total Tokens**: {_format_tokens(analysis.total_tokens)}")
    report_lines.append(
        f"- **Input Tokens**: {_format_tokens(analysis.total_input_tokens)}"
    )
    report_lines.append(
        f"- **Output Tokens**: {_format_tokens(analysis.total_output_tokens)}"
    )
    report_lines.append(
        f"- **Cache Efficiency**: {analysis.overall_cache_efficiency * 100:.1f}%"
    )
    report_lines.append(f"- **Sessions**: {len(analysis.sessions)}")
    report_lines.append(f"- **Days Active**: {len(analysis.daily)}")
    report_lines.append("")

    # Understanding This Report section
    report_lines.append("## Understanding This Report")
    report_lines.append("")
    report_lines.append(
        "This section explains the metrics and terminology used throughout this report."
    )
    report_lines.append("")

    # Token Usage Metrics
    report_lines.append("### Token Usage Metrics")
    report_lines.append("")
    report_lines.append(
        "Tokens are the fundamental units Claude uses to process text. "
        "Understanding token usage helps you track your Claude Code consumption "
        "and optimize your workflows."
    )
    report_lines.append("")
    report_lines.append(
        "- **Input Tokens**: The context sent to Claude in each request. This includes "
        "your messages, file contents, tool outputs, and system prompts. Larger codebases "
        "and longer conversations consume more input tokens."
    )
    report_lines.append(
        "- **Output Tokens**: Claude's responses, including explanations, generated code, "
        "and tool invocations. Complex tasks requiring detailed responses use more output tokens."
    )
    report_lines.append(
        "- **Total Tokens**: The sum of input and output tokens. This represents your "
        "overall Claude Code usage for the analysis period."
    )
    report_lines.append("")
    report_lines.append(
        "Token counts relate directly to Claude Code usage limits. Subscription plans "
        "have rolling limits based on token consumption within 5-hour windows. High token "
        "usage in a short period may trigger rate limiting."
    )
    report_lines.append("")

    # Cache Performance
    report_lines.append("### Cache Performance")
    report_lines.append("")
    report_lines.append(
        "Claude Code uses prompt caching to improve performance and reduce costs when "
        "the same context is sent repeatedly (common in coding workflows)."
    )
    report_lines.append("")
    report_lines.append(
        "- **Cache Creation Tokens**: Tokens used when content is first added to the cache. "
        "This happens when you start a new conversation or introduce new context."
    )
    report_lines.append(
        "- **Cache Read Tokens**: Tokens retrieved from cache instead of being reprocessed. "
        "Cache reads are faster and more efficient than processing new content."
    )
    report_lines.append(
        "- **Cache Efficiency**: Calculated as `cache_read_tokens / (cache_read_tokens + "
        "cache_creation_tokens + input_tokens)`. Higher percentages indicate better cache "
        "utilization."
    )
    report_lines.append("")
    report_lines.append("**Interpreting Cache Efficiency:**")
    report_lines.append("")
    report_lines.append(
        "- **50%+** (green): Excellent - your workflows effectively reuse context"
    )
    report_lines.append(
        "- **25-50%** (yellow): Good - some optimization opportunities may exist"
    )
    report_lines.append(
        "- **<25%** (red): Low - consider longer sessions or more focused conversations"
    )
    report_lines.append("")
    report_lines.append(
        "Power users can improve cache efficiency by: working in longer sessions, "
        "keeping related tasks in the same conversation, and avoiding frequent context switches."
    )
    report_lines.append("")

    # Session Metrics
    report_lines.append("### Session Metrics")
    report_lines.append("")
    report_lines.append(
        "A **session** in Claude Code represents a continuous conversation thread. "
        "Each time you start a new conversation (via `/clear` or opening a new terminal), "
        "a new session begins."
    )
    report_lines.append("")
    report_lines.append("Sessions are important for understanding your usage patterns:")
    report_lines.append("")
    report_lines.append(
        "- Multiple short sessions typically have lower cache efficiency than fewer longer sessions"
    )
    report_lines.append(
        "- Session boundaries reset the conversation context, requiring cache recreation"
    )
    report_lines.append(
        "- Claude Code's 5-hour rolling limit windows are based on token consumption, not session count"
    )
    report_lines.append("")

    # Time Aggregations
    report_lines.append("### Time Aggregations")
    report_lines.append("")
    report_lines.append(
        "All time-based metrics in this report use UTC (Coordinated Universal Time) "
        "to ensure consistency regardless of your local timezone."
    )
    report_lines.append("")
    report_lines.append(
        "- **Daily Aggregations**: Based on UTC day boundaries (00:00-23:59 UTC). "
        "Your local day may span two UTC days depending on your timezone."
    )
    report_lines.append(
        "- **Weekly Aggregations**: Monday through Sunday in UTC. These align with "
        "Claude Code's usage limit windows, which reset on a rolling basis."
    )
    report_lines.append("")
    report_lines.append(
        "Understanding UTC timing helps when correlating usage spikes with rate limit "
        "events or planning heavy usage periods."
    )
    report_lines.append("")

    # Model Breakdown
    report_lines.append("### Model Breakdown")
    report_lines.append("")
    report_lines.append(
        "Claude Code automatically selects models based on task complexity. "
        "Understanding model usage helps explain token consumption patterns."
    )
    report_lines.append("")
    report_lines.append(
        "- **Opus 4.5**: The most capable model, used for complex reasoning, "
        "architecture decisions, and difficult debugging. Highest token consumption per response."
    )
    report_lines.append(
        "- **Sonnet 4**: Balanced model for general coding tasks, code generation, "
        "and explanations. Good balance of capability and efficiency."
    )
    report_lines.append(
        "- **Haiku 4.5**: Fastest model for simple tasks, quick edits, and "
        "straightforward questions. Most token-efficient for simple operations."
    )
    report_lines.append("")
    report_lines.append(
        "Higher-capability models (Opus) consume more tokens for equivalent tasks but "
        "may require fewer iterations to reach correct solutions."
    )
    report_lines.append("")

    # Tool Usage
    report_lines.append("### Tool Usage")
    report_lines.append("")
    report_lines.append(
        "Claude Code uses tools to interact with your development environment. "
        "Tool invocations contribute to both input tokens (tool definitions, results) "
        "and output tokens (tool calls)."
    )
    report_lines.append("")
    report_lines.append("**Common Tools:**")
    report_lines.append("")
    report_lines.append(
        "- **Read**: Reads file contents into context. Large files increase input tokens significantly."
    )
    report_lines.append(
        "- **Write**: Creates or overwrites files. Token cost scales with file size."
    )
    report_lines.append(
        "- **Edit**: Makes targeted changes to files. More token-efficient than Write for small changes."
    )
    report_lines.append(
        "- **Bash**: Executes shell commands. Command output becomes input tokens."
    )
    report_lines.append(
        "- **Glob/Grep**: File discovery and search. Results add to input token count."
    )
    report_lines.append(
        "- **WebFetch/WebSearch**: Retrieves web content. External content adds to context."
    )
    report_lines.append("- **TodoWrite**: Manages task lists. Minimal token overhead.")
    report_lines.append("")
    report_lines.append(
        "High tool invocation counts often correlate with productive sessions but also "
        "higher token usage. The Edit tool is generally more efficient than Write for "
        "iterative changes."
    )
    report_lines.append("")

    # Visualizations Guide (conditional)
    if has_charts:
        report_lines.append("### Visualizations Guide")
        report_lines.append("")
        report_lines.append(
            "The charts in this report provide visual insights into your usage patterns."
        )
        report_lines.append("")
        report_lines.append("**Daily Token Usage Chart:**")
        report_lines.append("")
        report_lines.append(
            "- Shows token consumption over time with input and output tokens stacked"
        )
        report_lines.append(
            "- Spikes indicate heavy usage days; look for patterns (e.g., project deadlines)"
        )
        report_lines.append("- Gaps indicate days with no Claude Code activity")
        report_lines.append("")
        report_lines.append("**Model Distribution Pie Chart:**")
        report_lines.append("")
        report_lines.append("- Shows the proportion of tokens consumed by each model")
        report_lines.append(
            "- Heavy Opus usage suggests complex tasks; heavy Haiku suggests simpler workflows"
        )
        report_lines.append(
            "- An unexpected model distribution may indicate task complexity mismatch"
        )
        report_lines.append("")
        report_lines.append("**Hourly Distribution Chart:**")
        report_lines.append("")
        report_lines.append("- Displays token usage by hour of day (UTC)")
        report_lines.append("- Identifies your peak productivity hours")
        report_lines.append(
            "- Useful for planning heavy usage to avoid rate limits during peak times"
        )
        report_lines.append("")
        report_lines.append("**Weekly Trends Chart:**")
        report_lines.append("")
        report_lines.append("- Shows week-over-week token consumption trends")
        report_lines.append("- Helps identify usage growth or decline over time")
        report_lines.append("- Useful for capacity planning and subscription decisions")
        report_lines.append("")
        report_lines.append("**Cache Efficiency Chart:**")
        report_lines.append("")
        report_lines.append("- Tracks cache efficiency over time")
        report_lines.append(
            "- Declining efficiency may indicate workflow changes or more context switching"
        )
        report_lines.append("- Improving efficiency suggests optimized usage patterns")
        report_lines.append("")
        report_lines.append("**Tool Usage Chart:**")
        report_lines.append("")
        report_lines.append("- Ranks tools by invocation count")
        report_lines.append("- High Read counts suggest exploration-heavy work")
        report_lines.append("- High Edit/Write counts indicate active development")
        report_lines.append("")

    # Charts section
    if has_charts:
        report_lines.append("## Visualizations")
        report_lines.append("")
        report_lines.append(f"![Daily Token Usage](charts/daily_usage.{chart_format})")
        report_lines.append("")
        report_lines.append(
            f"![Model Distribution](charts/model_distribution.{chart_format})"
        )
        report_lines.append("")
        report_lines.append(f"![Tool Usage](charts/tool_usage.{chart_format})")
        report_lines.append("")
        report_lines.append(
            f"![Cache Efficiency](charts/cache_efficiency.{chart_format})"
        )
        report_lines.append("")
        report_lines.append(
            f"![Hourly Distribution](charts/hourly_distribution.{chart_format})"
        )
        report_lines.append("")
        report_lines.append(f"![Weekly Trends](charts/weekly_trends.{chart_format})")
        report_lines.append("")

    # Interactive dashboard link
    if has_dashboard:
        report_lines.append("## Interactive Dashboard")
        report_lines.append("")
        report_lines.append(
            "Open [dashboard.html](dashboard.html) in a browser for interactive exploration."
        )
        report_lines.append("")

    # Model breakdown table
    if analysis.model_breakdown:
        report_lines.append("## Token Usage by Model")
        report_lines.append("")
        report_lines.append("| Model | Tokens | Share |")
        report_lines.append("|-------|--------|-------|")
        total = analysis.total_tokens or 1
        for model, tokens in analysis.model_breakdown.items():
            display_name = MODEL_DISPLAY_NAMES.get(model, model)
            share = (tokens / total) * 100
            report_lines.append(
                f"| {display_name} | {_format_tokens(tokens)} | {share:.1f}% |"
            )
        report_lines.append("")

    # Tool breakdown table
    if analysis.tool_breakdown:
        report_lines.append("## Tool Usage")
        report_lines.append("")
        report_lines.append("| Tool | Invocations | Output Tokens |")
        report_lines.append("|------|-------------|---------------|")
        for tool, stats in list(analysis.tool_breakdown.items())[:20]:
            report_lines.append(
                f"| {tool} | {stats.invocations:,} | {_format_tokens(stats.output_tokens)} |"
            )
        report_lines.append("")

    # Bash commands breakdown
    if analysis.bash_breakdown:
        report_lines.append("### Bash Commands (Top 15)")
        report_lines.append("")
        report_lines.append("| Command | Invocations | Tokens |")
        report_lines.append("|---------|-------------|--------|")
        for cmd, stats in list(analysis.bash_breakdown.items())[:15]:
            report_lines.append(
                f"| {cmd} | {stats.invocations:,} | {_format_tokens(stats.output_tokens)} |"
            )
        report_lines.append("")

    # File operations breakdown
    if analysis.file_breakdown:
        report_lines.append("### File Operations (Top 15)")
        report_lines.append("")
        report_lines.append("| Path | Operations | Tokens |")
        report_lines.append("|------|------------|--------|")
        for path, stats in list(analysis.file_breakdown.items())[:15]:
            # Escape pipes in paths for markdown
            display_path = path.replace("|", "\\|")
            report_lines.append(
                f"| `{display_path}` | {stats.invocations:,} | {_format_tokens(stats.output_tokens)} |"
            )
        report_lines.append("")

    # Agent breakdown
    if analysis.agent_breakdown:
        report_lines.append("### Agent Usage (Task Tool)")
        report_lines.append("")
        report_lines.append("| Agent Type | Invocations | Tokens |")
        report_lines.append("|------------|-------------|--------|")
        for agent, stats in list(analysis.agent_breakdown.items())[:15]:
            report_lines.append(
                f"| {agent} | {stats.invocations:,} | {_format_tokens(stats.output_tokens)} |"
            )
        report_lines.append("")

    # Weekly summary table
    if analysis.weekly:
        report_lines.append("## Weekly Summary")
        report_lines.append("")
        report_lines.append("| Week | Tokens | Sessions | Days | Cache Eff |")
        report_lines.append("|------|--------|----------|------|-----------|")
        for week in analysis.weekly[:8]:
            report_lines.append(
                f"| {week.week_start} | {_format_tokens(week.total_tokens)} | "
                f"{week.session_count} | {week.day_count} | {week.cache_efficiency * 100:.1f}% |"
            )
        report_lines.append("")

    # Data exports section
    report_lines.append("## Data Exports")
    report_lines.append("")
    report_lines.append("Parquet files for further analysis:")
    report_lines.append("")
    report_lines.append("- `data/sessions.parquet` - Per-session statistics")
    report_lines.append("- `data/daily.parquet` - Daily aggregates")
    report_lines.append("- `data/weekly.parquet` - Weekly aggregates")
    report_lines.append("")

    # Write the file
    index_path = output_dir / "index.md"
    index_path.write_text("\n".join(report_lines))
    return index_path


def _export_parquet_files(analysis: UsageAnalysis, output_dir: Path) -> None:
    """Export analysis data to parquet files.

    Args:
        analysis: Usage analysis results.
        output_dir: Output directory path (data/ subdirectory will be created).
    """
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Sessions parquet
    if analysis.sessions:
        sessions_data = {
            "session_id": [s.session_id for s in analysis.sessions],
            "start_time": [s.start_time for s in analysis.sessions],
            "end_time": [s.end_time for s in analysis.sessions],
            "input_tokens": [s.input_tokens for s in analysis.sessions],
            "output_tokens": [s.output_tokens for s in analysis.sessions],
            "cache_creation_tokens": [
                s.cache_creation_tokens for s in analysis.sessions
            ],
            "cache_read_tokens": [s.cache_read_tokens for s in analysis.sessions],
            "total_tokens": [s.total_tokens for s in analysis.sessions],
            "cache_efficiency": [s.cache_efficiency for s in analysis.sessions],
            "tool_invocations": [s.tool_invocations for s in analysis.sessions],
        }
        sessions_df = pl.DataFrame(sessions_data)
        sessions_df.write_parquet(data_dir / "sessions.parquet")

    # Daily parquet
    if analysis.daily:
        daily_data = {
            "date": [d.date for d in analysis.daily],
            "input_tokens": [d.input_tokens for d in analysis.daily],
            "output_tokens": [d.output_tokens for d in analysis.daily],
            "cache_creation_tokens": [d.cache_creation_tokens for d in analysis.daily],
            "cache_read_tokens": [d.cache_read_tokens for d in analysis.daily],
            "total_tokens": [d.total_tokens for d in analysis.daily],
            "session_count": [d.session_count for d in analysis.daily],
            "cache_efficiency": [d.cache_efficiency for d in analysis.daily],
        }
        daily_df = pl.DataFrame(daily_data)
        daily_df.write_parquet(data_dir / "daily.parquet")

    # Weekly parquet
    if analysis.weekly:
        weekly_data = {
            "week_start": [w.week_start for w in analysis.weekly],
            "week_end": [w.week_end for w in analysis.weekly],
            "input_tokens": [w.input_tokens for w in analysis.weekly],
            "output_tokens": [w.output_tokens for w in analysis.weekly],
            "cache_creation_tokens": [w.cache_creation_tokens for w in analysis.weekly],
            "cache_read_tokens": [w.cache_read_tokens for w in analysis.weekly],
            "total_tokens": [w.total_tokens for w in analysis.weekly],
            "session_count": [w.session_count for w in analysis.weekly],
            "day_count": [w.day_count for w in analysis.weekly],
            "cache_efficiency": [w.cache_efficiency for w in analysis.weekly],
        }
        weekly_df = pl.DataFrame(weekly_data)
        weekly_df.write_parquet(data_dir / "weekly.parquet")


@app.command(name="usage")
def usage(
    *,
    transcript_dir: Annotated[
        Path | None,
        Parameter(
            name=["--transcript-dir", "-t"],
            help="Override transcript directory (default: auto-discover from project)",
        ),
    ] = None,
    since: Annotated[
        str | None,
        Parameter(
            name=["--since", "-s"],
            help="Filter sessions since (e.g., 7d, 2w, 1m, 2024-12-01)",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        Parameter(
            name=["--output", "-o"],
            help="Output directory for reports (default: .oaps/docs/reports/usage/<timestamp>)",
        ),
    ] = None,
    format: Annotated[
        str,
        Parameter(
            name=["--format", "-f"],
            help="Chart format: png, svg",
        ),
    ] = "png",
    no_interactive: Annotated[
        bool,
        Parameter(
            name=["--no-interactive"],
            help="Skip Bokeh interactive dashboard generation",
        ),
    ] = False,
    no_charts: Annotated[
        bool,
        Parameter(
            name=["--no-charts"],
            help="Skip static chart generation",
        ),
    ] = False,
    no_parquet: Annotated[
        bool,
        Parameter(
            name=["--no-parquet"],
            help="Skip parquet data export",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        Parameter(
            name=["--quiet", "-q"],
            help="Suppress terminal output (only generate files)",
        ),
    ] = False,
) -> None:
    """Analyze Claude Code token usage from transcript files.

    Discovers transcript files from the Claude Code projects directory,
    extracts token usage data, and generates reports with visualizations.

    Examples:
        oaps analyze usage                    # Analyze all available transcripts
        oaps analyze usage --since 7d         # Last 7 days only
        oaps analyze usage --since 2024-12-01 # Since specific date
        oaps analyze usage --no-charts        # Skip chart generation
        oaps analyze usage -o ./my-report     # Custom output directory

    Exit codes:
        0: Analysis completed successfully
        1: Failed to load or parse transcript files
        3: Transcript directory not found
        4: Failed to write output files
    """
    console = Console()

    # Determine project root
    try:
        project_root = get_worktree_root()
    except Exception:
        console.print("[red]Error:[/red] Could not determine project root.")
        raise SystemExit(EXIT_NOT_FOUND) from None

    # Discover transcript directory
    transcript_directory = discover_transcript_directory(
        project_root,
        transcript_dir_override=transcript_dir,
    )

    if transcript_directory is None:
        if transcript_dir:
            console.print(
                f"[red]Error:[/red] Transcript directory not found: {transcript_dir}"
            )
        else:
            expected = project_root.as_posix().replace("/", "-")
            console.print(
                f"[red]Error:[/red] No transcript directory found for this project.\n"
                f"Expected: ~/.claude/projects/{expected}/"
            )
        raise SystemExit(EXIT_NOT_FOUND)

    if transcript_directory.total_files == 0:
        console.print("[yellow]No transcript files found.[/yellow]")
        raise SystemExit(EXIT_SUCCESS)

    if not quiet:
        console.print(
            f"[dim]Found {transcript_directory.total_files} transcript file(s)[/dim]"
        )

    # Parse since filter
    since_dt: pendulum.DateTime | None = None
    if since:
        try:
            since_dt = parse_since_filter(since)
            if not quiet:
                console.print(
                    f"[dim]Filtering to sessions since {since_dt.to_date_string()}[/dim]"
                )
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(EXIT_LOAD_ERROR) from None

    # Run analysis
    try:
        analysis = analyze_usage(transcript_directory, since=since_dt)
    except Exception as e:
        console.print(f"[red]Error analyzing transcripts:[/red] {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    if not analysis.sessions:
        console.print("[yellow]No usage data found in transcripts.[/yellow]")
        raise SystemExit(EXIT_SUCCESS)

    # Display terminal output
    if not quiet:
        _render_rich_output(analysis, console)

    # Determine output directory
    if output_dir is None:
        timestamp = pendulum.now("UTC").format("YYYYMMDD-HHmmss")
        output_dir = get_oaps_dir() / "docs" / "reports" / "usage" / timestamp

    # Create output directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console.print(f"[red]Error creating output directory:[/red] {e}")
        raise SystemExit(EXIT_OUTPUT_ERROR) from None

    # Generate visualizations
    has_charts = False
    has_dashboard = False

    if not no_charts:
        try:
            from ._viz import generate_static_charts

            charts_dir = output_dir / "charts"
            charts_dir.mkdir(parents=True, exist_ok=True)
            generate_static_charts(analysis, charts_dir, chart_format=format)
            has_charts = True
            if not quiet:
                console.print(f"[green]Generated static charts:[/green] {charts_dir}")
        except ImportError:
            if not quiet:
                console.print(
                    "[yellow]Warning:[/yellow] matplotlib/seaborn not available, skipping charts"
                )
        except Exception as e:
            if not quiet:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to generate charts: {e}"
                )

    if not no_interactive:
        try:
            from ._viz import generate_bokeh_dashboard

            dashboard_path = output_dir / "dashboard.html"
            generate_bokeh_dashboard(analysis, dashboard_path)
            has_dashboard = True
            if not quiet:
                console.print(
                    f"[green]Generated interactive dashboard:[/green] {dashboard_path}"
                )
        except ImportError:
            if not quiet:
                console.print(
                    "[yellow]Warning:[/yellow] bokeh not available, skipping dashboard"
                )
        except Exception as e:
            if not quiet:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to generate dashboard: {e}"
                )

    # Export parquet files
    if not no_parquet:
        try:
            _export_parquet_files(analysis, output_dir)
            if not quiet:
                console.print(
                    f"[green]Exported parquet files:[/green] {output_dir}/data/"
                )
        except Exception as e:
            if not quiet:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to export parquet: {e}"
                )

    # Write markdown report
    try:
        report_path = _write_markdown_report(
            analysis,
            output_dir,
            chart_format=format,
            has_charts=has_charts,
            has_dashboard=has_dashboard,
        )
        if not quiet:
            console.print(f"[green]Generated report:[/green] {report_path}")
    except Exception as e:
        console.print(f"[red]Error writing report:[/red] {e}")
        raise SystemExit(EXIT_OUTPUT_ERROR) from None

    if not quiet:
        console.print()
        console.print(f"[bold]Report directory:[/bold] {output_dir}")

    raise SystemExit(EXIT_SUCCESS)
