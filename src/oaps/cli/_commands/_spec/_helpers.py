# pyright: reportExplicitAny=false, reportAny=false, reportUnreachable=false
# pyright: reportUnnecessaryIsInstance=false, reportUnknownMemberType=false
# ruff: noqa: PLR2004, PLR0912
"""Helper utilities for spec commands."""

import sys
from typing import TYPE_CHECKING, Any

from oaps.cli._commands._context import CLIContext, OutputFormat
from oaps.cli._commands._shared import get_error_console
from oaps.spec import RequirementManager, SpecManager, TestManager

if TYPE_CHECKING:
    from datetime import datetime

    from rich.console import Console

    from oaps.spec import (
        Artifact,
        ArtifactManager,
        HistoryEntry,
        HistoryManager,
        RebuildResult,
        Requirement,
        SpecMetadata,
        SpecSummary,
        SpecValidationIssue,
        SyncResult,
        Test,
    )

from ._output import SpecData, format_ids, format_json, format_table, format_yaml

__all__ = [
    "ACTOR",
    "artifact_to_dict",
    "confirm_destructive",
    "get_artifact_manager",
    "get_error_console",
    "get_history_manager",
    "get_requirement_manager",
    "get_spec_manager",
    "get_test_manager",
    "history_entry_to_dict",
    "output_list_result",
    "output_result",
    "parse_qualified_id",
    "parse_time_filter",
    "print_spec_result",
    "rebuild_result_to_dict",
    "requirement_to_dict",
    "spec_to_dict",
    "sync_result_to_dict",
    "test_to_dict",
    "validation_issues_to_dict",
]

# Static actor identifier for history tracking
ACTOR: str = "cli"


def confirm_destructive(message: str, *, force: bool, console: Console) -> bool:
    """Prompt for confirmation on destructive operations.

    Returns True if operation should proceed.
    Skips prompt and returns True if force=True or stdin is not a TTY.

    Args:
        message: The confirmation message to display.
        force: If True, skip confirmation and proceed.
        console: Rich console for output.

    Returns:
        True if the operation should proceed, False otherwise.
    """
    if force:
        return True

    # Non-interactive mode requires explicit --force (secure by default)
    if not sys.stdin.isatty():
        return False

    try:
        console.print(f"[yellow]{message}[/yellow]")
        response = console.input("[bold]Confirm (y/N): [/bold]")
        return response.lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def get_spec_manager() -> SpecManager:
    """Get SpecManager configured from CLIContext or default path.

    Returns:
        A configured SpecManager instance.
    """
    from oaps.utils._paths import get_oaps_dir

    ctx = CLIContext.get_current()

    # Use project_root from context if available, otherwise use default
    if ctx.project_root is not None:
        base_path = ctx.project_root / ".oaps" / "docs" / "specs"
    else:
        base_path = get_oaps_dir() / "docs" / "specs"

    return SpecManager(base_path)


def get_requirement_manager() -> RequirementManager:
    """Get RequirementManager configured from CLIContext.

    Returns:
        A configured RequirementManager instance.
    """
    spec_manager = get_spec_manager()
    return RequirementManager(spec_manager)


def parse_qualified_id(qualified_id: str, console: Console) -> tuple[str, str]:
    """Parse 'spec-id:req-id' into (spec_id, req_id).

    Args:
        qualified_id: The qualified ID string in format 'spec-id:req-id'.
        console: Rich console for error output.

    Returns:
        Tuple of (spec_id, req_id).

    Raises:
        SystemExit: With ExitCode.VALIDATION_ERROR if format is invalid.
    """
    from oaps.cli._commands._shared import ExitCode, exit_with_error

    parts = qualified_id.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        console.print("Expected format: <spec-id>:<req-id> (e.g., '0001:FR-0001')")
        exit_with_error(
            f"Invalid qualified ID format: {qualified_id}",
            ExitCode.VALIDATION_ERROR,
            console=console,
        )
    return parts[0], parts[1]


def _metadata_to_dict(spec: SpecMetadata) -> dict[str, Any]:
    """Convert SpecMetadata to dictionary."""
    data: dict[str, Any] = {
        "id": spec.id,
        "slug": spec.slug,
        "title": spec.title,
        "type": spec.spec_type.value,
        "status": spec.status.value,
        "created": spec.created.isoformat(),
        "updated": spec.updated.isoformat(),
    }
    if spec.version:
        data["version"] = spec.version
    if spec.summary:
        data["summary"] = spec.summary
    if spec.authors:
        data["authors"] = list(spec.authors)
    if spec.reviewers:
        data["reviewers"] = list(spec.reviewers)
    if spec.tags:
        data["tags"] = list(spec.tags)

    # Include relationships if present
    relationships = _relationships_to_dict(spec.relationships)
    if relationships:
        data["relationships"] = relationships

    # Include counts
    if spec.counts.requirements or spec.counts.tests or spec.counts.artifacts:
        data["counts"] = {
            "requirements": spec.counts.requirements,
            "tests": spec.counts.tests,
            "artifacts": spec.counts.artifacts,
        }

    return data


def _relationships_to_dict(rel: Any) -> dict[str, Any]:
    """Convert Relationships object to dictionary."""
    relationships: dict[str, Any] = {}
    if rel.depends_on:
        relationships["depends_on"] = list(rel.depends_on)
    if rel.extends:
        relationships["extends"] = rel.extends
    if rel.supersedes:
        relationships["supersedes"] = rel.supersedes
    if rel.integrates:
        relationships["integrates"] = list(rel.integrates)
    if rel.dependents:
        relationships["dependents"] = list(rel.dependents)
    if rel.extended_by:
        relationships["extended_by"] = list(rel.extended_by)
    if rel.superseded_by:
        relationships["superseded_by"] = rel.superseded_by
    if rel.integrated_by:
        relationships["integrated_by"] = list(rel.integrated_by)
    return relationships


def _summary_to_dict(spec: SpecSummary) -> dict[str, Any]:
    """Convert SpecSummary to dictionary."""
    data: dict[str, Any] = {
        "id": spec.id,
        "slug": spec.slug,
        "title": spec.title,
        "type": spec.spec_type.value,
        "status": spec.status.value,
        "created": spec.created.isoformat(),
        "updated": spec.updated.isoformat(),
    }
    if spec.depends_on:
        data["depends_on"] = list(spec.depends_on)
    if spec.tags:
        data["tags"] = list(spec.tags)
    return data


def spec_to_dict(spec: SpecMetadata | SpecSummary) -> SpecData:
    """Convert spec model to dictionary for output.

    Args:
        spec: SpecMetadata or SpecSummary instance.

    Returns:
        Dictionary representation of the spec.
    """
    from oaps.spec import SpecMetadata, SpecSummary

    if isinstance(spec, SpecMetadata):
        return _metadata_to_dict(spec)

    if isinstance(spec, SpecSummary):
        return _summary_to_dict(spec)

    # Fallback - should not reach here but satisfies type checker
    return {"id": getattr(spec, "id", "unknown")}


def requirement_to_dict(req: Requirement) -> SpecData:
    """Convert Requirement model to output dictionary.

    Args:
        req: Requirement instance.

    Returns:
        Dictionary representation of the requirement.
    """
    data: dict[str, Any] = {
        "id": req.id,
        "title": req.title,
        "req_type": req.req_type.value,
        "status": req.status.value,
        "created": req.created.isoformat(),
        "updated": req.updated.isoformat(),
        "author": req.author,
        "description": req.description,
    }

    # Optional fields
    if req.rationale:
        data["rationale"] = req.rationale
    if req.acceptance_criteria:
        data["acceptance_criteria"] = list(req.acceptance_criteria)
    if req.verified_by:
        data["verified_by"] = list(req.verified_by)
    if req.depends_on:
        data["depends_on"] = list(req.depends_on)
    if req.tags:
        data["tags"] = list(req.tags)
    if req.source_section:
        data["source_section"] = req.source_section
    if req.parent:
        data["parent"] = req.parent
    if req.subtype:
        data["subtype"] = req.subtype

    # Planguage fields
    if req.scale:
        data["scale"] = req.scale
    if req.meter:
        data["meter"] = req.meter
    if req.baseline is not None:
        data["baseline"] = req.baseline
    if req.goal is not None:
        data["goal"] = req.goal
    if req.stretch is not None:
        data["stretch"] = req.stretch
    if req.fail is not None:
        data["fail"] = req.fail

    return data


def validation_issues_to_dict(issues: list[SpecValidationIssue]) -> SpecData:
    """Convert validation issues to dictionary for output.

    Args:
        issues: List of validation issues.

    Returns:
        Dictionary with issues list.
    """
    return {
        "issues": [
            {
                "spec_id": issue.spec_id,
                "field": issue.field,
                "message": issue.message,
                "severity": issue.severity,
                **({"related_id": issue.related_id} if issue.related_id else {}),
            }
            for issue in issues
        ],
        "error_count": sum(1 for i in issues if i.severity == "error"),
        "warning_count": sum(1 for i in issues if i.severity == "warning"),
    }


def _format_output_json_or_yaml(data: SpecData, output_format: OutputFormat) -> str:
    """Format data as JSON or YAML."""
    if output_format == OutputFormat.JSON:
        return format_json(data)
    return format_yaml(data)


def _format_output_table_or_plain(
    data: SpecData,
    output_format: OutputFormat,
    table_headers: list[str] | None,
    table_rows: list[list[str]] | None,
    id_field: str,
) -> str:
    """Format data as table or plain text."""
    if output_format == OutputFormat.TABLE:
        if table_headers is not None and table_rows is not None:
            return format_table(table_headers, table_rows)
        return format_json(data)

    # Plain/text output - extract ID(s)
    if "specs" in data:
        ids = [str(spec.get(id_field, "")) for spec in data["specs"]]
        return format_ids(ids)
    if id_field in data:
        return str(data[id_field])
    return format_json(data)


def output_result(
    data: SpecData,
    output_format: OutputFormat,
    *,
    table_headers: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
    id_field: str = "id",
) -> str:
    """Dispatch output formatting based on format enum.

    Args:
        data: The data dictionary to format.
        output_format: The output format to use.
        table_headers: Headers for table output.
        table_rows: Rows for table output.
        id_field: Field to use for plain/ids output.

    Returns:
        Formatted string representation.
    """
    if output_format in (OutputFormat.JSON, OutputFormat.YAML):
        return _format_output_json_or_yaml(data, output_format)

    if output_format in (OutputFormat.TABLE, OutputFormat.PLAIN, OutputFormat.TEXT):
        return _format_output_table_or_plain(
            data, output_format, table_headers, table_rows, id_field
        )

    if output_format == OutputFormat.TOML:
        import tomli_w

        return tomli_w.dumps(data)

    # Default fallback
    return format_json(data)


def output_list_result(
    specs: list[SpecSummary],
    output_format: OutputFormat,
) -> str:
    """Format a list of specs for output.

    Args:
        specs: List of spec summaries.
        output_format: The output format to use.

    Returns:
        Formatted string representation.
    """
    spec_dicts = [spec_to_dict(s) for s in specs]

    if output_format == OutputFormat.JSON:
        return format_json({"specs": spec_dicts})

    if output_format == OutputFormat.YAML:
        return format_yaml({"specs": spec_dicts})

    if output_format == OutputFormat.TABLE:
        headers = ["ID", "Title", "Type", "Status"]
        rows = [[s.id, s.title, s.spec_type.value, s.status.value] for s in specs]
        return format_table(headers, rows)

    if output_format in (OutputFormat.PLAIN, OutputFormat.TEXT):
        return format_ids([s.id for s in specs])

    if output_format == OutputFormat.TOML:
        import tomli_w

        return tomli_w.dumps({"specs": spec_dicts})

    return format_json({"specs": spec_dicts})


def print_spec_result(data: SpecData, format_: OutputFormat) -> None:
    """Print spec result and exit with success.

    This is a convenience function that handles the common pattern of
    formatting output based on the output format and exiting successfully.

    Args:
        data: The spec data dictionary to format.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with ExitCode.SUCCESS (0).
    """
    from oaps.cli._commands._shared import exit_with_success

    from ._output import format_spec_info

    if format_ == OutputFormat.TABLE:
        output = format_spec_info(data)
    else:
        output = output_result(data, format_)

    print(output)
    exit_with_success()


def get_test_manager() -> TestManager:
    """Get TestManager configured from CLIContext.

    Returns:
        A configured TestManager instance.
    """
    spec_manager = get_spec_manager()
    requirement_manager = RequirementManager(spec_manager)
    return TestManager(spec_manager, requirement_manager)


def test_to_dict(test: Test) -> SpecData:
    """Convert Test model to output dictionary.

    Args:
        test: Test instance.

    Returns:
        Dictionary representation of the test.
    """
    data: dict[str, Any] = {
        "id": test.id,
        "title": test.title,
        "method": test.method.value,
        "status": test.status.value,
        "created": test.created.isoformat(),
        "updated": test.updated.isoformat(),
        "author": test.author,
        "tests_requirements": list(test.tests_requirements),
    }

    # Optional fields
    if test.description:
        data["description"] = test.description
    if test.file:
        data["file"] = test.file
    if test.function:
        data["function"] = test.function
    if test.last_run:
        data["last_run"] = test.last_run.isoformat()
    if test.last_result:
        data["last_result"] = test.last_result.value
    if test.tags:
        data["tags"] = list(test.tags)

    # Performance test fields
    if test.last_value is not None:
        data["last_value"] = test.last_value
    if test.threshold is not None:
        data["threshold"] = test.threshold
    if test.perf_baseline is not None:
        data["perf_baseline"] = test.perf_baseline

    # Manual test fields
    if test.steps:
        data["steps"] = list(test.steps)
    if test.expected_result:
        data["expected_result"] = test.expected_result
    if test.actual_result:
        data["actual_result"] = test.actual_result
    if test.tested_by:
        data["tested_by"] = test.tested_by
    if test.tested_on:
        data["tested_on"] = test.tested_on.isoformat()

    return data


def sync_result_to_dict(result: SyncResult) -> SpecData:
    """Convert SyncResult model to output dictionary.

    Args:
        result: SyncResult instance.

    Returns:
        Dictionary representation of the sync result.
    """
    data: dict[str, Any] = {
        "updated": result.updated,
        "orphaned": result.orphaned,
        "skipped_no_file": result.skipped_no_file,
        "errors": list(result.errors),
    }
    return data


def get_artifact_manager() -> ArtifactManager:
    """Get ArtifactManager configured from CLIContext.

    Returns:
        A configured ArtifactManager instance.
    """
    from oaps.spec import ArtifactManager

    spec_manager = get_spec_manager()
    return ArtifactManager(spec_manager)


def artifact_to_dict(artifact: Artifact) -> SpecData:
    """Convert Artifact model to output dictionary.

    Args:
        artifact: Artifact instance.

    Returns:
        Dictionary representation of the artifact.
    """
    data: dict[str, Any] = {
        "id": artifact.id,
        "title": artifact.title,
        "artifact_type": artifact.artifact_type.value,
        "status": artifact.status.value,
        "created": artifact.created.isoformat(),
        "updated": artifact.updated.isoformat(),
        "author": artifact.author,
        "file_path": artifact.file_path,
    }

    # Optional fields
    if artifact.description:
        data["description"] = artifact.description
    if artifact.subtype:
        data["subtype"] = artifact.subtype
    if artifact.references:
        data["references"] = list(artifact.references)
    if artifact.tags:
        data["tags"] = list(artifact.tags)
    if artifact.supersedes:
        data["supersedes"] = artifact.supersedes
    if artifact.superseded_by:
        data["superseded_by"] = artifact.superseded_by
    if artifact.summary:
        data["summary"] = artifact.summary
    if artifact.type_fields:
        data["type_fields"] = dict(artifact.type_fields)
    if artifact.metadata_file_path:
        data["metadata_file_path"] = artifact.metadata_file_path

    return data


def rebuild_result_to_dict(result: RebuildResult) -> SpecData:
    """Convert RebuildResult model to output dictionary.

    Args:
        result: RebuildResult instance.

    Returns:
        Dictionary representation of the rebuild result.
    """
    data: dict[str, Any] = {
        "scanned": result.scanned,
        "indexed": result.indexed,
        "skipped": result.skipped,
        "errors": list(result.errors),
    }
    return data


def get_history_manager() -> HistoryManager:
    """Get HistoryManager configured from CLIContext.

    Returns:
        A configured HistoryManager instance.
    """
    from oaps.spec import HistoryManager

    spec_manager = get_spec_manager()
    return HistoryManager(spec_manager)


def history_entry_to_dict(entry: HistoryEntry) -> SpecData:
    """Convert HistoryEntry model to output dictionary.

    Args:
        entry: HistoryEntry instance.

    Returns:
        Dictionary representation of the history entry.
    """
    data: dict[str, Any] = {
        "timestamp": entry.timestamp.isoformat(),
        "event": entry.event,
        "actor": entry.actor,
    }

    # Optional fields
    if entry.command:
        data["command"] = entry.command
    if entry.id:
        data["id"] = entry.id
    if entry.target:
        data["target"] = entry.target
    if entry.from_value:
        data["from_value"] = entry.from_value
    if entry.to_value:
        data["to_value"] = entry.to_value
    if entry.result:
        data["result"] = entry.result.value
    if entry.reason:
        data["reason"] = entry.reason

    return data


def parse_time_filter(value: str | None) -> datetime | None:
    """Parse a time filter value into a datetime.

    Supports two formats:
    - Relative: 1d (1 day ago), 2h (2 hours ago), 30m (30 minutes ago)
    - Absolute: ISO 8601 dates like 2024-12-01 or 2024-12-01T10:30:00

    Args:
        value: The time filter string to parse, or None.

    Returns:
        Parsed datetime in UTC, or None if value is None.

    Raises:
        ValueError: If the time format is not recognized.
    """
    if value is None:
        return None

    import re
    from datetime import UTC, datetime, timedelta

    # Try relative format first (e.g., 1d, 2h, 30m)
    relative_match = re.match(r"^(\d+)([dhm])$", value)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)

        now = datetime.now(UTC)
        if unit == "d":
            return now - timedelta(days=amount)
        if unit == "h":
            return now - timedelta(hours=amount)
        if unit == "m":
            return now - timedelta(minutes=amount)

    # Try ISO 8601 format
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        msg = (
            f"Invalid time format: {value}. "
            "Use relative format (1d, 2h, 30m) or ISO 8601 (2024-12-01T10:30:00)"
        )
        raise ValueError(msg) from None
    else:
        # If no timezone, assume UTC
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
