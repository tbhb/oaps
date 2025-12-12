# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportAny=false
# ruff: noqa: D415, PLR0913, TC001, TC003
"""Artifact plumbing commands.

This module provides commands for managing artifacts within specifications.
Commands: add, update, rebuild, list, show, delete.
"""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_error, exit_with_success
from oaps.exceptions import (
    SpecArtifactNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec import ArtifactStatus, ArtifactType

from ._artifact_app import artifact_app
from ._errors import exit_code_for_exception
from ._helpers import (
    ACTOR,
    artifact_to_dict,
    confirm_destructive,
    get_artifact_manager,
    get_error_console,
    parse_qualified_id,
    rebuild_result_to_dict,
)
from ._output import (
    format_artifact_info,
    format_artifact_table,
    format_rebuild_result,
)

__all__ = [
    "add",
    "delete",
    "list_artifacts",
    "rebuild",
    "show",
    "update",
]


@artifact_app.command(name="add")
def add(
    spec_id: str,
    artifact_type: ArtifactType,
    /,
    *,
    title: Annotated[
        str,
        Parameter(name=["--title", "-t"], help="Artifact title"),
    ],
    file: Annotated[
        Path | None,
        Parameter(name=["--file", "-f"], help="Path to existing file to import"),
    ] = None,
    description: Annotated[
        str | None,
        Parameter(
            name=["--description", "-d"], help="Brief description of the artifact"
        ),
    ] = None,
    requirements: Annotated[
        list[str] | None,
        Parameter(
            name=["--requirements", "-r"],
            help="IDs of related requirements (can be repeated)",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="Freeform tags for filtering"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Add a new artifact to a specification

    Args:
        spec_id: The specification ID.
        artifact_type: Artifact type (review, change, analysis, decision, etc.).
        title: Human-readable artifact title.
        file: Path to existing file to import (optional).
        description: Brief description of the artifact.
        requirements: IDs of related requirements.
        tags: Freeform tags for filtering.
        format_: Output format.
    """
    try:
        manager = get_artifact_manager()

        # Determine whether to use content mode or import mode
        if file is not None:
            # Import mode: use source_path
            artifact = manager.add_artifact(
                spec_id,
                artifact_type,
                title,
                source_path=file,
                description=description,
                references=requirements,
                tags=tags,
                actor=ACTOR,
            )
        else:
            # Content mode: create with empty content
            artifact = manager.add_artifact(
                spec_id,
                artifact_type,
                title,
                content="",
                description=description,
                references=requirements,
                tags=tags,
                actor=ACTOR,
            )

        data = artifact_to_dict(artifact)
        _print_artifact_result(data, format_)

    except (SpecNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@artifact_app.command(name="update")
def update(
    qualified_id: str,
    /,
    *,
    title: Annotated[
        str | None,
        Parameter(name=["--title", "-t"], help="New artifact title"),
    ] = None,
    status: Annotated[
        ArtifactStatus | None,
        Parameter(name=["--status", "-s"], help="New status"),
    ] = None,
    description: Annotated[
        str | None,
        Parameter(name=["--description", "-d"], help="New description"),
    ] = None,
    requirements: Annotated[
        list[str] | None,
        Parameter(
            name=["--requirements", "-r"],
            help="New references (replaces existing)",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="New tags (replaces existing)"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Update an existing artifact

    Args:
        qualified_id: Qualified ID in format 'spec-id:artifact-id'.
        title: New title (optional).
        status: New status (optional).
        description: New description (optional).
        requirements: New references (replaces existing).
        tags: New tags (replaces existing).
        format_: Output format.
    """
    console = get_error_console()

    spec_id, artifact_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_artifact_manager()
        artifact = manager.update_artifact(
            spec_id,
            artifact_id,
            title=title,
            status=status,
            description=description,
            references=requirements,
            tags=tags,
            actor=ACTOR,
        )

        data = artifact_to_dict(artifact)
        _print_artifact_result(data, format_)

    except (SpecNotFoundError, SpecArtifactNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@artifact_app.command(name="rebuild")
def rebuild(
    spec_id: str,
    /,
    *,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Rebuild artifacts index from files in artifacts directory

    Scans the artifacts directory and rebuilds the index based on
    frontmatter (text files) or sidecar metadata (binary files).

    Args:
        spec_id: The specification ID.
        format_: Output format.
    """
    try:
        manager = get_artifact_manager()
        result = manager.rebuild_index(spec_id, actor=ACTOR)

        data = rebuild_result_to_dict(result)
        _print_rebuild_result(data, format_)

    except SpecNotFoundError as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@artifact_app.command(name="list")
def list_artifacts(
    spec_id: str,
    /,
    *,
    type_: Annotated[
        ArtifactType | None,
        Parameter(name=["--type", "-t"], help="Filter by artifact type"),
    ] = None,
    status: Annotated[
        ArtifactStatus | None,
        Parameter(name=["--status", "-s"], help="Filter by status"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="Filter by tags (all must match)"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """List artifacts in a specification with optional filtering

    Args:
        spec_id: The specification ID.
        type_: Filter by artifact type.
        status: Filter by status.
        tags: Filter by tags (artifacts must have all listed tags).
        format_: Output format.
    """
    try:
        manager = get_artifact_manager()
        artifacts = manager.list_artifacts(
            spec_id,
            filter_type=type_,
            filter_status=status,
            filter_tags=tags,
        )

        artifact_dicts = [artifact_to_dict(a) for a in artifacts]

        output: str
        if format_ == OutputFormat.TABLE:
            output = format_artifact_table(artifact_dicts)
        elif format_ == OutputFormat.JSON:
            from ._output import format_json

            output = format_json({"artifacts": artifact_dicts})
        elif format_ == OutputFormat.YAML:
            from ._output import format_yaml

            output = format_yaml({"artifacts": artifact_dicts})
        elif format_ in (OutputFormat.PLAIN, OutputFormat.TEXT):
            from ._output import format_ids

            output = format_ids([a.id for a in artifacts])
        else:
            # TOML format
            import tomli_w

            output = tomli_w.dumps({"artifacts": artifact_dicts})

        print(output)
        exit_with_success()

    except SpecNotFoundError as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@artifact_app.command(name="show")
def show(
    qualified_id: str,
    /,
    *,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TEXT,
) -> None:
    """Show detailed information about an artifact

    Args:
        qualified_id: Qualified ID in format 'spec-id:artifact-id'.
        format_: Output format.
    """
    console = get_error_console()

    spec_id, artifact_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_artifact_manager()
        artifact = manager.get_artifact(spec_id, artifact_id)

        data = artifact_to_dict(artifact)
        _print_artifact_result(data, format_)

    except (SpecNotFoundError, SpecArtifactNotFoundError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@artifact_app.command(name="delete")
def delete(
    qualified_id: str,
    /,
    *,
    force: Annotated[
        bool,
        Parameter(name=["--force", "-f"], help="Delete without confirmation"),
    ] = False,
    delete_file: Annotated[
        bool,
        Parameter(name=["--delete-file"], help="Also delete the artifact file(s)"),
    ] = False,
) -> None:
    """Delete an artifact from a specification

    Args:
        qualified_id: Qualified ID in format 'spec-id:artifact-id'.
        force: Delete without confirmation prompt.
        delete_file: If True, also delete the artifact file(s).
    """
    console = get_error_console()

    spec_id, artifact_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_artifact_manager()

        # Verify artifact exists first and get its file path
        artifact = manager.get_artifact(spec_id, artifact_id)
        file_path = artifact.file_path

        # Confirm deletion
        message = f"Are you sure you want to delete artifact {artifact_id}?"
        if delete_file:
            message += " (including file)"
        if not confirm_destructive(message, force=force, console=console):
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(ExitCode.NOT_FOUND)

        manager.delete_artifact(
            spec_id, artifact_id, _delete_file=delete_file, actor=ACTOR
        )

        # Format output message
        if delete_file:
            console.print(
                f"[green]Deleted artifact {artifact_id} (file deleted)[/green]"
            )
        else:
            msg = f"Deleted artifact {artifact_id} (file retained: {file_path})"
            console.print(f"[green]{msg}[/green]")
        exit_with_success()

    except (SpecNotFoundError, SpecArtifactNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


def _print_artifact_result(data: dict[str, object], format_: OutputFormat) -> None:
    """Print artifact result and exit with success.

    Args:
        data: The artifact data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._helpers import output_result

    if format_ in (OutputFormat.TABLE, OutputFormat.TEXT):
        output = format_artifact_info(data)  # type: ignore[arg-type]
    else:
        output = output_result(data, format_)  # type: ignore[arg-type]

    print(output)
    exit_with_success()


def _print_rebuild_result(data: dict[str, object], format_: OutputFormat) -> None:
    """Print rebuild result and exit with success.

    Args:
        data: The rebuild result data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._helpers import output_result

    if format_ in (OutputFormat.TABLE, OutputFormat.TEXT):
        output = format_rebuild_result(data)  # type: ignore[arg-type]
    else:
        output = output_result(data, format_)  # type: ignore[arg-type]

    print(output)
    exit_with_success()
