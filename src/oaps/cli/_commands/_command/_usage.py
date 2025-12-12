# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false
# ruff: noqa: A002, PLR0912, TRY300
"""Usage subcommand for commands - analyze slash command usage from hook logs."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.table import Table

from oaps.cli._commands._context import OutputFormat
from oaps.utils import get_oaps_hooks_log_file

from ._app import app
from ._exit_codes import EXIT_LOAD_ERROR, EXIT_SUCCESS

# Display constants
_ARG_DISPLAY_LEN = 50
_TOP_ARGS_COUNT = 5
_SESSION_ID_DISPLAY_LEN = 16

# Schema inference length
_SCHEMA_INFER_LENGTH = 10000


@dataclass(frozen=True, slots=True)
class CommandUsageStats:
    """Statistics derived from slash command usage analysis.

    Attributes:
        total_invocations: Total number of slash command invocations.
        unique_commands: Number of unique command names.
        command_counts: Mapping of command name to invocation count.
        argument_patterns: Mapping of command name to top argument patterns.
        time_range_start: Earliest timestamp in the filtered log.
        time_range_end: Latest timestamp in the filtered log.
        sessions: List of (session_id, count) for sessions using commands.
    """

    total_invocations: int
    unique_commands: int
    command_counts: dict[str, int]
    argument_patterns: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    time_range_start: str | None = None
    time_range_end: str | None = None
    sessions: list[tuple[str, int]] = field(default_factory=list)


def _parse_time_filter(since: str | None) -> datetime | None:
    """Parse a time filter string into a datetime.

    Supports:
    - Relative formats: "1d" (1 day), "2h" (2 hours), "30m" (30 minutes)
    - Absolute formats: ISO 8601 dates like "2024-12-01" or "2024-12-01T10:30:00"

    Args:
        since: Time filter string, or None.

    Returns:
        datetime in UTC, or None if since is None.

    Raises:
        ValueError: If the format is invalid.
    """
    if since is None:
        return None

    # Try relative format first: e.g., "1d", "2h", "30m"
    relative_match = re.match(r"^(\d+)([dhm])$", since)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        now = datetime.now(UTC)
        if unit == "d":
            return now - timedelta(days=amount)
        if unit == "h":
            return now - timedelta(hours=amount)
        if unit == "m":
            return now - timedelta(minutes=amount)

    # Try absolute ISO 8601 format
    try:
        parsed = datetime.fromisoformat(since)
        # Add UTC timezone if not specified
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        pass

    msg = (
        f"Invalid time format: {since!r}. "
        "Use relative (1d, 2h, 30m) or absolute (2024-12-01) format."
    )
    raise ValueError(msg)


def _parse_command_string(command: str) -> tuple[str, str]:
    """Parse a slash command string into name and arguments.

    Args:
        command: Full command string, e.g., "/oaps:dev some args here"

    Returns:
        Tuple of (command_name, arguments).
        command_name includes the leading slash.
        arguments is the rest of the string after the command name.
    """
    # Split on first whitespace
    parts = command.split(None, 1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])


def _parse_log_to_dataframe(log_path: str) -> pl.DataFrame:
    """Parse JSONL hook log file into a Polars DataFrame.

    Args:
        log_path: Path to the hooks.log file.

    Returns:
        DataFrame with parsed log entries.

    Raises:
        FileNotFoundError: If log file doesn't exist.
        pl.exceptions.ComputeError: If log file is malformed.
    """
    return pl.read_ndjson(log_path, infer_schema_length=_SCHEMA_INFER_LENGTH)


def _filter_to_slash_commands(df: pl.DataFrame) -> pl.DataFrame:
    """Filter DataFrame to only SlashCommand PreToolUse events.

    Looks for:
    - event == "hook_input"
    - input.hook_event_name == "PreToolUse"
    - input.tool_name == "SlashCommand"

    Args:
        df: Full log DataFrame.

    Returns:
        Filtered DataFrame with only slash command events.
    """
    if "input" not in df.columns or "event" not in df.columns:
        return df.clear()

    try:
        # Filter to hook_input events with non-null input
        hook_input_df = df.filter(
            (pl.col("event") == "hook_input") & pl.col("input").is_not_null()
        )
        if hook_input_df.height == 0:
            return hook_input_df

        # Extract fields from the input struct
        hook_input_df = hook_input_df.with_columns(
            [
                pl.col("input")
                .struct.field("hook_event_name")
                .alias("hook_event_name"),
                pl.col("input").struct.field("tool_name").alias("tool_name"),
                pl.col("input").struct.field("tool_input").alias("tool_input"),
                pl.col("input").struct.field("session_id").alias("session_id"),
            ]
        )

        # Filter to PreToolUse + SlashCommand
        return hook_input_df.filter(
            (pl.col("hook_event_name") == "PreToolUse")
            & (pl.col("tool_name") == "SlashCommand")
        )
    except pl.exceptions.StructFieldNotFoundError:
        return df.clear()


def _extract_command_strings(df: pl.DataFrame) -> pl.DataFrame:
    """Extract command strings from the tool_input struct.

    Args:
        df: DataFrame with tool_input column.

    Returns:
        DataFrame with command_string column added.
    """
    if df.height == 0 or "tool_input" not in df.columns:
        return df.with_columns(pl.lit(None).alias("command_string"))

    try:
        return df.with_columns(
            pl.col("tool_input").struct.field("command").alias("command_string")
        )
    except pl.exceptions.StructFieldNotFoundError:
        return df.with_columns(pl.lit(None).alias("command_string"))


def _compute_stats(
    df: pl.DataFrame, command_filter: str | None = None
) -> CommandUsageStats:
    """Compute command usage statistics from filtered DataFrame.

    Args:
        df: DataFrame filtered to slash command events with command_string column.
        command_filter: Optional command name to filter by.

    Returns:
        CommandUsageStats with computed statistics.
    """
    # Filter out null command strings
    df = df.filter(pl.col("command_string").is_not_null())

    if df.height == 0:
        return CommandUsageStats(
            total_invocations=0,
            unique_commands=0,
            command_counts={},
        )

    # Parse command strings into name and args
    commands_df = df.with_columns(
        [
            pl.col("command_string")
            .map_elements(lambda x: _parse_command_string(x)[0], return_dtype=pl.Utf8)
            .alias("command_name"),
            pl.col("command_string")
            .map_elements(lambda x: _parse_command_string(x)[1], return_dtype=pl.Utf8)
            .alias("command_args"),
        ]
    )

    # Apply command filter if specified
    if command_filter:
        # Match with or without leading slash
        filter_pattern = command_filter
        if not filter_pattern.startswith("/"):
            filter_pattern = "/" + filter_pattern
        commands_df = commands_df.filter(
            pl.col("command_name").str.to_lowercase() == filter_pattern.lower()
        )

    if commands_df.height == 0:
        return CommandUsageStats(
            total_invocations=0,
            unique_commands=0,
            command_counts={},
        )

    total_invocations = commands_df.height

    # Count by command name
    command_counts_df = (
        commands_df.group_by("command_name")
        .len()
        .sort("len", descending=True)
        .to_dicts()
    )
    command_counts = {
        str(row["command_name"]): int(row["len"]) for row in command_counts_df
    }
    unique_commands = len(command_counts)

    # Compute argument patterns for each command
    argument_patterns: dict[str, list[tuple[str, int]]] = {}
    for cmd_name in command_counts:
        cmd_df = commands_df.filter(pl.col("command_name") == cmd_name)

        # Group by args (treating empty string as "(no args)")
        args_df = cmd_df.with_columns(
            pl.when(pl.col("command_args") == "")
            .then(pl.lit("(no args)"))
            .otherwise(pl.col("command_args").str.slice(0, _ARG_DISPLAY_LEN))
            .alias("args_display")
        )

        arg_counts = (
            args_df.group_by("args_display")
            .len()
            .sort("len", descending=True)
            .head(_TOP_ARGS_COUNT)
            .to_dicts()
        )
        argument_patterns[cmd_name] = [
            (str(row["args_display"]), int(row["len"])) for row in arg_counts
        ]

    # Time range
    time_range_start: str | None = None
    time_range_end: str | None = None
    if "timestamp" in commands_df.columns and commands_df.height > 0:
        timestamps = commands_df.select("timestamp").to_series()
        time_range_start = str(timestamps.min())
        time_range_end = str(timestamps.max())

    # Session counts
    sessions: list[tuple[str, int]] = []
    if "session_id" in commands_df.columns:
        session_counts = (
            commands_df.with_columns(
                pl.col("session_id")
                .cast(pl.Utf8)
                .str.replace(r"^UUID\('(.+)'\)$", "$1")
                .alias("session_id_normalized")
            )
            .group_by("session_id_normalized")
            .len()
            .sort("len", descending=True)
            .head(5)
            .to_dicts()
        )
        sessions = [
            (str(row["session_id_normalized"]), int(row["len"]))
            for row in session_counts
        ]

    return CommandUsageStats(
        total_invocations=total_invocations,
        unique_commands=unique_commands,
        command_counts=command_counts,
        argument_patterns=argument_patterns,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        sessions=sessions,
    )


def _render_rich_output(stats: CommandUsageStats, console: Console) -> None:
    """Render statistics using Rich for terminal output.

    Args:
        stats: Computed command usage statistics.
        console: Rich console for output.
    """
    console.print()
    console.print("[bold blue]Slash Command Usage[/bold blue]")
    console.print()

    # Single consolidated table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Category", width=30)
    table.add_column("Value", justify="right")

    # Time range
    if stats.time_range_start and stats.time_range_end:
        table.add_row("Time Range", stats.time_range_start)
        table.add_row("", f"→ {stats.time_range_end}")
        table.add_row("", "")

    # Overview
    table.add_row("[bold cyan]Overview[/bold cyan]", "")
    table.add_row("  Total Invocations", f"{stats.total_invocations:,}")
    table.add_row("  Unique Commands", f"{stats.unique_commands:,}")
    table.add_row("", "")

    # Commands
    if stats.command_counts:
        table.add_row("[bold cyan]Commands[/bold cyan]", "")
        total = stats.total_invocations
        for cmd_name, count in stats.command_counts.items():
            pct = (count / total * 100) if total > 0 else 0
            table.add_row(f"  {cmd_name}", f"{count:,}  ({pct:.1f}%)")
        table.add_row("", "")

    # Argument patterns for each command
    if stats.argument_patterns:
        for cmd_name, patterns in stats.argument_patterns.items():
            if patterns:
                table.add_row(f"[bold cyan]Top Args for {cmd_name}[/bold cyan]", "")
                for arg_pattern, count in patterns:
                    # Truncate long args for display
                    display_arg = arg_pattern
                    if len(display_arg) > _ARG_DISPLAY_LEN:
                        display_arg = display_arg[:_ARG_DISPLAY_LEN] + "..."
                    table.add_row(f"  {display_arg}", f"{count:,}")
                table.add_row("", "")

    # Sessions
    if stats.sessions:
        table.add_row("[bold cyan]Top Sessions[/bold cyan]", "")
        for session_id, count in stats.sessions:
            if len(session_id) > _SESSION_ID_DISPLAY_LEN:
                short_id = session_id[:_SESSION_ID_DISPLAY_LEN] + "..."
            else:
                short_id = session_id
            table.add_row(f"  {short_id}", f"{count:,}")

    console.print(table)
    console.print()


def _format_json_output(stats: CommandUsageStats) -> str:
    """Format statistics as JSON.

    Args:
        stats: Computed command usage statistics.

    Returns:
        JSON string output.
    """
    import orjson

    data = {
        "time_range": {
            "start": stats.time_range_start,
            "end": stats.time_range_end,
        },
        "overview": {
            "total_invocations": stats.total_invocations,
            "unique_commands": stats.unique_commands,
        },
        "command_counts": stats.command_counts,
        "argument_patterns": {
            cmd: [{"pattern": p, "count": c} for p, c in patterns]
            for cmd, patterns in stats.argument_patterns.items()
        },
        "sessions": [
            {"session_id": sid, "count": count} for sid, count in stats.sessions
        ],
    }

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.command(name="usage")
def _usage(
    command_name: Annotated[
        str | None,
        Parameter(
            help="Filter to a specific command name (with or without leading slash)",
        ),
    ] = None,
    *,
    since: Annotated[
        str | None,
        Parameter(
            name=["--since", "-s"],
            help="Filter to events since this time (e.g., 1d, 2h, 30m, or 2024-12-01)",
        ),
    ] = None,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Analyze slash command usage from hook logs.

    Shows statistics about how slash commands are being used, including:
    - Total invocations and unique commands
    - Command frequency with percentages
    - Top argument patterns for each command
    - Active sessions

    Examples:
        oaps command usage                    # Show all command usage
        oaps command usage /oaps:dev          # Filter to specific command
        oaps command usage --since 1d         # Last 24 hours only
        oaps command usage -f json            # Output as JSON

    Exit codes:
        0: Statistics displayed successfully (or no data)
        1: Failed to load or parse log file
    """
    console = Console()
    log_path = get_oaps_hooks_log_file()

    if not log_path.exists():
        if format == OutputFormat.JSON:
            print(
                _format_json_output(
                    CommandUsageStats(
                        total_invocations=0,
                        unique_commands=0,
                        command_counts={},
                    )
                )
            )
        else:
            console.print(f"[yellow]Hook log file not found:[/yellow] {log_path}")
            console.print("No hook executions have been recorded yet.")
        raise SystemExit(EXIT_SUCCESS)

    try:
        df = _parse_log_to_dataframe(str(log_path))
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing hook log:[/red] {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    if df.height == 0:
        if format == OutputFormat.JSON:
            print(
                _format_json_output(
                    CommandUsageStats(
                        total_invocations=0,
                        unique_commands=0,
                        command_counts={},
                    )
                )
            )
        else:
            console.print(
                "[yellow]Hook log is empty.[/yellow] No statistics to display."
            )
        raise SystemExit(EXIT_SUCCESS)

    # Apply time filter if specified
    if since is not None:
        try:
            since_dt = _parse_time_filter(since)
        except ValueError as e:
            console.print(f"[red]Invalid --since value:[/red] {e}")
            raise SystemExit(EXIT_LOAD_ERROR) from None

        if since_dt is not None and "timestamp" in df.columns:
            # Convert timestamp column to datetime for comparison
            since_str = since_dt.isoformat()
            df = df.filter(pl.col("timestamp") >= since_str)

    # Filter to slash commands
    slash_df = _filter_to_slash_commands(df)
    slash_df = _extract_command_strings(slash_df)

    # Compute statistics
    stats = _compute_stats(slash_df, command_filter=command_name)

    if stats.total_invocations == 0:
        if format == OutputFormat.JSON:
            print(_format_json_output(stats))
        elif command_name:
            console.print(
                f"[yellow]No usage found for command:[/yellow] {command_name}"
            )
        else:
            console.print("[yellow]No slash command usage found in the log.[/yellow]")
        raise SystemExit(EXIT_SUCCESS)

    if format == OutputFormat.JSON:
        print(_format_json_output(stats))
    else:
        _render_rich_output(stats, console)

    raise SystemExit(EXIT_SUCCESS)
