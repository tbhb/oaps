# ruff: noqa: PLR0913
# pyright: reportUnusedCallResult=false
"""Skill creation functionality."""

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class SkillTemplate:
    """Template content for creating a new skill.

    Attributes:
        skill_md: Content for SKILL.md.
        example_reference: Content for example reference file.
    """

    skill_md: str
    example_reference: str


def _generate_skill_md(skill_name: str, today: datetime.date) -> str:
    """Generate SKILL.md content.

    Args:
        skill_name: Name of the skill.
        today: Current date for version info.

    Returns:
        SKILL.md content as a string.
    """
    # Convert kebab-case to title case for display
    title = skill_name.replace("-", " ").title()

    # Build multi-line TODO comments to avoid line length issues
    intro_todo = (
        "TODO: Write a brief introduction (2-3 sentences) "
        "explaining what this skill does."
    )
    concepts_todo = (
        "TODO: Describe the key concepts a user needs to understand "
        "to work with this skill."
    )
    structure_todo = (
        "TODO: If this skill works with specific file types or "
        "project structures, document them."
    )

    return f"""---
name: {skill_name}
description: >-
  This skill should be used when the user asks to "TODO: add trigger phrase 1",
  "TODO: add trigger phrase 2", or needs guidance on TODO: describe domain.
version: 0.1.0
---

# {title}

{intro_todo}

## Core concepts

{concepts_todo}

## Quick start

TODO: Provide a minimal example or quick workflow to get started.

## Directory structure

{structure_todo}

```text
project/
├── TODO: document expected structure
└── ...
```

## Common tasks

TODO: List common tasks and how to accomplish them using this skill.

### Task 1

TODO: Describe how to accomplish a common task.

### Task 2

TODO: Describe another common task.

## Best practices

TODO: List best practices for working with this skill's domain.

- Practice 1
- Practice 2
- Practice 3

## See also

For detailed information, load specific references:

```bash
oaps skill context {skill_name} --references <reference-name>
```

Available references:

- `example`: Example reference (TODO: update or delete)

---

*Skill created: {today.isoformat()}*
"""


def _generate_example_reference() -> str:
    """Generate example reference content.

    Returns:
        Example reference content as a string.
    """
    return """---
name: example
title: Example Reference
description: An example reference demonstrating the reference structure
required: false
principles:
  - TODO Add principles that guide this domain
  - Each principle should be actionable and specific
best_practices:
  - TODO Add best practices for this domain
  - Focus on common mistakes to avoid
checklist:
  - TODO Add checklist items for validation
  - Each item should be verifiable
commands:
  oaps skill validate <name>: Validate skill structure and content
references:
  https://docs.anthropic.com/en/docs/claude-code: Claude Code documentation
---

# Example Reference

TODO: Replace this with actual reference content.

This reference file demonstrates the structure of a skill reference:

1. **YAML Frontmatter** - Contains metadata for discovery and organization
2. **Principles** - High-level guidance that shapes decisions
3. **Best Practices** - Concrete recommendations based on experience
4. **Checklist** - Verifiable items for quality assurance
5. **Commands** - CLI commands relevant to this reference
6. **References** - External links for further reading

## Using References

References are loaded on-demand to keep context lean. To load this reference:

```bash
oaps skill context <skill-name> --references example
```

## Next Steps

1. Rename this file to match your reference topic (e.g., `api.md`, `patterns.md`)
2. Update the frontmatter metadata
3. Replace the body content with your actual documentation
4. Delete this file if no references are needed
"""


def generate_skill_template(skill_name: str) -> SkillTemplate:
    """Generate all template content for a new skill.

    Args:
        skill_name: Name of the skill.

    Returns:
        SkillTemplate with all content.
    """
    today = datetime.datetime.now(tz=datetime.UTC).date()

    return SkillTemplate(
        skill_md=_generate_skill_md(skill_name, today),
        example_reference=_generate_example_reference(),
    )


def create_skill(
    skill_name: str,
    *,
    plugin: bool = False,
    project: bool = False,
    with_references: bool = True,
    with_scripts: bool = False,
    with_assets: bool = False,
) -> Path:
    """Create a new skill directory with template files.

    Args:
        skill_name: Name of the skill to create.
        plugin: If True, create in plugin location (skills/).
        project: If True, create in project location (.oaps/claude/skills/).
        with_references: Create example reference file.
        with_scripts: Create empty scripts directory.
        with_assets: Create empty assets directory.

    Returns:
        Path to the created skill directory.

    Raises:
        ValueError: If both plugin and project are True, or skill already exists.
        FileExistsError: If the skill directory already exists.
    """
    from oaps.utils._paths import get_project_skills_dir, get_worktree_root

    if plugin and project:
        msg = "Cannot specify both plugin and project"
        raise ValueError(msg)

    # Default to project if neither specified
    if not plugin and not project:
        project = True

    # Determine target directory
    skills_dir = get_project_skills_dir() if project else get_worktree_root() / "skills"
    skill_dir = skills_dir / skill_name

    # Check if skill already exists
    if skill_dir.exists():
        msg = f"Skill already exists: {skill_dir}"
        raise FileExistsError(msg)

    # Generate template content
    template = generate_skill_template(skill_name)

    # Create directories
    skill_dir.mkdir(parents=True)

    # Write SKILL.md
    (skill_dir / "SKILL.md").write_text(template.skill_md, encoding="utf-8")

    # Create references directory and example
    if with_references:
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "example.md").write_text(
            template.example_reference, encoding="utf-8"
        )

    # Create scripts directory (empty)
    if with_scripts:
        (skill_dir / "scripts").mkdir()

    # Create assets directory (empty)
    if with_assets:
        (skill_dir / "assets").mkdir()

    return skill_dir
