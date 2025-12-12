# pyright: reportUnusedCallResult=false
# pyright: reportAny=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
# ruff: noqa: PLR0912, SIM108, TRY300, TC003
"""Follow mode for real-time log tailing."""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import polars as pl
from rich.console import Console

if TYPE_CHECKING:
    from ._sources import LogSource

# Polling interval in seconds
_POLL_INTERVAL = 0.5

# Level ordering for filtering
_LEVEL_ORDER = ["debug", "info", "warning", "error"]

# Display widths (same as _query.py)
_SOURCE_WIDTH = 20
_LEVEL_WIDTH = 5
_EVENT_WIDTH = 24
_SESSION_ID_DISPLAY_LEN = 8
_VALUE_DISPLAY_LEN = 24


def _matches_level(entry_level: str, min_level: str) -> bool:
    """Check if an entry level meets the minimum threshold.

    Args:
        entry_level: The entry's log level.
        min_level: The minimum level to show.

    Returns:
        True if entry should be shown.
    """
    entry_lower = entry_level.lower()
    min_lower = min_level.lower()

    if min_lower not in _LEVEL_ORDER:
        return True

    if entry_lower not in _LEVEL_ORDER:
        return True  # Show unknown levels

    return _LEVEL_ORDER.index(entry_lower) >= _LEVEL_ORDER.index(min_lower)


def _format_entry(entry: dict[str, object], source_hint: str) -> str:
    """Format a log entry as a compact one-liner.

    Args:
        entry: Parsed log entry dictionary.
        source_hint: Source hint string.

    Returns:
        Formatted string.
    """
    # Extract timestamp (time only)
    timestamp = str(entry.get("timestamp", ""))
    if "T" in timestamp:
        time_part = timestamp.split("T")[1][:8]  # HH:MM:SS
    else:
        time_part = timestamp[:8]

    # Build source hint with event type
    display_hint = source_hint
    hook_event = entry.get("hook_event")
    if hook_event and source_hint == "hooks":
        display_hint = f"hooks:{hook_event}"
    elif source_hint.startswith("cli"):
        command = entry.get("command", "")
        if command:
            display_hint = f"cli:{command}"

    # Truncate source hint
    if len(display_hint) > _SOURCE_WIDTH:
        display_hint = display_hint[: _SOURCE_WIDTH - 1] + "…"

    # Level
    level = str(entry.get("level", "")).upper()[:_LEVEL_WIDTH]

    # Event name
    event = str(entry.get("event", ""))
    if len(event) > _EVENT_WIDTH:
        event = event[: _EVENT_WIDTH - 1] + "…"

    # Key-value pairs
    kv_parts: list[str] = []

    session_id = entry.get("session_id")
    if session_id:
        session_str = str(session_id)
        if session_str.startswith("UUID('"):
            session_str = session_str[6:-2]
        if len(session_str) > _SESSION_ID_DISPLAY_LEN:
            session_str = session_str[:_SESSION_ID_DISPLAY_LEN] + "…"
        kv_parts.append(f"session_id={session_str}")

    rule_id = entry.get("rule_id")
    if rule_id:
        kv_parts.append(f"rule_id={rule_id}")

    count = entry.get("count")
    if count is not None:
        kv_parts.append(f"count={count}")

    reason = entry.get("reason")
    if reason:
        reason_str = str(reason)
        if len(reason_str) > _VALUE_DISPLAY_LEN:
            reason_str = reason_str[: _VALUE_DISPLAY_LEN - 1] + "…"
        kv_parts.append(f"reason={reason_str}")

    kv_str = " ".join(kv_parts)

    # Build formatted line
    source_col = f"{display_hint:<{_SOURCE_WIDTH}}"
    level_col = f"{level:<{_LEVEL_WIDTH}}"
    event_col = f"{event:<{_EVENT_WIDTH}}"
    return f"{time_part} {source_col} {level_col} {event_col} {kv_str}"


def _infer_source_hint(path: Path) -> str:
    """Infer source hint from file path."""
    if path.name == "hooks.log":
        return "hooks"
    if path.name == "cli.log":
        return "cli"
    return f"sess:{path.stem[:8]}"


def _apply_polars_filter(entry: dict[str, object], filter_expr: pl.Expr | None) -> bool:
    """Apply a Polars filter expression to a single entry.

    This is less efficient than batch filtering but necessary for streaming.

    Args:
        entry: Log entry dictionary.
        filter_expr: Polars filter expression, or None.

    Returns:
        True if entry passes the filter.
    """
    if filter_expr is None:
        return True

    # Create a single-row DataFrame and apply the filter
    try:
        df = pl.DataFrame([entry])
        filtered = df.filter(filter_expr)
        return filtered.height > 0
    except (pl.exceptions.ComputeError, pl.exceptions.ColumnNotFoundError):
        # If filtering fails, include the entry
        return True


def follow_logs(
    source: LogSource,
    filter_expr: pl.Expr | None,
    level: str,
    *,
    plain: bool = False,
    console: Console | None = None,
) -> NoReturn:
    """Follow log file(s) in real-time.

    Uses simple polling with file position tracking.
    Ctrl+C to exit.

    Args:
        source: Resolved log source.
        filter_expr: Polars filter expression for entries.
        level: Minimum log level to display.
        plain: If True, use plain print instead of Rich.
        console: Rich Console for output (used if not plain).
    """
    if console is None:
        console = Console()

    # Track file positions (byte offsets)
    positions: dict[Path, int] = {}
    for path in source.paths:
        if path.exists():
            positions[path] = path.stat().st_size
        else:
            positions[path] = 0

    # Show initial message
    source_desc = source.name
    if len(source.paths) > 1:
        source_desc = f"{source.name} ({len(source.paths)} files)"

    if plain:
        print(f"Following {source_desc}... (Ctrl+C to stop)")
    else:
        console.print(f"[dim]Following {source_desc}... (Ctrl+C to stop)[/dim]")

    try:
        if plain:
            _follow_plain(source, positions, filter_expr, level)
        else:
            _follow_rich(source, positions, filter_expr, level, console)
    except KeyboardInterrupt:
        if not plain:
            console.print("\n[dim]Stopped.[/dim]")
        raise SystemExit(0) from None


def _follow_plain(
    source: LogSource,
    positions: dict[Path, int],
    filter_expr: pl.Expr | None,
    level: str,
) -> NoReturn:
    """Follow logs with plain text output.

    Args:
        source: Log source.
        positions: File position tracking dict.
        filter_expr: Filter expression.
        level: Minimum log level.
    """
    while True:
        new_entries = _read_new_entries(source, positions, filter_expr, level)
        for entry, source_hint in new_entries:
            line = _format_entry(entry, source_hint)
            print(line, flush=True)

        time.sleep(_POLL_INTERVAL)


def _follow_rich(
    source: LogSource,
    positions: dict[Path, int],
    filter_expr: pl.Expr | None,
    level: str,
    console: Console,
) -> NoReturn:
    """Follow logs with Rich formatted output.

    Args:
        source: Log source.
        positions: File position tracking dict.
        filter_expr: Filter expression.
        level: Minimum log level.
        console: Rich Console.
    """
    while True:
        new_entries = _read_new_entries(source, positions, filter_expr, level)
        for entry, source_hint in new_entries:
            line = _format_entry(entry, source_hint)
            entry_level = str(entry.get("level", "")).lower()

            # Apply color based on level
            if entry_level == "error":
                console.print(f"[red]{line}[/red]")
            elif entry_level == "warning":
                console.print(f"[yellow]{line}[/yellow]")
            elif entry_level == "debug":
                console.print(f"[dim]{line}[/dim]")
            else:
                console.print(line)

        time.sleep(_POLL_INTERVAL)


def _read_new_entries(
    source: LogSource,
    positions: dict[Path, int],
    filter_expr: pl.Expr | None,
    level: str,
) -> list[tuple[dict[str, object], str]]:
    """Read new entries from all source files.

    Args:
        source: Log source.
        positions: File position tracking dict (mutated).
        filter_expr: Filter expression.
        level: Minimum log level.

    Returns:
        List of (entry_dict, source_hint) tuples.
    """
    new_entries: list[tuple[dict[str, object], str]] = []

    for path in source.paths:
        if not path.exists():
            continue

        current_size = path.stat().st_size

        # Handle file truncation (log rotation)
        if current_size < positions.get(path, 0):
            positions[path] = 0

        if current_size <= positions.get(path, 0):
            continue

        # Read new content
        try:
            with path.open() as f:
                f.seek(positions[path])
                new_content = f.read()
            positions[path] = current_size
        except OSError:
            continue

        # Parse new lines
        source_hint = _infer_source_hint(path)
        for line in new_content.strip().split("\n"):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Apply level filter first (cheap)
            entry_level = str(entry.get("level", "info"))
            if not _matches_level(entry_level, level):
                continue

            # Apply other filters
            if not _apply_polars_filter(entry, filter_expr):
                continue

            new_entries.append((entry, source_hint))

    # Sort by timestamp
    new_entries.sort(key=lambda x: str(x[0].get("timestamp", "")))

    return new_entries
