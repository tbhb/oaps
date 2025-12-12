"""Reference artifact discovery, loading, merging, and formatting for skills."""

from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from pytablewriter import MarkdownTableWriter

from oaps.context import extract_string_dict, extract_string_list
from oaps.templating import load_frontmatter_file, render_template_string

if TYPE_CHECKING:
    from pathlib import Path

    from oaps.context import SkillContext


class ReferenceFrontmatter(TypedDict):
    """Frontmatter for a skill reference file.

    Each reference file must have 'name' and 'description' in its frontmatter.
    The optional 'required' field marks references that are always included.
    The optional 'references' field lists dependencies on other references.
    """

    name: str
    description: str
    required: NotRequired[bool]
    references: NotRequired[list[str]]


@dataclass(slots=True)
class ReferenceContent:
    """Content loaded from a reference file."""

    title: str = ""
    body: str = ""
    commands: dict[str, str] = field(default_factory=dict)
    principles: list[str] = field(default_factory=list)
    best_practices: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    references: dict[str, str] = field(default_factory=dict)


def discover_references(references_dir: Path) -> dict[str, ReferenceFrontmatter]:
    """Discover all references in a directory.

    Args:
        references_dir: Path to the references directory.

    Returns:
        A dict mapping reference name to its frontmatter.
    """
    references: dict[str, ReferenceFrontmatter] = {}

    if not references_dir.is_dir():
        return references

    for path in chain(references_dir.glob("*.md"), references_dir.glob("*.j2")):
        frontmatter, _ = load_frontmatter_file(path)
        # Validate required fields for references
        if (
            frontmatter is not None
            and "name" in frontmatter
            and "description" in frontmatter
            and isinstance(frontmatter["name"], str)
            and isinstance(frontmatter["description"], str)
        ):
            reference: ReferenceFrontmatter = {
                "name": frontmatter["name"],
                "description": frontmatter["description"],
            }
            # Extract optional required field
            if "required" in frontmatter and isinstance(frontmatter["required"], bool):
                reference["required"] = frontmatter["required"]
            # Extract optional references field
            raw_refs = frontmatter.get("references")
            if isinstance(raw_refs, list) and all(isinstance(r, str) for r in raw_refs):
                reference["references"] = cast("list[str]", raw_refs)
            references[reference["name"]] = reference

    return references


def resolve_reference_dependencies(
    requested: list[str],
    all_references: dict[str, ReferenceFrontmatter],
) -> tuple[list[str], list[str]]:
    """Resolve reference dependencies recursively.

    Performs depth-first traversal to collect all transitive dependencies.
    Dependencies are placed before their dependents in the output.
    Cycles are detected and broken gracefully.

    Args:
        requested: Initial list of reference names to load.
        all_references: All discovered references (name -> frontmatter).

    Returns:
        Tuple of (resolved_order, missing_deps) where:
        - resolved_order: References in dependency order (dependencies first)
        - missing_deps: Names of dependencies that weren't found
    """
    resolved: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()
    missing: list[str] = []

    def visit(name: str) -> None:
        """Visit a reference and its dependencies using DFS."""
        if name in visited:
            return
        if name in visiting:
            # Cycle detected, skip to break the cycle
            return
        if name not in all_references:
            if name not in missing:
                missing.append(name)
            return

        visiting.add(name)

        # Visit dependencies first
        fm = all_references[name]
        for dep in fm.get("references", []):
            visit(dep)

        visiting.remove(name)
        visited.add(name)
        resolved.append(name)

    # Visit all requested references
    for name in requested:
        visit(name)

    return resolved, missing


def merge_references(
    builtin: dict[str, ReferenceFrontmatter],
    overrides: dict[str, ReferenceFrontmatter],
) -> dict[str, ReferenceFrontmatter]:
    """Merge override references with builtin references.

    Override references take precedence. New references from overrides are added.

    Args:
        builtin: The builtin references dict.
        overrides: The override references dict.

    Returns:
        A merged dict with overrides taking precedence.
    """
    merged = dict(builtin)
    merged.update(overrides)
    return merged


def find_reference_file(
    name: str,
    builtin_dir: Path,
    override_dir: Path | None,
) -> Path | None:
    """Find the file for a reference, preferring overrides.

    Args:
        name: The reference name to find.
        builtin_dir: Path to the builtin references directory.
        override_dir: Path to the override references directory, or None.

    Returns:
        Path to the reference file, or None if not found.
    """
    # Check override first
    if override_dir is not None and override_dir.is_dir():
        for path in chain(override_dir.glob("*.md"), override_dir.glob("*.j2")):
            frontmatter, _ = load_frontmatter_file(path)
            if (
                frontmatter is not None
                and "name" in frontmatter
                and frontmatter["name"] == name
            ):
                return path

    # Fall back to builtin
    if builtin_dir.is_dir():
        for path in chain(builtin_dir.glob("*.md"), builtin_dir.glob("*.j2")):
            frontmatter, _ = load_frontmatter_file(path)
            if (
                frontmatter is not None
                and "name" in frontmatter
                and frontmatter["name"] == name
            ):
                return path

    return None


def load_reference_content(
    path: Path, template_context: SkillContext
) -> ReferenceContent:
    """Load reference file content, stripping frontmatter.

    Args:
        path: Path to the reference file.
        template_context: Context for rendering the body template.

    Returns:
        ReferenceContent with all extracted fields.
    """
    frontmatter, body = load_frontmatter_file(path, template_context)
    content = ReferenceContent(body=render_template_string(body, template_context))

    if frontmatter is not None:
        # Prefer title, fall back to name, then empty string
        raw_title = frontmatter.get("title") or frontmatter.get("name") or ""
        content.title = str(raw_title)

        # Extract commands dict
        raw_commands = frontmatter.get("commands")
        if isinstance(raw_commands, dict):
            typed_commands = cast("dict[str, object]", raw_commands)
            for key, value in typed_commands.items():
                content.commands[key] = str(value)

        # Extract list fields
        content.principles = extract_string_list(frontmatter, "principles")
        content.best_practices = extract_string_list(frontmatter, "best_practices")
        content.checklist = extract_string_list(frontmatter, "checklist")

        # Extract references as dict (URL -> description)
        content.references = extract_string_dict(frontmatter, "references")

    return content


def merge_commands(all_commands: list[dict[str, str]]) -> dict[str, str]:
    """Merge commands from multiple references.

    When the same command appears in multiple references, descriptions are
    merged with semicolons (stripping trailing periods before merging).

    Args:
        all_commands: List of command dicts from each reference.

    Returns:
        Merged dict mapping command to combined description.
    """
    merged: dict[str, list[str]] = {}

    for commands in all_commands:
        for cmd, desc in commands.items():
            if cmd not in merged:
                merged[cmd] = []
            # Strip trailing period for merging
            desc_clean = desc.rstrip(".")
            if desc_clean not in merged[cmd]:
                merged[cmd].append(desc_clean)

    # Join descriptions with semicolons
    return {cmd: "; ".join(descs) for cmd, descs in merged.items()}


def format_commands_table(commands: dict[str, str]) -> str:
    """Format commands as a markdown table.

    Args:
        commands: Dict mapping command to description.

    Returns:
        Markdown table string.
    """
    if not commands:
        return ""

    writer = MarkdownTableWriter(
        headers=["Command", "Description"],
        value_matrix=[[f"`{cmd}`", desc] for cmd, desc in sorted(commands.items())],
        margin=1,
    )
    return f"## Allowed commands\n\n{writer.dumps()}"


def format_consolidated_section(
    section_name: str,
    items_by_reference: dict[str, list[str]],
) -> str:
    """Format a consolidated section with items from multiple references.

    Args:
        section_name: The name of the section (e.g., "Principles").
        items_by_reference: Dict mapping reference title to list of items.

    Returns:
        Markdown string with H2 header and H3 subsections for each reference.
        Returns empty string if no references have items.
    """
    non_empty = {title: items for title, items in items_by_reference.items() if items}

    if not non_empty:
        return ""

    lines = [f"## {section_name}\n"]

    for title, items in non_empty.items():
        lines.append(f"### {title} {section_name.lower()}\n")
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    return "\n".join(lines)


def format_references_section(
    refs_by_reference: dict[str, dict[str, str]],
) -> str:
    """Format a consolidated references section.

    Args:
        refs_by_reference: Dict mapping reference title to references dict
            (URL -> description).

    Returns:
        Markdown string with H2 header and H3 subsections for each reference.
        References formatted as `<URL>: description`.
        Returns empty string if no references have references.
    """
    non_empty = {title: refs for title, refs in refs_by_reference.items() if refs}

    if not non_empty:
        return ""

    lines = ["## References\n"]

    for title, refs in non_empty.items():
        lines.append(f"### {title} references\n")
        lines.extend(f"- <{url}>: {desc}" for url, desc in refs.items())
        lines.append("")

    return "\n".join(lines)
