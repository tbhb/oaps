# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false
"""Specification system hook actions.

This module provides Python action entrypoints for hook rules that support
the OAPS specification system. Actions handle:

- Spec validation (structure, IDs, cross-references)
- Metadata synchronization (indexes, artifacts)
- History tracking
- Test result synchronization
- Status change notifications

All functions follow the hook action signature:
    def action_name(context: HookContext) -> dict[str, object] | None

Return values can include:
- "deny": bool - Block the operation
- "deny_message": str - Message for deny
- "warn_message": str - Warning message to display
- "inject_content": str - Content to inject into context
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext

# Constants
SPEC_DIR = ".oaps/docs/specs"
SPEC_ID_LENGTH = 4
REQUIREMENT_ID_PATTERN = re.compile(r"^[A-Z]{2,3}-\d{4}(\.\d+)?$")
TEST_ID_PATTERN = re.compile(r"^T-\d{4}(\.\d+)?$")
CROSSREF_PATTERN = re.compile(r"(\d{4}):([A-Z]{2,3}-\d{4}(\.\d+)?)")

# Standard requirement prefixes
STANDARD_REQUIREMENT_PREFIXES = frozenset({"FR", "QR", "SR", "AR", "IR", "DR", "CR"})

# Pytest status mapping to spec test status
PYTEST_STATUS_MAP: dict[str, str] = {
    "PASSED": "passing",
    "FAILED": "failing",
    "SKIPPED": "skipped",
    "XFAIL": "failing",
    "XPASS": "passing",
    "ERROR": "failing",
}

# Required fields for JSON schema validation
INDEX_REQUIRED_FIELDS = frozenset({"id", "title", "status", "version"})
REQUIREMENTS_ITEM_REQUIRED_FIELDS = frozenset({"id", "title"})
TESTS_ITEM_REQUIRED_FIELDS = frozenset({"id", "title", "method"})


# -----------------------------------------------------------------------------
# Validation hooks
# -----------------------------------------------------------------------------


def validate_specs_precommit(context: HookContext) -> dict[str, object]:
    """Validate spec structure before git commit.

    Checks that all specs have required files, valid JSON structure with
    required fields, and root index consistency.

    Args:
        context: Hook context.

    Returns:
        Status dict with validation results.
    """
    project_root = _get_project_root(context)
    if project_root is None:
        return {"status": "skipped", "reason": "No project root"}

    specs_dir = project_root / SPEC_DIR
    if not specs_dir.exists():
        return {"status": "skipped", "reason": "No specs directory"}

    errors: list[str] = []
    warnings: list[str] = []
    found_spec_ids: set[str] = set()

    # Check each spec directory
    for spec_path in specs_dir.iterdir():
        if not spec_path.is_dir() or spec_path.name == "artifacts":
            continue

        spec_id = spec_path.name
        found_spec_ids.add(spec_id[:SPEC_ID_LENGTH])

        # Validate structure and JSON schemas
        struct_errors, schema_errors = _validate_spec_structure(spec_path)
        errors.extend(f"{spec_id}: {err}" for err in struct_errors)
        warnings.extend(f"{spec_id}: {err}" for err in schema_errors)

        # Check bidirectional links
        req_path = spec_path / "requirements.json"
        test_path = spec_path / "tests.json"
        if req_path.exists() and test_path.exists():
            link_errors = _check_bidirectional_links(req_path, test_path)
            warnings.extend(f"{spec_id}: {err}" for err in link_errors)

    # Validate root index consistency
    root_index_errors = _validate_root_index_consistency(specs_dir, found_spec_ids)
    errors.extend(root_index_errors)

    if errors:
        return {
            "deny": True,
            "deny_message": "Spec validation failed:\n- " + "\n- ".join(errors),
            "status": "failed",
            "errors": errors,
            "warnings": warnings,
        }

    if warnings:
        return {
            "status": "passed_with_warnings",
            "warnings": warnings,
            "warn_message": "Spec warnings:\n- " + "\n- ".join(warnings),
        }

    return {"status": "passed"}


def _validate_spec_structure(spec_path: Path) -> tuple[list[str], list[str]]:
    """Validate a single spec directory structure with JSON schema checking.

    Args:
        spec_path: Path to the spec directory.

    Returns:
        Tuple of (errors, warnings) where errors are blocking and warnings
        are informational schema issues.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check required files
    required_files = [
        "index.json",
        "index.md",
        "requirements.json",
        "tests.json",
        "history.jsonl",
    ]
    missing = [f for f in required_files if not (spec_path / f).exists()]
    errors.extend(f"Missing {filename}" for filename in missing)

    # Validate JSON files with schema checking
    json_validators: dict[str, tuple[frozenset[str], str | None]] = {
        "index.json": (INDEX_REQUIRED_FIELDS, None),
        "requirements.json": (REQUIREMENTS_ITEM_REQUIRED_FIELDS, "requirements"),
        "tests.json": (TESTS_ITEM_REQUIRED_FIELDS, "tests"),
    }

    for json_file, (required_fields, array_key) in json_validators.items():
        json_path = spec_path / json_file
        if not json_path.exists():
            continue
        try:
            with json_path.open() as f:
                data = json.load(f)
            schema_warnings = _validate_json_schema(
                data, required_fields, array_key, json_file
            )
            warnings.extend(schema_warnings)
        except json.JSONDecodeError as e:
            errors.append(f"{json_file}: Invalid JSON - {e}")

    return errors, warnings


def _validate_json_schema(
    data: object,
    required_fields: frozenset[str],
    array_key: str | None,
    filename: str,
) -> list[str]:
    """Validate JSON data against required fields.

    Args:
        data: Parsed JSON data.
        required_fields: Required field names.
        array_key: If set, validate items in this array key; else validate root.
        filename: Filename for error messages.

    Returns:
        List of schema warning messages.
    """
    warnings: list[str] = []

    if array_key is None:
        # Validate root object
        if isinstance(data, dict):
            missing = required_fields - set(data.keys())
            if missing:
                warnings.append(
                    f"{filename}: Missing required fields: {', '.join(sorted(missing))}"
                )
    else:
        # Validate items in array
        items: list[object] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and array_key in data:
            array_value = data.get(array_key)
            if isinstance(array_value, list):
                items = array_value

        for i, item in enumerate(items):
            if isinstance(item, dict):
                missing = required_fields - set(item.keys())
                if missing:
                    item_id = item.get("id", f"index {i}")
                    missing_str = ", ".join(sorted(missing))
                    warnings.append(
                        f"{filename}[{item_id}]: Missing fields: {missing_str}"
                    )

    return warnings


def _validate_root_index_consistency(
    specs_dir: Path, found_spec_ids: set[str]
) -> list[str]:
    """Validate root index.json consistency with spec directories.

    Args:
        specs_dir: Path to specs directory.
        found_spec_ids: Set of spec IDs found in filesystem.

    Returns:
        List of error messages for inconsistencies.
    """
    errors: list[str] = []
    root_index_path = specs_dir / "index.json"

    if not root_index_path.exists():
        if found_spec_ids:
            errors.append("Root index.json missing but spec directories exist")
        return errors

    try:
        with root_index_path.open() as f:
            root_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        errors.append("Root index.json is invalid or unreadable")
        return errors

    if not isinstance(root_data, dict):
        errors.append("Root index.json must be an object")
        return errors

    indexed_specs = root_data.get("specs", [])
    if not isinstance(indexed_specs, list):
        errors.append("Root index.json 'specs' must be an array")
        return errors

    indexed_ids = {spec.get("id") for spec in indexed_specs if isinstance(spec, dict)}

    # Check for specs in index but not on filesystem
    orphaned_in_index = indexed_ids - found_spec_ids
    errors.extend(
        f"Root index references non-existent spec: {spec_id}"
        for spec_id in orphaned_in_index
    )

    # Check for specs on filesystem but not in index
    missing_from_index = found_spec_ids - indexed_ids
    errors.extend(
        f"Spec {spec_id} exists but missing from root index"
        for spec_id in missing_from_index
    )

    return errors


def validate_requirement_ids(context: HookContext) -> dict[str, object]:
    """Validate requirement IDs before spec modifications.

    Ensures IDs follow the correct format with standard prefixes (FR, QR, SR,
    AR, IR, DR, CR), are unique within the spec, and warns about non-sequential
    numbering.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with validation results.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    new_content = tool_input.get("content") or tool_input.get("new_string")

    if not new_content or not isinstance(new_content, str):
        return {"status": "skipped"}

    errors: list[str] = []
    warnings: list[str] = []

    # Parse requirements from content
    try:
        data = json.loads(new_content)
        if isinstance(data, list):
            requirements = data
        elif isinstance(data, dict) and "requirements" in data:
            req_value = data.get("requirements")
            requirements = req_value if isinstance(req_value, list) else []
        else:
            return {"status": "skipped", "reason": "Unknown format"}
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "Not valid JSON"}

    seen_ids: set[str] = set()
    prefix_numbers: dict[str, list[int]] = {}

    for req in requirements:
        if not isinstance(req, dict):
            continue

        req_id = req.get("id", "")
        if not isinstance(req_id, str):
            continue

        # Check format
        if not REQUIREMENT_ID_PATTERN.match(req_id):
            errors.append(f"Invalid ID format: {req_id} (expected PREFIX-NNNN)")
            continue

        # Extract and validate prefix
        prefix = req_id.split("-")[0]
        if prefix not in STANDARD_REQUIREMENT_PREFIXES:
            valid_prefixes = ", ".join(sorted(STANDARD_REQUIREMENT_PREFIXES))
            errors.append(
                f"Non-standard prefix in {req_id}: expected one of {valid_prefixes}"
            )

        # Track numbers by prefix for sequential check
        num_part = req_id.split("-")[1].split(".")[0]
        try:
            num = int(num_part)
            prefix_numbers.setdefault(prefix, []).append(num)
        except ValueError:
            pass

        # Check uniqueness
        if req_id in seen_ids:
            errors.append(f"Duplicate ID: {req_id}")
        seen_ids.add(req_id)

    # Check for non-sequential IDs (warning only)
    for prefix, numbers in prefix_numbers.items():
        sorted_nums = sorted(numbers)
        gaps = [
            f"{sorted_nums[i - 1]}-{sorted_nums[i]}"
            for i in range(1, len(sorted_nums))
            if sorted_nums[i] - sorted_nums[i - 1] > 1
        ]
        if gaps:
            warnings.append(f"{prefix} IDs have gaps: {', '.join(gaps)}")

    if errors:
        return {
            "deny": True,
            "deny_message": f"Requirement ID validation failed in {file_path}:\n- "
            + "\n- ".join(errors),
            "status": "failed",
        }

    result: dict[str, object] = {"status": "passed", "validated_count": len(seen_ids)}
    if warnings:
        result["warn_message"] = "ID warnings:\n- " + "\n- ".join(warnings)
        result["warnings"] = warnings

    return result


def validate_test_ids(context: HookContext) -> dict[str, object]:
    """Validate test IDs before spec modifications.

    Ensures test IDs follow the correct format and are unique.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with validation results.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    new_content = tool_input.get("content") or tool_input.get("new_string")

    if not new_content or not isinstance(new_content, str):
        return {"status": "skipped"}

    errors: list[str] = []

    try:
        data = json.loads(new_content)
        if isinstance(data, list):
            tests = data
        elif isinstance(data, dict) and "tests" in data:
            tests = data.get("tests", [])
        else:
            return {"status": "skipped", "reason": "Unknown format"}
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "Not valid JSON"}

    seen_ids: set[str] = set()
    for test in tests:
        if not isinstance(test, dict):
            continue

        test_id = test.get("id", "")

        if not TEST_ID_PATTERN.match(test_id):
            errors.append(f"Invalid test ID format: {test_id} (expected T-NNNN)")

        if test_id in seen_ids:
            errors.append(f"Duplicate test ID: {test_id}")
        seen_ids.add(test_id)

    if errors:
        return {
            "deny": True,
            "deny_message": f"Test ID validation failed in {file_path}:\n- "
            + "\n- ".join(errors),
            "status": "failed",
        }

    return {"status": "passed", "validated_count": len(seen_ids)}


def validate_crossrefs(context: HookContext) -> dict[str, object]:
    """Validate cross-references in spec files.

    Checks that cross-references point to existing specs and items.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with validation results (warnings only, non-blocking).
    """
    project_root = _get_project_root(context)
    if project_root is None:
        return {"status": "skipped"}

    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    new_content = tool_input.get("content") or tool_input.get("new_string")

    if not new_content or not isinstance(new_content, str):
        return {"status": "skipped"}

    # Find cross-references
    crossrefs = CROSSREF_PATTERN.findall(new_content)
    if not crossrefs:
        return {"status": "passed", "crossref_count": 0}

    warnings = _validate_crossref_targets(project_root, crossrefs)

    if warnings:
        return {
            "status": "passed_with_warnings",
            "warnings": warnings,
            "warn_message": f"Cross-reference warnings in {file_path}:\n- "
            + "\n- ".join(warnings),
        }

    return {"status": "passed", "crossref_count": len(crossrefs)}


def _validate_crossref_targets(
    project_root: Path, crossrefs: list[tuple[str, str, str]]
) -> list[str]:
    """Validate cross-reference targets exist."""
    warnings: list[str] = []
    specs_dir = project_root / SPEC_DIR

    for spec_num, item_id, _ in crossrefs:
        target_spec = _find_spec_by_id(specs_dir, spec_num)

        if target_spec is None:
            warnings.append(f"Cross-reference target spec not found: {spec_num}")
            continue

        if not _item_exists_in_spec(target_spec, item_id):
            warnings.append(f"Cross-reference target not found: {spec_num}:{item_id}")

    return warnings


def _find_spec_by_id(specs_dir: Path, spec_id: str) -> Path | None:
    """Find a spec directory by its numeric ID prefix."""
    for spec_path in specs_dir.iterdir():
        if spec_path.is_dir() and spec_path.name.startswith(spec_id):
            return spec_path
    return None


def _item_exists_in_spec(spec_path: Path, item_id: str) -> bool:
    """Check if an item exists in a spec's requirements or tests."""
    for json_file in ["requirements.json", "tests.json"]:
        json_path = spec_path / json_file
        if not json_path.exists():
            continue
        try:
            with json_path.open() as f:
                data = json.load(f)
            items = (
                data
                if isinstance(data, list)
                else data.get("requirements", data.get("tests", []))
            )
            if any(
                item.get("id") == item_id for item in items if isinstance(item, dict)
            ):
                return True
        except (json.JSONDecodeError, OSError):
            pass
    return False


# -----------------------------------------------------------------------------
# Synchronization hooks
# -----------------------------------------------------------------------------


def sync_root_index(context: HookContext) -> dict[str, object]:
    """Sync root index.json after per-spec index changes.

    Updates the root index to reflect changes in per-spec indexes. Handles
    both creation and deletion of spec directories by scanning the filesystem
    and detecting removed specs.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with sync results including added/removed specs.
    """
    project_root = _get_project_root(context)
    if project_root is None:
        return {"status": "skipped", "reason": "No project root"}

    specs_dir = project_root / SPEC_DIR
    root_index_path = specs_dir / "index.json"

    if not specs_dir.exists():
        return {"status": "skipped", "reason": "No specs directory"}

    # Read existing root index to detect deletions
    old_spec_ids: set[str] = set()
    if root_index_path.exists():
        try:
            with root_index_path.open() as f:
                old_data = json.load(f)
            if isinstance(old_data, dict):
                old_specs = old_data.get("specs", [])
                if isinstance(old_specs, list):
                    for spec in old_specs:
                        if isinstance(spec, dict):
                            spec_id = spec.get("id")
                            if isinstance(spec_id, str):
                                old_spec_ids.add(spec_id)
        except (json.JSONDecodeError, OSError):
            pass

    # Build root index from per-spec indexes
    specs = _collect_spec_metadata(specs_dir)
    new_spec_ids = {spec["id"] for spec in specs}

    # Detect additions and deletions
    added_specs = sorted(new_spec_ids - old_spec_ids)
    removed_specs = sorted(old_spec_ids - new_spec_ids)

    # Write updated root index
    root_index = {"specs": specs, "updated": datetime.now(tz=UTC).isoformat()}

    try:
        with root_index_path.open("w") as f:
            json.dump(root_index, f, indent=2)
    except OSError as e:
        return {"status": "error", "warn_message": f"Failed to sync root index: {e}"}

    result: dict[str, object] = {"status": "synced", "spec_count": len(specs)}

    # Report changes
    if added_specs or removed_specs:
        changes: list[str] = []
        if added_specs:
            changes.append(f"Added: {', '.join(added_specs)}")
        if removed_specs:
            changes.append(f"Removed: {', '.join(removed_specs)}")
        result["inject_content"] = "Root index updated. " + "; ".join(changes)
        result["added"] = added_specs
        result["removed"] = removed_specs

    return result


def _collect_spec_metadata(specs_dir: Path) -> list[dict[str, str]]:
    """Collect metadata from all spec index.json files."""
    specs: list[dict[str, str]] = []

    for spec_path in sorted(specs_dir.iterdir()):
        if not spec_path.is_dir() or spec_path.name == "artifacts":
            continue

        spec_index_path = spec_path / "index.json"
        if spec_index_path.exists():
            try:
                with spec_index_path.open() as f:
                    spec_data = json.load(f)
                spec_name = spec_path.name
                specs.append(
                    {
                        "id": spec_name[:SPEC_ID_LENGTH],
                        "slug": spec_name[SPEC_ID_LENGTH + 1 :]
                        if len(spec_name) > SPEC_ID_LENGTH
                        else "",
                        "title": spec_data.get("title", ""),
                        "status": spec_data.get("status", "draft"),
                        "version": spec_data.get("version", "0.1.0"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                pass

    return specs


def rebuild_artifacts_index(context: HookContext) -> dict[str, object]:
    """Rebuild artifacts.json after artifact file changes.

    Scans artifact files and rebuilds the index from frontmatter.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with rebuild results.
    """
    result = _get_artifacts_dir_for_rebuild(context)
    if result is None:
        return {"status": "skipped"}

    artifacts_dir, artifacts_index_path = result

    # Scan artifacts
    artifacts = [
        _parse_artifact_metadata(p) for p in artifacts_dir.iterdir() if p.is_file()
    ]
    artifacts = [a for a in artifacts if a is not None]

    # Write artifacts index
    try:
        with artifacts_index_path.open("w") as f:
            json.dump(artifacts, f, indent=2)
    except OSError as e:
        return {
            "status": "error",
            "warn_message": f"Failed to rebuild artifacts index: {e}",
        }
    else:
        return {"status": "rebuilt", "artifact_count": len(artifacts)}


def _get_artifacts_dir_for_rebuild(
    context: HookContext,
) -> tuple[Path, Path] | None:
    """Get artifacts directory and index path for rebuild operation."""
    tool_input = _get_tool_input(context)
    if not tool_input:
        return None

    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str):
        return None

    # Extract spec directory from file path
    match = re.search(r"(\.oaps/docs/specs/\d{4}-[a-z0-9-]+)/artifacts/", file_path)
    if not match:
        return None

    project_root = _get_project_root(context)
    if project_root is None:
        return None

    spec_dir = project_root / match.group(1)
    artifacts_dir = spec_dir / "artifacts"
    artifacts_index_path = spec_dir / "artifacts.json"

    if not artifacts_dir.exists():
        return None

    return artifacts_dir, artifacts_index_path


# -----------------------------------------------------------------------------
# History tracking hooks
# -----------------------------------------------------------------------------


def record_history(context: HookContext) -> dict[str, object]:
    """Record changes to history.jsonl with change detection.

    Appends a history entry when spec files are modified, including details
    about what changed (added, modified, removed items).

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with recording results.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str):
        return {"status": "skipped"}

    # Extract spec directory
    match = re.search(r"(\.oaps/docs/specs/\d{4}-[a-z0-9-]+)/", file_path)
    if not match:
        return {"status": "skipped"}

    project_root = _get_project_root(context)
    if project_root is None:
        return {"status": "skipped"}

    spec_dir = project_root / match.group(1)
    history_path = spec_dir / "history.jsonl"

    # Determine action type from filename
    filename = Path(file_path).name
    action = _get_action_type(filename)

    # Detect actor
    actor = _detect_actor()

    # Detect changes by comparing old vs new content
    changes = _detect_content_changes(context, project_root / file_path, filename)

    # Create history entry
    entry: dict[str, object] = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "action": action,
        "actor": actor,
        "files": [filename],
        "reason": None,
    }

    if changes:
        entry["changes"] = changes

    # Append to history
    try:
        with history_path.open("a") as f:
            _ = f.write(json.dumps(entry) + "\n")
    except OSError as e:
        return {"status": "error", "warn_message": f"Failed to record history: {e}"}

    return {"status": "recorded", "action": action, "changes": changes}


def _detect_content_changes(
    context: HookContext, file_path: Path, filename: str
) -> dict[str, list[str]] | None:
    """Detect changes between old and new content.

    Args:
        context: Hook context with tool input.
        file_path: Path to the file being modified.
        filename: Name of the file.

    Returns:
        Dict with added/modified/removed arrays, or None if detection fails.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return None

    new_content = tool_input.get("content") or tool_input.get("new_string")
    if not new_content or not isinstance(new_content, str):
        return None

    # Only detect changes for JSON files with IDs
    if not filename.endswith(".json"):
        return None

    # Read old content from file (if exists)
    old_content: str | None = None
    if file_path.exists():
        try:
            old_content = file_path.read_text()
        except OSError:
            pass

    if not old_content:
        # New file - all items are additions
        try:
            new_data = json.loads(new_content)
            new_ids = _extract_ids_from_data(new_data, filename)
            if new_ids:
                return {"added": sorted(new_ids), "modified": [], "removed": []}
        except json.JSONDecodeError:
            pass
        return None

    # Compare old and new
    try:
        old_data = json.loads(old_content)
        new_data = json.loads(new_content)
    except json.JSONDecodeError:
        return None

    old_ids = _extract_ids_from_data(old_data, filename)
    new_ids = _extract_ids_from_data(new_data, filename)

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)

    # For items in both, check if content changed
    common_ids = old_ids & new_ids
    modified: list[str] = []
    if common_ids:
        old_items = _build_id_map(old_data, filename)
        new_items = _build_id_map(new_data, filename)
        modified = sorted(
            item_id
            for item_id in common_ids
            if old_items.get(item_id) != new_items.get(item_id)
        )

    if added or modified or removed:
        return {"added": added, "modified": modified, "removed": removed}

    return None


def _extract_ids_from_data(data: object, filename: str) -> set[str]:
    """Extract IDs from JSON data based on filename."""
    ids: set[str] = set()

    if filename == "requirements.json":
        array_key = "requirements"
    elif filename == "tests.json":
        array_key = "tests"
    else:
        return ids

    items: list[object] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        array_value = data.get(array_key)
        if isinstance(array_value, list):
            items = array_value

    for item in items:
        if isinstance(item, dict):
            item_id = item.get("id")
            if isinstance(item_id, str):
                ids.add(item_id)

    return ids


def _build_id_map(data: object, filename: str) -> dict[str, object]:
    """Build a map of ID to item content for comparison."""
    id_map: dict[str, object] = {}

    if filename == "requirements.json":
        array_key = "requirements"
    elif filename == "tests.json":
        array_key = "tests"
    else:
        return id_map

    items: list[object] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        array_value = data.get(array_key)
        if isinstance(array_value, list):
            items = array_value

    for item in items:
        if isinstance(item, dict):
            item_id = item.get("id")
            if isinstance(item_id, str):
                id_map[item_id] = item

    return id_map


def _get_action_type(filename: str) -> str:
    """Get action type from filename."""
    action_map = {
        "requirements.json": "update_requirements",
        "tests.json": "update_tests",
        "index.json": "update_metadata",
        "index.md": "update_content",
    }
    return action_map.get(filename, "update")


# -----------------------------------------------------------------------------
# Test synchronization hooks
# -----------------------------------------------------------------------------


def sync_test_results(context: HookContext) -> dict[str, object]:
    """Update test status after pytest runs.

    Parses pytest output for individual test results and updates tests.json
    files with status and timestamp. Maps pytest statuses to spec statuses:
    PASSED->passing, FAILED->failing, SKIPPED->skipped, XFAIL->failing,
    XPASS->passing, ERROR->failing.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with sync results.
    """
    tool_response = _get_tool_response(context)
    if not tool_response:
        return {"status": "skipped", "reason": "No tool response"}

    output = str(tool_response.get("result", ""))

    # Parse individual test results
    test_results = _parse_pytest_output(output)

    # Count by status
    status_counts: dict[str, int] = {}
    for result in test_results.values():
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    # Update tests.json files if we found results
    project_root = _get_project_root(context)
    updated_specs: list[str] = []
    if project_root and test_results:
        updated_specs = _update_tests_json_with_results(project_root, test_results)

    passed = status_counts.get("passing", 0)
    failed = status_counts.get("failing", 0)
    skipped = status_counts.get("skipped", 0)

    msg = f"Test results: {passed} passed, {failed} failed, {skipped} skipped"
    if updated_specs:
        msg += f"\nUpdated specs: {', '.join(updated_specs)}"

    return {
        "status": "synced",
        "inject_content": msg,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "updated_specs": updated_specs,
    }


def _parse_pytest_output(output: str) -> dict[str, dict[str, str]]:
    """Parse pytest output to extract individual test results.

    Args:
        output: Raw pytest output string.

    Returns:
        Dict mapping test names to result info with status and timestamp.
    """
    results: dict[str, dict[str, str]] = {}
    timestamp = datetime.now(tz=UTC).isoformat()

    # Pattern to match pytest test results like:
    # tests/test_foo.py::test_bar PASSED
    # tests/test_foo.py::TestClass::test_method FAILED
    test_pattern = re.compile(
        r"^([\w/\-\.]+::\S+)\s+(PASSED|FAILED|SKIPPED|XFAIL|XPASS|ERROR)",
        re.MULTILINE,
    )

    for match in test_pattern.finditer(output):
        test_name = match.group(1)
        pytest_status = match.group(2)
        spec_status = PYTEST_STATUS_MAP.get(pytest_status, "failing")

        results[test_name] = {
            "status": spec_status,
            "timestamp": timestamp,
            "pytest_status": pytest_status,
        }

    return results


def _update_tests_json_with_results(
    project_root: Path, test_results: dict[str, dict[str, str]]
) -> list[str]:
    """Update tests.json files with pytest results.

    Args:
        project_root: Project root path.
        test_results: Parsed test results from pytest.

    Returns:
        List of spec IDs that were updated.
    """
    updated_specs: list[str] = []
    specs_dir = project_root / SPEC_DIR

    if not specs_dir.exists():
        return updated_specs

    for spec_path in specs_dir.iterdir():
        if not spec_path.is_dir() or spec_path.name == "artifacts":
            continue

        tests_path = spec_path / "tests.json"
        if not tests_path.exists():
            continue

        try:
            with tests_path.open() as f:
                tests_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Get tests array
        if isinstance(tests_data, list):
            tests = tests_data
            wrapper = None
        elif isinstance(tests_data, dict):
            tests_value = tests_data.get("tests")
            tests = tests_value if isinstance(tests_value, list) else []
            wrapper = tests_data
        else:
            continue

        # Update test statuses
        modified = False
        for test in tests:
            if not isinstance(test, dict):
                continue

            impl_path = test.get("implementation")
            if not impl_path or not isinstance(impl_path, str):
                continue

            # Check if any pytest result matches this test implementation
            for pytest_name, result in test_results.items():
                if impl_path in pytest_name or pytest_name.endswith(impl_path):
                    test["status"] = result["status"]
                    test["last_run"] = result["timestamp"]
                    modified = True
                    break

        if modified:
            try:
                output_data = wrapper if wrapper else tests
                with tests_path.open("w") as f:
                    json.dump(output_data, f, indent=2)
                updated_specs.append(spec_path.name[:SPEC_ID_LENGTH])
            except OSError:
                pass

    return updated_specs


def sync_coverage(context: HookContext) -> dict[str, object]:
    """Parse coverage output and update test records.

    Extracts line and branch coverage percentages from coverage output
    and updates corresponding test records in tests.json files.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with coverage sync results.
    """
    tool_response = _get_tool_response(context)
    if not tool_response:
        return {"status": "skipped", "reason": "No tool response"}

    output = str(tool_response.get("result", ""))

    # Parse coverage output
    coverage_data = _parse_coverage_output(output)
    if not coverage_data:
        return {"status": "skipped", "reason": "No coverage data found"}

    # Update tests.json files with coverage
    project_root = _get_project_root(context)
    updated_specs: list[str] = []
    if project_root:
        updated_specs = _update_tests_json_with_coverage(project_root, coverage_data)

    total_coverage = coverage_data.get("total", {})
    line_cov = total_coverage.get("line", 0)
    branch_cov = total_coverage.get("branch")

    msg = f"Coverage: {line_cov}% lines"
    if branch_cov is not None:
        msg += f", {branch_cov}% branches"
    if updated_specs:
        msg += f"\nUpdated specs: {', '.join(updated_specs)}"

    return {
        "status": "synced",
        "inject_content": msg,
        "coverage": coverage_data,
        "updated_specs": updated_specs,
    }


def _parse_coverage_output(output: str) -> dict[str, dict[str, object]]:
    """Parse coverage output to extract line and branch coverage.

    Args:
        output: Raw coverage output string.

    Returns:
        Dict mapping file paths to coverage data with line/branch percentages.
    """
    coverage_data: dict[str, dict[str, object]] = {}

    # Pattern for pytest-cov output like:
    # src/module.py    100   10    90%
    # Or with branch coverage:
    # src/module.py    100   10    90%   50    5   90%
    cov_pattern = re.compile(
        r"^([\w/\-\.]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%(?:\s+(\d+)\s+(\d+)\s+(\d+)%)?",
        re.MULTILINE,
    )

    for match in cov_pattern.finditer(output):
        file_path = match.group(1)
        line_pct = int(match.group(4))

        file_coverage: dict[str, object] = {
            "line": line_pct,
            "statements": int(match.group(2)),
            "missing": int(match.group(3)),
        }

        # Branch coverage if present
        if match.group(7):
            file_coverage["branch"] = int(match.group(7))
            file_coverage["branches"] = int(match.group(5))
            file_coverage["branch_missing"] = int(match.group(6))

        coverage_data[file_path] = file_coverage

    # Look for total line
    total_match = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", output, re.MULTILINE)
    if total_match:
        coverage_data["total"] = {"line": int(total_match.group(1))}

        # Check for branch total
        branch_total = re.search(
            r"^TOTAL\s+\d+\s+\d+\s+\d+%\s+\d+\s+\d+\s+(\d+)%", output, re.MULTILINE
        )
        if branch_total:
            coverage_data["total"]["branch"] = int(branch_total.group(1))

    return coverage_data


def _update_tests_json_with_coverage(
    project_root: Path, coverage_data: dict[str, dict[str, object]]
) -> list[str]:
    """Update tests.json files with coverage data.

    Args:
        project_root: Project root path.
        coverage_data: Parsed coverage data from coverage output.

    Returns:
        List of spec IDs that were updated.
    """
    updated_specs: list[str] = []
    specs_dir = project_root / SPEC_DIR
    timestamp = datetime.now(tz=UTC).isoformat()

    if not specs_dir.exists():
        return updated_specs

    for spec_path in specs_dir.iterdir():
        if not spec_path.is_dir() or spec_path.name == "artifacts":
            continue

        tests_path = spec_path / "tests.json"
        if not tests_path.exists():
            continue

        try:
            with tests_path.open() as f:
                tests_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Get tests array
        if isinstance(tests_data, list):
            tests = tests_data
            wrapper = None
        elif isinstance(tests_data, dict):
            tests_value = tests_data.get("tests")
            tests = tests_value if isinstance(tests_value, list) else []
            wrapper = tests_data
        else:
            continue

        # Update test coverage
        modified = False
        for test in tests:
            if not isinstance(test, dict):
                continue

            impl_path = test.get("implementation")
            if not impl_path or not isinstance(impl_path, str):
                continue

            # Find matching coverage data
            for cov_path, cov_info in coverage_data.items():
                if cov_path == "total":
                    continue
                if impl_path in cov_path or cov_path.endswith(impl_path):
                    test["coverage"] = {
                        "line": cov_info.get("line"),
                        "branch": cov_info.get("branch"),
                        "timestamp": timestamp,
                    }
                    modified = True
                    break

        if modified:
            try:
                output_data = wrapper if wrapper else tests
                with tests_path.open("w") as f:
                    json.dump(output_data, f, indent=2)
                updated_specs.append(spec_path.name[:SPEC_ID_LENGTH])
            except OSError:
                pass

    return updated_specs


# -----------------------------------------------------------------------------
# Notification hooks
# -----------------------------------------------------------------------------


def notify_status_change(context: HookContext) -> dict[str, object]:
    """Notify on spec status changes.

    Reads current file to get old status, compares to new status, and produces
    a notification message showing the transition.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with notification info including old and new status.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str):
        return {"status": "skipped"}

    new_content = tool_input.get("content") or tool_input.get("new_string")
    if not new_content or not isinstance(new_content, str):
        return {"status": "skipped"}

    # Parse new status
    try:
        new_data = json.loads(new_content)
        new_status = new_data.get("status")
        if not new_status or not isinstance(new_status, str):
            return {"status": "skipped", "reason": "No status field"}
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "Invalid JSON"}

    # Read old status from current file
    project_root = _get_project_root(context)
    old_status: str | None = None
    if project_root:
        current_path = project_root / file_path.lstrip("/")
        if current_path.exists():
            try:
                with current_path.open() as f:
                    old_data = json.load(f)
                old_status = (
                    old_data.get("status") if isinstance(old_data, dict) else None
                )
            except (json.JSONDecodeError, OSError):
                pass

    # No change or couldn't determine old status
    if old_status == new_status:
        return {"status": "no_change", "current_status": new_status}

    # Build notification message
    if old_status:
        msg = f"Spec status changed: {old_status} -> {new_status}"
    else:
        msg = f"Spec status set to: {new_status}"

    # Add special messages for significant transitions
    if new_status == "review":
        msg += ". Reviewers may now be notified."
    elif new_status == "approved":
        msg += ". Spec is now approved for implementation."
    elif new_status == "implemented":
        msg += ". Implementation complete, ready for verification."
    elif new_status == "verified":
        msg += ". All requirements verified successfully."
    elif new_status == "deprecated":
        msg += ". This spec is now deprecated."

    return {
        "status": "notified",
        "inject_content": msg,
        "old_status": old_status,
        "new_status": new_status,
    }


def notify_review_ready(context: HookContext) -> dict[str, object]:
    """Notify when spec is ready for review.

    Checks that status is "review", reviewers are populated, and all
    requirements have associated tests.

    Args:
        context: Hook context with tool input.

    Returns:
        Status dict with review readiness check results.
    """
    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"status": "skipped"}

    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str):
        return {"status": "skipped"}

    new_content = tool_input.get("content") or tool_input.get("new_string")
    if not new_content or not isinstance(new_content, str):
        return {"status": "skipped"}

    # Parse new content
    try:
        new_data = json.loads(new_content)
    except json.JSONDecodeError:
        return {"status": "skipped", "reason": "Invalid JSON"}

    # Check if status is "review"
    status = new_data.get("status")
    if status != "review":
        return {"status": "skipped", "reason": "Status is not review"}

    # Check for reviewers
    reviewers = new_data.get("reviewers", [])
    has_reviewers = bool(
        reviewers and isinstance(reviewers, list) and len(reviewers) > 0
    )

    # Check requirements have tests
    project_root = _get_project_root(context)
    req_coverage = _check_requirements_coverage(project_root, file_path)

    issues: list[str] = []
    if not has_reviewers:
        issues.append("No reviewers assigned")
    if req_coverage["uncovered"]:
        issues.append(
            f"Requirements without tests: {', '.join(req_coverage['uncovered'])}"
        )

    if issues:
        msg = "Review readiness issues:\n- " + "\n- ".join(issues)
        return {
            "status": "not_ready",
            "warn_message": msg,
            "issues": issues,
            "has_reviewers": has_reviewers,
            "req_coverage": req_coverage,
        }

    msg = "Spec is ready for review."
    if reviewers:
        reviewer_names = ", ".join(str(r) for r in reviewers[:3])
        if len(reviewers) > 3:
            reviewer_names += f" +{len(reviewers) - 3} more"
        msg += f" Reviewers: {reviewer_names}"

    return {
        "status": "ready",
        "inject_content": msg,
        "has_reviewers": has_reviewers,
        "req_coverage": req_coverage,
    }


def _check_requirements_coverage(
    project_root: Path | None, index_path: str
) -> dict[str, list[str]]:
    """Check that all requirements have tests.

    All requirements in OAPS specs are mandatory, so this checks coverage
    for every requirement, not just specific priority levels.

    Args:
        project_root: Project root path.
        index_path: Path to the index.json being modified.

    Returns:
        Dict with 'covered' and 'uncovered' lists of requirement IDs.
    """
    result: dict[str, list[str]] = {"covered": [], "uncovered": []}

    if not project_root:
        return result

    # Extract spec directory from index path
    match = re.search(r"(\.oaps/docs/specs/\d{4}-[a-z0-9-]+)/", index_path)
    if not match:
        return result

    spec_dir = project_root / match.group(1)
    req_path = spec_dir / "requirements.json"
    test_path = spec_dir / "tests.json"

    if not req_path.exists():
        return result

    # Load requirements
    try:
        with req_path.open() as f:
            req_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return result

    # Get requirements array
    if isinstance(req_data, list):
        requirements = req_data
    elif isinstance(req_data, dict):
        req_value = req_data.get("requirements")
        requirements = req_value if isinstance(req_value, list) else []
    else:
        return result

    # Collect all requirement IDs
    all_req_ids: set[str] = set()
    for req in requirements:
        if not isinstance(req, dict):
            continue
        req_id = req.get("id")
        if isinstance(req_id, str):
            all_req_ids.add(req_id)

    if not all_req_ids:
        return result

    # Load tests and find which requirements are covered
    covered_reqs: set[str] = set()
    if test_path.exists():
        try:
            with test_path.open() as f:
                test_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            test_data = None

        if test_data:
            if isinstance(test_data, list):
                tests = test_data
            elif isinstance(test_data, dict):
                test_value = test_data.get("tests")
                tests = test_value if isinstance(test_value, list) else []
            else:
                tests = []

            for test in tests:
                if not isinstance(test, dict):
                    continue
                test_reqs = test.get("requirements", [])
                if isinstance(test_reqs, list):
                    for req_id in test_reqs:
                        if isinstance(req_id, str):
                            covered_reqs.add(req_id)

    # Determine coverage
    result["covered"] = sorted(all_req_ids & covered_reqs)
    result["uncovered"] = sorted(all_req_ids - covered_reqs)

    return result


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_project_root(context: HookContext) -> Path | None:
    """Get project root from context.

    The project root is the parent of the .oaps directory.
    """
    # oaps_dir points to .oaps/, so parent is project root
    if hasattr(context, "oaps_dir") and context.oaps_dir:
        return context.oaps_dir.parent
    return None


def _get_tool_input(context: HookContext) -> dict[str, object] | None:
    """Extract tool input from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "tool_input"):
        tool_input = getattr(hook_input, "tool_input", None)
        if isinstance(tool_input, dict):
            return dict(tool_input)
    return None


def _get_tool_response(context: HookContext) -> dict[str, object] | None:
    """Extract tool response from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "tool_response"):
        response = getattr(hook_input, "tool_response", None)
        if isinstance(response, dict):
            return dict(response)
    return None


def _detect_actor() -> str:
    """Detect actor from environment.

    Checks for agent context, CI environment, and other indicators to
    determine who is making the change.

    Returns:
        Actor identifier string: 'agent:<name>', 'ci', or 'user'.
    """
    # Check for Claude agent environment variables
    agent_name = os.environ.get("CLAUDE_AGENT_NAME")
    if agent_name:
        return f"agent:{agent_name}"

    # Check for generic agent indicators
    if os.environ.get("CLAUDE_CODE"):
        return "agent:claude-code"

    # Check for subagent context
    if os.environ.get("CLAUDE_SUBAGENT"):
        subagent_name = os.environ.get("CLAUDE_SUBAGENT_NAME", "subagent")
        return f"agent:{subagent_name}"

    # Check for CI environment
    if os.environ.get("CI"):
        ci_name = os.environ.get("CI_NAME") or os.environ.get("GITHUB_ACTIONS")
        if ci_name:
            return f"ci:{ci_name}"
        return "ci"

    # Check for automation indicators
    if os.environ.get("OAPS_AUTOMATION"):
        return "automation"

    return "user"


def _check_bidirectional_links(req_path: Path, test_path: Path) -> list[str]:
    """Check bidirectional links between requirements and tests."""
    errors: list[str] = []

    try:
        with req_path.open() as f:
            req_data = json.load(f)
        with test_path.open() as f:
            test_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    requirements = (
        req_data if isinstance(req_data, list) else req_data.get("requirements", [])
    )
    tests = test_data if isinstance(test_data, list) else test_data.get("tests", [])

    # Build maps
    req_tests: dict[str, set[str]] = {}
    for req in requirements:
        if isinstance(req, dict):
            req_id = req.get("id", "")
            req_tests[req_id] = set(req.get("tests", []))

    test_reqs: dict[str, set[str]] = {}
    for test in tests:
        if isinstance(test, dict):
            test_id = test.get("id", "")
            test_reqs[test_id] = set(test.get("requirements", []))

    # Check requirement -> test links
    for req_id, test_ids in req_tests.items():
        for test_id in test_ids:
            if test_id not in test_reqs:
                errors.append(
                    f"Requirement {req_id} references non-existent test {test_id}"
                )
            elif req_id not in test_reqs.get(test_id, set()):
                errors.append(f"Bidirectional link missing: {req_id} -> {test_id}")

    # Check test -> requirement links
    for test_id, req_ids in test_reqs.items():
        orphan_reqs = [r for r in req_ids if r not in req_tests]
        errors.extend(
            f"Test {test_id} references non-existent requirement {req_id}"
            for req_id in orphan_reqs
        )

    return errors


def _parse_artifact_metadata(artifact_path: Path) -> dict[str, str] | None:
    """Parse metadata from artifact file."""
    if artifact_path.suffix == ".md":
        return _parse_markdown_frontmatter(artifact_path)

    # Check for sidecar metadata
    sidecar_path = artifact_path.with_suffix(artifact_path.suffix + ".metadata.yaml")
    if sidecar_path.exists():
        return _parse_sidecar_metadata(artifact_path, sidecar_path)

    # Return basic info
    return {
        "filename": artifact_path.name,
        "type": "file",
    }


def _parse_markdown_frontmatter(artifact_path: Path) -> dict[str, str] | None:
    """Parse YAML frontmatter from markdown file."""
    try:
        content = artifact_path.read_text()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                frontmatter = yaml.safe_load(content[3:end])
                if isinstance(frontmatter, dict):
                    return {
                        "filename": artifact_path.name,
                        "type": frontmatter.get("type", "document"),
                        "title": frontmatter.get("title", artifact_path.stem),
                        "created": frontmatter.get("created", ""),
                    }
    except (OSError, yaml.YAMLError):
        pass
    return None


def _parse_sidecar_metadata(
    artifact_path: Path, sidecar_path: Path
) -> dict[str, str] | None:
    """Parse metadata from sidecar YAML file."""
    try:
        metadata = yaml.safe_load(sidecar_path.read_text())
        if isinstance(metadata, dict):
            return {
                "filename": artifact_path.name,
                **{k: str(v) for k, v in metadata.items()},
            }
    except (OSError, yaml.YAMLError):
        pass
    return None
