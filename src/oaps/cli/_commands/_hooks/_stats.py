# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false
# ruff: noqa: A002, PLR0912, PLR0915
"""Stats subcommand for hooks - analyze hook log with Polars."""

from dataclasses import dataclass
from typing import Annotated

import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.table import Table

from oaps.cli._commands._context import OutputFormat
from oaps.cli._shared import (
    count_unique_sessions,
    get_time_range,
    normalize_session_ids,
    parse_log_to_dataframe,
)
from oaps.utils import get_oaps_hooks_log_file

from ._app import app
from ._exit_codes import EXIT_LOAD_ERROR, EXIT_SUCCESS

# Health score thresholds
_HEALTH_EXCELLENT = 90
_HEALTH_GOOD = 70
_HEALTH_FAIR = 50
_COMPLETION_RATE_THRESHOLD = 0.95

# Display constants
_SESSION_ID_DISPLAY_LEN = 16
_ERROR_MSG_DISPLAY_LEN = 40


@dataclass(frozen=True, slots=True)
class HookStats:
    """Statistics derived from hook log analysis.

    Attributes:
        total_entries: Total number of log entries.
        total_sessions: Number of unique sessions.
        entries_by_level: Count of entries per log level.
        entries_by_event: Count of entries per event type.
        entries_by_hook_event: Count of entries per hook event type.
        error_count: Number of error-level entries.
        warning_count: Number of warning-level entries.
        blocked_count: Number of hook_blocked events.
        failed_count: Number of hook_failed events.
        completed_count: Number of hook_completed events.
        avg_hooks_per_session: Average number of hook executions per session.
        most_active_sessions: Top sessions by hook count.
        time_range_start: Earliest timestamp in the log.
        time_range_end: Latest timestamp in the log.
        tool_usage: Count of tool usage by tool name (from pre_tool_use events).
        top_errors: Most common error messages with counts.
    """

    total_entries: int
    total_sessions: int
    entries_by_level: dict[str, int]
    entries_by_event: dict[str, int]
    entries_by_hook_event: dict[str, int]
    error_count: int
    warning_count: int
    blocked_count: int
    failed_count: int
    completed_count: int
    avg_hooks_per_session: float
    most_active_sessions: list[tuple[str, int]]
    time_range_start: str | None
    time_range_end: str | None
    tool_usage: dict[str, int]
    top_errors: list[tuple[str, int]]


def _compute_level_counts(df: pl.DataFrame) -> dict[str, int]:
    """Compute entry counts by log level."""
    if "level" not in df.columns:
        return {}
    level_counts = df.group_by("level").len().sort("len", descending=True).to_dicts()
    return {str(row["level"]): int(row["len"]) for row in level_counts}


def _compute_event_counts(df: pl.DataFrame) -> dict[str, int]:
    """Compute entry counts by event type."""
    if "event" not in df.columns:
        return {}
    event_counts = df.group_by("event").len().sort("len", descending=True).to_dicts()
    return {str(row["event"]): int(row["len"]) for row in event_counts}


def _compute_hook_event_counts(df: pl.DataFrame) -> dict[str, int]:
    """Compute entry counts by hook event type."""
    if "hook_event" not in df.columns:
        return {}
    hook_event_counts = (
        df.filter(pl.col("hook_event").is_not_null())
        .group_by("hook_event")
        .len()
        .sort("len", descending=True)
        .to_dicts()
    )
    return {str(row["hook_event"]): int(row["len"]) for row in hook_event_counts}


def _compute_top_errors(df: pl.DataFrame) -> list[tuple[str, int]]:
    """Extract top error messages from hook_failed events.

    Extracts exception info from structlog's dict_tracebacks format which stores
    structured exception data in the 'exception' column.
    """
    if "event" not in df.columns or "level" not in df.columns:
        return []

    # Filter to error-level entries
    error_df = df.filter(pl.col("level") == "error")
    if error_df.height == 0:
        return []

    # Try to extract from structlog's dict_tracebacks format (exception column)
    # dict_tracebacks stores exception info in a struct with exc_type and exc_value
    if "exception" in error_df.columns:
        exc_df = error_df.filter(pl.col("exception").is_not_null())
        if exc_df.height > 0:
            # Extract exc_type and exc_value from the exception struct
            # Use try/except for schema mismatch if exception format differs
            try:
                exc_df = exc_df.with_columns(
                    [
                        pl.col("exception").struct.field("exc_type").alias("exc_type"),
                        pl.col("exception")
                        .struct.field("exc_value")
                        .alias("exc_value"),
                    ]
                )
            except pl.exceptions.SchemaFieldNotFoundError:
                pass  # Different exception format, fall through to fallback
            else:
                # Combine type and value (truncated)
                exc_df = exc_df.with_columns(
                    (
                        pl.col("exc_type").fill_null("")
                        + pl.lit(": ")
                        + pl.col("exc_value").fill_null("").str.slice(0, 60)
                    ).alias("error_combined")
                )
                error_counts = (
                    exc_df.group_by("error_combined")
                    .len()
                    .sort("len", descending=True)
                    .head(5)
                    .to_dicts()
                )
                if error_counts:
                    return [
                        (str(row["error_combined"]), int(row["len"]))
                        for row in error_counts
                    ]

    # Fall back to 'error' field (legacy format before dict_tracebacks)
    if "error" in error_df.columns:
        err_df = error_df.filter(pl.col("error").is_not_null())
        if err_df.height > 0:
            # Truncate error messages for grouping
            err_df = err_df.with_columns(
                pl.col("error").str.slice(0, 80).alias("error_truncated")
            )
            error_counts = (
                err_df.group_by("error_truncated")
                .len()
                .sort("len", descending=True)
                .head(5)
                .to_dicts()
            )
            if error_counts:
                return [
                    (str(row["error_truncated"]), int(row["len"]))
                    for row in error_counts
                ]

    # Final fallback to event names for error-level entries
    event_counts = (
        error_df.group_by("event").len().sort("len", descending=True).head(5).to_dicts()
    )
    return [(str(row["event"]), int(row["len"])) for row in event_counts]


def _compute_tool_usage(df: pl.DataFrame) -> dict[str, int]:
    """Compute tool usage counts from hook_input events for PreToolUse hooks."""
    if "input" not in df.columns or "event" not in df.columns:
        return {}
    try:
        # Filter to hook_input events (which contain the full input with tool_name)
        hook_input_df = df.filter(
            (pl.col("event") == "hook_input") & pl.col("input").is_not_null()
        )
        if hook_input_df.height == 0:
            return {}

        # Extract hook_event_name and tool_name from the input struct
        hook_input_df = hook_input_df.with_columns(
            [
                pl.col("input")
                .struct.field("hook_event_name")
                .alias("hook_event_name"),
                pl.col("input").struct.field("tool_name").alias("tool_name"),
            ]
        )

        # Filter to PreToolUse events with non-null tool_name
        tool_df = hook_input_df.filter(
            (pl.col("hook_event_name") == "PreToolUse")
            & pl.col("tool_name").is_not_null()
        )
        if tool_df.height == 0:
            return {}

        tool_counts = (
            tool_df.group_by("tool_name").len().sort("len", descending=True).to_dicts()
        )
        return {str(row["tool_name"]): int(row["len"]) for row in tool_counts}
    except pl.exceptions.StructFieldNotFoundError:
        return {}


def _compute_stats(df: pl.DataFrame) -> HookStats:
    """Compute statistics from the parsed log DataFrame.

    Args:
        df: DataFrame with parsed hook log entries.

    Returns:
        HookStats with computed statistics.
    """
    total_entries = df.height

    # Count unique sessions using shared utility
    total_sessions = count_unique_sessions(df)

    # Count by log level, event, and hook_event
    entries_by_level = _compute_level_counts(df)
    entries_by_event = _compute_event_counts(df)
    entries_by_hook_event = _compute_hook_event_counts(df)

    # Count specific events
    error_count = entries_by_level.get("error", 0)
    warning_count = entries_by_level.get("warning", 0)
    blocked_count = entries_by_event.get("hook_blocked", 0)
    failed_count = entries_by_event.get("hook_failed", 0)
    completed_count = entries_by_event.get("hook_completed", 0)

    # Average hooks per session
    avg_hooks_per_session = 0.0
    if total_sessions > 0 and "session_id" in df.columns:
        started_events = df.filter(pl.col("event") == "hook_started")
        if started_events.height > 0:
            avg_hooks_per_session = started_events.height / total_sessions

    # Most active sessions (by hook_started count)
    most_active_sessions: list[tuple[str, int]] = []
    if "session_id" in df.columns:
        started_df = df.filter(pl.col("event") == "hook_started")
        normalized_df = normalize_session_ids(started_df)
        session_activity = (
            normalized_df.group_by("session_id_normalized")
            .len()
            .sort("len", descending=True)
            .head(5)
            .to_dicts()
        )
        most_active_sessions = [
            (str(row["session_id_normalized"]), int(row["len"]))
            for row in session_activity
        ]

    # Time range using shared utility
    time_range_start, time_range_end = get_time_range(df)

    # Tool usage from pre_tool_use events
    tool_usage = _compute_tool_usage(df)

    # Top errors
    top_errors = _compute_top_errors(df)

    return HookStats(
        total_entries=total_entries,
        total_sessions=total_sessions,
        entries_by_level=entries_by_level,
        entries_by_event=entries_by_event,
        entries_by_hook_event=entries_by_hook_event,
        error_count=error_count,
        warning_count=warning_count,
        blocked_count=blocked_count,
        failed_count=failed_count,
        completed_count=completed_count,
        avg_hooks_per_session=avg_hooks_per_session,
        most_active_sessions=most_active_sessions,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        tool_usage=tool_usage,
        top_errors=top_errors,
    )


def _compute_health_score(stats: HookStats) -> tuple[int, list[str]]:
    """Compute a health score (0-100) and list of issues.

    Args:
        stats: Computed hook statistics.

    Returns:
        Tuple of (score, list of issues found).
    """
    score = 100
    issues: list[str] = []

    # Deduct for errors
    if stats.error_count > 0:
        deduction = min(30, stats.error_count * 5)
        score -= deduction
        issues.append(f"{stats.error_count} error(s) found in log")

    # Deduct for warnings
    if stats.warning_count > 0:
        deduction = min(15, stats.warning_count * 2)
        score -= deduction
        issues.append(f"{stats.warning_count} warning(s) found in log")

    # Deduct for blocked hooks
    if stats.blocked_count > 0:
        deduction = min(10, stats.blocked_count)
        score -= deduction
        issues.append(f"{stats.blocked_count} hook(s) were blocked")

    # Deduct for failed hooks
    if stats.failed_count > 0:
        deduction = min(20, stats.failed_count * 3)
        score -= deduction
        issues.append(f"{stats.failed_count} hook(s) failed")

    # Check completion rate
    started_count = stats.entries_by_event.get("hook_started", 0)
    if started_count > 0:
        completion_rate = stats.completed_count / started_count
        if completion_rate < _COMPLETION_RATE_THRESHOLD:
            deduction = int((1 - completion_rate) * 20)
            score -= deduction
            issues.append(f"Completion rate is {completion_rate:.1%} (expected >95%)")

    return max(0, score), issues


def _get_health_style(score: int) -> tuple[str, str]:
    """Get health status string and color from score."""
    if score >= _HEALTH_EXCELLENT:
        return "Excellent", "green"
    if score >= _HEALTH_GOOD:
        return "Good", "blue"
    if score >= _HEALTH_FAIR:
        return "Fair", "yellow"
    return "Poor", "red"


def _render_rich_output(stats: HookStats, console: Console) -> None:
    """Render statistics using Rich for beautiful terminal output.

    Args:
        stats: Computed hook statistics.
        console: Rich console for output.
    """
    console.print()
    console.print("[bold blue]Hook Log Statistics[/bold blue]")
    console.print()

    # Single consolidated table for all stats
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Category", width=22)
    table.add_column("Value", justify="right")

    # Time range
    if stats.time_range_start and stats.time_range_end:
        table.add_row("Time Range", stats.time_range_start)
        table.add_row("", f"→ {stats.time_range_end}")
        table.add_row("", "")

    # Overview
    table.add_row("[bold cyan]Overview[/bold cyan]", "")
    table.add_row("  Total Entries", f"{stats.total_entries:,}")
    table.add_row("  Sessions", f"{stats.total_sessions:,}")
    table.add_row("  Avg Hooks/Session", f"{stats.avg_hooks_per_session:.1f}")
    table.add_row("  Completed", f"[green]{stats.completed_count:,}[/green]")
    table.add_row("  Blocked", f"[yellow]{stats.blocked_count:,}[/yellow]")
    table.add_row("  Failed", f"[red]{stats.failed_count:,}[/red]")
    table.add_row("", "")

    # Log levels
    if stats.entries_by_level:
        table.add_row("[bold cyan]By Log Level[/bold cyan]", "")
        for level, count in sorted(
            stats.entries_by_level.items(), key=lambda x: x[1], reverse=True
        ):
            style = {"error": "red", "warning": "yellow", "debug": "dim"}.get(level, "")
            if style:
                table.add_row(f"  {level}", f"[{style}]{count:,}[/{style}]")
            else:
                table.add_row(f"  {level}", f"{count:,}")
        table.add_row("", "")

    # Hook events
    if stats.entries_by_hook_event:
        table.add_row("[bold cyan]By Hook Event[/bold cyan]", "")
        for hook_event, count in sorted(
            stats.entries_by_hook_event.items(), key=lambda x: x[1], reverse=True
        ):
            table.add_row(f"  {hook_event}", f"{count:,}")
        table.add_row("", "")

    # Tool usage
    if stats.tool_usage:
        table.add_row("[bold cyan]Tool Usage (Top 10)[/bold cyan]", "")
        for tool, count in list(stats.tool_usage.items())[:10]:
            table.add_row(f"  {tool}", f"{count:,}")
        table.add_row("", "")

    # Most active sessions
    if stats.most_active_sessions:
        table.add_row("[bold cyan]Top Sessions[/bold cyan]", "")
        for session_id, count in stats.most_active_sessions:
            if len(session_id) > _SESSION_ID_DISPLAY_LEN:
                short_id = session_id[:_SESSION_ID_DISPLAY_LEN] + "..."
            else:
                short_id = session_id
            table.add_row(f"  {short_id}", f"{count:,}")
        table.add_row("", "")

    # Top errors
    if stats.top_errors:
        table.add_row("[bold cyan]Top Errors[/bold cyan]", "")
        for error_msg, count in stats.top_errors:
            # Truncate long error messages
            if len(error_msg) > _ERROR_MSG_DISPLAY_LEN:
                display_msg = error_msg[:_ERROR_MSG_DISPLAY_LEN] + "..."
            else:
                display_msg = error_msg
            table.add_row(f"  [red]{display_msg}[/red]", f"[red]{count:,}[/red]")
        table.add_row("", "")

    # Health score
    score, issues = _compute_health_score(stats)
    status, color = _get_health_style(score)

    table.add_row(
        "[bold cyan]Health Score[/bold cyan]",
        f"[{color}]{score}/100 ({status})[/{color}]",
    )
    if issues:
        for issue in issues:
            table.add_row("", f"[red]• {issue}[/red]")

    console.print(table)
    console.print()


def _format_json_output(stats: HookStats) -> str:
    """Format statistics as JSON.

    Args:
        stats: Computed hook statistics.

    Returns:
        JSON string output.
    """
    import orjson

    score, issues = _compute_health_score(stats)

    data = {
        "time_range": {
            "start": stats.time_range_start,
            "end": stats.time_range_end,
        },
        "overview": {
            "total_entries": stats.total_entries,
            "total_sessions": stats.total_sessions,
            "avg_hooks_per_session": round(stats.avg_hooks_per_session, 2),
        },
        "execution": {
            "completed": stats.completed_count,
            "blocked": stats.blocked_count,
            "failed": stats.failed_count,
        },
        "by_level": stats.entries_by_level,
        "by_event": stats.entries_by_event,
        "by_hook_event": stats.entries_by_hook_event,
        "tool_usage": stats.tool_usage,
        "most_active_sessions": [
            {"session_id": sid, "hook_count": count}
            for sid, count in stats.most_active_sessions
        ],
        "top_errors": [
            {"error": err, "count": count} for err, count in stats.top_errors
        ],
        "health": {
            "score": score,
            "issues": issues,
        },
    }

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.command(name="stats")
def _stats(
    *,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
    session_id: Annotated[
        str | None,
        Parameter(
            name=["--session", "-s"],
            help="Filter statistics to a specific session ID",
        ),
    ] = None,
) -> None:
    """Analyze hook log and display statistics.

    Uses Polars to efficiently analyze the JSONL hook log file and provides:
    - Overview statistics (total entries, sessions, averages)
    - Execution statistics (completed, blocked, failed)
    - Breakdown by log level, event type, and hook event
    - Tool usage statistics
    - Most active sessions
    - Health score with identified issues

    Examples:
        oaps hooks stats              # Show all statistics
        oaps hooks stats -f json      # Output as JSON
        oaps hooks stats -s abc123    # Stats for specific session

    Exit codes:
        0: Statistics displayed successfully
        1: Failed to load or parse log file
    """
    console = Console()
    log_path = get_oaps_hooks_log_file()

    if not log_path.exists():
        console.print(f"[yellow]Hook log file not found:[/yellow] {log_path}")
        console.print("No hook executions have been recorded yet.")
        raise SystemExit(EXIT_SUCCESS)

    try:
        df = parse_log_to_dataframe(str(log_path))
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing hook log:[/red] {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    if df.height == 0:
        console.print("[yellow]Hook log is empty.[/yellow] No statistics to display.")
        raise SystemExit(EXIT_SUCCESS)

    # Filter by session if requested
    if session_id and "session_id" in df.columns:
        df = df.filter(
            pl.col("session_id").cast(pl.Utf8).str.contains(session_id, literal=True)
        )
        if df.height == 0:
            console.print(
                f"[yellow]No entries found for session:[/yellow] {session_id}"
            )
            raise SystemExit(EXIT_SUCCESS)

    stats = _compute_stats(df)

    if format == OutputFormat.JSON:
        print(_format_json_output(stats))
    else:
        _render_rich_output(stats, console)

    raise SystemExit(EXIT_SUCCESS)
