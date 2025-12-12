# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false
# ruff: noqa: D415, FBT002, PLR0912, PLR0915
"""Generic skill commands for orientation and contextualization."""

import sys
from typing import Annotated

from cyclopts import Parameter
from pytablewriter import MarkdownTableWriter

from oaps.skill import is_project_skill

# Import command modules to register decorators
from . import _stats as _stats

# Re-export app
from ._app import app

__all__ = ["app"]


@app.command(name="create")
def _create(
    skill_name: str,
    /,
    plugin: Annotated[
        bool, Parameter(help="Create a plugin skill (in skills/)")
    ] = False,
    project: Annotated[
        bool, Parameter(help="Create a project skill (in .oaps/claude/skills/)")
    ] = False,
) -> None:
    """Create a new skill with template files

    Creates a skill directory with SKILL.md and example resources.

    Args:
        skill_name: Name of the skill to create
        plugin: Whether to create a plugin skill
        project: Whether to create a project skill
    """
    from ._create import create_skill

    try:
        skill_dir = create_skill(skill_name, plugin=plugin, project=project)
        print(f"Created skill: {skill_dir}")
        print()
        print("Next steps:")
        print(f"1. Edit {skill_dir}/SKILL.md to customize the skill")
        print("2. Update or remove example files in references/")
        print(f"3. Run `oaps skill validate {skill_name}` to validate the skill")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@app.command(name="save")
def _save(
    skill_name: str,
    /,
    message: Annotated[str, Parameter(help="Commit message for saving the skill")],
    validate: Annotated[
        bool, Parameter(help="Whether to validate before saving")
    ] = True,
) -> None:
    """Save a project skill

    Args:
        skill_name: Name of the skill to save
        message: Commit message for saving the skill
        validate: Whether to validate before saving
    """
    print(f"Saving project skill: {skill_name}")
    print(f"Message: {message}")
    print(f"Validate: {validate}")
    print("(Not yet implemented)")


@app.command(name="validate")
def _validate(
    skill_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Validate a plugin skill")] = False,
    project: Annotated[bool, Parameter(help="Validate a project skill")] = False,
) -> None:
    """Validate a skill's structure and content

    Checks naming conventions, frontmatter, description quality,
    body length, writing style, and resource file validity.

    Args:
        skill_name: Name of the skill to validate
        plugin: Whether to validate a plugin skill
        project: Whether to validate a project skill
    """
    from oaps.context import get_skill_dir

    from ._validate import format_validation_result, validate_skill

    # Resolve skill directory
    skill_dir = get_skill_dir(skill_name, plugin=plugin, project=project)
    if skill_dir is None:
        print(f"Could not find skill: {skill_name}", file=sys.stderr)
        sys.exit(1)

    # Validate the skill
    result = validate_skill(skill_dir)

    # Print formatted result
    print(format_validation_result(result))

    # Exit with error code if validation failed
    if not result.is_valid:
        sys.exit(1)


@app.command(name="orient")
def _orient(
    skill_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Orient for a plugin skill")] = False,
    project: Annotated[bool, Parameter(help="Orient for a project skill")] = False,
) -> None:
    """Provide static context for a skill

    Outputs:
    - Environment summary (tool versions)
    - Available references with descriptions
    - Instructions to load specific context

    Args:
        skill_name: Name of the skill to provide context for
        plugin: Whether to provide context for a plugin skill
        project: Whether to provide context for a project skill
    """
    from oaps.context import SkillContext, get_skill_dir, get_skill_override_dir
    from oaps.reference import discover_references, merge_references
    from oaps.utils import detect_tooling

    # Resolve skill directory
    skill_dir = get_skill_dir(skill_name, plugin=plugin, project=project)
    if skill_dir is None:
        print(f"Could not find skill: {skill_name}")
        return

    # Detect actual source from resolved path
    is_project = is_project_skill(skill_dir)

    # Discover references
    references_dir = skill_dir / "references"
    references = discover_references(references_dir)

    # Merge overrides (plugin skills only)
    if not is_project:
        override_dir = get_skill_override_dir(skill_name)
        if override_dir:
            # Merge reference overrides
            override_refs = discover_references(override_dir / "references")
            references = merge_references(references, override_refs)

    # Detect environment
    tools = detect_tooling()

    # Build template context
    _template_context = SkillContext(tool_versions=tools)

    # Build output
    output_parts: list[str] = []

    # Header section
    output_parts.append(f"## {skill_name} Skill context\n")

    # Environment section
    output_parts.append("### Environment\n")
    for tool_name, version in tools.items():
        if version:
            output_parts.append(f"- {tool_name}: {version}")
    output_parts.append("")

    # References section
    if references:
        output_parts.append("### Available references\n")
        writer = MarkdownTableWriter(
            headers=["Name", "Description"],
            value_matrix=[
                [
                    f"{name}{' (required)' if fm.get('required') else ''}",
                    fm["description"],
                ]
                for name, fm in sorted(references.items())
            ],
            margin=1,
        )
        output_parts.append(writer.dumps())
        output_parts.append("")
    else:
        output_parts.append("### Available references\n")
        output_parts.append("*No references found.*\n")

    # Usage hints
    output_parts.append("---\n")
    flag = "--project" if is_project else "--plugin"
    output_parts.append("To load specific references, run:")
    output_parts.append("```bash")
    output_parts.append(
        f"oaps skill context {flag} {skill_name} --references <names...>"
    )
    output_parts.append("```")

    print("\n".join(output_parts))


@app.command(name="context")
def _context(
    skill_name: str,
    /,
    plugin: Annotated[bool, Parameter(help="Load context for a plugin skill")] = False,
    project: Annotated[
        bool, Parameter(help="Load context for a project skill")
    ] = False,
    references: Annotated[
        list[str] | None, Parameter(help="Names of references to load")
    ] = None,
) -> None:
    """Provide dynamic context for a skill

    Loads and outputs the full content of requested references.

    Output order:
    1. Principles (consolidated from all references)
    2. Free text bodies from each reference
    3. Best practices (consolidated)
    4. Checklist (consolidated)
    5. References (consolidated)
    6. Allowed commands (merged table)

    Args:
        skill_name: Name of the skill to provide context for
        plugin: Whether to provide context for a plugin skill
        project: Whether to provide context for a project skill
        references: List of reference names to load
    """
    from oaps.context import SkillContext, get_skill_dir, get_skill_override_dir
    from oaps.reference import (
        ReferenceContent,
        discover_references,
        find_reference_file,
        format_commands_table,
        format_consolidated_section,
        format_references_section,
        load_reference_content,
        merge_commands,
        merge_references,
    )
    from oaps.utils import detect_tooling

    # Resolve skill directory
    skill_dir = get_skill_dir(skill_name, plugin=plugin, project=project)
    if skill_dir is None:
        print(f"Could not find skill: {skill_name}")
        return

    # Detect actual source from resolved path
    is_project = is_project_skill(skill_dir)

    # Set up directories
    builtin_refs_dir = skill_dir / "references"
    override_refs_dir = None

    if not is_project:
        override_dir = get_skill_override_dir(skill_name)
        if override_dir:
            override_refs_dir = override_dir / "references"

    # Discover all references to find required ones
    all_references = discover_references(builtin_refs_dir)
    if override_refs_dir and override_refs_dir.is_dir():
        override_refs = discover_references(override_refs_dir)
        all_references = merge_references(all_references, override_refs)

    # Find required references not already in requested list
    requested = list(references) if references else []
    required = [
        name
        for name, fm in all_references.items()
        if fm.get("required", False) and name not in requested
    ]

    # Combine required + requested references
    all_requested = required + requested

    # Resolve transitive dependencies
    from oaps.reference import resolve_reference_dependencies

    all_requested, missing_deps = resolve_reference_dependencies(
        all_requested, all_references
    )

    # Warn about missing dependencies
    if missing_deps:
        print(f"**Missing dependencies:** {', '.join(missing_deps)}", file=sys.stderr)

    # Validate: if no required references, --references is required
    if not required and not references:
        flag = "--project" if is_project else "--plugin"
        msg = (
            "Error: --references is required for domain-only skills "
            "(skills without required references)."
        )
        print(msg, file=sys.stderr)
        print(
            f"\nRun `oaps skill orient {flag} {skill_name}` for available refs.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Exit early if no references to load
    if not all_requested and not references:
        print("No references specified.")
        flag = "--project" if is_project else "--plugin"
        print(f"\nRun `oaps skill orient {flag} {skill_name}` for available refs.")
        return

    # Build template context
    tools = detect_tooling()
    template_context = SkillContext(tool_versions=tools)

    # Load reference content
    loaded: list[tuple[str, ReferenceContent]] = []
    not_found: list[str] = []

    for name in all_requested:
        path = find_reference_file(name, builtin_refs_dir, override_refs_dir)
        if path is None:
            not_found.append(name)
            continue
        content = load_reference_content(path, template_context)
        header = content.title if content.title else name
        loaded.append((header, content))

    # Build output in specified order
    output_parts: list[str] = []

    # 1. Principles (consolidated)
    principles_by_ref = {title: content.principles for title, content in loaded}
    principles_section = format_consolidated_section("Principles", principles_by_ref)
    if principles_section:
        output_parts.append(principles_section)
        output_parts.append("---\n")

    # 2. Free text bodies from each reference
    for title, content in loaded:
        output_parts.append(f"# {title}\n")
        output_parts.append(content.body)
        output_parts.append("\n---\n")

    # 3. Best practices (consolidated)
    best_practices_by_reference = {
        title: content.best_practices for title, content in loaded
    }
    best_practices_section = format_consolidated_section(
        "Best practices", best_practices_by_reference
    )
    if best_practices_section:
        output_parts.append(best_practices_section)

    # 4. Checklist (consolidated)
    checklist_by_reference = {title: content.checklist for title, content in loaded}
    checklist_section = format_consolidated_section("Checklist", checklist_by_reference)
    if checklist_section:
        output_parts.append(checklist_section)

    # 5. References (consolidated)
    references_by_reference = {title: content.references for title, content in loaded}
    references_section = format_references_section(references_by_reference)
    if references_section:
        output_parts.append(references_section)

    # 6. Allowed commands (merged table)
    all_commands = [content.commands for _, content in loaded if content.commands]
    if all_commands:
        merged_commands = merge_commands(all_commands)
        commands_table = format_commands_table(merged_commands)
        output_parts.append(commands_table)

    # Report not found references
    if not_found:
        output_parts.append(f"\n**References not found:** {', '.join(not_found)}")
        flag_name = "--project" if is_project else "--plugin"
        cmd = f"oaps skill orient {flag_name} {skill_name}"
        output_parts.append(f"\nRun `{cmd}` to see available references.")

    print("\n".join(output_parts))
