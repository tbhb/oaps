# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportExplicitAny=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# ruff: noqa: D415, A002
"""Validate command for OAPS configuration."""

from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.config import (
    ConfigSource,
    ConfigSourceName,
    ValidationIssue,
    discover_sources,
    read_toml_file,
    validate_config,
)
from oaps.exceptions import ConfigLoadError

from ._app import app
from ._exit_codes import (
    EXIT_LOAD_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATE_ERRORS,
    EXIT_VALIDATE_STRICT_WARNINGS,
)
from ._formatters import ConfigData, format_json
from ._write import FileSource

# Valid source names for validation
VALIDATABLE_SOURCES = (
    ConfigSourceName.PROJECT,
    ConfigSourceName.LOCAL,
    ConfigSourceName.USER,
)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _validate_source_file(
    source: ConfigSource,
    *,
    strict: bool,
) -> tuple[list[ValidationIssue], str | None]:
    """Validate a single config source file.

    Args:
        source: The ConfigSource to validate.
        strict: If True, unknown keys are errors. If False, they are warnings.

    Returns:
        Tuple of (list of validation issues, error message or None).
    """
    if not source.exists or source.path is None:
        return [], None

    # Load and parse the file
    try:
        config_data = read_toml_file(source.path)
    except ConfigLoadError as e:
        # Return a synthetic parse error as a validation issue
        return [
            ValidationIssue(
                severity="error",
                key="",
                message=f"Failed to parse file: {e}",
                source=source.name.value,
                actual=None,
                expected=None,
            )
        ], None

    # Run validation
    issues = validate_config(config_data, strict=strict)

    # Tag issues with source name and convert unknown key errors to warnings
    # in non-strict mode
    tagged_issues: list[ValidationIssue] = []
    for issue in issues:
        # Pydantic returns extra_forbidden errors for unknown keys
        is_unknown_key = "extra inputs are not permitted" in issue.message.lower()

        if is_unknown_key and not strict:
            # Convert to warning in non-strict mode
            tagged_issues.append(
                ValidationIssue(
                    severity="warning",
                    key=issue.key,
                    message=f"Unknown key '{issue.key}'",
                    source=source.name.value,
                    actual=issue.actual,
                    expected=issue.expected,
                )
            )
        else:
            # Keep as error, but tag with source
            tagged_issues.append(
                ValidationIssue(
                    severity=issue.severity,
                    key=issue.key,
                    message=issue.message,
                    source=source.name.value,
                    actual=issue.actual,
                    expected=issue.expected,
                )
            )

    return tagged_issues, None


def _format_text_output(
    results: dict[ConfigSourceName, tuple[ConfigSource, list[ValidationIssue]]],
) -> str:
    """Format validation results as human-readable text.

    Args:
        results: Dict mapping source names to (source, issues) tuples.

    Returns:
        Human-readable text output.
    """
    lines: list[str] = ["Validating config files...", ""]

    total_errors = 0
    total_warnings = 0

    for source_name, (source, issues) in results.items():
        # Skip sources without paths (DEFAULT, ENV, CLI)
        if source.path is None:
            continue

        # Format source header with relative path hint
        path_str = str(source.path)
        lines.append(f"{source_name.value} ({path_str}):")

        if not issues:
            lines.append("  OK")
        else:
            for issue in issues:
                prefix = "ERROR" if issue.severity == "error" else "WARNING"
                key_info = f"'{issue.key}'" if issue.key else ""

                if issue.expected:
                    lines.append(f"  {prefix}: {issue.message} {key_info}")
                    lines.append(f"         Expected: {issue.expected}")
                else:
                    lines.append(f"  {prefix}: {issue.message} {key_info}")

                if issue.severity == "error":
                    total_errors += 1
                else:
                    total_warnings += 1

        lines.append("")

    # Summary line
    err = "error" if total_errors == 1 else "errors"
    warn = "warning" if total_warnings == 1 else "warnings"
    lines.append(f"Validation complete: {total_errors} {err}, {total_warnings} {warn}")

    return "\n".join(lines)


def _format_json_output(
    results: dict[ConfigSourceName, tuple[ConfigSource, list[ValidationIssue]]],
) -> str:
    """Format validation results as JSON.

    Args:
        results: Dict mapping source names to (source, issues) tuples.

    Returns:
        JSON-formatted string.
    """
    files_list: list[ConfigData] = []
    summary: ConfigData = {"errors": 0, "warnings": 0}

    for source_name, (source, issues) in results.items():
        # Skip sources without paths
        if source.path is None:
            continue

        file_entry: ConfigData = {
            "source": source_name.value,
            "path": str(source.path),
            "valid": len([i for i in issues if i.severity == "error"]) == 0,
            "issues": [],
        }

        issue_list: list[ConfigData] = []
        for issue in issues:
            issue_entry: ConfigData = {
                "severity": issue.severity,
                "key": issue.key,
                "message": issue.message,
            }
            if issue.expected:
                issue_entry["expected"] = issue.expected
            if issue.actual is not None:
                issue_entry["actual"] = issue.actual

            issue_list.append(issue_entry)

            if issue.severity == "error":
                summary["errors"] = int(summary["errors"]) + 1
            else:
                summary["warnings"] = int(summary["warnings"]) + 1

        file_entry["issues"] = issue_list
        files_list.append(file_entry)

    output: ConfigData = {"files": files_list, "summary": summary}
    return format_json(output)


# -----------------------------------------------------------------------------
# Command
# -----------------------------------------------------------------------------


@app.command(name="validate")
def _validate(
    *,
    file: Annotated[
        FileSource | None,
        Parameter(
            name=["--file", "-f"],
            help="Validate specific file only (project, local, user)",
        ),
    ] = None,
    strict: Annotated[
        bool,
        Parameter(
            name="--strict",
            help="Treat warnings as errors",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Validate config files against the schema

    Validates configuration files for syntax and schema compliance.
    Unknown keys are reported as warnings unless --strict is used.

    Args:
        file: Specific source to validate (project, local, user).
        strict: If True, treat warnings as errors.
        format: Output format (text, json).
    """
    # Discover all sources
    try:
        sources = discover_sources()
    except (ConfigLoadError, OSError) as e:
        print(f"Error: Failed to discover sources: {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    # Filter to specific file if requested
    if file is not None:
        # Map FileSource to ConfigSourceName
        source_map = {
            FileSource.LOCAL: ConfigSourceName.LOCAL,
            FileSource.PROJECT: ConfigSourceName.PROJECT,
            FileSource.USER: ConfigSourceName.USER,
        }
        target_name = source_map[file]
        sources = [s for s in sources if s.name == target_name]

        if not sources:
            print(f"Error: Source '{file.value}' not found")
            raise SystemExit(EXIT_LOAD_ERROR)

        if not sources[0].exists:
            path_str = sources[0].path
            print(f"Error: Source '{file.value}' does not exist at {path_str}")
            raise SystemExit(EXIT_LOAD_ERROR)

    # Filter to file-based sources that exist
    file_sources = [
        s
        for s in sources
        if s.path is not None and s.exists and s.name in VALIDATABLE_SOURCES
    ]

    if not file_sources:
        print("No config files found to validate")
        raise SystemExit(EXIT_SUCCESS)

    # Validate each source
    results: dict[ConfigSourceName, tuple[ConfigSource, list[ValidationIssue]]] = {}
    for source in file_sources:
        issues, error = _validate_source_file(source, strict=strict)
        if error:
            print(f"Error: {error}")
            raise SystemExit(EXIT_LOAD_ERROR)
        results[source.name] = (source, issues)

    # Format output
    if format == OutputFormat.JSON:
        output = _format_json_output(results)
    else:
        output = _format_text_output(results)

    print(output.rstrip())

    # Determine exit code
    total_errors = sum(
        1
        for _, issues in results.values()
        for issue in issues
        if issue.severity == "error"
    )
    total_warnings = sum(
        1
        for _, issues in results.values()
        for issue in issues
        if issue.severity == "warning"
    )

    if total_errors > 0:
        raise SystemExit(EXIT_VALIDATE_ERRORS)
    if strict and total_warnings > 0:
        raise SystemExit(EXIT_VALIDATE_STRICT_WARNINGS)

    raise SystemExit(EXIT_SUCCESS)
