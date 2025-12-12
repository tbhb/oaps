# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false
# ruff: noqa: A002, PLR0912, PLR0913
"""Errors subcommand for hooks - display recent hook execution errors."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_success
from oaps.utils import get_oaps_hooks_log_file

from ._app import app

# Display constants
_DEFAULT_LIMIT = 10
_SESSION_ID_DISPLAY_LEN = 16
_SCHEMA_INFER_LENGTH = 10000


@dataclass(frozen=True, slots=True)
class HookError:
    """A single hook error extracted from the log.

    Attributes:
        timestamp: When the error occurred.
        session_id: The Claude session ID.
        hook_event: The hook event type (e.g., PreToolUse, PostToolUse).
        exc_type: The exception type name.
        exc_value: The exception message.
        rule_id: The rule ID that caused the error, if available.
        frames: Stack trace frames, if available.
    """

    timestamp: str
    session_id: str
    hook_event: str
    exc_type: str
    exc_value: str
    rule_id: str | None = None
    frames: list[dict[str, str]] = field(default_factory=list)


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
    except ValueError:
        msg = (
            f"Invalid time format: {since!r}. "
            "Use relative (1d, 2h, 30m) or absolute (2024-12-01) format."
        )
        raise ValueError(msg) from None
    else:
        # Add UTC timezone if not specified
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed


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


def _extract_errors(df: pl.DataFrame) -> list[HookError]:
    """Extract hook errors from the DataFrame.

    Looks for hook_failed events and extracts exception info from
    structlog's dict_tracebacks format.

    Args:
        df: DataFrame with parsed log entries.

    Returns:
        List of HookError objects, sorted by timestamp descending.
    """
    if "event" not in df.columns or "level" not in df.columns:
        return []

    # Filter to error-level hook_failed events
    error_df = df.filter(
        (pl.col("level") == "error") & (pl.col("event") == "hook_failed")
    )

    if error_df.height == 0:
        return []

    errors: list[HookError] = []

    # Process each error row
    for row in error_df.to_dicts():
        timestamp = str(row.get("timestamp", ""))
        session_id = str(row.get("session_id", ""))
        hook_event = str(row.get("hook_event", ""))
        rule_id = row.get("rule_id")

        # Extract exception info from structlog's dict_tracebacks format
        exc_type = ""
        exc_value = ""
        frames: list[dict[str, str]] = []

        exception_data = row.get("exception")
        if exception_data and isinstance(exception_data, dict):
            exc_type = str(exception_data.get("exc_type", ""))
            exc_value = str(exception_data.get("exc_value", ""))

            # Extract stack frames if available
            raw_frames = exception_data.get("frames", [])
            if isinstance(raw_frames, list):
                frames.extend(
                    {
                        "filename": str(frame.get("filename", "")),
                        "lineno": str(frame.get("lineno", "")),
                        "name": str(frame.get("name", "")),
                    }
                    for frame in raw_frames
                    if isinstance(frame, dict)
                )

        # Fall back to 'error' field for legacy format
        if not exc_type and not exc_value:
            error_msg = row.get("error")
            if error_msg:
                exc_type = "Error"
                exc_value = str(error_msg)

        if exc_type or exc_value:
            errors.append(
                HookError(
                    timestamp=timestamp,
                    session_id=session_id,
                    hook_event=hook_event,
                    exc_type=exc_type,
                    exc_value=exc_value,
                    rule_id=str(rule_id) if rule_id else None,
                    frames=frames,
                )
            )

    # Sort by timestamp descending (most recent first)
    errors.sort(key=lambda e: e.timestamp, reverse=True)
    return errors


def _filter_errors(
    errors: list[HookError],
    events: list[str] | None,
    hook_id: str | None,
    since_dt: datetime | None,
) -> list[HookError]:
    """Filter errors by event type, hook ID, and time.

    Args:
        errors: List of HookError objects to filter.
        events: List of event types to include, or None for all.
        hook_id: Hook (rule) ID to filter by, or None for all.
        since_dt: Only include errors after this time, or None for all.

    Returns:
        Filtered list of HookError objects.
    """
    result = errors

    if events:
        # Case-insensitive matching
        events_lower = [e.lower() for e in events]
        result = [e for e in result if e.hook_event.lower() in events_lower]

    if hook_id:
        # Case-insensitive partial match on rule_id
        hook_id_lower = hook_id.lower()
        result = [e for e in result if e.rule_id and hook_id_lower in e.rule_id.lower()]

    if since_dt:
        since_str = since_dt.isoformat()
        result = [e for e in result if e.timestamp >= since_str]

    return result


def _render_rich_output(
    errors: list[HookError],
    console: Console,
    *,
    verbose: bool = False,
) -> None:
    """Render errors using Rich for terminal output.

    Args:
        errors: List of HookError objects to display.
        console: Rich console for output.
        verbose: Whether to show stack traces.
    """
    console.print()
    console.print(f"[bold blue]Hook Errors[/bold blue] ({len(errors)} found)")
    console.print()

    for i, error in enumerate(errors, 1):
        # Build error display
        session_display = error.session_id
        if len(session_display) > _SESSION_ID_DISPLAY_LEN:
            session_display = session_display[:_SESSION_ID_DISPLAY_LEN] + "..."

        # Error header
        header = Text()
        header.append(f"#{i} ", style="bold")
        header.append(f"[{error.timestamp}]", style="dim")

        # Error details
        content = Text()
        content.append(f"{error.exc_type}: ", style="bold red")
        content.append(error.exc_value, style="red")
        content.append("\n\n")
        content.append("Event: ", style="bold")
        content.append(error.hook_event)
        content.append("  ")
        content.append("Session: ", style="bold")
        content.append(session_display, style="dim")

        if error.rule_id:
            content.append("  ")
            content.append("Rule: ", style="bold")
            content.append(error.rule_id)

        # Stack trace (verbose mode only)
        if verbose and error.frames:
            content.append("\n\n")
            content.append("Stack trace:", style="bold")
            for frame in error.frames:
                content.append(f"\n  {frame['filename']}:{frame['lineno']}")
                content.append(f" in {frame['name']}", style="italic")

        panel = Panel(
            content,
            title=header,
            title_align="left",
            border_style="red" if i == 1 else "dim",
        )
        console.print(panel)

    console.print()


def _format_json_output(errors: list[HookError]) -> str:
    """Format errors as JSON.

    Args:
        errors: List of HookError objects to format.

    Returns:
        JSON string output.
    """
    import orjson

    data = {
        "count": len(errors),
        "errors": [
            {
                "timestamp": e.timestamp,
                "session_id": e.session_id,
                "hook_event": e.hook_event,
                "exc_type": e.exc_type,
                "exc_value": e.exc_value,
                "rule_id": e.rule_id,
                "frames": e.frames if e.frames else None,
            }
            for e in errors
        ],
    }

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.command(name="errors")
def _errors(
    *,
    event: Annotated[
        list[str] | None,
        Parameter(
            name=["--event", "-e"],
            help="Filter by hook event type (can be specified multiple times)",
        ),
    ] = None,
    hook: Annotated[
        str | None,
        Parameter(
            name=["--hook", "-H"],
            help="Filter by hook (rule) ID (partial match)",
        ),
    ] = None,
    since: Annotated[
        str | None,
        Parameter(
            name=["--since", "-s"],
            help="Filter to errors since this time (e.g., 1d, 2h, 30m, or 2024-12-01)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Parameter(
            name=["--limit", "-n"],
            help="Maximum number of errors to display",
        ),
    ] = _DEFAULT_LIMIT,
    verbose: Annotated[
        bool,
        Parameter(
            name=["--verbose", "-v"],
            help="Show stack traces for each error",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Display recent hook execution errors.

    Shows detailed information about hook errors including timestamp,
    session ID, hook event, exception type and message. Use --verbose
    to include stack traces.

    Examples:
        oaps hooks errors                     # Show last 10 errors
        oaps hooks errors -n 20               # Show last 20 errors
        oaps hooks errors -e PreToolUse       # Filter by event type
        oaps hooks errors -H my-rule          # Filter by rule ID
        oaps hooks errors --since 1d          # Errors from last 24 hours
        oaps hooks errors -v                  # Include stack traces
        oaps hooks errors -f json             # Output as JSON

    Exit codes:
        0: Errors displayed successfully (or no errors found)
        1: Failed to load or parse log file
    """
    console = Console()
    log_path = get_oaps_hooks_log_file()

    if not log_path.exists():
        if format == OutputFormat.JSON:
            print(_format_json_output([]))
        else:
            console.print(f"[yellow]Hook log file not found:[/yellow] {log_path}")
            console.print("No hook executions have been recorded yet.")
        exit_with_success()

    try:
        df = _parse_log_to_dataframe(str(log_path))
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing hook log:[/red] {e}")
        raise SystemExit(ExitCode.LOAD_ERROR) from None

    if df.height == 0:
        if format == OutputFormat.JSON:
            print(_format_json_output([]))
        else:
            console.print("[yellow]Hook log is empty.[/yellow] No errors to display.")
        exit_with_success()

    # Parse time filter
    since_dt: datetime | None = None
    if since is not None:
        try:
            since_dt = _parse_time_filter(since)
        except ValueError as e:
            console.print(f"[red]Invalid --since value:[/red] {e}")
            raise SystemExit(ExitCode.LOAD_ERROR) from None

    # Extract and filter errors
    errors = _extract_errors(df)
    errors = _filter_errors(errors, event, hook, since_dt)

    # Apply limit
    if limit > 0:
        errors = errors[:limit]

    if not errors:
        if format == OutputFormat.JSON:
            print(_format_json_output([]))
        else:
            console.print("[green]No hook errors found.[/green]")
        exit_with_success()

    if format == OutputFormat.JSON:
        print(_format_json_output(errors))
    else:
        _render_rich_output(errors, console, verbose=verbose)

    exit_with_success()
