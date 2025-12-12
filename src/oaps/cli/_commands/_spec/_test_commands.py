# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# ruff: noqa: D415, PLR0913, TC003
"""Test plumbing commands.

This module provides commands for managing tests within specifications.
Commands: add, update, link, list, show, delete, sync.
"""

import json
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
    TestNotFoundError,
)
from oaps.spec import PytestResults, PytestTest, TestMethod, TestStatus

from ._errors import (
    EXIT_CANCELLED,
    EXIT_IO_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    exit_code_for_exception,
)
from ._helpers import (
    ACTOR,
    confirm_destructive,
    get_error_console,
    get_test_manager,
    parse_qualified_id,
    sync_result_to_dict,
    test_to_dict,
)
from ._output import (
    format_sync_result,
    format_test_info,
    format_test_table,
)
from ._test_app import test_app

__all__ = [
    "add",
    "delete",
    "link",
    "list_tests",
    "show",
    "sync",
    "update",
]


@test_app.command(name="add")
def add(
    spec_id: str,
    method: TestMethod,
    /,
    *,
    title: Annotated[
        str,
        Parameter(name=["--title", "-t"], help="Test title"),
    ],
    requirements: Annotated[
        list[str],
        Parameter(
            name=["--requirements", "-r"], help="Requirement IDs this test verifies"
        ),
    ],
    description: Annotated[
        str | None,
        Parameter(name=["--description", "-d"], help="Full test description"),
    ] = None,
    file: Annotated[
        str | None,
        Parameter(name=["--file"], help="Path to test implementation file"),
    ] = None,
    function: Annotated[
        str | None,
        Parameter(name=["--function"], help="Name of test function or method"),
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
    """Add a new test to a specification

    Args:
        spec_id: The specification ID.
        method: Test method (unit, integration, e2e, etc.).
        title: Human-readable test title.
        requirements: IDs of requirements this test verifies (non-empty).
        description: Full test description.
        file: Path to test implementation file.
        function: Name of test function or method.
        tags: Freeform tags for filtering.
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_test_manager()
        test = manager.add_test(
            spec_id,
            method,
            title,
            requirements,
            description=description,
            file=file,
            function=function,
            tags=tags,
            actor=ACTOR,
        )

        data = test_to_dict(test)
        _print_test_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except RequirementNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="update")
def update(
    qualified_id: str,
    /,
    *,
    title: Annotated[
        str | None,
        Parameter(name=["--title", "-t"], help="New test title"),
    ] = None,
    status: Annotated[
        TestStatus | None,
        Parameter(name=["--status", "-s"], help="New status"),
    ] = None,
    description: Annotated[
        str | None,
        Parameter(name=["--description", "-d"], help="New description"),
    ] = None,
    file: Annotated[
        str | None,
        Parameter(name=["--file"], help="New file path"),
    ] = None,
    function: Annotated[
        str | None,
        Parameter(name=["--function"], help="New function name"),
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
    """Update an existing test

    Note: This does not update requirement links. Use 'test link' for that.

    Args:
        qualified_id: Qualified ID in format 'spec-id:test-id'.
        title: New title (optional).
        status: New status (optional).
        description: New description (optional).
        file: New file path (optional).
        function: New function name (optional).
        tags: New tags (replaces existing).
        format_: Output format.
    """
    console = get_error_console()

    spec_id, test_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_test_manager()
        test = manager.update_test(
            spec_id,
            test_id,
            title=title,
            status=status,
            description=description,
            file=file,
            function=function,
            tags=tags,
            actor=ACTOR,
        )

        data = test_to_dict(test)
        _print_test_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except TestNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="link")
def link(
    qualified_id: str,
    /,
    *,
    requirements: Annotated[
        list[str],
        Parameter(
            name=["--requirements", "-r"], help="Requirement IDs (replaces existing)"
        ),
    ],
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Replace requirement links for a test

    Args:
        qualified_id: Qualified ID in format 'spec-id:test-id'.
        requirements: New list of requirement IDs (non-empty, replaces existing).
        format_: Output format.
    """
    console = get_error_console()

    # Validate requirements is non-empty
    if not requirements:
        console.print(
            "[red]Error:[/red] --requirements is required and cannot be empty"
        )
        raise SystemExit(EXIT_VALIDATION_ERROR)

    spec_id, test_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_test_manager()
        test = manager.link_test(
            spec_id,
            test_id,
            requirements,
            actor=ACTOR,
        )

        data = test_to_dict(test)
        _print_test_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except TestNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except RequirementNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="list")
def list_tests(
    spec_id: str,
    /,
    *,
    method: Annotated[
        TestMethod | None,
        Parameter(name=["--method", "-m"], help="Filter by test method"),
    ] = None,
    status: Annotated[
        TestStatus | None,
        Parameter(name=["--status", "-s"], help="Filter by status"),
    ] = None,
    requirements: Annotated[
        list[str] | None,
        Parameter(
            name=["--requirements", "-r"],
            help="Filter by requirements (all must match)",
        ),
    ] = None,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """List tests in a specification with optional filtering

    Args:
        spec_id: The specification ID.
        method: Filter by test method.
        status: Filter by status.
        requirements: Filter by requirements (tests must verify all listed).
        format_: Output format.
    """
    console = get_error_console()

    try:
        manager = get_test_manager()
        tests = manager.list_tests(
            spec_id,
            filter_method=method,
            filter_status=status,
            filter_requirements=requirements,
        )

        test_dicts = [test_to_dict(t) for t in tests]

        output: str
        if format_ == OutputFormat.TABLE:
            output = format_test_table(test_dicts)
        elif format_ == OutputFormat.JSON:
            from ._output import format_json

            output = format_json({"tests": test_dicts})
        elif format_ == OutputFormat.YAML:
            from ._output import format_yaml

            output = format_yaml({"tests": test_dicts})
        elif format_ in (OutputFormat.PLAIN, OutputFormat.TEXT):
            from ._output import format_ids

            output = format_ids([t.id for t in tests])
        else:
            # TOML format
            import tomli_w

            output = tomli_w.dumps({"tests": test_dicts})

        print(output)
        raise SystemExit(EXIT_SUCCESS)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="show")
def show(
    qualified_id: str,
    /,
    *,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TEXT,
) -> None:
    """Show detailed information about a test

    Args:
        qualified_id: Qualified ID in format 'spec-id:test-id'.
        format_: Output format.
    """
    console = get_error_console()

    spec_id, test_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_test_manager()
        test = manager.get_test(spec_id, test_id)

        data = test_to_dict(test)
        _print_test_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except TestNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="delete")
def delete(
    qualified_id: str,
    /,
    *,
    force: Annotated[
        bool,
        Parameter(name=["--force", "-f"], help="Delete without confirmation"),
    ] = False,
) -> None:
    """Delete a test from a specification

    Args:
        qualified_id: Qualified ID in format 'spec-id:test-id'.
        force: Delete without confirmation prompt.
    """
    console = get_error_console()

    spec_id, test_id = parse_qualified_id(qualified_id, console)

    try:
        manager = get_test_manager()

        # Verify test exists first
        _ = manager.get_test(spec_id, test_id)

        # Confirm deletion
        message = f"Are you sure you want to delete test {test_id}?"
        if not confirm_destructive(message, force=force, console=console):
            console.print("[yellow]Cancelled[/yellow]")
            raise SystemExit(EXIT_CANCELLED)

        manager.delete_test(spec_id, test_id, actor=ACTOR)

        console.print(f"[green]Deleted test {test_id}[/green]")
        raise SystemExit(EXIT_SUCCESS)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except TestNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None
    except SpecValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


@test_app.command(name="sync")
def sync(
    spec_id: str,
    /,
    *,
    pytest_results: Annotated[
        Path,
        Parameter(
            name=["--pytest-results", "-p"], help="Path to pytest JSON report file"
        ),
    ],
    dry_run: Annotated[
        bool,
        Parameter(
            name=["--dry-run", "-n"],
            help="Show what would be updated without making changes",
        ),
    ] = False,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Synchronize spec tests with pytest results

    Matches pytest results to spec tests by file + function.
    Only matches tests that have both file AND function set.

    The pytest JSON report should be generated with pytest-json-report plugin:
        pytest --json-report --json-report-file=results.json

    Args:
        spec_id: The specification ID.
        pytest_results: Path to pytest JSON report file.
        dry_run: Show what would be updated without making changes.
        format_: Output format.
    """
    console = get_error_console()

    # Read and parse pytest results file
    try:
        results_data = _read_pytest_json(pytest_results)
    except FileNotFoundError:
        console.print(
            f"[red]Error:[/red] Pytest results file not found: {pytest_results}"
        )
        raise SystemExit(EXIT_IO_ERROR) from None
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in pytest results file: {e}")
        raise SystemExit(EXIT_IO_ERROR) from None

    # Transform to PytestResults model
    pytest_model = _transform_pytest_results(results_data)

    try:
        manager = get_test_manager()

        if dry_run:
            # For dry run, just show what would be matched
            console.print("[yellow]Dry run - no changes made[/yellow]")
            # We could enhance this to show detailed matching info
            # For now, just run sync and show results without modifications
            # Note: TestManager.sync() doesn't support dry_run, so we just warn
            test_count = len(pytest_model.tests)
            console.print(f"Would sync {test_count} pytest results with spec {spec_id}")
            raise SystemExit(EXIT_SUCCESS)

        result = manager.sync(spec_id, pytest_model, actor=ACTOR)

        data = sync_result_to_dict(result)
        _print_sync_result(data, format_)

    except SpecNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(exit_code_for_exception(e)) from None


def _read_pytest_json(path: Path) -> dict[str, object]:
    """Read and parse pytest JSON report file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: If file doesn't exist.
        json.JSONDecodeError: If JSON is invalid.
    """
    with path.open() as f:
        return json.load(f)


def _transform_pytest_results(data: dict[str, object]) -> PytestResults:
    """Transform pytest JSON report to PytestResults model.

    Args:
        data: Parsed pytest JSON data.

    Returns:
        PytestResults model instance.
    """
    tests_data = data.get("tests", [])
    tests: list[PytestTest] = []

    if isinstance(tests_data, list):
        for test_entry in tests_data:
            if not isinstance(test_entry, dict):
                continue

            node_id = test_entry.get("nodeid", "")
            outcome = test_entry.get("outcome", "")
            duration_val = test_entry.get("duration", 0.0)

            # Extract error message from call.longrepr if present
            message: str | None = None
            call_data = test_entry.get("call")
            if isinstance(call_data, dict):
                longrepr = call_data.get("longrepr")
                if isinstance(longrepr, str):
                    message = longrepr

            # Parse duration with type narrowing
            test_duration: float = 0.0
            if isinstance(duration_val, (int, float)):
                test_duration = float(duration_val)

            if isinstance(node_id, str) and isinstance(outcome, str):
                tests.append(
                    PytestTest(
                        node_id=node_id,
                        outcome=outcome,
                        duration=test_duration,
                        message=message,
                    )
                )

    # Parse top-level duration and exit_code with type narrowing
    duration_raw = data.get("duration", 0.0)
    total_duration: float = 0.0
    if isinstance(duration_raw, (int, float)):
        total_duration = float(duration_raw)

    exit_code_raw = data.get("exitcode", 0)
    exit_code: int = 0
    if isinstance(exit_code_raw, int):
        exit_code = exit_code_raw

    return PytestResults(
        tests=tuple(tests),
        duration=total_duration,
        exit_code=exit_code,
    )


def _print_test_result(data: dict[str, object], format_: OutputFormat) -> None:
    """Print test result and exit with success.

    Args:
        data: The test data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._helpers import output_result

    if format_ in (OutputFormat.TABLE, OutputFormat.TEXT):
        output = format_test_info(data)  # type: ignore[arg-type]
    else:
        output = output_result(data, format_)  # type: ignore[arg-type]

    print(output)
    raise SystemExit(EXIT_SUCCESS)


def _print_sync_result(data: dict[str, object], format_: OutputFormat) -> None:
    """Print sync result and exit with success.

    Args:
        data: The sync result data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._helpers import output_result

    if format_ in (OutputFormat.TABLE, OutputFormat.TEXT):
        output = format_sync_result(data)  # type: ignore[arg-type]
    else:
        output = output_result(data, format_)  # type: ignore[arg-type]

    print(output)
    raise SystemExit(EXIT_SUCCESS)
