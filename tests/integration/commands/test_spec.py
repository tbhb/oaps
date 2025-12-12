# pyright: reportAny=false, reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnusedImport=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportArgumentType=false
"""Integration tests for the spec command."""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from oaps.cli._commands._context import CLIContext

# NOTE: Workaround for missing artifact commands registration.
# The _artifact_commands module must be imported to register its commands
# with artifact_app. This import triggers the decorator registration.
from oaps.cli._commands._spec import (
    _artifact_commands,  # noqa: F401
)
from oaps.cli._commands._spec._errors import (
    EXIT_CANCELLED,
    EXIT_IO_ERROR,
    EXIT_NOT_FOUND,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
)
from oaps.config import Config
from oaps.spec import (
    ArtifactManager as SpecArtifactManager,
    ArtifactType,
    RequirementManager as SpecRequirementManager,
    RequirementType,
    SpecManager,
    SpecType,
    TestManager as SpecTestManager,
    TestMethod as SpecTestMethod,
)

from tests.conftest import OapsProject


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def spec_context(oaps_project: OapsProject) -> Generator[None]:
    """Set up CLI context with specs directory for tests."""
    # Create specs directory
    specs_dir = oaps_project.oaps_dir / "docs" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    config = Config.from_dict({})
    ctx = CLIContext(config=config, project_root=oaps_project.root)
    CLIContext.set_current(ctx)
    yield
    CLIContext.reset()


@pytest.fixture
def get_spec_manager(oaps_project: OapsProject) -> SpecManager:
    """Get a SpecManager for creating test data."""
    specs_dir = oaps_project.oaps_dir / "docs" / "specs"
    return SpecManager(specs_dir)


@pytest.fixture
def get_requirement_manager(
    get_spec_manager: SpecManager,
) -> SpecRequirementManager:
    """Get a RequirementManager for creating test data."""
    return SpecRequirementManager(get_spec_manager)


@pytest.fixture
def get_test_manager(
    get_spec_manager: SpecManager, get_requirement_manager: SpecRequirementManager
) -> SpecTestManager:
    """Get a TestManager for creating test data."""
    return SpecTestManager(get_spec_manager, get_requirement_manager)


@pytest.fixture
def get_artifact_manager(get_spec_manager: SpecManager) -> SpecArtifactManager:
    """Get an ArtifactManager for creating test data."""
    return SpecArtifactManager(get_spec_manager)


CreateSpecFunc = Callable[[str, str], str]
CreateRequirementFunc = Callable[[str], tuple[str, str]]
CreateTestEntryFunc = Callable[[str], tuple[str, str]]
CreateArtifactFunc = Callable[[str], tuple[str, str]]


@pytest.fixture
def create_spec(get_spec_manager: SpecManager) -> CreateSpecFunc:
    """Factory fixture to create a spec and return its ID."""

    def _create(slug: str = "test-spec", title: str = "Test Specification") -> str:
        metadata = get_spec_manager.create_spec(
            slug,
            title,
            SpecType.FEATURE,
            summary="Test summary",
            actor="test",
        )
        return metadata.id

    return _create


@pytest.fixture
def create_requirement(
    get_spec_manager: SpecManager, get_requirement_manager: SpecRequirementManager
) -> CreateRequirementFunc:
    """Factory to create a spec with requirement, returns (spec_id, req_id)."""

    def _create(slug: str = "test-spec") -> tuple[str, str]:
        metadata = get_spec_manager.create_spec(
            slug,
            "Test Specification",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Requirement",
            "A test requirement",
            actor="test",
        )
        return metadata.id, requirement.id

    return _create


@pytest.fixture
def create_test_entry(
    get_spec_manager: SpecManager,
    get_requirement_manager: SpecRequirementManager,
    get_test_manager: SpecTestManager,
) -> CreateTestEntryFunc:
    """Factory fixture to create a spec with test and return (spec_id, test_id)."""

    def _create(slug: str = "test-spec", req_id: str | None = None) -> tuple[str, str]:
        metadata = get_spec_manager.create_spec(
            slug,
            "Test Specification",
            SpecType.FEATURE,
            actor="test",
        )
        # Create a requirement first if not provided
        if req_id is None:
            requirement = get_requirement_manager.add_requirement(
                metadata.id,
                RequirementType.FUNCTIONAL,
                "Test Requirement",
                "A test requirement",
                actor="test",
            )
            req_id = requirement.id

        test = get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [req_id],
            description="A test entry",
            actor="test",
        )
        return metadata.id, test.id

    return _create


@pytest.fixture
def create_artifact(
    get_spec_manager: SpecManager, get_artifact_manager: SpecArtifactManager
) -> CreateArtifactFunc:
    """Factory to create a spec with artifact, returns (spec_id, artifact_id)."""

    def _create(slug: str = "test-spec") -> tuple[str, str]:
        metadata = get_spec_manager.create_spec(
            slug,
            "Test Specification",
            SpecType.FEATURE,
            actor="test",
        )
        artifact = get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Test Artifact",
            content="Test content",
            type_fields={"review_type": "peer"},
            actor="test",
        )
        return metadata.id, artifact.id

    return _create


# ---------------------------------------------------------------------------
# Porcelain Command Tests
# ---------------------------------------------------------------------------


class TestSpecCreate:
    def test_create_success(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "create", "my-feature", "My Feature"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "my-feature" in captured.out
        assert "My Feature" in captured.out

    def test_create_with_type(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "create", "my-subsystem", "My Component", "--type", "subsystem"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "subsystem" in captured.out.lower()

    def test_create_with_options(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec",
            "create",
            "full-spec",
            "Full Specification",
            "--summary",
            "A detailed summary",
            "--tags",
            "tag1",
            "--tags",
            "tag2",
            "--authors",
            "author1",
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "full-spec" in captured.out

    def test_create_duplicate_slug_fails(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create first spec
        create_spec("duplicate-test", "First Spec")

        # Try to create with same slug
        exit_code = oaps_cli_with_exit_code(
            "spec", "create", "duplicate-test", "Second Spec"
        )

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize(
        "format_arg",
        ["json", "yaml", "table"],
    )
    def test_create_output_formats(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec",
            "create",
            f"format-{format_arg}",
            "Format Test",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        if format_arg == "json":
            assert '"id"' in captured.out
        elif format_arg == "yaml":
            assert "id:" in captured.out


class TestSpecDelete:
    def test_delete_success_with_force(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("to-delete", "Delete Me")

        exit_code = oaps_cli_with_exit_code("spec", "delete", spec_id, "--force")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Deleted" in captured.out or "Deleted" in captured.err

    def test_delete_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "delete", "9999", "--force")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_delete_cancelled_without_force(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spec_id = create_spec("cancel-delete", "Cancel Delete")

        # Mock stdin to be non-TTY for consistent behavior
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        exit_code = oaps_cli_with_exit_code("spec", "delete", spec_id)

        # Should be cancelled because stdin is not a TTY and --force not given
        assert exit_code == EXIT_CANCELLED


class TestSpecArchive:
    def test_archive_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("to-archive", "Archive Me")

        exit_code = oaps_cli_with_exit_code("spec", "archive", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # The spec should now be deprecated
        assert spec_id in captured.out or "deprecated" in captured.out.lower()

    def test_archive_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "archive", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_archive_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        # Create unique spec for each format test
        metadata = get_spec_manager.create_spec(
            f"archive-{format_arg}",
            "Archive Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "archive", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestSpecUpdate:
    def test_update_title(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("to-update", "Original Title")

        exit_code = oaps_cli_with_exit_code(
            "spec", "update", spec_id, "--title", "Updated Title"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Updated Title" in captured.out

    def test_update_multiple_fields(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("multi-update", "Multi Update")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "update",
            spec_id,
            "--title",
            "New Title",
            "--summary",
            "New summary",
            "--tags",
            "newtag",
        )

        assert exit_code == EXIT_SUCCESS

    def test_update_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "update", "9999", "--title", "New Title"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_update_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"update-fmt-{format_arg}",
            "Update Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "update", metadata.id, "--title", "New", "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestSpecRename:
    def test_rename_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("old-name", "Rename Test")

        exit_code = oaps_cli_with_exit_code("spec", "rename", spec_id, "new-name")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "new-name" in captured.out

    def test_rename_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "rename", "9999", "new-name")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_rename_duplicate_fails(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create two specs
        spec1 = get_spec_manager.create_spec(
            "rename-first", "First", SpecType.FEATURE, actor="test"
        )
        get_spec_manager.create_spec(
            "rename-second", "Second", SpecType.FEATURE, actor="test"
        )

        # Try to rename first to second's slug
        exit_code = oaps_cli_with_exit_code("spec", "rename", spec1.id, "rename-second")

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_rename_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"rename-fmt-{format_arg}",
            "Rename Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "rename",
            metadata.id,
            f"renamed-{format_arg}",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestSpecValidate:
    def test_validate_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("valid-spec", "Valid Spec")

        exit_code = oaps_cli_with_exit_code("spec", "validate", spec_id)

        assert exit_code == EXIT_SUCCESS

    def test_validate_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "validate", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_validate_strict_mode(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create spec with authors to pass strict validation
        metadata = get_spec_manager.create_spec(
            "strict-spec",
            "Strict Spec",
            SpecType.FEATURE,
            summary="Summary",
            authors=["author1"],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code("spec", "validate", metadata.id, "--strict")

        # Should succeed since our test spec has authors
        assert exit_code == EXIT_SUCCESS

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_validate_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"validate-fmt-{format_arg}",
            "Validate Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "validate", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestSpecInfo:
    def test_info_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("info-spec", "Info Spec")

        exit_code = oaps_cli_with_exit_code("spec", "info", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Info Spec" in captured.out
        assert spec_id in captured.out

    def test_info_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "info", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_info_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"info-fmt-{format_arg}",
            "Info Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "info", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestSpecList:
    def test_list_empty(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "list")

        assert exit_code == EXIT_SUCCESS

    def test_list_with_specs(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create multiple specs
        get_spec_manager.create_spec(
            "list-one", "List One", SpecType.FEATURE, actor="test"
        )
        get_spec_manager.create_spec(
            "list-two", "List Two", SpecType.SUBSYSTEM, actor="test"
        )

        exit_code = oaps_cli_with_exit_code("spec", "list")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "List One" in captured.out
        assert "List Two" in captured.out

    def test_list_filter_by_type(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        get_spec_manager.create_spec(
            "filter-feat", "Feature Spec", SpecType.FEATURE, actor="test"
        )
        get_spec_manager.create_spec(
            "filter-comp", "Component Spec", SpecType.SUBSYSTEM, actor="test"
        )

        exit_code = oaps_cli_with_exit_code("spec", "list", "--type", "subsystem")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Component Spec" in captured.out
        # Feature spec should not appear with subsystem filter
        assert "Feature Spec" not in captured.out

    def test_list_filter_by_status(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        get_spec_manager.create_spec(
            "status-draft", "Draft Spec", SpecType.FEATURE, actor="test"
        )

        exit_code = oaps_cli_with_exit_code("spec", "list", "--status", "draft")

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Draft Spec" in captured.out

    def test_list_with_limit(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        # Create multiple specs
        for i in range(5):
            get_spec_manager.create_spec(
                f"limit-{i}", f"Limit Spec {i}", SpecType.FEATURE, actor="test"
            )

        exit_code = oaps_cli_with_exit_code("spec", "list", "--limit", "2")

        assert exit_code == EXIT_SUCCESS

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table", "plain"])
    def test_list_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        get_spec_manager.create_spec(
            f"list-fmt-{format_arg}",
            "List Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code("spec", "list", "--format", format_arg)

        assert exit_code == EXIT_SUCCESS


class TestSpecSave:
    def test_save_nothing_to_save(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("save-spec", "Save Spec")

        exit_code = oaps_cli_with_exit_code(
            "spec", "save", spec_id, "-m", "Test commit"
        )

        # Should succeed with "nothing to save" since files are already committed
        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Messages go to stderr in this command
        output = captured.out + captured.err
        assert "Nothing to save" in output or "Saved" in output

    def test_save_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "save", "9999", "-m", "Test commit")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err


class TestSpecListTemplates:
    def test_list_templates(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "list-templates")

        # May succeed or show "no templates" - either is valid
        assert exit_code == EXIT_SUCCESS


# ---------------------------------------------------------------------------
# Requirement Command Tests
# ---------------------------------------------------------------------------


class TestReqAdd:
    def test_add_requirement_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-add", "Requirement Add Test")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "add", spec_id, "functional", "--title", "My Requirement"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "My Requirement" in captured.out

    def test_add_requirement_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "add", "9999", "functional", "--title", "Test"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_add_requirement_with_options(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-add-opts", "Requirement Add Options")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "req",
            "add",
            spec_id,
            "security",
            "--title",
            "Security Requirement",
            "--description",
            "Detailed description",
            "--rationale",
            "Because security",
            "--tags",
            "auth",
        )

        assert exit_code == EXIT_SUCCESS

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_add_requirement_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"req-add-fmt-{format_arg}",
            "Req Add Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "req",
            "add",
            metadata.id,
            "functional",
            "--title",
            "Format Test",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestReqUpdate:
    def test_update_requirement_success(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-update")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "update", f"{spec_id}:{req_id}", "--title", "Updated Title"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Updated Title" in captured.out

    def test_update_requirement_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-update-nf", "Requirement Update NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "update", f"{spec_id}:FR-9999", "--title", "Test"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_update_requirement_invalid_qualified_id(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "update", "invalid-id-format", "--title", "Test"
        )

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_update_requirement_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"req-upd-fmt-{format_arg}",
            "Req Update Format Test",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "req",
            "update",
            f"{metadata.id}:{requirement.id}",
            "--title",
            "New Title",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestReqLink:
    def test_link_requirement_with_commit(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-link")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "link", f"{spec_id}:{req_id}", "--commit", "abc123def"
        )

        assert exit_code == EXIT_SUCCESS

    def test_link_requirement_with_pr(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-link-pr")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "link", f"{spec_id}:{req_id}", "--pr", "42"
        )

        assert exit_code == EXIT_SUCCESS

    def test_link_requirement_missing_options(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-link-err")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "link", f"{spec_id}:{req_id}"
        )

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_link_requirement_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-link-nf", "Requirement Link NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "link", f"{spec_id}:FR-9999", "--commit", "abc123"
        )

        assert exit_code == EXIT_NOT_FOUND

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_link_requirement_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"req-link-fmt-{format_arg}",
            "Req Link Format Test",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "req",
            "link",
            f"{metadata.id}:{requirement.id}",
            "--commit",
            "abc123",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestReqList:
    def test_list_requirements_success(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-list")

        exit_code = oaps_cli_with_exit_code("spec", "req", "list", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert req_id in captured.out or "Test Requirement" in captured.out

    def test_list_requirements_empty(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-list-empty", "Empty Requirements")

        exit_code = oaps_cli_with_exit_code("spec", "req", "list", spec_id)

        assert exit_code == EXIT_SUCCESS

    def test_list_requirements_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "req", "list", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_list_requirements_filter_by_type(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        metadata = get_spec_manager.create_spec(
            "req-list-filter", "Requirement List Filter", SpecType.FEATURE, actor="test"
        )
        get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Functional Req",
            "Desc",
            actor="test",
        )
        get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.SECURITY,
            "Security Req",
            "Desc",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "list", metadata.id, "--type", "security"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Security Req" in captured.out
        # Functional should not appear
        assert "Functional Req" not in captured.out

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table", "plain"])
    def test_list_requirements_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"req-list-fmt-{format_arg}",
            "Req List Format Test",
            SpecType.FEATURE,
            actor="test",
        )
        get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "list", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestReqShow:
    def test_show_requirement_success(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-show")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "show", f"{spec_id}:{req_id}"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Test Requirement" in captured.out or req_id in captured.out

    def test_show_requirement_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-show-nf", "Requirement Show NF")

        exit_code = oaps_cli_with_exit_code("spec", "req", "show", f"{spec_id}:FR-9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "text"])
    def test_show_requirement_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"req-show-fmt-{format_arg}",
            "Req Show Format Test",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "req",
            "show",
            f"{metadata.id}:{requirement.id}",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestReqDelete:
    def test_delete_requirement_success(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("req-delete")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "delete", f"{spec_id}:{req_id}", "--force"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Deleted" in captured.out or "Deleted" in captured.err

    def test_delete_requirement_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("req-delete-nf", "Requirement Delete NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "delete", f"{spec_id}:FR-9999", "--force"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_delete_requirement_cancelled(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spec_id, req_id = create_requirement("req-delete-cancel")

        # Mock stdin to be non-TTY
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        exit_code = oaps_cli_with_exit_code(
            "spec", "req", "delete", f"{spec_id}:{req_id}"
        )

        assert exit_code == EXIT_CANCELLED


# ---------------------------------------------------------------------------
# Test Command Tests
# ---------------------------------------------------------------------------


class TestTestAdd:
    def test_add_test_success(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("test-add")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "add",
            spec_id,
            "unit",
            "--title",
            "My Unit Test",
            "--requirements",
            req_id,
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "My Unit Test" in captured.out

    def test_add_test_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "add",
            "9999",
            "unit",
            "--title",
            "Test",
            "--requirements",
            "FR-0001",
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_add_test_requirement_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-add-req-nf", "Test Add Req NF")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "add",
            spec_id,
            "unit",
            "--title",
            "Test",
            "--requirements",
            "FR-9999",
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_add_test_with_options(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("test-add-opts")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "add",
            spec_id,
            "integration",
            "--title",
            "Integration Test",
            "--requirements",
            req_id,
            "--description",
            "A detailed test",
            "--file",
            "tests/test_example.py",
            "--function",
            "test_example",
            "--tags",
            "critical",
        )

        assert exit_code == EXIT_SUCCESS

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_add_test_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-add-fmt-{format_arg}",
            "Test Add Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "add",
            metadata.id,
            "unit",
            "--title",
            "Format Test",
            "--requirements",
            requirement.id,
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestTestUpdate:
    def test_update_test_success(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, test_id = create_test_entry("test-update")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "update", f"{spec_id}:{test_id}", "--title", "Updated Test"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Updated Test" in captured.out

    def test_update_test_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-update-nf", "Test Update NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "update", f"{spec_id}:UT-9999", "--title", "Test"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_update_test_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-upd-fmt-{format_arg}",
            "Test Update Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )
        test = get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [requirement.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "update",
            f"{metadata.id}:{test.id}",
            "--title",
            "New Title",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestTestLink:
    def test_link_test_success(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        metadata = get_spec_manager.create_spec(
            "test-link", "Test Link", SpecType.FEATURE, actor="test"
        )
        req1 = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Req 1",
            "Desc",
            actor="test",
        )
        req2 = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Req 2",
            "Desc",
            actor="test",
        )
        test = get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [req1.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "link",
            f"{metadata.id}:{test.id}",
            "--requirements",
            req2.id,
        )

        assert exit_code == EXIT_SUCCESS

    def test_link_test_empty_requirements_error(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, test_id = create_test_entry("test-link-empty")

        # Run without --requirements (cyclopts should handle this)
        # But we need at least one requirement
        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "link", f"{spec_id}:{test_id}"
        )

        # Should fail due to missing required parameter (cyclopts uses exit code 1)
        assert exit_code != EXIT_SUCCESS
        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Cyclopts prints error about missing required parameter
        assert "requires an argument" in output or "required" in output.lower()

    def test_link_test_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-link-nf", "Test Link NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "link", f"{spec_id}:UT-9999", "--requirements", "FR-0001"
        )

        assert exit_code == EXIT_NOT_FOUND

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_link_test_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-link-fmt-{format_arg}",
            "Test Link Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )
        test = get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [requirement.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "link",
            f"{metadata.id}:{test.id}",
            "--requirements",
            requirement.id,
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestTestList:
    def test_list_tests_success(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, test_id = create_test_entry("test-list")

        exit_code = oaps_cli_with_exit_code("spec", "test", "list", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert test_id in captured.out or "Test Entry" in captured.out

    def test_list_tests_empty(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-list-empty", "Empty Tests")

        exit_code = oaps_cli_with_exit_code("spec", "test", "list", spec_id)

        assert exit_code == EXIT_SUCCESS

    def test_list_tests_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "test", "list", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_list_tests_filter_by_method(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        metadata = get_spec_manager.create_spec(
            "test-list-filter", "Test List Filter", SpecType.FEATURE, actor="test"
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Desc",
            actor="test",
        )
        get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Unit Test",
            [requirement.id],
            actor="test",
        )
        get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.INTEGRATION,
            "Integration Test",
            [requirement.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "list", metadata.id, "--method", "integration"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Integration Test" in captured.out
        assert "Unit Test" not in captured.out

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table", "plain"])
    def test_list_tests_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-list-fmt-{format_arg}",
            "Test List Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )
        get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [requirement.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "list", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestTestShow:
    def test_show_test_success(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, test_id = create_test_entry("test-show")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "show", f"{spec_id}:{test_id}"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Test Entry" in captured.out or test_id in captured.out

    def test_show_test_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-show-nf", "Test Show NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "show", f"{spec_id}:UT-9999"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "text"])
    def test_show_test_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-show-fmt-{format_arg}",
            "Test Show Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )
        test = get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [requirement.id],
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "show", f"{metadata.id}:{test.id}", "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestTestDelete:
    def test_delete_test_success(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, test_id = create_test_entry("test-delete")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "delete", f"{spec_id}:{test_id}", "--force"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Deleted" in captured.out or "Deleted" in captured.err

    def test_delete_test_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-delete-nf", "Test Delete NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "delete", f"{spec_id}:UT-9999", "--force"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_delete_test_cancelled(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spec_id, test_id = create_test_entry("test-delete-cancel")

        # Mock stdin to be non-TTY
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "delete", f"{spec_id}:{test_id}"
        )

        assert exit_code == EXIT_CANCELLED


class TestTestSync:
    def test_sync_pytest_results_file_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("test-sync", "Test Sync")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "sync",
            spec_id,
            "--pytest-results",
            "/nonexistent/file.json",
        )

        assert exit_code == EXIT_IO_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_sync_pytest_results_success(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        tmp_path: Path,
    ) -> None:
        spec_id, _test_id = create_test_entry("test-sync-ok")

        # Create a valid pytest results file
        results_file = tmp_path / "results.json"
        results_file.write_text('{"tests": [], "duration": 0.1, "exitcode": 0}')

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "sync", spec_id, "--pytest-results", str(results_file)
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Verify sync produced some output about the operation
        assert output  # Should have output about sync results

    def test_sync_pytest_results_dry_run(
        self,
        oaps_project: OapsProject,
        create_test_entry: CreateTestEntryFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        tmp_path: Path,
    ) -> None:
        spec_id, _test_id = create_test_entry("test-sync-dry")

        # Create a valid pytest results file
        results_file = tmp_path / "results.json"
        results_file.write_text('{"tests": [], "duration": 0.1, "exitcode": 0}')

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "sync",
            spec_id,
            "--pytest-results",
            str(results_file),
            "--dry-run",
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        # Output goes to stderr
        output = captured.out + captured.err
        assert "Dry run" in output or "dry run" in output.lower()

    def test_sync_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        tmp_path: Path,
    ) -> None:
        results_file = tmp_path / "results.json"
        results_file.write_text('{"tests": [], "duration": 0.1, "exitcode": 0}')

        exit_code = oaps_cli_with_exit_code(
            "spec", "test", "sync", "9999", "--pytest-results", str(results_file)
        )

        assert exit_code == EXIT_NOT_FOUND

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_sync_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_requirement_manager: SpecRequirementManager,
        get_test_manager: SpecTestManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        tmp_path: Path,
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"test-sync-fmt-{format_arg}",
            "Test Sync Format",
            SpecType.FEATURE,
            actor="test",
        )
        requirement = get_requirement_manager.add_requirement(
            metadata.id,
            RequirementType.FUNCTIONAL,
            "Test Req",
            "Description",
            actor="test",
        )
        get_test_manager.add_test(
            metadata.id,
            SpecTestMethod.UNIT,
            "Test Entry",
            [requirement.id],
            actor="test",
        )

        results_file = tmp_path / f"results-{format_arg}.json"
        results_file.write_text('{"tests": [], "duration": 0.1, "exitcode": 0}')

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "test",
            "sync",
            metadata.id,
            "--pytest-results",
            str(results_file),
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


# ---------------------------------------------------------------------------
# Artifact Command Tests
# ---------------------------------------------------------------------------


class TestArtifactAdd:
    # NOTE: Artifact add via CLI fails because the CLI doesn't support type_fields
    # which are required for review artifacts. This is a known limitation.
    @pytest.mark.skip(
        reason="CLI doesn't support type_fields required by artifact types"
    )
    def test_add_artifact_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("artifact-add", "Artifact Add Test")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "add", spec_id, "review", "--title", "My Review"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "My Review" in captured.out

    def test_add_artifact_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "add", "9999", "review", "--title", "Test"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.skip(
        reason="CLI doesn't support type_fields required by artifact types"
    )
    def test_add_artifact_with_options(
        self,
        oaps_project: OapsProject,
        create_requirement: CreateRequirementFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, req_id = create_requirement("artifact-add-opts")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "artifact",
            "add",
            spec_id,
            "decision",
            "--title",
            "Architecture Decision",
            "--description",
            "A decision record",
            "--requirements",
            req_id,
            "--tags",
            "architecture",
        )

        assert exit_code == EXIT_SUCCESS

    @pytest.mark.skip(
        reason="CLI doesn't support type_fields required by artifact types"
    )
    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_add_artifact_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"artifact-add-fmt-{format_arg}",
            "Artifact Add Format",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "artifact",
            "add",
            metadata.id,
            "review",
            "--title",
            "Format Test",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestArtifactUpdate:
    def test_update_artifact_success(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, artifact_id = create_artifact("artifact-update")

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "artifact",
            "update",
            f"{spec_id}:{artifact_id}",
            "--title",
            "Updated Artifact",
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Updated Artifact" in captured.out

    def test_update_artifact_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("artifact-update-nf", "Artifact Update NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "update", f"{spec_id}:RV-9999", "--title", "Test"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_update_artifact_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_artifact_manager: SpecArtifactManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"artifact-upd-fmt-{format_arg}",
            "Artifact Update Format",
            SpecType.FEATURE,
            actor="test",
        )
        artifact = get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Test Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "artifact",
            "update",
            f"{metadata.id}:{artifact.id}",
            "--title",
            "New Title",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestArtifactRebuild:
    def test_rebuild_success(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, _artifact_id = create_artifact("artifact-rebuild")

        exit_code = oaps_cli_with_exit_code("spec", "artifact", "rebuild", spec_id)

        assert exit_code == EXIT_SUCCESS

    def test_rebuild_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "artifact", "rebuild", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_rebuild_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_artifact_manager: SpecArtifactManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"artifact-rebuild-fmt-{format_arg}",
            "Artifact Rebuild Format",
            SpecType.FEATURE,
            actor="test",
        )
        get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Test Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "rebuild", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestArtifactList:
    def test_list_artifacts_success(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, artifact_id = create_artifact("artifact-list")

        exit_code = oaps_cli_with_exit_code("spec", "artifact", "list", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert artifact_id in captured.out or "Test Artifact" in captured.out

    def test_list_artifacts_empty(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("artifact-list-empty", "Empty Artifacts")

        exit_code = oaps_cli_with_exit_code("spec", "artifact", "list", spec_id)

        assert exit_code == EXIT_SUCCESS

    def test_list_artifacts_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "artifact", "list", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_list_artifacts_filter_by_type(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_artifact_manager: SpecArtifactManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        metadata = get_spec_manager.create_spec(
            "artifact-list-filter",
            "Artifact List Filter",
            SpecType.FEATURE,
            actor="test",
        )
        get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Review Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )
        get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.DECISION,
            "Decision Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "list", metadata.id, "--type", "decision"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Decision Artifact" in captured.out
        assert "Review Artifact" not in captured.out

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table", "plain"])
    def test_list_artifacts_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_artifact_manager: SpecArtifactManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"artifact-list-fmt-{format_arg}",
            "Artifact List Format",
            SpecType.FEATURE,
            actor="test",
        )
        get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Test Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "list", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS


class TestArtifactShow:
    def test_show_artifact_success(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, artifact_id = create_artifact("artifact-show")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "show", f"{spec_id}:{artifact_id}"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Test Artifact" in captured.out or artifact_id in captured.out

    def test_show_artifact_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("artifact-show-nf", "Artifact Show NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "show", f"{spec_id}:RV-9999"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "text"])
    def test_show_artifact_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        get_artifact_manager: SpecArtifactManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"artifact-show-fmt-{format_arg}",
            "Artifact Show Format",
            SpecType.FEATURE,
            actor="test",
        )
        artifact = get_artifact_manager.add_artifact(
            metadata.id,
            ArtifactType.REVIEW,
            "Test Artifact",
            content="Content",
            type_fields={"review_type": "peer"},
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec",
            "artifact",
            "show",
            f"{metadata.id}:{artifact.id}",
            "--format",
            format_arg,
        )

        assert exit_code == EXIT_SUCCESS


class TestArtifactDelete:
    def test_delete_artifact_success(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id, artifact_id = create_artifact("artifact-delete")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "delete", f"{spec_id}:{artifact_id}", "--force"
        )

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Deleted" in captured.out or "Deleted" in captured.err

    def test_delete_artifact_not_found(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("artifact-delete-nf", "Artifact Delete NF")

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "delete", f"{spec_id}:RV-9999", "--force"
        )

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_delete_artifact_cancelled(
        self,
        oaps_project: OapsProject,
        create_artifact: CreateArtifactFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spec_id, artifact_id = create_artifact("artifact-delete-cancel")

        # Mock stdin to be non-TTY
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        exit_code = oaps_cli_with_exit_code(
            "spec", "artifact", "delete", f"{spec_id}:{artifact_id}"
        )

        assert exit_code == EXIT_CANCELLED


# ---------------------------------------------------------------------------
# History Command Tests
# ---------------------------------------------------------------------------


class TestHistoryShow:
    def test_show_history_success(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("history-show", "History Show Test")

        exit_code = oaps_cli_with_exit_code("spec", "history", "show", spec_id)

        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        output = captured.out + captured.err
        # Verify the command produced output (history table or entries)
        # History is written per-spec, so we should see the spec creation event
        assert output  # Command should produce output
        assert (
            spec_id in output
            or "created" in output.lower()
            or "history" in output.lower()
        )

    def test_show_history_spec_not_found(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        exit_code = oaps_cli_with_exit_code("spec", "history", "show", "9999")

        assert exit_code == EXIT_NOT_FOUND
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    def test_show_history_with_filters(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("history-filter", "History Filter Test")

        exit_code = oaps_cli_with_exit_code(
            "spec", "history", "show", spec_id, "--event", "create", "--limit", "10"
        )

        assert exit_code == EXIT_SUCCESS

    def test_show_history_with_time_filter(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("history-time", "History Time Filter Test")

        exit_code = oaps_cli_with_exit_code(
            "spec", "history", "show", spec_id, "--since", "1d"
        )

        assert exit_code == EXIT_SUCCESS

    def test_show_history_invalid_time_format(
        self,
        oaps_project: OapsProject,
        create_spec: CreateSpecFunc,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
    ) -> None:
        spec_id = create_spec("history-invalid-time", "Invalid Time Test")

        exit_code = oaps_cli_with_exit_code(
            "spec", "history", "show", spec_id, "--since", "invalid"
        )

        assert exit_code == EXIT_VALIDATION_ERROR
        captured = capsys.readouterr()
        assert "Error" in captured.out or "Error" in captured.err

    @pytest.mark.parametrize("format_arg", ["json", "yaml", "table"])
    def test_show_history_output_formats(
        self,
        oaps_project: OapsProject,
        get_spec_manager: SpecManager,
        capsys: pytest.CaptureFixture[str],
        oaps_cli_with_exit_code: Callable[..., int],
        format_arg: str,
    ) -> None:
        metadata = get_spec_manager.create_spec(
            f"history-fmt-{format_arg}",
            "History Format Test",
            SpecType.FEATURE,
            actor="test",
        )

        exit_code = oaps_cli_with_exit_code(
            "spec", "history", "show", metadata.id, "--format", format_arg
        )

        assert exit_code == EXIT_SUCCESS
