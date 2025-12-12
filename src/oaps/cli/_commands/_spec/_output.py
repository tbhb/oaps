# pyright: reportAny=false
# ruff: noqa: PLR0912
"""Output formatters for spec commands."""

from typing import Any

# Type alias for spec data - uses Any to match library signatures
type SpecData = dict[str, Any]  # pyright: ignore[reportExplicitAny]


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a Markdown table.

    Args:
        headers: Column headers for the table.
        rows: List of rows, where each row is a list of cell values.

    Returns:
        Markdown table string representation.
    """
    from pytablewriter import MarkdownTableWriter

    writer = MarkdownTableWriter(
        headers=headers,
        value_matrix=rows,
        margin=1,
    )
    return writer.dumps()


def format_json(data: SpecData, *, indent: bool = True) -> str:
    """Format data as JSON.

    Args:
        data: Dictionary to format as JSON.
        indent: Whether to pretty-print with indentation.

    Returns:
        JSON-formatted string representation.
    """
    import orjson

    options = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(data, option=options).decode("utf-8")


def format_yaml(data: SpecData) -> str:
    """Format data as YAML.

    Args:
        data: Dictionary to format as YAML.

    Returns:
        YAML-formatted string representation.
    """
    import yaml

    return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)


def format_ids(ids: list[str]) -> str:
    """Format IDs as newline-separated list.

    Args:
        ids: List of ID strings to format.

    Returns:
        IDs joined with newlines.
    """
    return "\n".join(ids)


def format_spec_table(specs: list[SpecData]) -> str:
    """Format specs as table with ID, Title, Type, Status columns.

    Args:
        specs: List of spec dictionaries.

    Returns:
        Markdown table string representation.
    """
    headers = ["ID", "Title", "Type", "Status"]
    rows = [
        [
            str(spec.get("id", "")),
            str(spec.get("title", "")),
            str(spec.get("type", "")),
            str(spec.get("status", "")),
        ]
        for spec in specs
    ]
    return format_table(headers, rows)


def _format_relationships(relationships: SpecData) -> list[str]:
    """Format relationships section of spec info."""
    if not relationships:
        return []

    lines = ["", "Relationships:"]

    # Map of relationship keys to display labels
    rel_map = [
        ("depends_on", "Depends on", True),
        ("extends", "Extends", False),
        ("supersedes", "Supersedes", False),
        ("integrates", "Integrates", True),
        ("dependents", "Dependents", True),
        ("extended_by", "Extended by", True),
        ("superseded_by", "Superseded by", False),
        ("integrated_by", "Integrated by", True),
    ]

    for key, label, is_list in rel_map:
        value = relationships.get(key)
        if value:
            formatted = ", ".join(value) if is_list else value
            lines.append(f"  {label}:{' ' * (14 - len(label))}{formatted}")

    return lines


def format_spec_info(spec: SpecData) -> str:
    """Format single spec as detailed info block.

    Args:
        spec: Spec dictionary with full metadata.

    Returns:
        Human-readable info block.
    """
    lines = [
        f"ID:       {spec.get('id', '')}",
        f"Slug:     {spec.get('slug', '')}",
        f"Title:    {spec.get('title', '')}",
        f"Type:     {spec.get('type', '')}",
        f"Status:   {spec.get('status', '')}",
        f"Created:  {spec.get('created', '')}",
        f"Updated:  {spec.get('updated', '')}",
    ]

    # Add optional fields
    optional_fields = [
        ("version", "Version"),
        ("summary", "Summary"),
    ]
    for key, label in optional_fields:
        value = spec.get(key)
        if value:
            lines.append(f"{label}:{' ' * (10 - len(label))}{value}")

    # Add list fields
    if spec.get("authors"):
        lines.append(f"Authors:  {', '.join(spec.get('authors', []))}")

    if spec.get("tags"):
        lines.append(f"Tags:     {', '.join(spec.get('tags', []))}")

    # Add relationships
    lines.extend(_format_relationships(spec.get("relationships", {})))

    # Add counts
    counts = spec.get("counts", {})
    if counts:
        lines.extend(
            [
                "",
                "Counts:",
                f"  Requirements: {counts.get('requirements', 0)}",
                f"  Tests:        {counts.get('tests', 0)}",
                f"  Artifacts:    {counts.get('artifacts', 0)}",
            ]
        )

    return "\n".join(lines)


def format_validation_table(issues: list[SpecData]) -> str:
    """Format validation issues as table with Severity, Field, Message.

    Args:
        issues: List of validation issue dictionaries.

    Returns:
        Markdown table string representation.
    """
    if not issues:
        return "No validation issues found."

    headers = ["Severity", "Field", "Message"]
    rows = [
        [
            str(issue.get("severity", "")),
            str(issue.get("field", "")),
            str(issue.get("message", "")),
        ]
        for issue in issues
    ]
    return format_table(headers, rows)


def format_requirement_table(requirements: list[SpecData]) -> str:
    """Format requirements as table with ID, Type, Title, Status, Tests.

    Args:
        requirements: List of requirement dictionaries.

    Returns:
        Markdown table string representation.
    """
    headers = ["ID", "Type", "Title", "Status", "Tests"]
    rows = [
        [
            str(r.get("id", "")),
            str(r.get("req_type", "")),
            str(r.get("title", ""))[:30],
            str(r.get("status", "")),
            str(len(r.get("verified_by", []))),
        ]
        for r in requirements
    ]
    return format_table(headers, rows)


def format_requirement_info(req: SpecData) -> str:
    """Format single requirement as detailed info block.

    Args:
        req: Requirement dictionary with full metadata.

    Returns:
        Human-readable info block.
    """
    lines = [
        f"ID:          {req.get('id', '')}",
        f"Title:       {req.get('title', '')}",
        f"Type:        {req.get('req_type', '')}",
        f"Status:      {req.get('status', '')}",
        f"Author:      {req.get('author', '')}",
        f"Created:     {req.get('created', '')}",
        f"Updated:     {req.get('updated', '')}",
    ]

    # Add description
    if req.get("description"):
        lines.extend(["", "Description:", f"  {req.get('description', '')}"])

    # Add optional fields
    if req.get("rationale"):
        lines.extend(["", "Rationale:", f"  {req.get('rationale', '')}"])

    if req.get("parent"):
        lines.append(f"Parent:      {req.get('parent', '')}")

    if req.get("source_section"):
        lines.append(f"Source:      {req.get('source_section', '')}")

    # Add list fields
    if req.get("acceptance_criteria"):
        lines.extend(["", "Acceptance Criteria:"])
        lines.extend(
            f"  - {criterion}" for criterion in req.get("acceptance_criteria", [])
        )

    if req.get("verified_by"):
        lines.append(f"Verified by: {', '.join(req.get('verified_by', []))}")

    if req.get("depends_on"):
        lines.append(f"Depends on:  {', '.join(req.get('depends_on', []))}")

    if req.get("tags"):
        lines.append(f"Tags:        {', '.join(req.get('tags', []))}")

    # Add Planguage fields if present
    planguage_fields = ["scale", "meter", "baseline", "goal", "stretch", "fail"]
    planguage_lines: list[str] = []
    for field in planguage_fields:
        value = req.get(field)
        if value is not None:
            label = field.capitalize()
            planguage_lines.append(f"  {label}:{' ' * (10 - len(label))}{value}")

    if planguage_lines:
        lines.extend(["", "Planguage:"])
        lines.extend(planguage_lines)

    return "\n".join(lines)


def format_test_table(tests: list[SpecData]) -> str:
    """Format tests as table with ID, Method, Title, Status, Reqs columns.

    Args:
        tests: List of test dictionaries.

    Returns:
        Markdown table string representation.
    """
    headers = ["ID", "Method", "Title", "Status", "Reqs"]
    rows = [
        [
            str(t.get("id", "")),
            str(t.get("method", "")),
            str(t.get("title", ""))[:30],
            str(t.get("status", "")),
            str(len(t.get("tests_requirements", []))),
        ]
        for t in tests
    ]
    return format_table(headers, rows)


def format_test_info(test: SpecData) -> str:
    """Format single test as detailed info block.

    Args:
        test: Test dictionary with full metadata.

    Returns:
        Human-readable info block.
    """
    lines = [
        f"ID:           {test.get('id', '')}",
        f"Title:        {test.get('title', '')}",
        f"Method:       {test.get('method', '')}",
        f"Status:       {test.get('status', '')}",
        f"Author:       {test.get('author', '')}",
        f"Created:      {test.get('created', '')}",
        f"Updated:      {test.get('updated', '')}",
    ]

    # Add requirements
    reqs = test.get("tests_requirements", [])
    if reqs:
        lines.append(f"Requirements: {', '.join(reqs)}")

    # Add description
    if test.get("description"):
        lines.extend(["", "Description:", f"  {test.get('description', '')}"])

    # Add file and function
    if test.get("file"):
        lines.append(f"File:         {test.get('file', '')}")
    if test.get("function"):
        lines.append(f"Function:     {test.get('function', '')}")

    # Add last run info
    if test.get("last_run"):
        lines.append(f"Last run:     {test.get('last_run', '')}")
    if test.get("last_result"):
        lines.append(f"Last result:  {test.get('last_result', '')}")

    # Add tags
    if test.get("tags"):
        lines.append(f"Tags:         {', '.join(test.get('tags', []))}")

    # Add performance test fields if present
    perf_lines: list[str] = []
    if test.get("last_value") is not None:
        perf_lines.append(f"  Last value:  {test.get('last_value')}")
    if test.get("threshold") is not None:
        perf_lines.append(f"  Threshold:   {test.get('threshold')}")
    if test.get("perf_baseline") is not None:
        perf_lines.append(f"  Baseline:    {test.get('perf_baseline')}")

    if perf_lines:
        lines.extend(["", "Performance:"])
        lines.extend(perf_lines)

    # Add manual test fields if present
    if test.get("steps"):
        lines.extend(["", "Steps:"])
        lines.extend(
            f"  {i + 1}. {step}" for i, step in enumerate(test.get("steps", []))
        )
    if test.get("expected_result"):
        lines.extend(["", "Expected:", f"  {test.get('expected_result', '')}"])
    if test.get("actual_result"):
        lines.extend(["", "Actual:", f"  {test.get('actual_result', '')}"])
    if test.get("tested_by"):
        lines.append(f"Tested by:    {test.get('tested_by', '')}")
    if test.get("tested_on"):
        lines.append(f"Tested on:    {test.get('tested_on', '')}")

    return "\n".join(lines)


def format_sync_result(result: SpecData) -> str:
    """Format sync result as summary block.

    Args:
        result: SyncResult dictionary with counts.

    Returns:
        Human-readable summary block.
    """
    lines = [
        "Sync Summary:",
        f"  Updated:     {result.get('updated', 0)}",
        f"  Orphaned:    {result.get('orphaned', 0)}",
        f"  Skipped:     {result.get('skipped_no_file', 0)} (no file/function)",
    ]

    errors = result.get("errors", [])
    if errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"  - {error}" for error in errors)

    return "\n".join(lines)


def format_artifact_table(artifacts: list[SpecData]) -> str:
    """Format artifacts as table with ID, Type, Title, Status columns.

    Args:
        artifacts: List of artifact dictionaries.

    Returns:
        Markdown table string representation.
    """
    headers = ["ID", "Type", "Title", "Status"]
    rows = [
        [
            str(a.get("id", "")),
            str(a.get("artifact_type", "")),
            str(a.get("title", ""))[:30],
            str(a.get("status", "")),
        ]
        for a in artifacts
    ]
    return format_table(headers, rows)


def format_artifact_info(artifact: SpecData) -> str:
    """Format single artifact as detailed info block.

    Args:
        artifact: Artifact dictionary with full metadata.

    Returns:
        Human-readable info block.
    """
    lines = [
        f"ID:           {artifact.get('id', '')}",
        f"Title:        {artifact.get('title', '')}",
        f"Type:         {artifact.get('artifact_type', '')}",
        f"Status:       {artifact.get('status', '')}",
        f"Author:       {artifact.get('author', '')}",
        f"Created:      {artifact.get('created', '')}",
        f"Updated:      {artifact.get('updated', '')}",
        f"File:         {artifact.get('file_path', '')}",
    ]

    # Add description
    if artifact.get("description"):
        lines.extend(["", "Description:", f"  {artifact.get('description', '')}"])

    # Add optional fields
    if artifact.get("subtype"):
        lines.append(f"Subtype:      {artifact.get('subtype', '')}")

    if artifact.get("references"):
        lines.append(f"References:   {', '.join(artifact.get('references', []))}")

    if artifact.get("tags"):
        lines.append(f"Tags:         {', '.join(artifact.get('tags', []))}")

    if artifact.get("supersedes"):
        lines.append(f"Supersedes:   {artifact.get('supersedes', '')}")

    if artifact.get("superseded_by"):
        lines.append(f"Superseded by: {artifact.get('superseded_by', '')}")

    if artifact.get("summary"):
        lines.extend(["", "Summary:", f"  {artifact.get('summary', '')}"])

    if artifact.get("metadata_file_path"):
        lines.append(f"Metadata file: {artifact.get('metadata_file_path', '')}")

    return "\n".join(lines)


def format_rebuild_result(result: SpecData) -> str:
    """Format rebuild result as summary block.

    Args:
        result: RebuildResult dictionary with counts.

    Returns:
        Human-readable summary block.
    """
    lines = [
        "Rebuild Summary:",
        f"  Scanned:     {result.get('scanned', 0)}",
        f"  Indexed:     {result.get('indexed', 0)}",
        f"  Skipped:     {result.get('skipped', 0)}",
    ]

    errors = result.get("errors", [])
    if errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"  - {error}" for error in errors)

    return "\n".join(lines)


def _format_timestamp(timestamp: str) -> str:
    """Format an ISO timestamp for display.

    Converts ISO 8601 timestamp to a more readable format.

    Args:
        timestamp: ISO 8601 timestamp string.

    Returns:
        Human-readable timestamp string.
    """
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(timestamp)


def _format_history_details(entry: SpecData) -> str:
    """Format history entry details for table display.

    Args:
        entry: History entry dictionary.

    Returns:
        Formatted details string.
    """
    details: list[str] = []

    if entry.get("id"):
        details.append(f"id={entry['id']}")
    if entry.get("target"):
        details.append(f"target={entry['target']}")
    if entry.get("from_value") and entry.get("to_value"):
        details.append(f"{entry['from_value']} -> {entry['to_value']}")
    elif entry.get("to_value"):
        details.append(f"-> {entry['to_value']}")
    if entry.get("result"):
        details.append(f"result={entry['result']}")

    return ", ".join(details) if details else ""


def format_history_table(entries: list[SpecData]) -> str:
    """Format history entries as table with Timestamp, Event, Actor, Details.

    Args:
        entries: List of history entry dictionaries.

    Returns:
        Markdown table string representation.
    """
    if not entries:
        return "No history entries found."

    headers = ["Timestamp", "Event", "Actor", "Details"]
    rows = [
        [
            _format_timestamp(str(e.get("timestamp", ""))),
            str(e.get("event", "")),
            str(e.get("actor", "")),
            _format_history_details(e),
        ]
        for e in entries
    ]
    return format_table(headers, rows)


def format_history_info(entry: SpecData) -> str:
    """Format single history entry as detailed info block.

    Args:
        entry: History entry dictionary with full metadata.

    Returns:
        Human-readable info block.
    """
    lines = [
        f"Timestamp:  {_format_timestamp(str(entry.get('timestamp', '')))}",
        f"Event:      {entry.get('event', '')}",
        f"Actor:      {entry.get('actor', '')}",
    ]

    # Add optional fields
    if entry.get("command"):
        lines.append(f"Command:    {entry.get('command', '')}")
    if entry.get("id"):
        lines.append(f"ID:         {entry.get('id', '')}")
    if entry.get("target"):
        lines.append(f"Target:     {entry.get('target', '')}")
    if entry.get("from_value"):
        lines.append(f"From:       {entry.get('from_value', '')}")
    if entry.get("to_value"):
        lines.append(f"To:         {entry.get('to_value', '')}")
    if entry.get("result"):
        lines.append(f"Result:     {entry.get('result', '')}")
    if entry.get("reason"):
        lines.append(f"Reason:     {entry.get('reason', '')}")

    return "\n".join(lines)
