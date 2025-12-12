"""Template discovery and resolution."""

# ruff: noqa: PLC0415

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class TemplateInfo:
    """Metadata about a discovered template.

    Attributes:
        name: Template name from frontmatter.
        description: Template description from frontmatter.
        path: Absolute path to the template file.
        source: Where the template was found.
    """

    name: str
    description: str
    path: Path
    source: Literal["override", "skill", "builtin"]


def _discover_templates_in_dir(
    templates_dir: Path,
    source: Literal["override", "skill", "builtin"],
) -> dict[str, TemplateInfo]:
    """Discover all templates in a directory.

    Args:
        templates_dir: Path to templates directory.
        source: Source label for discovered templates.

    Returns:
        Dict mapping template name to TemplateInfo.
    """
    from ._frontmatter import load_frontmatter_file

    templates: dict[str, TemplateInfo] = {}

    if not templates_dir.is_dir():
        return templates

    for path in templates_dir.glob("*.md.j2"):
        frontmatter, _ = load_frontmatter_file(path)
        if (
            frontmatter is not None
            and "name" in frontmatter
            and "description" in frontmatter
            and isinstance(frontmatter["name"], str)
            and isinstance(frontmatter["description"], str)
        ):
            info = TemplateInfo(
                name=frontmatter["name"],
                description=frontmatter["description"],
                path=path,
                source=source,
            )
            templates[info.name] = info

    return templates


def _get_skill_templates_dir(skill_name: str) -> Path | None:
    """Get the templates directory for a plugin skill.

    Looks for the skill in:
    1. Claude plugin's installed skills directory (production)
    2. Current Git worktree's skills directory (development)

    Args:
        skill_name: Name of the skill.

    Returns:
        Path to the skill's templates directory, or None if not found.
    """
    from oaps.utils._claude_plugin import get_claude_plugin_skill_dir

    skill_dir = get_claude_plugin_skill_dir(skill_name)
    if skill_dir is not None:
        templates_dir = skill_dir / "templates"
        if templates_dir.is_dir():
            return templates_dir

    return None


def _get_skill_override_templates_dir(skill_name: str) -> Path | None:
    """Get the override templates directory for a skill.

    Args:
        skill_name: Name of the skill.

    Returns:
        Path to .oaps/overrides/skills/<skill>/templates/, or None if not found.
    """
    from oaps.utils._paths import get_oaps_skill_overrides_dir

    override_dir = get_oaps_skill_overrides_dir(skill_name)
    if override_dir is not None:
        templates_dir = override_dir / "templates"
        if templates_dir.is_dir():
            return templates_dir

    return None


def discover_skill_templates(skill_name: str) -> dict[str, TemplateInfo]:
    """Discover all templates for a skill, with overrides merged.

    Search order (first found wins):
    1. Override: .oaps/overrides/skills/<skill>/templates/
    2. Skill: skills/<skill>/templates/

    Args:
        skill_name: Name of the skill.

    Returns:
        Dict mapping template name to TemplateInfo.
    """
    templates: dict[str, TemplateInfo] = {}

    # First discover skill templates (lower precedence)
    skill_templates_dir = _get_skill_templates_dir(skill_name)
    if skill_templates_dir is not None:
        templates.update(_discover_templates_in_dir(skill_templates_dir, "skill"))

    # Then override templates (higher precedence, overwrites skill templates)
    override_templates_dir = _get_skill_override_templates_dir(skill_name)
    if override_templates_dir is not None:
        templates.update(_discover_templates_in_dir(override_templates_dir, "override"))

    return templates


def find_skill_template(
    skill_name: str,
    template_name: str,
) -> TemplateInfo | None:
    """Find a specific template within a skill's templates.

    Search order (first found wins):
    1. Override: .oaps/overrides/skills/<skill>/templates/
    2. Skill: skills/<skill>/templates/

    Args:
        skill_name: Name of the skill.
        template_name: Name of the template to find.

    Returns:
        TemplateInfo if found, None otherwise.
    """
    from ._frontmatter import load_frontmatter_file

    # Search override first (higher precedence)
    override_templates_dir = _get_skill_override_templates_dir(skill_name)
    if override_templates_dir is not None:
        for path in override_templates_dir.glob("*.md.j2"):
            frontmatter, _ = load_frontmatter_file(path)
            if (
                frontmatter is not None
                and frontmatter.get("name") == template_name
                and isinstance(frontmatter.get("description"), str)
            ):
                return TemplateInfo(
                    name=template_name,
                    description=str(frontmatter["description"]),
                    path=path,
                    source="override",
                )

    # Then skill templates (lower precedence)
    skill_templates_dir = _get_skill_templates_dir(skill_name)
    if skill_templates_dir is not None:
        for path in skill_templates_dir.glob("*.md.j2"):
            frontmatter, _ = load_frontmatter_file(path)
            if (
                frontmatter is not None
                and frontmatter.get("name") == template_name
                and isinstance(frontmatter.get("description"), str)
            ):
                return TemplateInfo(
                    name=template_name,
                    description=str(frontmatter["description"]),
                    path=path,
                    source="skill",
                )

    return None
