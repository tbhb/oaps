"""Tests for skill validation command."""

from pathlib import Path

from oaps.cli._commands._skill._validate import (
    ValidationResult,
    format_validation_result,
    validate_skill,
)

from tests.conftest import (
    OapsProject,
    create_reference,
    create_skill,
)


class TestValidateSkill:
    """Tests for validate_skill function."""

    def test_valid_skill_passes(self, oaps_project: OapsProject) -> None:
        """Valid skill with proper frontmatter passes validation."""
        desc = 'This skill should be used when the user asks to "test something"'
        skill_dir = create_skill(
            oaps_project.skills_dir,
            "test-skill",
            description=desc,
        )

        result = validate_skill(skill_dir)

        assert result.is_valid
        # May have warnings about short body, but no errors
        assert result.error_count == 0

    def test_missing_skill_directory_fails(self, oaps_project: OapsProject) -> None:
        """Non-existent skill directory fails validation."""
        skill_dir = oaps_project.skills_dir / "nonexistent-skill"

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert result.error_count == 1
        assert any(i.code == "dir-missing" for i in result.issues)

    def test_missing_skill_md_fails(self, oaps_project: OapsProject) -> None:
        """Skill directory without SKILL.md fails validation."""
        skill_dir = oaps_project.skills_dir / "empty-skill"
        skill_dir.mkdir()

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert any(i.code == "skill-md-missing" for i in result.issues)

    def test_invalid_frontmatter_fails(self, oaps_project: OapsProject) -> None:
        """SKILL.md with invalid YAML frontmatter fails validation."""
        skill_dir = oaps_project.skills_dir / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: [invalid: yaml
---

# Test
""")

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert any(i.code == "frontmatter-invalid" for i in result.issues)

    def test_missing_name_fails(self, oaps_project: OapsProject) -> None:
        """SKILL.md without 'name' field fails validation."""
        skill_dir = oaps_project.skills_dir / "no-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: A test skill
---

# Test
""")

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert any(i.code == "name-missing" for i in result.issues)

    def test_missing_description_fails(self, oaps_project: OapsProject) -> None:
        """SKILL.md without 'description' field fails validation."""
        skill_dir = oaps_project.skills_dir / "no-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: no-desc
---

# Test
""")

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert any(i.code == "description-missing" for i in result.issues)

    def test_name_mismatch_warns(self, oaps_project: OapsProject) -> None:
        """SKILL.md with mismatched name warns but passes."""
        skill_dir = oaps_project.skills_dir / "actual-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: different-name
description: 'This skill should be used when the user asks to "test"'
---

# Test content that is long enough to avoid the body too short warning.
This is additional content to make the body longer.
More content here.
""")

        result = validate_skill(skill_dir)

        assert result.is_valid  # Still passes, just warns
        assert any(i.code == "name-mismatch" for i in result.issues)

    def test_vague_description_warns(self, oaps_project: OapsProject) -> None:
        """Vague description without trigger phrases warns."""
        skill_dir = oaps_project.skills_dir / "vague-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: vague-skill
description: Helps with testing
---

# Test
""")

        result = validate_skill(skill_dir)

        assert result.is_valid  # Warnings don't cause failure
        assert any(
            i.code == "description-quality" and "trigger phrases" in i.message
            for i in result.issues
        )

    def test_short_body_warns(self, oaps_project: OapsProject) -> None:
        """Very short body warns."""
        skill_dir = create_skill(
            oaps_project.skills_dir,
            "short-body",
            description='This skill should be used when the user asks to "test"',
        )

        result = validate_skill(skill_dir)

        assert result.is_valid
        assert any(i.code == "body-too-short" for i in result.issues)

    def test_validates_references(self, oaps_project: OapsProject) -> None:
        """References with missing frontmatter fields fail validation."""
        skill_dir = create_skill(
            oaps_project.skills_dir,
            "ref-skill",
            description='This skill should be used when the user asks to "test"',
        )
        refs_dir = skill_dir / "references"
        (refs_dir / "bad-ref.md").write_text("""---
name: bad-ref
---

# Missing description
""")

        result = validate_skill(skill_dir)

        assert not result.is_valid
        assert any(i.code == "ref-description-missing" for i in result.issues)

    def test_valid_reference_passes(self, oaps_project: OapsProject) -> None:
        """Reference with proper frontmatter passes validation."""
        skill_dir = create_skill(
            oaps_project.skills_dir,
            "good-ref-skill",
            description='This skill should be used when the user asks to "test"',
        )
        create_reference(skill_dir, "good-ref", description="A good reference")

        result = validate_skill(skill_dir)

        # Should not have reference errors
        assert not any(i.code.startswith("ref-") for i in result.issues)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_is_valid_with_no_issues(self, tmp_path: Path) -> None:
        """Result with no issues is valid."""
        result = ValidationResult(skill_name="test", skill_dir=tmp_path)

        assert result.is_valid
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_is_valid_with_warnings_only(self, tmp_path: Path) -> None:
        """Result with only warnings is valid."""
        result = ValidationResult(skill_name="test", skill_dir=tmp_path)
        result.add_warning("test-warning", "This is a warning")

        assert result.is_valid
        assert result.error_count == 0
        assert result.warning_count == 1

    def test_is_invalid_with_errors(self, tmp_path: Path) -> None:
        """Result with errors is invalid."""
        result = ValidationResult(skill_name="test", skill_dir=tmp_path)
        result.add_error("test-error", "This is an error")

        assert not result.is_valid
        assert result.error_count == 1

    def test_counts_multiple_issues(self, tmp_path: Path) -> None:
        """Correctly counts multiple issues of different severities."""
        result = ValidationResult(skill_name="test", skill_dir=tmp_path)
        result.add_error("err1", "Error 1")
        result.add_error("err2", "Error 2")
        result.add_warning("warn1", "Warning 1")
        result.add_info("info1", "Info 1")

        assert result.error_count == 2
        assert result.warning_count == 1


class TestFormatValidationResult:
    """Tests for format_validation_result function."""

    def test_format_passed_result(self, tmp_path: Path) -> None:
        """Formats passing result correctly."""
        result = ValidationResult(skill_name="test-skill", skill_dir=tmp_path)

        output = format_validation_result(result)

        assert "Validation: test-skill" in output
        assert "**Result: PASSED**" in output

    def test_format_passed_with_warnings(self, tmp_path: Path) -> None:
        """Formats passing result with warnings correctly."""
        result = ValidationResult(skill_name="test-skill", skill_dir=tmp_path)
        result.add_warning("test-warn", "A warning")

        output = format_validation_result(result)

        assert "**Result: PASSED with warnings**" in output
        assert "A warning" in output

    def test_format_failed_result(self, tmp_path: Path) -> None:
        """Formats failing result correctly."""
        result = ValidationResult(skill_name="test-skill", skill_dir=tmp_path)
        result.add_error("test-err", "An error")

        output = format_validation_result(result)

        assert "**Result: FAILED**" in output
        assert "An error" in output
