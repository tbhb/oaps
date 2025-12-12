# pyright: reportAny=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# ruff: noqa: PLR2004, TC003
"""Log source resolution and loading."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

from oaps.utils import (
    get_oaps_cli_log_file,
    get_oaps_hooks_log_file,
    get_oaps_log_dir,
)

LogSourceType = Literal["hooks", "cli", "session", "all"]

_SCHEMA_INFER_LENGTH = 10000


def _get_sessions_log_dir() -> Path:
    """Get the sessions log directory path."""
    return get_oaps_log_dir() / "sessions"


@dataclass(frozen=True, slots=True)
class LogSource:
    """Resolved log source with metadata.

    Attributes:
        name: Display name (e.g., "hooks", "cli", "sess:a39cb323").
        paths: One or more log file paths.
        source_type: The type of log source.
    """

    name: str
    paths: tuple[Path, ...]
    source_type: LogSourceType


def resolve_source(source: str) -> LogSource:
    """Resolve a source specifier to a LogSource.

    Args:
        source: One of "hooks", "cli", "session:<id>", or "all".

    Returns:
        LogSource with resolved paths.

    Raises:
        ValueError: If source format is invalid.
        FileNotFoundError: If no matching log files found.
    """
    source_lower = source.lower()

    if source_lower == "hooks":
        path = get_oaps_hooks_log_file()
        if not path.exists():
            msg = f"Hooks log not found: {path}"
            raise FileNotFoundError(msg)
        return LogSource(name="hooks", paths=(path,), source_type="hooks")

    if source_lower == "cli":
        path = get_oaps_cli_log_file()
        if not path.exists():
            msg = f"CLI log not found: {path}"
            raise FileNotFoundError(msg)
        return LogSource(name="cli", paths=(path,), source_type="cli")

    if source_lower.startswith("session:"):
        prefix = source[8:]  # Remove "session:" prefix
        return _resolve_session_source(prefix)

    if source_lower == "all":
        return _resolve_all_sources()

    msg = f"Invalid source: {source!r}. Use 'hooks', 'cli', 'session:<id>', or 'all'."
    raise ValueError(msg)


def _resolve_session_source(prefix: str) -> LogSource:
    """Resolve a session source by ID prefix.

    Args:
        prefix: Session ID or prefix to match.

    Returns:
        LogSource with matching session log paths.

    Raises:
        FileNotFoundError: If no matching sessions found.
    """
    sessions_dir = _get_sessions_log_dir()
    if not sessions_dir.exists():
        msg = f"Sessions directory not found: {sessions_dir}"
        raise FileNotFoundError(msg)

    # Find matching session files
    pattern = f"{prefix}*.log"
    matches = sorted(sessions_dir.glob(pattern))

    if not matches:
        # List available sessions for helpful error
        available = sorted(sessions_dir.glob("*.log"))
        if available:
            available_ids = [p.stem[:16] + "..." for p in available[:5]]
            suffix = f" ({len(available) - 5} more)" if len(available) > 5 else ""
            msg = (
                f"No sessions matching '{prefix}'. "
                f"Available: {', '.join(available_ids)}{suffix}"
            )
        else:
            msg = f"No session logs found in {sessions_dir}"
        raise FileNotFoundError(msg)

    # Build display name
    if len(matches) == 1:
        short_id = matches[0].stem[:8]
        name = f"sess:{short_id}"
    else:
        name = f"sess:{prefix}*({len(matches)})"

    return LogSource(
        name=name,
        paths=tuple(matches),
        source_type="session",
    )


def _resolve_all_sources() -> LogSource:
    """Resolve all available log sources.

    Returns:
        LogSource with all available log file paths.

    Raises:
        FileNotFoundError: If no log files found at all.
    """
    paths: list[Path] = []

    # Add hooks log if exists
    hooks_path = get_oaps_hooks_log_file()
    if hooks_path.exists():
        paths.append(hooks_path)

    # Add CLI log if exists
    cli_path = get_oaps_cli_log_file()
    if cli_path.exists():
        paths.append(cli_path)

    # Add all session logs
    sessions_dir = _get_sessions_log_dir()
    if sessions_dir.exists():
        paths.extend(sorted(sessions_dir.glob("*.log")))

    if not paths:
        msg = "No log files found"
        raise FileNotFoundError(msg)

    return LogSource(
        name="all",
        paths=tuple(paths),
        source_type="all",
    )


def _infer_source_hint(path: Path) -> str:
    """Infer a source hint from a log file path.

    Args:
        path: Path to a log file.

    Returns:
        Source hint string (e.g., "hooks", "cli", "sess:abc12345").
    """
    if path.name == "hooks.log":
        return "hooks"
    if path.name == "cli.log":
        return "cli"
    # Session log: extract first 8 chars of session ID
    return f"sess:{path.stem[:8]}"


def load_logs(source: LogSource) -> pl.DataFrame:
    """Load logs from a source into a DataFrame.

    Adds a '_source' column to identify the origin of each entry.
    Handles missing columns gracefully by using diagonal concatenation.

    Args:
        source: Resolved log source.

    Returns:
        DataFrame with log entries and '_source' column.

    Raises:
        FileNotFoundError: If log files don't exist.
        pl.exceptions.ComputeError: If log files are malformed.
    """
    if len(source.paths) == 1:
        df = _load_single_log(source.paths[0])
        hint = _infer_source_hint(source.paths[0])
        return df.with_columns(pl.lit(hint).alias("_source"))

    # Multiple files: load and merge
    dfs: list[pl.DataFrame] = []
    for path in source.paths:
        if not path.exists():
            continue
        try:
            df = _load_single_log(path)
            hint = _infer_source_hint(path)
            df = df.with_columns(pl.lit(hint).alias("_source"))
            # Normalize core columns to strings to avoid type conflicts
            df = _normalize_schema(df)
            dfs.append(df)
        except pl.exceptions.ComputeError:
            # Skip malformed files
            continue

    if not dfs:
        # Return empty DataFrame with expected columns
        return pl.DataFrame(
            {
                "timestamp": pl.Series([], dtype=pl.Utf8),
                "level": pl.Series([], dtype=pl.Utf8),
                "event": pl.Series([], dtype=pl.Utf8),
                "_source": pl.Series([], dtype=pl.Utf8),
            }
        )

    # Diagonal concat handles schema differences
    return pl.concat(dfs, how="diagonal")


def _normalize_schema(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize DataFrame columns to consistent types.

    Casts all columns to strings to avoid type conflicts when merging
    DataFrames from different log sources. This is necessary because
    the same field may be serialized as different types (e.g., "count"
    may be Int64 in one log and String in another).

    Struct columns are serialized to JSON strings.

    Args:
        df: DataFrame to normalize.

    Returns:
        DataFrame with all columns as strings.
    """
    cast_exprs = []
    for col_name in df.columns:
        dtype = df[col_name].dtype
        if dtype == pl.Utf8:
            # Already a string
            cast_exprs.append(pl.col(col_name))
        elif isinstance(dtype, pl.Struct):
            # Serialize struct to JSON
            expr = pl.col(col_name).struct.json_encode().alias(col_name)
            cast_exprs.append(expr)
        elif isinstance(dtype, pl.List):
            # Serialize list to string (join with comma after casting to string)
            expr = (
                pl.col(col_name).cast(pl.List(pl.Utf8)).list.join(", ").alias(col_name)
            )
            cast_exprs.append(expr)
        else:
            # Cast primitive types to string
            cast_exprs.append(pl.col(col_name).cast(pl.Utf8).alias(col_name))

    return df.select(cast_exprs)


def _load_single_log(path: Path) -> pl.DataFrame:
    """Load a single log file into a DataFrame.

    Args:
        path: Path to the log file.

    Returns:
        DataFrame with log entries.
    """
    return pl.read_ndjson(str(path), infer_schema_length=_SCHEMA_INFER_LENGTH)


def list_sessions(limit: int = 10) -> list[tuple[str, Path]]:
    """List available session log files.

    Args:
        limit: Maximum number of sessions to return.

    Returns:
        List of (session_id, path) tuples, sorted by modification time.
    """
    sessions_dir = _get_sessions_log_dir()
    if not sessions_dir.exists():
        return []

    # Get session files sorted by mtime (most recent first)
    session_files = sorted(
        sessions_dir.glob("*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return [(p.stem, p) for p in session_files[:limit]]
