# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
# ruff: noqa: A002, PLR0912, PLR0913, PLR0915, PLR0911, TRY300, SIM108, FBT003, PERF401
"""Main logs command implementation."""

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import polars as pl
from cyclopts import Parameter
from rich.console import Console

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_success

from ._app import app
from ._sources import LogSource, load_logs, resolve_source

# Level ordering for filtering (index = severity)
_LEVEL_ORDER = ["debug", "info", "warning", "error"]

# Display widths for compact format
_SOURCE_WIDTH = 20
_LEVEL_WIDTH = 5
_EVENT_WIDTH = 24

# Truncation lengths
_SESSION_ID_DISPLAY_LEN = 8
_VALUE_DISPLAY_LEN = 24


def _parse_time_filter(value: str | None) -> datetime | None:
    """Parse a time filter string into a datetime.

    Supports:
    - Relative formats: "1d" (1 day), "2h" (2 hours), "30m" (30 minutes)
    - Absolute formats: ISO 8601 dates like "2024-12-01" or "2024-12-01T10:30:00"

    Args:
        value: Time filter string, or None.

    Returns:
        datetime in UTC, or None if value is None.

    Raises:
        ValueError: If the format is invalid.
    """
    if value is None:
        return None

    # Try relative format first: e.g., "1d", "2h", "30m"
    relative_match = re.match(r"^(\d+)([dhm])$", value)
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
        parsed = datetime.fromisoformat(value)
    except ValueError:
        msg = (
            f"Invalid time format: {value!r}. "
            "Use relative (1d, 2h, 30m) or absolute (2024-12-01) format."
        )
        raise ValueError(msg) from None
    else:
        # Add UTC timezone if not specified
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed


def _parse_where_clause(clause: str) -> pl.Expr:
    """Parse a --where clause into a Polars expression.

    Supported syntax:
    - field = value
    - field != value
    - field > value, field < value, field >= value, field <= value
    - field ~ regex
    - field contains substring

    Supports dot notation for nested fields: context.exit_code

    Args:
        clause: Where clause string.

    Returns:
        Polars expression for the filter.

    Raises:
        ValueError: If the clause syntax is invalid.
    """
    # Pattern: field operator value
    # Operators: =, !=, >, <, >=, <=, ~, contains
    pattern = r"^([\w.]+)\s*(=|!=|>=|<=|>|<|~|contains)\s*(.+)$"
    match = re.match(pattern, clause.strip())

    if not match:
        msg = (
            f"Invalid --where syntax: {clause!r}. "
            "Expected: field op value "
            "(e.g., 'level = error', 'count > 5', 'event ~ hook_.*')"
        )
        raise ValueError(msg)

    field, operator, value = match.groups()
    value = value.strip().strip("'\"")  # Remove quotes if present

    # Build column reference (handle dot notation for nested fields)
    col_expr = _build_column_expr(field)

    # Apply operator
    if operator == "=":
        # Try numeric comparison first
        try:
            num_value = float(value) if "." in value else int(value)
            return col_expr == num_value
        except ValueError:
            return col_expr.cast(pl.Utf8) == value

    if operator == "!=":
        try:
            num_value = float(value) if "." in value else int(value)
            return col_expr != num_value
        except ValueError:
            return col_expr.cast(pl.Utf8) != value

    if operator == ">":
        return col_expr > _parse_numeric(value)

    if operator == "<":
        return col_expr < _parse_numeric(value)

    if operator == ">=":
        return col_expr >= _parse_numeric(value)

    if operator == "<=":
        return col_expr <= _parse_numeric(value)

    if operator == "~":
        return col_expr.cast(pl.Utf8).str.contains(value)

    if operator == "contains":
        return col_expr.cast(pl.Utf8).str.contains(value, literal=True)

    msg = f"Unknown operator: {operator}"
    raise ValueError(msg)


def _build_column_expr(field: str) -> pl.Expr:
    """Build a Polars column expression, handling dot notation.

    Args:
        field: Field name, possibly with dots for nested access.

    Returns:
        Polars expression for the column.
    """
    parts = field.split(".")
    if len(parts) == 1:
        return pl.col(field)

    # Nested field access: a.b.c -> col("a").struct.field("b").struct.field("c")
    expr = pl.col(parts[0])
    for part in parts[1:]:
        expr = expr.struct.field(part)
    return expr


def _parse_numeric(value: str) -> int | float:
    """Parse a string as numeric value.

    Args:
        value: String to parse.

    Returns:
        int or float.

    Raises:
        ValueError: If not a valid number.
    """
    try:
        return int(value)
    except ValueError:
        return float(value)


def _build_filter_expr(
    *,
    level: str,
    events: list[str] | None,
    since_dt: datetime | None,
    until_dt: datetime | None,
    grep_pattern: str | None,
    session_filter: str | None,
    rule_id_filter: str | None,
    tool_name_filter: str | None,
    where_clauses: list[str] | None,
) -> pl.Expr | None:
    """Build a combined Polars filter expression.

    Args:
        level: Minimum log level (debug, info, warning, error).
        events: List of event names to include, or None for all.
        since_dt: Only include entries after this time.
        until_dt: Only include entries before this time.
        grep_pattern: Regex pattern to search in any field.
        session_filter: Session ID prefix to filter by.
        rule_id_filter: Rule ID to filter by.
        tool_name_filter: Tool name to filter by.
        where_clauses: List of --where clause strings.

    Returns:
        Combined filter expression, or None if no filters.
    """
    filters: list[pl.Expr] = []

    # Level filter
    level_lower = level.lower()
    if level_lower in _LEVEL_ORDER:
        min_index = _LEVEL_ORDER.index(level_lower)
        allowed_levels = _LEVEL_ORDER[min_index:]
        filters.append(pl.col("level").str.to_lowercase().is_in(allowed_levels))

    # Event filter
    if events:
        filters.append(pl.col("event").is_in(events))

    # Time filters
    if since_dt:
        since_str = since_dt.isoformat()
        filters.append(pl.col("timestamp") >= since_str)

    if until_dt:
        until_str = until_dt.isoformat()
        filters.append(pl.col("timestamp") <= until_str)

    # Grep filter (search across multiple string columns)
    if grep_pattern:
        # Search in event, level, and session_id columns
        grep_expr = pl.col("event").cast(pl.Utf8).str.contains(grep_pattern) | pl.col(
            "level"
        ).cast(pl.Utf8).str.contains(grep_pattern)
        # Add session_id if it exists
        session_grep = pl.col("session_id").cast(pl.Utf8).str.contains(grep_pattern)
        grep_expr = grep_expr | session_grep
        filters.append(grep_expr)

    # Session filter
    if session_filter:
        session_col = pl.col("session_id").cast(pl.Utf8)
        session_expr = session_col.str.contains(session_filter, literal=True)
        filters.append(session_expr)

    # Rule ID filter (in input.rule_id or rule_id)
    if rule_id_filter:
        rule_filter = (
            pl.col("rule_id").cast(pl.Utf8).str.contains(rule_id_filter, literal=True)
        )
        filters.append(rule_filter)

    # Tool name filter (in input.tool_name)
    if tool_name_filter:
        try:
            tool_filter = (
                pl.col("input").struct.field("tool_name").cast(pl.Utf8)
                == tool_name_filter
            )
            filters.append(tool_filter)
        except pl.exceptions.StructFieldNotFoundError:
            # Column doesn't have this field, filter will match nothing
            filters.append(pl.lit(False))

    # Where clauses
    if where_clauses:
        for clause in where_clauses:
            filters.append(_parse_where_clause(clause))

    if not filters:
        return None

    # Combine all filters with AND
    combined = filters[0]
    for f in filters[1:]:
        combined = combined & f
    return combined


def _format_compact_entry(row: dict[str, Any], source: LogSource) -> str:
    """Format a log entry as a compact one-liner.

    Format: HH:MM:SS source:hint  LEVEL  event_name       key=value...

    Args:
        row: Log entry as a dictionary.
        source: The log source for context.

    Returns:
        Formatted string.
    """
    # Extract timestamp (time only)
    timestamp = str(row.get("timestamp", ""))
    if "T" in timestamp:
        time_part = timestamp.split("T")[1][:8]  # HH:MM:SS
    else:
        time_part = timestamp[:8]

    # Build source hint
    source_hint = row.get("_source", source.name)
    hook_event = row.get("hook_event")
    if hook_event and source_hint == "hooks":
        source_hint = f"hooks:{hook_event}"
    elif source_hint.startswith("cli"):
        command = row.get("command", "")
        if command:
            source_hint = f"cli:{command}"

    # Truncate source hint to fit column
    if len(source_hint) > _SOURCE_WIDTH:
        source_hint = source_hint[: _SOURCE_WIDTH - 1] + "…"

    # Level
    level = str(row.get("level", "")).upper()[:_LEVEL_WIDTH]

    # Event name
    event = str(row.get("event", ""))
    if len(event) > _EVENT_WIDTH:
        event = event[: _EVENT_WIDTH - 1] + "…"

    # Key-value pairs (selected important fields)
    kv_parts: list[str] = []

    # Session ID (truncated)
    session_id = row.get("session_id")
    if session_id:
        session_str = str(session_id)
        # Handle UUID('...') format
        if session_str.startswith("UUID('"):
            session_str = session_str[6:-2]
        if len(session_str) > _SESSION_ID_DISPLAY_LEN:
            session_str = session_str[:_SESSION_ID_DISPLAY_LEN] + "…"
        kv_parts.append(f"session_id={session_str}")

    # Rule ID
    rule_id = row.get("rule_id")
    if rule_id:
        kv_parts.append(f"rule_id={rule_id}")

    # Count (for rules_matched events)
    count = row.get("count")
    if count is not None:
        kv_parts.append(f"count={count}")

    # Reason (for blocked events)
    reason = row.get("reason")
    if reason:
        reason_str = str(reason)
        if len(reason_str) > _VALUE_DISPLAY_LEN:
            reason_str = reason_str[: _VALUE_DISPLAY_LEN - 1] + "…"
        kv_parts.append(f"reason={reason_str}")

    kv_str = " ".join(kv_parts)

    # Compose the line
    source_col = f"{source_hint:<{_SOURCE_WIDTH}}"
    level_col = f"{level:<{_LEVEL_WIDTH}}"
    event_col = f"{event:<{_EVENT_WIDTH}}"
    return f"{time_part} {source_col} {level_col} {event_col} {kv_str}"


def _format_json_output(df: pl.DataFrame) -> str:
    """Format log entries as JSON array.

    Args:
        df: DataFrame with log entries.

    Returns:
        JSON string.
    """
    import orjson

    rows = df.to_dicts()
    return orjson.dumps(rows, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.default
def logs(
    source: Annotated[
        str,
        Parameter(
            help="Log source: hooks (default), cli, session:<id>, or all",
        ),
    ] = "hooks",
    *,
    follow: Annotated[
        bool,
        Parameter(
            name=["-f", "--follow"],
            help="Follow log output (like tail -f)",
        ),
    ] = False,
    level: Annotated[
        str,
        Parameter(
            name=["-l", "--level"],
            help="Minimum log level: debug, info (default), warning, error",
        ),
    ] = "info",
    verbose: Annotated[
        bool,
        Parameter(
            name=["-v", "--verbose"],
            help="Show debug-level entries (shortcut for --level debug)",
        ),
    ] = False,
    event: Annotated[
        list[str] | None,
        Parameter(
            name=["-e", "--event"],
            help="Filter by event name (can be repeated)",
        ),
    ] = None,
    since: Annotated[
        str | None,
        Parameter(
            name=["-s", "--since"],
            help="Show entries since this time (e.g., 1h, 30m, 2024-12-01)",
        ),
    ] = None,
    until: Annotated[
        str | None,
        Parameter(
            name=["-u", "--until"],
            help="Show entries until this time",
        ),
    ] = None,
    limit: Annotated[
        int,
        Parameter(
            name=["-n", "--limit"],
            help="Maximum number of entries to show (default: 50)",
        ),
    ] = 50,
    grep: Annotated[
        str | None,
        Parameter(
            name=["-g", "--grep"],
            help="Filter entries matching regex pattern",
        ),
    ] = None,
    session: Annotated[
        str | None,
        Parameter(
            name=["--session"],
            help="Filter by session ID (prefix match)",
        ),
    ] = None,
    rule_id: Annotated[
        str | None,
        Parameter(
            name=["--rule-id"],
            help="Filter by hook rule ID",
        ),
    ] = None,
    tool_name: Annotated[
        str | None,
        Parameter(
            name=["--tool-name"],
            help="Filter by tool name (for PreToolUse events)",
        ),
    ] = None,
    where: Annotated[
        list[str] | None,
        Parameter(
            name=["-w", "--where"],
            help="Filter with expression (e.g., 'count > 0', 'level = error')",
        ),
    ] = None,
    plain: Annotated[
        bool,
        Parameter(
            name=["--plain"],
            help="Plain output without colors (for piping)",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format"],
            help="Output format: text (default), json",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """View and filter OAPS logs.

    Displays log entries from hooks, CLI, or session logs with powerful
    filtering options. Use --follow for real-time tail mode.

    Examples:
        oaps logs                           # Recent hook logs
        oaps logs cli                       # CLI command logs
        oaps logs session:a39cb323          # Session logs by prefix
        oaps logs all --since 1h            # All logs from last hour
        oaps logs -e hook_completed         # Filter by event
        oaps logs -w 'count > 0'            # Filter with expression
        oaps logs -f                        # Follow mode (tail -f)
        oaps logs -v                        # Include debug entries

    Exit codes:
        0: Success
        1: Failed to load log file
        2: Log source not found
        3: Invalid filter expression
    """
    console = Console(force_terminal=not plain, no_color=plain)

    # Handle verbose flag
    effective_level = "debug" if verbose else level

    # Resolve source
    try:
        resolved_source = resolve_source(source)
    except FileNotFoundError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise SystemExit(ExitCode.NOT_FOUND) from None
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(ExitCode.NOT_FOUND) from None

    # Parse time filters
    try:
        since_dt = _parse_time_filter(since)
        until_dt = _parse_time_filter(until)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(ExitCode.VALIDATION_ERROR) from None

    # Build filter expression
    try:
        filter_expr = _build_filter_expr(
            level=effective_level,
            events=event,
            since_dt=since_dt,
            until_dt=until_dt,
            grep_pattern=grep,
            session_filter=session,
            rule_id_filter=rule_id,
            tool_name_filter=tool_name,
            where_clauses=where,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(ExitCode.VALIDATION_ERROR) from None

    # Handle follow mode
    if follow:
        from ._follow import follow_logs

        follow_logs(
            source=resolved_source,
            filter_expr=filter_expr,
            level=effective_level,
            plain=plain,
            console=console,
        )
        # follow_logs doesn't return (runs until interrupt)

    # Query mode: load and filter logs
    try:
        df = load_logs(resolved_source)
    except FileNotFoundError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise SystemExit(ExitCode.NOT_FOUND) from None
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing log file: {e}[/red]")
        raise SystemExit(ExitCode.LOAD_ERROR) from None

    if df.height == 0:
        console.print("[yellow]No log entries found.[/yellow]")
        exit_with_success()

    # Apply filters
    if filter_expr is not None:
        try:
            df = df.filter(filter_expr)
        except pl.exceptions.ColumnNotFoundError as e:
            console.print(f"[red]Filter error - column not found: {e}[/red]")
            raise SystemExit(ExitCode.VALIDATION_ERROR) from None
        except pl.exceptions.StructFieldNotFoundError as e:
            console.print(f"[red]Filter error - field not found: {e}[/red]")
            raise SystemExit(ExitCode.VALIDATION_ERROR) from None

    if df.height == 0:
        console.print("[yellow]No entries match the filters.[/yellow]")
        exit_with_success()

    # Sort by timestamp (most recent last for natural reading order)
    if "timestamp" in df.columns:
        df = df.sort("timestamp", descending=False)

    # Apply limit (take last N entries)
    if limit > 0 and df.height > limit:
        df = df.tail(limit)

    # Output formatting
    if format == OutputFormat.JSON:
        print(_format_json_output(df))
    else:
        # Compact text format
        for row in df.to_dicts():
            line = _format_compact_entry(row, resolved_source)
            if plain:
                print(line)
            else:
                # Add color based on level
                level_val = str(row.get("level", "")).lower()
                if level_val == "error":
                    console.print(f"[red]{line}[/red]")
                elif level_val == "warning":
                    console.print(f"[yellow]{line}[/yellow]")
                elif level_val == "debug":
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(line)

    exit_with_success()
