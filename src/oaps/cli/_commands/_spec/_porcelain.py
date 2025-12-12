# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportAny=false
# pyright: reportUnknownMemberType=false
# ruff: noqa: D415, FBT002, PLR0913
"""Porcelain commands for specification management.

This module provides user-facing commands for creating, updating, listing,
and managing specifications.
"""

from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.exceptions import (
    CircularDependencyError,
    DuplicateIdError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec import SpecStatus, SpecType

from ._app import app
from ._errors import (
    EXIT_CANCELLED,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    exit_code_for_exception,
)
from ._helpers import (
    ACTOR,
    confirm_destructive,
    get_error_console,
    get_spec_manager,
    output_list_result,
    output_result,
    print_spec_result,
    spec_to_dict,
    validation_issues_to_dict,
)
from ._output import format_spec_table, format_validation_table

__all__ = [
    "archive",
    "create",
    "delete",
    "info",
    "list_specs",
    "rename",
    "update",
    "validate",
]


@app.command(name="create")
def create(
    slug: str,
    title: str,
    /,
    type_: Annotated[
        SpecType,
        Parameter(name=["--type", "-t"], help="Spec type"),
    ] = SpecType.FEATURE,
    summary: Annotated[
        str | None,
        Parameter(name=["--summary", "-s"], help="Brief description"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="Freeform tags"),
    ] = None,
    depends_on: Annotated[
        list[str] | None,
        Parameter(name=["--depends-on"], help="IDs of specs this depends on"),
    ] = None,
    extends: Annotated[
        str | None,
        Parameter(name=["--extends"], help="ID of spec this extends"),
    ] = None,
    integrates: Annotated[
        list[str] | None,
        Parameter(name=["--integrates"], help="IDs of specs this integrates with"),
    ] = None,
    authors: Annotated[
        list[str] | None,
        Parameter(name=["--authors"], help="Author identifiers"),
    ] = None,
    version: Annotated[
        str | None,
        Parameter(name=["--version"], help="Specification version"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Create a new specification

    Args:
        slug: URL-friendly specification name.
        title: Human-readable specification title.
        type_: Architectural type of the specification.
        summary: Brief description for listings.
        tags: Freeform tags for filtering.
        depends_on: IDs of specs this spec depends on.
        extends: ID of spec this spec extends.
        integrates: IDs of specs this spec integrates with.
        authors: List of author identifiers.
        version: Specification version string.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        metadata = manager.create_spec(
            slug,
            title,
            type_,
            summary=summary,
            tags=tags,
            depends_on=depends_on,
            extends=extends,
            integrates=integrates,
            authors=authors,
            version=version,
            actor=ACTOR,
        )

        data = spec_to_dict(metadata)
        print_spec_result(data, format_)

    except (SpecValidationError, DuplicateIdError, CircularDependencyError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="delete")
def delete(
    spec_id: str,
    /,
    force: Annotated[
        bool,
        Parameter(name=["--force", "-f"], help="Delete without confirmation"),
    ] = False,
) -> None:
    """Delete a specification

    Args:
        spec_id: The specification ID to delete.
        force: Delete without confirmation prompt.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()

        # Verify spec exists first
        _ = manager.get_spec(spec_id)

        # Confirm deletion
        message = f"Are you sure you want to delete specification {spec_id}?"
        if not confirm_destructive(message, force=force, console=console):
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(EXIT_CANCELLED)

        manager.delete_spec(spec_id, force=force, actor=ACTOR)

        console.print(f"[green]Deleted specification {spec_id}[/green]")
        raise SystemExit(EXIT_SUCCESS)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="archive")
def archive(
    spec_id: str,
    /,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Archive a specification (set status to deprecated)

    Args:
        spec_id: The specification ID to archive.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        metadata = manager.archive_spec(spec_id, actor=ACTOR)

        data = spec_to_dict(metadata)
        print_spec_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="update")
def update(
    spec_id: str,
    /,
    title: Annotated[
        str | None,
        Parameter(name=["--title"], help="New title"),
    ] = None,
    type_: Annotated[
        SpecType | None,
        Parameter(name=["--type", "-t"], help="New spec type"),
    ] = None,
    status: Annotated[
        SpecStatus | None,
        Parameter(name=["--status"], help="New status"),
    ] = None,
    summary: Annotated[
        str | None,
        Parameter(name=["--summary", "-s"], help="New summary"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="New tags (replaces existing)"),
    ] = None,
    depends_on: Annotated[
        list[str] | None,
        Parameter(name=["--depends-on"], help="New dependencies (replaces existing)"),
    ] = None,
    extends: Annotated[
        str | None,
        Parameter(name=["--extends"], help="New extends target"),
    ] = None,
    integrates: Annotated[
        list[str] | None,
        Parameter(name=["--integrates"], help="New integrates (replaces existing)"),
    ] = None,
    supersedes: Annotated[
        str | None,
        Parameter(name=["--supersedes"], help="ID of spec this supersedes"),
    ] = None,
    version: Annotated[
        str | None,
        Parameter(name=["--version"], help="New version"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Update an existing specification

    Args:
        spec_id: The specification ID to update.
        title: New title (optional).
        type_: New type (optional).
        status: New status (optional).
        summary: New summary (optional).
        tags: New tags (replaces existing).
        depends_on: New dependencies (replaces existing).
        extends: New extends target (optional).
        integrates: New integrates targets (replaces existing).
        supersedes: New supersedes target (optional).
        version: New version string (optional).
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        metadata = manager.update_spec(
            spec_id,
            title=title,
            spec_type=type_,
            status=status,
            summary=summary,
            tags=tags,
            depends_on=depends_on,
            extends=extends,
            integrates=integrates,
            supersedes=supersedes,
            version=version,
            actor=ACTOR,
        )

        data = spec_to_dict(metadata)
        print_spec_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except (SpecValidationError, CircularDependencyError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="rename")
def rename(
    spec_id: str,
    new_slug: str,
    /,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Rename a specification (change its slug)

    Args:
        spec_id: The specification ID to rename.
        new_slug: The new slug.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        metadata = manager.rename_spec(spec_id, new_slug, actor=ACTOR)

        data = spec_to_dict(metadata)
        print_spec_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except (SpecValidationError, DuplicateIdError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="validate")
def validate(
    spec_id: str,
    /,
    strict: Annotated[
        bool,
        Parameter(name=["--strict"], help="Treat warnings as errors"),
    ] = False,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Validate a specification

    Args:
        spec_id: The specification ID to validate.
        strict: Include warnings as errors.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        issues = manager.validate_spec(spec_id, strict=strict)

        data = validation_issues_to_dict(issues)

        if format_ == OutputFormat.TABLE:
            issue_dicts = data.get("issues", [])
            output = format_validation_table(issue_dicts)
        else:
            output = output_result(data, format_)

        print(output)

        # Exit with error if there are errors
        error_count = data.get("error_count", 0)
        if error_count > 0:
            raise SystemExit(EXIT_VALIDATION_ERROR)
        raise SystemExit(EXIT_SUCCESS)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="info")
def info(
    spec_id: str,
    /,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Show detailed information about a specification

    Args:
        spec_id: The specification ID to show.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_spec_manager()
        metadata = manager.get_spec(spec_id)

        data = spec_to_dict(metadata)
        print_spec_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@app.command(name="list")
def list_specs(
    *,
    type_: Annotated[
        SpecType | None,
        Parameter(name=["--type", "-t"], help="Filter by spec type"),
    ] = None,
    status: Annotated[
        SpecStatus | None,
        Parameter(name=["--status", "-s"], help="Filter by status"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="Filter by tags (all must match)"),
    ] = None,
    extends: Annotated[
        str | None,
        Parameter(name=["--extends"], help="Filter by extends relationship"),
    ] = None,
    include_archived: Annotated[
        bool,
        Parameter(name=["--include-archived"], help="Include deprecated/superseded"),
    ] = False,
    limit: Annotated[
        int | None,
        Parameter(name=["--limit", "-n"], help="Maximum number of specs to show"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """List specifications with optional filtering

    Args:
        type_: Filter by spec type.
        status: Filter by status.
        tags: Filter by tags (specs must have all listed tags).
        extends: Filter by extends relationship (strict match).
        include_archived: Include archived (deprecated/superseded) specs.
        limit: Maximum number of specs to show.
        format_: Output format.
    """
    manager = get_spec_manager()

    # Get specs with basic filters
    specs = manager.list_specs(
        filter_type=type_,
        filter_status=status,
        filter_tags=tags,
        include_archived=include_archived,
    )

    # Apply extends filter if specified (requires loading full metadata)
    if extends is not None:
        filtered_specs = []
        for summary in specs:
            # Load full metadata to check extends relationship
            try:
                metadata = manager.get_spec(summary.id)
                if metadata.relationships.extends == extends:
                    filtered_specs.append(summary)
            except SpecNotFoundError:
                continue
        specs = filtered_specs

    # Apply limit if specified
    if limit is not None and limit > 0:
        specs = specs[:limit]

    if format_ == OutputFormat.TABLE:
        spec_dicts = [spec_to_dict(s) for s in specs]
        output = format_spec_table(spec_dicts)
    else:
        output = output_list_result(specs, format_)

    print(output)
    raise SystemExit(EXIT_SUCCESS)
