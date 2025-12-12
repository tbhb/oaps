"""Tests for skill creation command."""

import pytest

from oaps.cli._commands._skill._create import (
    SkillTemplate,
    create_skill,
    generate_skill_template,
)

from tests.conftest import OapsProject


class TestGenerateSkillTemplate:
    """Tests for generate_skill_template function."""

    def test_generates_all_template_parts(self) -> None:
        """Generates SKILL.md and reference templates."""
        template = generate_skill_template("test-skill")

        assert isinstance(template, SkillTemplate)
        assert template.skill_md
        assert template.example_reference

    def test_skill_md_contains_name(self) -> None:
        """SKILL.md template contains the skill name."""
        template = generate_skill_template("my-custom-skill")

        assert "name: my-custom-skill" in template.skill_md

    def test_skill_md_contains_title(self) -> None:
        """SKILL.md template contains title-cased name as heading."""
        template = generate_skill_template("my-custom-skill")

        assert "# My Custom Skill" in template.skill_md

    def test_skill_md_contains_description_placeholder(self) -> None:
        """SKILL.md template contains description with placeholder."""
        template = generate_skill_template("test-skill")

        assert "description: >-" in template.skill_md
        assert "TODO:" in template.skill_md

    def test_reference_template_has_frontmatter(self) -> None:
        """Example reference has proper frontmatter."""
        template = generate_skill_template("test-skill")

        assert "name: example" in template.example_reference
        assert "description:" in template.example_reference


class TestCreateSkill:
    """Tests for create_skill function."""

    def test_creates_skill_in_project_by_default(
        self, oaps_project: OapsProject
    ) -> None:
        """Creates skill in project location by default."""
        skill_dir = create_skill("new-skill")

        assert skill_dir.parent == oaps_project.skills_dir
        assert skill_dir.name == "new-skill"
        assert skill_dir.is_dir()

    def test_creates_skill_md(self, oaps_project: OapsProject) -> None:
        """Creates SKILL.md file."""
        skill_dir = create_skill("test-skill")

        skill_md = skill_dir / "SKILL.md"
        assert skill_md.is_file()
        content = skill_md.read_text()
        assert "name: test-skill" in content

    def test_creates_references_directory_and_example(
        self, oaps_project: OapsProject
    ) -> None:
        """Creates references directory with example file."""
        skill_dir = create_skill("test-skill")

        refs_dir = skill_dir / "references"
        assert refs_dir.is_dir()
        example = refs_dir / "example.md"
        assert example.is_file()

    def test_creates_skill_without_references(self, oaps_project: OapsProject) -> None:
        """Can create skill without references directory."""
        skill_dir = create_skill("no-refs-skill", with_references=False)

        assert not (skill_dir / "references").exists()

    def test_creates_scripts_directory_when_requested(
        self, oaps_project: OapsProject
    ) -> None:
        """Creates scripts directory when with_scripts=True."""
        skill_dir = create_skill("scripts-skill", with_scripts=True)

        assert (skill_dir / "scripts").is_dir()

    def test_creates_assets_directory_when_requested(
        self, oaps_project: OapsProject
    ) -> None:
        """Creates assets directory when with_assets=True."""
        skill_dir = create_skill("assets-skill", with_assets=True)

        assert (skill_dir / "assets").is_dir()

    def test_raises_when_skill_exists(self, oaps_project: OapsProject) -> None:
        """Raises FileExistsError when skill already exists."""
        create_skill("existing-skill")

        with pytest.raises(FileExistsError, match="already exists"):
            create_skill("existing-skill")

    def test_raises_when_both_plugin_and_project(
        self, oaps_project: OapsProject
    ) -> None:
        """Raises ValueError when both plugin and project are True."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            create_skill("test-skill", plugin=True, project=True)

    def test_creates_plugin_skill(self, oaps_project: OapsProject) -> None:
        """Creates skill in plugin location when plugin=True."""
        from oaps.utils._paths import get_worktree_root

        skill_dir = create_skill("plugin-skill", plugin=True)

        expected_parent = get_worktree_root() / "skills"
        assert skill_dir.parent == expected_parent

    def test_creates_project_skill_explicitly(self, oaps_project: OapsProject) -> None:
        """Creates skill in project location when project=True."""
        skill_dir = create_skill("project-skill", project=True)

        assert skill_dir.parent == oaps_project.skills_dir

    def test_skill_name_converted_to_title(self, oaps_project: OapsProject) -> None:
        """Kebab-case skill name is converted to title case in SKILL.md."""
        skill_dir = create_skill("my-awesome-skill")

        content = (skill_dir / "SKILL.md").read_text()
        assert "# My Awesome Skill" in content


class TestCreateSkillIntegration:
    """Integration tests for skill creation."""

    def test_created_skill_passes_validation(self, oaps_project: OapsProject) -> None:
        """Newly created skill passes validation (with expected warnings)."""
        from oaps.cli._commands._skill._validate import validate_skill

        skill_dir = create_skill("integration-test-skill")

        result = validate_skill(skill_dir)

        # Should pass (no errors), but may have warnings about TODOs
        assert result.is_valid
        assert result.error_count == 0
