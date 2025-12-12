# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""File I/O utilities for the OAPS specification system.

This module provides functions for reading and writing specification files
in JSON, JSONL, and Markdown with YAML frontmatter formats. All write
operations use atomic patterns to prevent data corruption.
"""

import tempfile
from pathlib import Path
from typing import Any

import orjson
import yaml

from oaps.exceptions import SpecIOError, SpecParseError

__all__ = [
    "append_jsonl",
    "read_json",
    "read_jsonl",
    "read_markdown_frontmatter",
    "write_json_atomic",
    "write_markdown_with_frontmatter",
]


def _atomic_write(path: Path, content: bytes | str) -> None:
    """Write content to a file atomically.

    Writes to a temporary file in the same directory, then renames to the
    target path. This ensures the file is either fully written or not at all.

    Args:
        path: Destination file path.
        content: Content to write (bytes or string).

    Raises:
        SpecIOError: If the write operation fails.
    """
    # Create parent directories if needed
    _ = path.parent.mkdir(parents=True, exist_ok=True)

    # Determine mode and encoding based on content type
    is_bytes = isinstance(content, bytes)
    mode = "wb" if is_bytes else "w"
    encoding = None if is_bytes else "utf-8"

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode=mode,
            dir=path.parent,
            delete=False,
            suffix=".tmp",
            encoding=encoding,
        ) as f:
            _ = f.write(content)
            temp_path = Path(f.name)

        # Path.replace() is atomic on both POSIX and Windows
        _ = temp_path.replace(path)

    except OSError as e:
        # Clean up temp file on failure
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        msg = f"Failed to write file: {e}"
        raise SpecIOError(msg, path=path, operation="write", cause=e) from e


def read_json(
    path: Path,
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        The parsed JSON data as a dictionary.

    Raises:
        SpecIOError: If the file cannot be read.
        SpecParseError: If the content is not valid JSON or not a dictionary.
    """
    try:
        content = path.read_bytes()
    except OSError as e:
        msg = f"Failed to read file: {e}"
        raise SpecIOError(msg, path=path, operation="read", cause=e) from e

    try:
        data = orjson.loads(content)
    except orjson.JSONDecodeError as e:
        msg = f"Invalid JSON: {e}"
        raise SpecParseError(msg, path=path, content_type="json", cause=e) from e

    if not isinstance(data, dict):
        msg = f"Expected JSON object, got {type(data).__name__}"
        raise SpecParseError(msg, path=path, content_type="json")

    return data


def write_json_atomic(
    path: Path,
    data: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> None:
    """Write a dictionary as JSON atomically.

    Serializes with indentation for readability and uses atomic write
    pattern to prevent data corruption.

    Args:
        path: Destination file path.
        data: Dictionary to serialize as JSON.

    Raises:
        SpecIOError: If the write operation fails.
    """
    try:
        content = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
    except TypeError as e:
        msg = f"Failed to serialize JSON: {e}"
        raise SpecIOError(msg, path=path, operation="write", cause=e) from e

    _atomic_write(path, content)


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:  # pyright: ignore[reportExplicitAny]
    """Read and parse a JSONL (JSON Lines) file.

    Returns an empty list for missing or empty files, making this suitable
    for history files that may not exist yet.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of parsed JSON objects, one per line.

    Raises:
        SpecIOError: If the file exists but cannot be read.
        SpecParseError: If a line contains invalid JSON or is not a dictionary.
    """
    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        msg = f"Failed to read file: {e}"
        raise SpecIOError(msg, path=path, operation="read", cause=e) from e

    if not content.strip():
        return []

    entries: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]
    for line_num, line in enumerate(content.splitlines(), start=1):
        # Skip blank lines
        if not line.strip():
            continue

        try:
            data = orjson.loads(line)
        except orjson.JSONDecodeError as e:
            msg = f"Invalid JSON on line {line_num}: {e}"
            raise SpecParseError(
                msg, path=path, line=line_num, content_type="jsonl", cause=e
            ) from e

        if not isinstance(data, dict):
            msg = f"Expected JSON object on line {line_num}, got {type(data).__name__}"
            raise SpecParseError(msg, path=path, line=line_num, content_type="jsonl")

        entries.append(data)

    return entries


def append_jsonl(
    path: Path,
    entry: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> None:
    """Append a JSON object to a JSONL file.

    Creates parent directories if needed. Uses append mode which provides
    natural concurrency safety for single-line writes.

    Args:
        path: Path to the JSONL file.
        entry: Dictionary to append as a JSON line.

    Raises:
        SpecIOError: If the append operation fails.
    """
    # Create parent directories if needed
    _ = path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Compact JSON (no indentation) for JSONL format
        content = orjson.dumps(entry)
    except TypeError as e:
        msg = f"Failed to serialize JSON: {e}"
        raise SpecIOError(msg, path=path, operation="append", cause=e) from e

    try:
        with path.open("ab") as f:
            _ = f.write(content)
            _ = f.write(b"\n")
    except OSError as e:
        msg = f"Failed to append to file: {e}"
        raise SpecIOError(msg, path=path, operation="append", cause=e) from e


def read_markdown_frontmatter(
    path: Path,
) -> tuple[dict[str, Any], str]:  # pyright: ignore[reportExplicitAny]
    """Read a Markdown file and extract YAML frontmatter.

    Returns an empty dictionary for frontmatter if no frontmatter block
    is found (this is not an error).

    Args:
        path: Path to the Markdown file.

    Returns:
        A tuple of (frontmatter dict, body content). If no frontmatter block
        is found, returns ({}, full_content).

    Raises:
        SpecIOError: If the file cannot be read.
        SpecParseError: If the frontmatter contains malformed YAML.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        msg = f"Failed to read file: {e}"
        raise SpecIOError(msg, path=path, operation="read", cause=e) from e

    # Check for frontmatter delimiter at start (requires newline after ---)
    if not content.startswith("---\n"):
        return {}, content

    # Find the closing delimiter (must be on its own line)
    end_marker = content.find("\n---", 3)
    if end_marker == -1:
        return {}, content

    frontmatter_str = content[4:end_marker].strip()  # Skip "---\n"
    body = content[end_marker + 4 :].lstrip("\n")  # Skip "\n---"

    try:
        frontmatter_data = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML in frontmatter: {e}"
        raise SpecParseError(msg, path=path, content_type="frontmatter", cause=e) from e

    # Handle empty frontmatter (---\n---)
    if frontmatter_data is None:
        return {}, body

    if not isinstance(frontmatter_data, dict):
        actual_type = type(frontmatter_data).__name__
        msg = f"Expected YAML mapping in frontmatter, got {actual_type}"
        raise SpecParseError(msg, path=path, content_type="frontmatter")

    return frontmatter_data, body


def write_markdown_with_frontmatter(
    path: Path,
    frontmatter: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    content: str,
) -> None:
    """Write a Markdown file with YAML frontmatter.

    Uses atomic write pattern to prevent data corruption.

    Args:
        path: Destination file path.
        frontmatter: Dictionary to serialize as YAML frontmatter.
        content: Markdown body content.

    Raises:
        SpecIOError: If the write operation fails.
    """
    try:
        # Use safe_dump with default_flow_style=False for readable YAML
        frontmatter_yaml = yaml.safe_dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=True,
        )
    except yaml.YAMLError as e:
        msg = f"Failed to serialize YAML: {e}"
        raise SpecIOError(msg, path=path, operation="write", cause=e) from e

    # Build the full document
    body = content.strip()
    full_content = f"---\n{frontmatter_yaml}---\n\n{body}\n"

    _atomic_write(path, full_content)
