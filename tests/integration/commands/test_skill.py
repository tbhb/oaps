"""Integration tests for the skill command."""

from collections.abc import Callable

import pytest

from tests.conftest import (
    OapsProject,
    create_reference,
    create_skill,
)


class TestSkillOrient:
    def test_displays_skill_context_header(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill")

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "## test-skill Skill context" in captured.out

    def test_displays_environment_section(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill")

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "### Environment" in captured.out

    def test_displays_no_references_message(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill", with_references=False)

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "### Available references" in captured.out
        assert "*No references found.*" in captured.out

    def test_displays_references_table(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(skill_dir, "core", description="Core reference")
        create_reference(skill_dir, "advanced", description="Advanced topics")

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "### Available references" in captured.out
        assert "Name" in captured.out
        assert "Description" in captured.out
        assert "| core" in captured.out
        assert "Core reference" in captured.out
        assert "| advanced" in captured.out
        assert "Advanced topics" in captured.out

    def test_marks_required_references(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir, "required-ref", description="Must read", required=True
        )

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "required-ref (required)" in captured.out

    def test_displays_usage_hints(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill")

        oaps_cli("skill", "orient", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "To load specific references, run:" in captured.out
        assert "oaps skill context" in captured.out

    def test_skill_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("skill", "orient", "nonexistent-skill", "--project")

        captured = capsys.readouterr()
        assert "Could not find skill: nonexistent-skill" in captured.out


class TestSkillContext:
    def test_domain_only_skill_requires_references_without_workflow(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill")

        oaps_cli("skill", "context", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "--references is required for domain-only skills" in captured.err
        assert "Run `oaps skill orient --project test-skill`" in captured.err

    def test_skill_with_required_references_works_without_explicit_refs(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir,
            "fundamentals",
            description="Required fundamentals",
            required=True,
            body="Fundamental content here.",
        )

        oaps_cli("skill", "context", "test-skill", "--project")

        captured = capsys.readouterr()
        assert "Fundamental content here." in captured.out

    def test_loads_requested_reference(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir,
            "core",
            description="Core concepts",
            body="This is the core content.",
        )

        oaps_cli("skill", "context", "test-skill", "--project", "--references", "core")

        captured = capsys.readouterr()
        assert "This is the core content." in captured.out

    def test_loads_required_reference_automatically(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir,
            "fundamentals",
            description="Required fundamentals",
            required=True,
            body="Fundamental content here.",
        )
        create_reference(
            skill_dir,
            "advanced",
            description="Advanced topics",
            body="Advanced content here.",
        )

        oaps_cli(
            "skill", "context", "test-skill", "--project", "--references", "advanced"
        )

        captured = capsys.readouterr()
        # Required reference loaded automatically
        assert "Fundamental content here." in captured.out
        # Requested reference also loaded
        assert "Advanced content here." in captured.out

    def test_reports_not_found_reference(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        create_skill(oaps_project.skills_dir, "test-skill")

        oaps_cli(
            "skill", "context", "test-skill", "--project", "--references", "missing"
        )
        captured = capsys.readouterr()
        # Missing references are reported during dependency resolution
        assert "**Missing dependencies:** missing" in captured.err

    def test_loads_multiple_references(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(skill_dir, "ref1", body="Content from ref1.")
        create_reference(skill_dir, "ref2", body="Content from ref2.")

        # cyclopts requires repeating the flag for list arguments
        oaps_cli(
            "skill",
            "context",
            "test-skill",
            "--project",
            "--references",
            "ref1",
            "--references",
            "ref2",
        )

        captured = capsys.readouterr()
        assert "Content from ref1." in captured.out
        assert "Content from ref2." in captured.out

    def test_skill_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("skill", "context", "nonexistent-skill", "--project")

        captured = capsys.readouterr()
        assert "Could not find skill: nonexistent-skill" in captured.out

    def test_formats_principles_from_reference(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir,
            "core",
            body="Core content.",
            principles=["Principle one", "Principle two"],
        )

        oaps_cli("skill", "context", "test-skill", "--project", "--references", "core")

        captured = capsys.readouterr()
        assert "Principle" in captured.out

    def test_formats_best_practices_from_reference(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        skill_dir = create_skill(oaps_project.skills_dir, "test-skill")
        create_reference(
            skill_dir,
            "core",
            body="Core content.",
            best_practices=["Best practice one"],
        )

        oaps_cli("skill", "context", "test-skill", "--project", "--references", "core")

        captured = capsys.readouterr()
        assert "Best practice" in captured.out
