"""Shared test fixtures for OAPS tests."""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from dulwich.repo import Repo
from rich.console import Console


@dataclass(frozen=True, slots=True)
class OapsProject:
    """Paths for an OAPS-enabled test project."""

    root: Path
    oaps_dir: Path
    claude_dir: Path
    skills_dir: Path
    commands_dir: Path
    agents_dir: Path
    overrides_dir: Path


@dataclass(frozen=True, slots=True)
class OapsPlugin:
    """Paths for OAPS plugin installation."""

    install_dir: Path
    skills_dir: Path
    commands_dir: Path
    agents_dir: Path


@pytest.fixture
def oaps_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OapsProject:
    """Create OAPS-enabled project with real git repos.

    Structure:
        tmp_path/
            project/
                .git/                    # real git repo
                .oaps/
                    .git/                # separate git repo for .oaps
                    claude/
                        skills/
                        commands/
                        agents/
                    overrides/
                        skills/
                .claude -> .oaps/claude  # symlink
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    Repo.init(str(project_root))

    oaps_dir = project_root / ".oaps"
    oaps_dir.mkdir()
    Repo.init(str(oaps_dir))

    claude_dir = oaps_dir / "claude"
    claude_dir.mkdir()

    skills_dir = claude_dir / "skills"
    skills_dir.mkdir()

    commands_dir = claude_dir / "commands"
    commands_dir.mkdir()

    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()

    overrides_dir = oaps_dir / "overrides" / "skills"
    overrides_dir.mkdir(parents=True)

    # Create symlink: .claude -> .oaps/claude
    (project_root / ".claude").symlink_to(claude_dir)

    # Patch get_worktree_root to return test project
    monkeypatch.setattr(
        "oaps.utils._paths.get_worktree_root",
        lambda: project_root,
    )

    return OapsProject(
        root=project_root,
        oaps_dir=oaps_dir,
        claude_dir=claude_dir,
        skills_dir=skills_dir,
        commands_dir=commands_dir,
        agents_dir=agents_dir,
        overrides_dir=overrides_dir,
    )


@pytest.fixture
def oaps_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OapsPlugin:
    """Create mock OAPS plugin installation.

    Structure:
        tmp_path/
            claude_home/
                plugins/
                    known_marketplaces.json
            oaps_plugin/
                skills/
                commands/
                agents/
    """
    claude_home = tmp_path / "claude_home"
    plugins_dir = claude_home / "plugins"
    plugins_dir.mkdir(parents=True)

    install_dir = tmp_path / "oaps_plugin"
    install_dir.mkdir()

    skills_dir = install_dir / "skills"
    skills_dir.mkdir()

    commands_dir = install_dir / "commands"
    commands_dir.mkdir()

    agents_dir = install_dir / "agents"
    agents_dir.mkdir()

    marketplaces_file = plugins_dir / "known_marketplaces.json"
    marketplaces_file.write_text(
        json.dumps({"oaps": {"installLocation": str(install_dir)}})
    )

    monkeypatch.setattr(
        "oaps.utils._paths.get_claude_config_dir",
        lambda: claude_home,
    )

    return OapsPlugin(
        install_dir=install_dir,
        skills_dir=skills_dir,
        commands_dir=commands_dir,
        agents_dir=agents_dir,
    )


# ---------------------------------------------------------------------------
# Helper functions for creating test artifacts
# ---------------------------------------------------------------------------


def create_skill(
    base_dir: Path,
    name: str,
    *,
    description: str = "",
    with_references: bool = True,
) -> Path:
    """Create a skill directory with SKILL.md.

    Args:
        base_dir: Directory to create skill in (e.g., oaps_project.skills_dir).
        name: Skill name (also used as directory name).
        description: Skill description for frontmatter.
        with_references: Create empty references/ subdirectory.

    Returns:
        Path to the created skill directory.
    """
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    (skill_dir / "SKILL.md").write_text(f"""---
name: {name}
description: {description or f"Test skill {name}"}
---

# {name}

Test skill content.
""")

    if with_references:
        (skill_dir / "references").mkdir(exist_ok=True)

    return skill_dir


def create_reference(
    skill_dir: Path,
    name: str,
    *,
    description: str = "",
    required: bool = False,
    body: str = "",
    title: str = "",
    commands: dict[str, str] | None = None,
    principles: list[str] | None = None,
    best_practices: list[str] | None = None,
    checklist: list[str] | None = None,
    references: dict[str, str] | None = None,
) -> Path:
    """Create a reference file in skill's references directory.

    Args:
        skill_dir: Path to the skill directory.
        name: Reference name (without .md extension).
        description: Reference description for frontmatter.
        required: Whether this reference is required.
        body: Markdown body content.
        title: Optional title for frontmatter.
        commands: Optional commands dict for frontmatter.
        principles: Optional principles list.
        best_practices: Optional best practices list.
        checklist: Optional checklist items.
        references: Optional external references dict.

    Returns:
        Path to the created reference file.
    """
    refs_dir = skill_dir / "references"
    refs_dir.mkdir(exist_ok=True)

    frontmatter_lines = [
        f"name: {name}",
        f"description: {description or f'Test {name}'}",
    ]

    if title:
        frontmatter_lines.insert(1, f"title: {title}")

    if required:
        frontmatter_lines.append("required: true")

    if commands:
        frontmatter_lines.append("commands:")
        frontmatter_lines.extend(
            f'  "{cmd}": "{desc}"' for cmd, desc in commands.items()
        )

    if principles:
        frontmatter_lines.append("principles:")
        frontmatter_lines.extend(f"  - {p}" for p in principles)

    if best_practices:
        frontmatter_lines.append("best_practices:")
        frontmatter_lines.extend(f"  - {bp}" for bp in best_practices)

    if checklist:
        frontmatter_lines.append("checklist:")
        frontmatter_lines.extend(f"  - {item}" for item in checklist)

    if references:
        frontmatter_lines.append("references:")
        frontmatter_lines.extend(f"  {url}: {desc}" for url, desc in references.items())

    ref_path = refs_dir / f"{name}.md"
    ref_path.write_text(f"""---
{chr(10).join(frontmatter_lines)}
---

{body or f"# {name}\n\nTest content."}
""")
    return ref_path


def create_agent(
    base_dir: Path,
    name: str,
    *,
    description: str = "",
    body: str = "",
) -> Path:
    """Create an agent markdown file.

    Args:
        base_dir: Directory to create agent in (e.g., oaps_project.agents_dir).
        name: Agent name (without .md extension).
        description: Agent description for frontmatter.
        body: Markdown body content.

    Returns:
        Path to the created agent file.
    """
    agent_path = base_dir / f"{name}.md"
    agent_path.write_text(f"""---
name: {name}
description: {description or f"Test agent {name}"}
---

{body or f"# {name}\n\nTest agent content."}
""")
    return agent_path


def create_command(
    base_dir: Path,
    name: str,
    *,
    description: str = "",
    body: str = "",
) -> Path:
    """Create a slash command markdown file.

    Args:
        base_dir: Directory to create command in (e.g., oaps_project.commands_dir).
        name: Command name (without .md extension).
        description: Command description for frontmatter.
        body: Markdown body content.

    Returns:
        Path to the created command file.
    """
    cmd_path = base_dir / f"{name}.md"
    cmd_path.write_text(f"""---
name: {name}
description: {description or f"Test command {name}"}
---

{body or f"# {name}\n\nTest command content."}
""")
    return cmd_path


@pytest.fixture
def console() -> Console:
    return Console(
        width=70,
        force_terminal=True,
        highlight=False,
        color_system=None,
        legacy_windows=False,
    )
