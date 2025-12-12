"""Skeleton file watcher using watchfiles.

This module provides a placeholder file watcher that can be run as a
subprocess to monitor file changes. Output is printed to stdout for
consumption by the supervisor.

The watcher is designed to be extended with filtering and event
transformation logic in future versions.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pathspec import PathSpec
    from watchfiles import Change


def format_change(change: Change, path: str) -> str:
    """Format a file change event as a string.

    Args:
        change: The type of change (added, modified, deleted).
        path: The path to the changed file.

    Returns:
        A formatted string describing the change.
    """
    from watchfiles import Change as WatchChange  # noqa: PLC0415

    change_names = {
        WatchChange.added: "added",
        WatchChange.modified: "modified",
        WatchChange.deleted: "deleted",
    }
    change_name = change_names.get(change, "unknown")
    return f"{change_name}: {path}"


def watch_directory(
    path: Path,
    *,
    recursive: bool = True,
    ignore_patterns: Iterable[str] | None = None,
    pathspec: PathSpec | None = None,
) -> None:
    """Watch a directory for file changes and print events to stdout.

    This is a blocking function that runs indefinitely until interrupted.
    Each change event is printed to stdout as a single line.

    Args:
        path: The directory to watch.
        recursive: Whether to watch subdirectories.
        ignore_patterns: Glob patterns for files to ignore (legacy, deprecated).
        pathspec: A PathSpec for gitignore-style pattern matching.
            Takes precedence over ignore_patterns if provided.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    from watchfiles import watch  # noqa: PLC0415

    from oaps.utils._ignore import matches_any  # noqa: PLC0415

    # Build filter based on what's provided
    ignore_set = set(ignore_patterns) if ignore_patterns else None

    def should_watch(_change: Change, changed_path: str) -> bool:
        """Filter function for watchfiles.

        Args:
            _change: The type of change (unused).
            changed_path: The path that changed.

        Returns:
            True if the change should be reported.
        """
        # Use pathspec-based matching if available (preferred)
        if pathspec is not None:
            # Make path relative to watched directory for better matching
            try:
                rel_path = Path(changed_path).relative_to(path)
                return not matches_any(pathspec, rel_path)
            except ValueError:
                # Path not relative to watched dir, use absolute
                return not matches_any(pathspec, changed_path)

        # Fall back to legacy pattern matching
        if ignore_set is None:
            return True

        changed = Path(changed_path)
        return all(not changed.match(pattern) for pattern in ignore_set)

    # Watch with filtering
    for changes in watch(path, recursive=recursive, watch_filter=should_watch):
        for change, changed_path in changes:
            line = format_change(change, changed_path)
            # Print to stdout for supervisor to capture
            # Using print here since this is CLI output
            print(line, flush=True)  # noqa: T201
