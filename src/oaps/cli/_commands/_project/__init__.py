# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportImplicitStringConcatenation=false
# ruff: noqa: D415, FBT002
"""Commands for project state and Git operations."""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import Parameter
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from oaps.cli._commands._shared import ExitCode, exit_with_error
from oaps.exceptions import ProjectRepositoryNotInitializedError
from oaps.repository import ProjectRepository

from ._app import app

if TYPE_CHECKING:
    from oaps.utils import SQLiteStateStore, StateEntry, StateStoreValue

__all__ = ["ExitCode", "app"]

# Time constants for relative time formatting (in seconds)
_SECONDS_PER_MINUTE: int = 60
_SECONDS_PER_HOUR: int = 3600
_SECONDS_PER_DAY: int = 86400
_SECONDS_PER_WEEK: int = 604800
_SECONDS_PER_MONTH: int = 2592000
_SECONDS_PER_YEAR: int = 31536000

# Maximum author name display length in blame output
_MAX_AUTHOR_DISPLAY_LENGTH: int = 20


def _get_store() -> SQLiteStateStore:
    """Get or create a state store for the project.

    Returns:
        A SQLiteStateStore instance scoped to the project (session_id=None).
    """
    from oaps.utils import SQLiteStateStore, get_oaps_state_file

    db_path = get_oaps_state_file()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStateStore(db_path, session_id=None)


def _parse_value(value: str) -> StateStoreValue:
    """Parse a string value into the appropriate type.

    Attempts to parse as int first, then float, falling back to string.

    Args:
        value: The string value from CLI input.

    Returns:
        The parsed value as int, float, or the original string.
    """
    # Try int first
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Fall back to string
    return value


def _format_value(value: StateStoreValue) -> str:
    """Format a project store value for display.

    Args:
        value: The value to format.

    Returns:
        A string representation of the value.
    """
    if value is None:
        return "null"
    if isinstance(value, bytes):
        return f"<bytes: {len(value)} bytes>"
    return str(value)


def _format_entry_verbose(entry: StateEntry) -> str:
    """Format a project store entry with full metadata.

    Args:
        entry: The entry to format.

    Returns:
        A formatted string with all metadata.
    """
    lines = [
        f"key: {entry.key}",
        f"value: {_format_value(entry.value)}",
        f"created_at: {entry.created_at}",
        f"created_by: {entry.created_by or 'null'}",
        f"updated_at: {entry.updated_at}",
        f"updated_by: {entry.updated_by or 'null'}",
    ]
    return "\n".join(lines)


@app.command(name="get")
def _get(
    key: str,
    /,
    verbose: Annotated[bool, Parameter(help="Show full entry metadata")] = False,
) -> None:
    """Get a value from the project store

    Args:
        key: The key to look up
        verbose: Whether to show full entry metadata
    """
    store = _get_store()

    if verbose:
        entry = store.get_entry(key)
        if entry is None:
            print(f"Error: Key '{key}' not found")
            raise SystemExit(ExitCode.NOT_FOUND)
        print(_format_entry_verbose(entry))
    else:
        if key not in store:
            print(f"Error: Key '{key}' not found")
            raise SystemExit(ExitCode.NOT_FOUND)
        print(_format_value(store[key]))


@app.command(name="set")
def _set(
    key: str,
    value: str,
    /,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
    string: Annotated[
        bool, Parameter(help="Store value as string (skip numeric detection)")
    ] = False,
) -> None:
    """Set a value in the project store

    By default, numeric values are detected and stored as int/float.
    Use --string to force storing as a string.

    Args:
        key: The key to set
        value: The value to store
        author: Optional author attribution
        string: Force storing as string
    """
    store = _get_store()
    parsed_value = value if string else _parse_value(value)
    store.set(key, parsed_value, author=author)
    print(f"Set '{key}' = {parsed_value}")


@app.command(name="delete")
def _delete(
    key: str,
    /,
) -> None:
    """Delete a key from the project store

    Args:
        key: The key to delete
    """
    store = _get_store()
    if store.delete(key):
        print(f"Deleted '{key}'")
    else:
        print(f"Key '{key}' not found")
        raise SystemExit(ExitCode.NOT_FOUND)


@app.command(name="clear")
def _clear(
    force: Annotated[bool, Parameter(help="Skip confirmation prompt")] = False,
) -> None:
    """Clear all entries from the project store

    Args:
        force: Skip confirmation prompt
    """
    store = _get_store()
    count = len(store)

    if count == 0:
        print("Project store is already empty")
        return

    if not force:
        print(f"This will delete {count} entries. Use --force to confirm.")
        raise SystemExit(ExitCode.VALIDATION_ERROR)

    store.clear()
    print(f"Cleared {count} entries from project store")


@app.command(name="increment")
def _increment(
    key: str,
    /,
    amount: Annotated[int, Parameter(help="Amount to increment by")] = 1,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
) -> None:
    """Increment a numeric value in the project store

    Creates the key with the increment amount if it doesn't exist.

    Args:
        key: The key to increment
        amount: Amount to increment by (default 1)
        author: Optional author attribution
    """
    store = _get_store()

    current_value: int = 0
    if key in store:
        existing = store[key]
        if not isinstance(existing, int):
            type_name = type(existing).__name__
            print(f"Error: Key '{key}' exists but is not an integer (got {type_name})")
            raise SystemExit(ExitCode.VALIDATION_ERROR)
        current_value = existing

    new_value = current_value + amount
    store.set(key, new_value, author=author)
    print(f"{key} = {new_value}")


@app.command(name="decrement")
def _decrement(
    key: str,
    /,
    amount: Annotated[int, Parameter(help="Amount to decrement by")] = 1,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
) -> None:
    """Decrement a numeric value in the project store

    Creates the key with the negative decrement amount if it doesn't exist.

    Args:
        key: The key to decrement
        amount: Amount to decrement by (default 1)
        author: Optional author attribution
    """
    store = _get_store()

    current_value: int = 0
    if key in store:
        existing = store[key]
        if not isinstance(existing, int):
            type_name = type(existing).__name__
            print(f"Error: Key '{key}' exists but is not an integer (got {type_name})")
            raise SystemExit(ExitCode.VALIDATION_ERROR)
        current_value = existing

    new_value = current_value - amount
    store.set(key, new_value, author=author)
    print(f"{key} = {new_value}")


@app.command(name="state")
def _state(
    verbose: Annotated[
        bool, Parameter(help="Show full entry metadata for each key")
    ] = False,
) -> None:
    """Show all state in the project store

    Args:
        verbose: Whether to show full entry metadata
    """
    store = _get_store()
    keys = list(store)

    if not keys:
        print("Project store is empty")
        return

    if verbose:
        for i, key in enumerate(keys):
            entry = store.get_entry(key)
            if entry is not None:
                if i > 0:
                    print("---")
                print(_format_entry_verbose(entry))
    else:
        for key in keys:
            value = store[key]
            print(f"{key}: {_format_value(value)}")


# =============================================================================
# Git Commands (project repository, excluding .oaps/)
# =============================================================================


def _get_project_repo() -> ProjectRepository:
    """Get ProjectRepository instance with error handling.

    Returns:
        ProjectRepository instance.

    Raises:
        SystemExit: If not inside a Git repository.
    """
    try:
        return ProjectRepository()
    except ProjectRepositoryNotInitializedError:
        exit_with_error("Not inside a Git repository.", ExitCode.NOT_FOUND)


def _pluralize(count: int, unit: str) -> str:
    """Format a count with unit, pluralized if needed.

    Args:
        count: The numeric value.
        unit: The time unit (e.g., "minute", "hour").

    Returns:
        Formatted string like "2 hours ago" or "1 day ago".
    """
    suffix = "s" if count != 1 else ""
    return f"{count} {unit}{suffix} ago"


def _format_relative_time(timestamp: datetime) -> str:
    """Format a datetime as a human-readable relative time string.

    Args:
        timestamp: The datetime to format.

    Returns:
        A string like "2 days ago", "3 hours ago", "just now", etc.
    """
    now = datetime.now(tz=UTC)
    # Convert timestamp to UTC for comparison
    ts_utc = timestamp.astimezone(UTC)
    diff = now - ts_utc

    seconds = int(diff.total_seconds())

    # Define thresholds and their corresponding formatting
    thresholds: list[tuple[int, int, str]] = [
        (_SECONDS_PER_YEAR, _SECONDS_PER_YEAR, "year"),
        (_SECONDS_PER_MONTH, _SECONDS_PER_MONTH, "month"),
        (_SECONDS_PER_WEEK, _SECONDS_PER_WEEK, "week"),
        (_SECONDS_PER_DAY, _SECONDS_PER_DAY, "day"),
        (_SECONDS_PER_HOUR, _SECONDS_PER_HOUR, "hour"),
        (_SECONDS_PER_MINUTE, _SECONDS_PER_MINUTE, "minute"),
    ]

    if seconds < 0:
        return "in the future"
    if seconds < _SECONDS_PER_MINUTE:
        return "just now"

    for threshold, divisor, unit in thresholds:
        if seconds >= threshold:
            return _pluralize(seconds // divisor, unit)

    return "just now"


@app.command(name="status")
def _git_status() -> None:
    """Show uncommitted changes in project (excluding .oaps/)"""
    console = Console()

    with _get_project_repo() as repo:
        status = repo.get_status()

        if not status.staged and not status.modified and not status.untracked:
            console.print("[dim]No uncommitted changes in project[/dim]")
            return

        if status.staged:
            console.print("[bold green]Staged files:[/bold green]")
            for path in sorted(status.staged):
                rel = path.relative_to(repo.root)
                console.print(f"  [green]+ {rel}[/green]")

        if status.modified:
            console.print("[bold yellow]Modified files:[/bold yellow]")
            for path in sorted(status.modified):
                rel = path.relative_to(repo.root)
                console.print(f"  [yellow]~ {rel}[/yellow]")

        if status.untracked:
            console.print("[bold cyan]Untracked files:[/bold cyan]")
            for path in sorted(status.untracked):
                rel = path.relative_to(repo.root)
                console.print(f"  [cyan]? {rel}[/cyan]")

        total = len(status.staged) + len(status.modified) + len(status.untracked)
        console.print(f"\n[dim]{total} file(s) with uncommitted changes[/dim]")


@app.command(name="diff")
def _diff(
    staged: Annotated[
        bool,
        Parameter(
            name=["--staged", "-s"],
            help="Show staged changes (HEAD vs index) instead of unstaged",
        ),
    ] = False,
) -> None:
    """Show unified diff of uncommitted changes (excluding .oaps/)"""
    console = Console()

    with _get_project_repo() as repo:
        diff_text = repo.get_diff(staged=staged)

        if not diff_text:
            kind = "staged" if staged else "unstaged"
            console.print(f"[dim]No {kind} changes[/dim]")
            return

        # Use Rich syntax highlighting for diff output
        syntax = Syntax(diff_text, lexer="diff", theme="monokai")
        console.print(syntax)


@app.command(name="log")
def _git_log(
    n: Annotated[
        int,
        Parameter(
            name=["--number", "-n"],
            help="Number of commits to show",
        ),
    ] = 10,
    path: Annotated[
        str | None,
        Parameter(
            name=["--path"],
            help="Filter to commits affecting this path",
        ),
    ] = None,
    grep: Annotated[
        str | None,
        Parameter(
            name=["--grep"],
            help="Filter to commits with message containing this string",
        ),
    ] = None,
    author: Annotated[
        str | None,
        Parameter(
            name=["--author"],
            help="Filter to commits by this author (name or email)",
        ),
    ] = None,
) -> None:
    """Show commit history (excluding .oaps/ changes)"""
    console = Console()

    with _get_project_repo() as repo:
        # Convert path string to Path if provided
        path_obj: Path | None = None
        if path is not None:
            path_obj = Path(path)
            # Make absolute if relative
            if not path_obj.is_absolute():
                path_obj = repo.root / path_obj

        commits = repo.get_log(n=n, path=path_obj, grep=grep, author=author)

        if not commits:
            console.print("[dim]No commits found[/dim]")
            return

        for commit in commits:
            # Get first line of message
            subject = (
                commit.message.splitlines()[0] if commit.message else "(no message)"
            )

            console.print(f"[yellow]{commit.sha[:8]}[/yellow] {subject}")
            console.print(f"  [dim]{commit.author_name} <{commit.author_email}>[/dim]")
            console.print(
                f"  [dim]{commit.timestamp.strftime('%Y-%m-%d %H:%M:%S %z')} "
                f"({commit.files_changed} file(s))[/dim]"
            )
            console.print()


@app.command(name="blame")
def _blame(
    path: str,
    /,
    max_commits: Annotated[
        int | None,
        Parameter(
            name=["--max-commits"],
            help="Maximum commits to traverse (reserved for future use)",
        ),
    ] = None,
) -> None:
    """Show file blame with author attribution (excluding .oaps/ files)

    Args:
        path: Path to the file to blame
        max_commits: Reserved for future use
    """
    console = Console()

    with _get_project_repo() as repo:
        # Convert to Path and make absolute if needed
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = repo.root / file_path

        try:
            blame_lines = repo.get_blame(file_path, max_commits=max_commits)
        except FileNotFoundError as e:
            exit_with_error(str(e), ExitCode.NOT_FOUND, console=console)

        if not blame_lines:
            console.print(
                "[dim]No blame information available "
                "(file may be empty or untracked)[/dim]"
            )
            return

        # Create table for blame output
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("SHA", style="yellow", width=8)
        table.add_column("Author", style="cyan", width=_MAX_AUTHOR_DISPLAY_LENGTH)
        table.add_column("When", style="dim", width=14)
        table.add_column("Line", style="dim", justify="right", width=5)
        table.add_column("Content")

        for line in blame_lines:
            # Truncate author name if too long
            author_display = (
                line.author_name[:_MAX_AUTHOR_DISPLAY_LENGTH]
                if len(line.author_name) > _MAX_AUTHOR_DISPLAY_LENGTH
                else line.author_name
            )
            relative_time = _format_relative_time(line.timestamp)

            table.add_row(
                line.sha[:8],
                author_display,
                relative_time,
                str(line.line_no),
                line.content,
            )

        console.print(table)


if __name__ == "__main__":
    app()
