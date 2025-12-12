# pyright: reportAny=false
"""Shared utilities for OAPS CLI commands."""

import polars as pl

# Schema inference length for Polars JSONL parsing
# Higher value captures sparse fields like 'error' that only appear on some entries
SCHEMA_INFER_LENGTH = 10000


def parse_log_to_dataframe(log_path: str) -> pl.DataFrame:
    """Parse JSONL hook log file into a Polars DataFrame.

    Uses a high infer_schema_length to capture sparse fields that
    may only appear in certain log entries (e.g., 'error' fields
    that only appear on error-level entries).

    Args:
        log_path: Path to the hooks.log JSONL file.

    Returns:
        DataFrame with parsed log entries.

    Raises:
        FileNotFoundError: If log file doesn't exist.
        pl.exceptions.ComputeError: If log file is malformed.
    """
    return pl.read_ndjson(log_path, infer_schema_length=SCHEMA_INFER_LENGTH)


def normalize_session_ids(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize session IDs by removing UUID wrapper format.

    Handles both UUID('...') format and plain string session IDs.

    Args:
        df: DataFrame with session_id column.

    Returns:
        DataFrame with session_id_normalized column added.
    """
    if "session_id" not in df.columns:
        return df

    return df.with_columns(
        pl.col("session_id")
        .cast(pl.Utf8)
        .str.replace(r"^UUID\('(.+)'\)$", "$1")
        .alias("session_id_normalized")
    )


def count_unique_sessions(df: pl.DataFrame) -> int:
    """Count unique sessions in a DataFrame.

    Args:
        df: DataFrame with session_id column.

    Returns:
        Number of unique sessions.
    """
    if "session_id" not in df.columns:
        return 0

    normalized = normalize_session_ids(df)
    return normalized.select("session_id_normalized").n_unique()


def get_time_range(df: pl.DataFrame) -> tuple[str | None, str | None]:
    """Extract time range from timestamp column.

    Args:
        df: DataFrame with timestamp column.

    Returns:
        Tuple of (start_timestamp, end_timestamp), or (None, None) if unavailable.
    """
    if "timestamp" not in df.columns or df.height == 0:
        return None, None

    timestamps = df.select("timestamp").to_series()
    return str(timestamps.min()), str(timestamps.max())
