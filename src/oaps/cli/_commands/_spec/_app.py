# ruff: noqa: E402
# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Spec command app definition."""

from typing import Annotated

from cyclopts import App, Parameter

app = App(name="spec", help="Create and manage specifications", help_on_error=True)

# Import and mount req subcommand group (must be after app definition)
from ._req_app import req_app

app.command(req_app)

# Import and mount test subcommand group
from ._test_app import test_app

app.command(test_app)

# Import and mount artifact subcommand group
from ._artifact_app import artifact_app

app.command(artifact_app)

# Import and mount history subcommand group
from ._history_app import history_app

app.command(history_app)

# =============================================================================
# Save Command
# =============================================================================


@app.command(name="save")
def save(
    spec_id: str,
    /,
    *,
    message: Annotated[
        str,
        Parameter(name=["--message", "-m"], help="Commit message for the save"),
    ],
    all_: Annotated[
        bool,
        Parameter(
            name=["--all", "-a"],
            help="Include all uncommitted files within the spec directory",
        ),
    ] = False,
) -> None:
    """Save changes to a specification.

    Commits changes to the OAPS repository for a specific specification.
    Only files within the spec directory are committed.

    Args:
        spec_id: The specification ID.
        message: Commit message describing the changes.
        all_: If True, commit all uncommitted files within the spec directory.
            Otherwise, only commit staged/modified files.
    """
    from pathlib import Path

    from oaps.cli._commands._context import CLIContext
    from oaps.cli._commands._shared import exit_with_error, exit_with_success
    from oaps.exceptions import OapsRepositoryNotInitializedError, SpecNotFoundError
    from oaps.repository import OapsRepository

    from ._errors import exit_code_for_exception
    from ._helpers import get_error_console, get_spec_manager

    console = get_error_console()

    try:
        # Validate spec exists and get metadata
        spec_manager = get_spec_manager()
        spec = spec_manager.get_spec(spec_id)

        # Compute spec directory path
        spec_dir = spec_manager.base_path / f"{spec_id}-{spec.slug}"

        # Get project root from CLI context
        ctx = CLIContext.get_current()
        project_root = ctx.project_root if ctx.project_root else Path.cwd()

        # Open OAPS repository
        with OapsRepository(project_root) as repo:
            # Get status to find uncommitted files
            status = repo.get_status()

            # Collect all uncommitted files within the spec directory
            all_uncommitted = set(status.staged) | set(status.modified)
            if all_:
                all_uncommitted |= set(status.untracked)

            # Filter to only files within the spec directory
            spec_files = [
                p for p in all_uncommitted if p.is_relative_to(spec_dir.resolve())
            ]

            if not spec_files:
                console.print("Nothing to save.")
                exit_with_success()

            # Commit the files
            result = repo.commit_files(spec_files, message)

            if result.no_changes:
                console.print("Nothing to save.")
                exit_with_success()

            sha_short = result.sha[:8] if result.sha else "unknown"
            file_count = len(result.files)
            msg = f"[green]Saved[/green] {file_count} file(s) [dim]({sha_short})[/dim]"
            console.print(msg)
            exit_with_success()

    except (SpecNotFoundError, OapsRepositoryNotInitializedError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))
