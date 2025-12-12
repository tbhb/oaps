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
    pathspec: PathSpec | None = None,
) -> None:
    """Watch a directory for file changes and print events to stdout.

    This is a blocking function that runs indefinitely until interrupted.
    Each change event is printed to stdout as a single line.

    Args:
        path: The directory to watch.
        recursive: Whether to watch subdirectories.
        pathspec: A PathSpec for gitignore-style pattern matching.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    from watchfiles import watch  # noqa: PLC0415

    def should_watch(_change: Change, changed_path: str) -> bool:
        """Filter function for watchfiles.

        Args:
            _change: The type of change (unused).
            changed_path: The path that changed.

        Returns:
            True if the change should be reported.
        """
        if pathspec is None:
            return True

        # Make path relative to watched directory for better matching
        try:
            rel_path = Path(changed_path).relative_to(path)
            return not pathspec.match_file(str(rel_path))
        except ValueError:
            # Path not relative to watched dir, use absolute
            return not pathspec.match_file(changed_path)

    # Watch with filtering
    for changes in watch(path, recursive=recursive, watch_filter=should_watch):
        for change, changed_path in changes:
            line = format_change(change, changed_path)
            # Print to stdout for supervisor to capture
            # Using print here since this is CLI output
            print(line, flush=True)  # noqa: T201
