# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportImplicitStringConcatenation=false
# ruff: noqa: D415, FBT002
"""OAPS repository management commands."""

import sys
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from pathlib import Path

from cyclopts import Parameter
from rich.console import Console

from oaps.exceptions import OapsRepositoryNotInitializedError
from oaps.repository import OapsRepository

from ._app import app

__all__ = ["app"]


def _get_repo() -> OapsRepository:
    """Get OapsRepository instance, handling initialization errors.

    Returns:
        OapsRepository instance.

    Raises:
        SystemExit: If repository is not initialized.
    """
    try:
        return OapsRepository()
    except OapsRepositoryNotInitializedError:
        console = Console()
        msg = (
            "[red]Error:[/red] OAPS repository not initialized. "
            "Run from a directory with .oaps/ initialized."
        )
        console.print(msg)
        sys.exit(1)


@app.command(name="status")
def _status() -> None:
    """Show uncommitted changes in .oaps/"""
    console = Console()

    with _get_repo() as repo:
        status = repo.get_status()

        if not status.staged and not status.modified and not status.untracked:
            console.print("[dim]No uncommitted changes in .oaps/[/dim]")
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


@app.command(name="commit")
def _commit(
    message: Annotated[
        str,
        Parameter(
            name=["--message", "-m"],
            help="Commit message",
        ),
    ] = "Manual checkpoint",
    session_id: Annotated[
        str | None,
        Parameter(
            name=["--session-id"],
            help="Session ID to include in commit trailer",
        ),
    ] = None,
) -> None:
    """Commit all pending changes in .oaps/"""
    console = Console()

    with _get_repo() as repo:
        result = repo.commit_pending(message, session_id=session_id)

        if result.no_changes:
            console.print("[dim]Nothing to commit[/dim]")
            return

        console.print(f"[green]Committed {len(result.files)} file(s)[/green]")
        console.print(f"[dim]SHA: {result.sha}[/dim]")


@app.command(name="discard")
def _discard(
    paths: Annotated[
        tuple[str, ...] | None,
        Parameter(
            help="Specific paths to discard (relative to .oaps/). "
            "If not provided, discards all changes.",
        ),
    ] = None,
    force: Annotated[
        bool,
        Parameter(
            name=["--force", "-f"],
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Discard uncommitted changes in .oaps/

    Restores tracked files to their HEAD state. Does not remove untracked files.
    """
    console = Console()

    with _get_repo() as repo:
        # Convert paths if provided
        path_list: list[Path] | None = None
        if paths:
            path_list = [repo.root / p for p in paths]

        # Check for changes first
        status = repo.get_status()
        has_changes = bool(status.staged or status.modified)

        if not has_changes:
            console.print("[dim]No changes to discard[/dim]")
            return

        # Confirm if not forced
        if not force:
            count = len(status.staged) + len(status.modified)
            console.print(
                f"[yellow]This will discard changes to {count} file(s). "
                "Use --force to confirm.[/yellow]"
            )
            sys.exit(1)

        result = repo.discard_changes(path_list)

        if result.no_changes:
            console.print("[dim]No changes to discard[/dim]")
            return

        if result.unstaged:
            console.print(f"[green]Unstaged {len(result.unstaged)} file(s)[/green]")
        if result.restored:
            console.print(f"[green]Restored {len(result.restored)} file(s)[/green]")


@app.command(name="log")
def _log(
    n: Annotated[
        int,
        Parameter(
            name=["--number", "-n"],
            help="Number of commits to show",
        ),
    ] = 10,
) -> None:
    """Show recent commits in .oaps/"""
    console = Console()

    with _get_repo() as repo:
        commits = repo.get_last_commits(n)

        if not commits:
            console.print("[dim]No commits yet[/dim]")
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


if __name__ == "__main__":
    app()
