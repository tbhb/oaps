# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Tests for ArtifactManager operations."""

from pathlib import Path

import pytest

from oaps.exceptions import (
    SpecArtifactNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec import (
    ArtifactManager,
    ArtifactStatus,
    ArtifactType,
    SpecManager,
    SpecType,
)


def setup_spec_manager(tmp_path: Path) -> tuple[SpecManager, str]:
    """Create a SpecManager and a test spec, returning the manager and spec ID."""
    manager = SpecManager(tmp_path)
    spec = manager.create_spec(
        slug="test-spec",
        title="Test Specification",
        spec_type=SpecType.FEATURE,
        actor="test-user",
    )
    return manager, spec.id


class TestArtifactManagerInit:
    def test_accepts_spec_manager(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)
        assert manager._spec_manager is spec_manager


class TestAddArtifact:
    def test_creates_text_artifact_with_content(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        result = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Code Review Notes",
            content="## Review\n\nLooks good overall.",
            actor="test-user",
        )

        assert result.title == "Code Review Notes"
        assert result.artifact_type == ArtifactType.DECISION
        assert result.status == ArtifactStatus.DRAFT

    def test_creates_artifact_with_optional_fields(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        result = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Architecture Decision",
            content="## Decision\n\nUse microservices.",
            description="Decision about architecture",
            subtype="architecture",
            references=["REQ-0001"],
            tags=["architecture", "decision"],
            actor="test-user",
        )

        # description maps to summary in the generic artifact layer
        assert result.summary == "Decision about architecture"
        assert result.subtype == "architecture"
        assert result.references == ("REQ-0001",)
        assert result.tags == ("architecture", "decision")

    def test_generates_sequential_id(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact1 = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="First",
            content="First artifact",
            actor="test-user",
        )
        artifact2 = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Second",
            content="Second artifact",
            actor="test-user",
        )

        assert artifact1.id < artifact2.id

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.add_artifact(
                "SPEC-9999",
                artifact_type=ArtifactType.DECISION,
                title="Test",
                content="Content",
                actor="test-user",
            )

    def test_raises_when_both_content_and_source_provided(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        source_path = tmp_path / "source.md"
        source_path.write_text("Source content")

        with pytest.raises(SpecValidationError, match="both content and source_path"):
            manager.add_artifact(
                spec_id,
                artifact_type=ArtifactType.DECISION,
                title="Test",
                content="Content",
                source_path=str(source_path),
                actor="test-user",
            )

    def test_raises_when_neither_content_nor_source_provided(
        self, tmp_path: Path
    ) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecValidationError, match="either content or source_path"):
            manager.add_artifact(
                spec_id,
                artifact_type=ArtifactType.DECISION,
                title="Test",
                actor="test-user",
            )

    def test_imports_artifact_from_source_file(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        source_content = "# Source Document\n\nThis is imported content."
        source_path = tmp_path / "source.md"
        source_path.write_text(source_content)

        result = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.ANALYSIS,
            title="Imported Analysis",
            source_path=str(source_path),
            actor="test-user",
        )

        assert result.title == "Imported Analysis"
        assert result.artifact_type == ArtifactType.ANALYSIS

    def test_raises_for_nonexistent_source_file(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecValidationError, match="Source file not found"):
            manager.add_artifact(
                spec_id,
                artifact_type=ArtifactType.ANALYSIS,
                title="Missing Source",
                source_path=str(tmp_path / "nonexistent.md"),
                actor="test-user",
            )


class TestListArtifacts:
    def test_returns_empty_list_when_no_artifacts(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        result = manager.list_artifacts(spec_id)
        assert result == []

    def test_returns_all_artifacts(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="First",
            content="First artifact",
            actor="test-user",
        )
        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.ANALYSIS,
            title="Second",
            content="Second artifact",
            actor="test-user",
        )

        result = manager.list_artifacts(spec_id)
        assert len(result) == 2

    def test_filters_by_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Decision",
            content="Decision content",
            actor="test-user",
        )
        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.ANALYSIS,
            title="Analysis",
            content="Analysis content",
            actor="test-user",
        )

        result = manager.list_artifacts(spec_id, filter_type=ArtifactType.DECISION)
        assert len(result) == 1
        assert result[0].artifact_type == ArtifactType.DECISION

    def test_filters_by_status(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Complete Decision",
            content="Complete content",
            actor="test-user",
        )
        manager.update_artifact(
            spec_id, artifact.id, status=ArtifactStatus.COMPLETE, actor="test-user"
        )
        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Draft Decision",
            content="Draft content",
            actor="test-user",
        )

        result = manager.list_artifacts(spec_id, filter_status=ArtifactStatus.COMPLETE)
        assert len(result) == 1
        assert result[0].status == ArtifactStatus.COMPLETE

    def test_filters_by_tags(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Tagged",
            content="Content",
            tags=["important", "api"],
            actor="test-user",
        )
        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Other",
            content="Content",
            tags=["other"],
            actor="test-user",
        )

        result = manager.list_artifacts(spec_id, filter_tags=["important"])
        assert len(result) == 1
        assert "important" in result[0].tags

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.list_artifacts("SPEC-9999")


class TestGetArtifact:
    def test_returns_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        created = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test Artifact",
            content="Content",
            actor="test-user",
        )

        result = manager.get_artifact(spec_id, created.id)
        assert result.id == created.id
        assert result.title == "Test Artifact"

    def test_raises_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecArtifactNotFoundError):
            manager.get_artifact(spec_id, "DC-9999")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.get_artifact("SPEC-9999", "DC-0001")


class TestArtifactExists:
    def test_returns_true_for_existing_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            actor="test-user",
        )

        assert manager.artifact_exists(spec_id, artifact.id) is True

    def test_returns_false_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        assert manager.artifact_exists(spec_id, "DC-9999") is False

    def test_returns_false_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        assert manager.artifact_exists("SPEC-9999", "DC-0001") is False


class TestGetArtifactContent:
    def test_returns_content(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="## Decision\n\nThis is the content.",
            actor="test-user",
        )

        content = manager.get_artifact_content(spec_id, artifact.id)
        assert "## Decision" in content
        assert "This is the content." in content

    def test_raises_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecArtifactNotFoundError):
            manager.get_artifact_content(spec_id, "DC-9999")


class TestUpdateArtifact:
    def test_updates_title(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Original",
            content="Content",
            actor="test-user",
        )

        result = manager.update_artifact(
            spec_id, artifact.id, title="Updated", actor="test-user"
        )

        assert result.title == "Updated"

    def test_updates_status(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            actor="test-user",
        )

        result = manager.update_artifact(
            spec_id, artifact.id, status=ArtifactStatus.COMPLETE, actor="test-user"
        )

        assert result.status == ArtifactStatus.COMPLETE

    def test_updates_summary(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            actor="test-user",
        )

        # description param maps to summary in generic layer
        result = manager.update_artifact(
            spec_id,
            artifact.id,
            description="Updated summary",
            actor="test-user",
        )

        assert result.summary == "Updated summary"

    def test_updates_tags(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            tags=["old"],
            actor="test-user",
        )

        result = manager.update_artifact(
            spec_id, artifact.id, tags=["new", "tags"], actor="test-user"
        )

        assert result.tags == ("new", "tags")

    def test_updates_references(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            actor="test-user",
        )

        result = manager.update_artifact(
            spec_id,
            artifact.id,
            references=["REQ-0001", "REQ-0002"],
            actor="test-user",
        )

        assert result.references == ("REQ-0001", "REQ-0002")

    def test_preserves_unmodified_fields(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Original",
            content="Content",
            description="Original summary",
            actor="test-user",
        )

        result = manager.update_artifact(
            spec_id, artifact.id, title="Updated", actor="test-user"
        )

        assert result.title == "Updated"
        # description maps to summary in generic layer
        assert result.summary == "Original summary"

    def test_raises_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecArtifactNotFoundError):
            manager.update_artifact(
                spec_id, "DC-9999", title="Updated", actor="test-user"
            )

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.update_artifact(
                "SPEC-9999", "DC-0001", title="Updated", actor="test-user"
            )


class TestUpdateArtifactContent:
    def test_updates_content(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Original content",
            actor="test-user",
        )

        manager.update_artifact_content(
            spec_id, artifact.id, content="Updated content", actor="test-user"
        )

        content = manager.get_artifact_content(spec_id, artifact.id)
        assert "Updated content" in content

    def test_raises_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecArtifactNotFoundError):
            manager.update_artifact_content(
                spec_id, "DC-9999", content="Content", actor="test-user"
            )


class TestDeleteArtifact:
    def test_removes_artifact_from_listing(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="To delete",
            content="Will be deleted",
            actor="test-user",
        )

        manager.delete_artifact(spec_id, artifact.id, actor="test-user")

        assert manager.artifact_exists(spec_id, artifact.id) is False

    def test_raises_for_nonexistent_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecArtifactNotFoundError):
            manager.delete_artifact(spec_id, "DC-9999", actor="test-user")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.delete_artifact("SPEC-9999", "DC-0001", actor="test-user")


class TestSupersedeArtifact:
    def test_supersedes_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        old = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Old Decision",
            content="Old content",
            actor="test-user",
        )
        new = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="New Decision",
            content="New content",
            actor="test-user",
        )

        old_result, _new_result = manager.supersede_artifact(
            spec_id, old.id, new.id, actor="test-user"
        )

        assert old_result.status == ArtifactStatus.SUPERSEDED
        assert old_result.superseded_by == new.id

    def test_raises_for_nonexistent_old_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        new = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="New",
            content="Content",
            actor="test-user",
        )

        with pytest.raises(SpecArtifactNotFoundError):
            manager.supersede_artifact(spec_id, "DC-9999", new.id, actor="test-user")

    def test_raises_for_nonexistent_new_artifact(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        old = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Old",
            content="Content",
            actor="test-user",
        )

        with pytest.raises(SpecArtifactNotFoundError):
            manager.supersede_artifact(spec_id, old.id, "DC-9999", actor="test-user")


class TestArtifactTypes:
    def test_supports_review_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.REVIEW,
            title="Review",
            content="Content",
            type_fields={"review_type": "design"},
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.REVIEW

    def test_supports_decision_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Decision",
            content="Content",
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.DECISION

    def test_supports_change_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.CHANGE,
            title="Change",
            content="Content",
            type_fields={"change_type": "erratum"},
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.CHANGE

    def test_supports_analysis_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.ANALYSIS,
            title="Analysis",
            content="Content",
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.ANALYSIS

    def test_supports_diagram_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DIAGRAM,
            title="Diagram",
            content="```mermaid\ngraph TD;\nA-->B;\n```",
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.DIAGRAM

    def test_supports_example_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        artifact = manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.EXAMPLE,
            title="Example",
            content="Content",
            actor="test-user",
        )
        assert artifact.artifact_type == ArtifactType.EXAMPLE


class TestRebuildIndex:
    def test_rebuilds_artifacts_index(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        manager.add_artifact(
            spec_id,
            artifact_type=ArtifactType.DECISION,
            title="Test",
            content="Content",
            actor="test-user",
        )

        result = manager.rebuild_index(spec_id, actor="test-user")

        assert result.indexed >= 1

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = ArtifactManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.rebuild_index("SPEC-9999", actor="test-user")
