# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportAny=false
# ruff: noqa: D415, PLR0913, TC001
"""Requirement plumbing commands.

This module provides commands for managing requirements within specifications.
Commands: add, update, link, list, show, delete.
"""

from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_error, exit_with_success
from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec import RequirementStatus, RequirementType

from ._errors import exit_code_for_exception
from ._helpers import (
    ACTOR,
    confirm_destructive,
    get_error_console,
    get_requirement_manager,
    parse_qualified_id,
    requirement_to_dict,
)
from ._output import (
    format_requirement_info,
    format_requirement_table,
)
from ._req_app import req_app

__all__ = [
    "add",
    "delete",
    "link",
    "list_requirements",
    "show",
    "update",
]


@req_app.command(name="add")
def add(
    spec_id: str,
    req_type: RequirementType,
    /,
    *,
    title: Annotated[
        str,
        Parameter(name=["--title", "-t"], help="Requirement title"),
    ],
    description: Annotated[
        str | None,
        Parameter(name=["--description", "-d"], help="Full requirement description"),
    ] = None,
    rationale: Annotated[
        str | None,
        Parameter(
            name=["--rationale"], help="Explanation of why this requirement exists"
        ),
    ] = None,
    acceptance: Annotated[
        list[str] | None,
        Parameter(
            name=["--acceptance", "-a"], help="Acceptance criteria (can be repeated)"
        ),
    ] = None,
    parent: Annotated[
        str | None,
        Parameter(
            name=["--parent"], help="ID of parent requirement for sub-requirements"
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="Freeform tags for filtering"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Add a new requirement to a specification

    Args:
        spec_id: The specification ID.
        req_type: Requirement type (functional, quality, security, etc.).
        title: Human-readable requirement title.
        description: Full requirement description.
        rationale: Explanation of why this requirement exists.
        acceptance: Acceptance criteria for verifying the requirement.
        parent: ID of parent requirement for sub-requirements.
        tags: Freeform tags for filtering.
        format_: Output format.
    """
    # Description defaults to title if not provided
    desc = description if description else title

    try:
        manager = get_requirement_manager()
        requirement = manager.add_requirement(
            spec_id,
            req_type,
            title,
            desc,
            rationale=rationale,
            acceptance_criteria=acceptance,
            parent=parent,
            tags=tags,
            actor=ACTOR,
        )

        data = requirement_to_dict(requirement)
        _print_requirement_result(data, format_)

    except (SpecNotFoundError, RequirementNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@req_app.command(name="update")
def update(
    qualified_id: str,
    /,
    *,
    title: Annotated[
        str | None,
        Parameter(name=["--title", "-t"], help="New requirement title"),
    ] = None,
    status: Annotated[
        RequirementStatus | None,
        Parameter(name=["--status", "-s"], help="New status"),
    ] = None,
    description: Annotated[
        str | None,
        Parameter(name=["--description", "-d"], help="New description"),
    ] = None,
    rationale: Annotated[
        str | None,
        Parameter(name=["--rationale"], help="New rationale"),
    ] = None,
    acceptance: Annotated[
        list[str] | None,
        Parameter(
            name=["--acceptance", "-a"],
            help="New acceptance criteria (replaces existing)",
        ),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Parameter(name=["--tags"], help="New tags (replaces existing)"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Update an existing requirement

    Args:
        qualified_id: Qualified ID in format 'spec-id:req-id'.
        title: New title (optional).
        status: New status (optional).
        description: New description (optional).
        rationale: New rationale (optional).
        acceptance: New acceptance criteria (replaces existing).
        tags: New tags (replaces existing).
        format_: Output format.
    """
    console = get_error_console()

    spec_id, req_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_requirement_manager()
        requirement = manager.update_requirement(
            spec_id,
            req_id,
            title=title,
            status=status,
            description=description,
            rationale=rationale,
            acceptance_criteria=acceptance,
            tags=tags,
            actor=ACTOR,
        )

        data = requirement_to_dict(requirement)
        _print_requirement_result(data, format_)

    except (SpecNotFoundError, RequirementNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@req_app.command(name="link")
def link(
    qualified_id: str,
    /,
    *,
    commit: Annotated[
        str | None,
        Parameter(name=["--commit", "-c"], help="Git commit SHA of the implementation"),
    ] = None,
    pr: Annotated[
        int | None,
        Parameter(name=["--pr"], help="GitHub PR number of the implementation"),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Link a requirement to its implementation

    At least one of --commit or --pr must be provided.

    Args:
        qualified_id: Qualified ID in format 'spec-id:req-id'.
        commit: Git commit SHA of the implementation.
        pr: GitHub PR number of the implementation.
        format_: Output format.
    """
    console = get_error_console()

    # Validate at least one link is provided
    if commit is None and pr is None:
        exit_with_error(
            "At least one of --commit or --pr is required",
            ExitCode.VALIDATION_ERROR,
        )

    spec_id, req_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_requirement_manager()
        requirement = manager.link_requirement(
            spec_id,
            req_id,
            commit_sha=commit,
            pr_number=pr,
            actor=ACTOR,
        )

        data = requirement_to_dict(requirement)
        _print_requirement_result(data, format_)

    except (SpecNotFoundError, RequirementNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@req_app.command(name="list")
def list_requirements(
    spec_id: str,
    /,
    *,
    type_: Annotated[
        RequirementType | None,
        Parameter(name=["--type", "-t"], help="Filter by requirement type"),
    ] = None,
    status: Annotated[
        RequirementStatus | None,
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
    """List requirements in a specification with optional filtering

    Args:
        spec_id: The specification ID.
        type_: Filter by requirement type.
        status: Filter by status.
        tags: Filter by tags (requirements must have all listed tags).
        format_: Output format.
    """
    try:
        manager = get_requirement_manager()
        requirements = manager.list_requirements(
            spec_id,
            filter_type=type_,
            filter_status=status,
            filter_tags=tags,
        )

        req_dicts = [requirement_to_dict(r) for r in requirements]

        output: str
        if format_ == OutputFormat.TABLE:
            output = format_requirement_table(req_dicts)
        elif format_ == OutputFormat.JSON:
            from ._output import format_json

            output = format_json({"requirements": req_dicts})
        elif format_ == OutputFormat.YAML:
            from ._output import format_yaml

            output = format_yaml({"requirements": req_dicts})
        elif format_ in (OutputFormat.PLAIN, OutputFormat.TEXT):
            from ._output import format_ids

            output = format_ids([r.id for r in requirements])
        else:
            # TOML format
            import tomli_w

            output = tomli_w.dumps({"requirements": req_dicts})

        print(output)
        exit_with_success()

    except SpecNotFoundError as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@req_app.command(name="show")
def show(
    qualified_id: str,
    /,
    *,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TEXT,
) -> None:
    """Show detailed information about a requirement

    Args:
        qualified_id: Qualified ID in format 'spec-id:req-id'.
        format_: Output format.
    """
    console = get_error_console()

    spec_id, req_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_requirement_manager()
        requirement = manager.get_requirement(spec_id, req_id)

        data = requirement_to_dict(requirement)
        _print_requirement_result(data, format_)

    except (SpecNotFoundError, RequirementNotFoundError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


@req_app.command(name="delete")
def delete(
    qualified_id: str,
    /,
    *,
    force: Annotated[
        bool,
        Parameter(name=["--force", "-f"], help="Delete without confirmation"),
    ] = False,
) -> None:
    """Delete a requirement from a specification

    Args:
        qualified_id: Qualified ID in format 'spec-id:req-id'.
        force: Delete without confirmation prompt.
    """
    console = get_error_console()

    spec_id, req_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_requirement_manager()

        # Verify requirement exists first
        _ = manager.get_requirement(spec_id, req_id)

        # Confirm deletion
        message = f"Are you sure you want to delete requirement {req_id}?"
        if not confirm_destructive(message, force=force, console=console):
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(ExitCode.NOT_FOUND)

        manager.delete_requirement(spec_id, req_id, actor=ACTOR)

        console.print(f"[green]Deleted requirement {req_id}[/green]")
        exit_with_success()

    except (SpecNotFoundError, RequirementNotFoundError, SpecValidationError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


def _print_requirement_result(data: dict[str, object], format_: OutputFormat) -> None:
    """Print requirement result and exit with success.

    Args:
        data: The requirement data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._helpers import output_result

    if format_ in (OutputFormat.TABLE, OutputFormat.TEXT):
        output = format_requirement_info(data)  # type: ignore[arg-type]
    else:
        output = output_result(data, format_)  # type: ignore[arg-type]

    print(output)
    exit_with_success()
