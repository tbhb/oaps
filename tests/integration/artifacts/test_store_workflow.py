"""Integration tests for full artifact store workflows.

These tests verify end-to-end workflows including filesystem operations,
index management, and artifact lifecycle operations.
"""

import json
from pathlib import Path

import pytest

from oaps.artifacts._store import ArtifactStore


class TestStoreInitialization:
    def test_initializes_directory_structure(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        store.initialize()

        assert (tmp_path / "artifacts").is_dir()
        assert (tmp_path / "artifacts.json").exists()

        # Verify index structure
        data = json.loads((tmp_path / "artifacts.json").read_text())
        assert "updated" in data
        assert "artifacts" in data
        assert data["artifacts"] == []


class TestTextArtifactWorkflow:
    def test_creates_markdown_with_frontmatter(self, store: ArtifactStore) -> None:
        artifact = store.add_artifact(
            type_prefix="DC",
            title="Architecture Decision",
            author="architect",
            content="# Decision\n\nWe chose option A.",
            tags=["architecture"],
        )

        content = artifact.file_path.read_text(encoding="utf-8")

        assert content.startswith("---\n")
        assert "id: DC-0001" in content
        assert "type: decision" in content
        assert "title: Architecture Decision" in content
        assert "author: architect" in content
        assert "tags:" in content
        assert "# Decision" in content

    def test_preserves_body_on_update(self, store: ArtifactStore) -> None:
        original_body = "# Decision\n\nOriginal content that should be preserved."
        store.add_artifact(
            type_prefix="DC",
            title="Decision",
            author="dev",
            content=original_body,
        )

        # Update metadata only
        store.update_artifact("DC-0001", title="Updated Title")

        content = store.get_artifact_content("DC-0001")
        assert content is not None
        assert isinstance(content, str)
        assert original_body in content

    def test_updates_body_when_content_provided(self, store: ArtifactStore) -> None:
        store.add_artifact(
            type_prefix="DC",
            title="Decision",
            author="dev",
            content="# Original",
        )

        store.update_artifact("DC-0001", content="# Updated Body")

        content = store.get_artifact_content("DC-0001")
        assert content is not None
        assert isinstance(content, str)
        assert "# Updated Body" in content
        assert "# Original" not in content


class TestBinaryArtifactWorkflow:
    def test_creates_sidecar_metadata(self, store: ArtifactStore) -> None:
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
        artifact = store.add_artifact(
            type_prefix="IM",
            title="Screenshot",
            author="dev",
            content=binary_data,
            type_fields={"alt_text": "Error screenshot"},
        )

        # Verify binary file
        assert artifact.file_path.read_bytes() == binary_data

        # Verify sidecar metadata
        assert artifact.metadata_file_path is not None
        assert artifact.metadata_file_path.exists()
        sidecar_content = artifact.metadata_file_path.read_text()
        assert "id: IM-0001" in sidecar_content
        assert "alt_text: Error screenshot" in sidecar_content

    def test_updates_sidecar_metadata(self, store: ArtifactStore) -> None:
        store.add_artifact(
            type_prefix="IM",
            title="Screenshot",
            author="dev",
            content=b"binary",
            type_fields={"alt_text": "Original alt text"},
        )

        store.update_artifact(
            "IM-0001",
            title="Updated Screenshot",
            type_fields={"alt_text": "Updated alt text"},
        )

        artifact = store.get_artifact("IM-0001")
        assert artifact is not None
        assert artifact.metadata_file_path is not None

        sidecar_content = artifact.metadata_file_path.read_text()
        assert "title: Updated Screenshot" in sidecar_content
        assert "alt_text: Updated alt text" in sidecar_content


class TestSequentialNumbering:
    def test_assigns_sequential_numbers_per_type(self, store: ArtifactStore) -> None:
        a1 = store.add_artifact(type_prefix="DC", title="D1", author="dev")
        a2 = store.add_artifact(type_prefix="DC", title="D2", author="dev")
        a3 = store.add_artifact(type_prefix="AN", title="A1", author="dev")
        a4 = store.add_artifact(type_prefix="DC", title="D3", author="dev")

        assert a1.id == "DC-0001"
        assert a2.id == "DC-0002"
        assert a3.id == "AN-0001"
        assert a4.id == "DC-0003"

    def test_continues_numbering_after_deletion(self, store: ArtifactStore) -> None:
        store.add_artifact(type_prefix="DC", title="D1", author="dev")
        store.add_artifact(type_prefix="DC", title="D2", author="dev")
        store.delete_artifact("DC-0001", force=True)

        # Next artifact should be DC-0003, not DC-0001
        a3 = store.add_artifact(type_prefix="DC", title="D3", author="dev")
        assert a3.id == "DC-0003"


class TestIndexIntegration:
    def test_index_reflects_additions(self, store: ArtifactStore) -> None:
        store.add_artifact(type_prefix="DC", title="Decision 1", author="dev")
        store.add_artifact(type_prefix="DC", title="Decision 2", author="dev")

        index = store.get_index()
        assert index.count == 2
        assert index.contains("DC-0001")
        assert index.contains("DC-0002")

    def test_index_reflects_deletions(self, store: ArtifactStore) -> None:
        store.add_artifact(type_prefix="DC", title="Decision", author="dev")
        assert store.get_index().count == 1

        store.delete_artifact("DC-0001", force=True)
        assert store.get_index().count == 0

    def test_index_reflects_updates(self, store: ArtifactStore) -> None:
        store.add_artifact(
            type_prefix="DC",
            title="Original Title",
            author="dev",
        )
        store.update_artifact("DC-0001", title="Updated Title", status="complete")

        index = store.get_index()
        summary = index.get("DC-0001")
        assert summary is not None
        assert summary["title"] == "Updated Title"
        assert summary["status"] == "complete"

    def test_rebuild_from_filesystem(self, store: ArtifactStore) -> None:
        store.add_artifact(type_prefix="DC", title="D1", author="dev")
        store.add_artifact(type_prefix="DC", title="D2", author="dev")

        # Corrupt the index
        store._write_index([])
        assert store.get_index().count == 0

        # Rebuild should restore it
        store.rebuild_index()
        index = store.get_index()
        assert index.count == 2


class TestSupersessionWorkflow:
    def test_complete_supersession_workflow(self, store: ArtifactStore) -> None:
        # Create original decision
        store.add_artifact(
            type_prefix="DC",
            title="Original Architecture Decision",
            author="architect",
            content="# Decision v1",
        )

        # Create updated decision
        store.add_artifact(
            type_prefix="DC",
            title="Updated Architecture Decision",
            author="architect",
            content="# Decision v2",
        )

        # Supersede
        old, new = store.supersede_artifact("DC-0001", "DC-0002")

        # Verify old artifact
        assert old.status == "superseded"
        assert old.superseded_by == "DC-0002"

        # Verify new artifact
        assert new.supersedes == "DC-0001"

        # Verify persistence
        old_from_store = store.get_artifact("DC-0001")
        assert old_from_store is not None
        assert old_from_store.status == "superseded"
        assert old_from_store.superseded_by == "DC-0002"

    def test_supersession_bidirectional_references_persist(
        self, store: ArtifactStore
    ) -> None:
        store.add_artifact(type_prefix="DC", title="D1", author="dev")
        store.add_artifact(type_prefix="DC", title="D2", author="dev")

        store.supersede_artifact("DC-0001", "DC-0002")

        # Both artifacts should have references persisted
        content1 = store.get_artifact_content("DC-0001")
        content2 = store.get_artifact_content("DC-0002")

        assert content1 is not None
        assert isinstance(content1, str)
        assert content2 is not None
        assert isinstance(content2, str)
        assert "superseded_by: DC-0002" in content1
        assert "supersedes: DC-0001" in content2


class TestRetractionWorkflow:
    def test_retraction_preserves_file(self, store: ArtifactStore) -> None:
        artifact = store.add_artifact(
            type_prefix="DC",
            title="Decision",
            author="dev",
            content="# Decision Content",
        )
        file_path = artifact.file_path

        store.retract_artifact("DC-0001", reason="Outdated information")

        # File should still exist
        assert file_path.exists()

        # Content should be preserved
        content = store.get_artifact_content("DC-0001")
        assert content is not None
        assert isinstance(content, str)
        assert "# Decision Content" in content

        # Status should be updated
        retracted = store.get_artifact("DC-0001")
        assert retracted is not None
        assert retracted.status == "retracted"

    def test_retraction_reason_persisted(self, store: ArtifactStore) -> None:
        store.add_artifact(type_prefix="DC", title="Decision", author="dev")

        store.retract_artifact("DC-0001", reason="No longer applicable")

        content = store.get_artifact_content("DC-0001")
        assert content is not None
        assert isinstance(content, str)
        assert "retraction_reason: No longer applicable" in content


class TestReferenceProtection:
    def test_prevents_deletion_of_referenced_artifact(
        self, store: ArtifactStore
    ) -> None:
        store.add_artifact(type_prefix="DC", title="Decision", author="dev")
        store.add_artifact(
            type_prefix="AN",
            title="Analysis",
            author="dev",
            references=["DC-0001"],
        )

        with pytest.raises(ValueError, match="referenced by"):
            store.delete_artifact("DC-0001")

    def test_force_deletion_bypasses_reference_check(
        self, store: ArtifactStore
    ) -> None:
        store.add_artifact(type_prefix="DC", title="Decision", author="dev")
        store.add_artifact(
            type_prefix="AN",
            title="Analysis",
            author="dev",
            references=["DC-0001"],
        )

        # Should not raise with force=True
        store.delete_artifact("DC-0001", force=True)
        assert not store.artifact_exists("DC-0001")


class TestFileImport:
    def test_imports_existing_binary_file(
        self, store: ArtifactStore, tmp_path: Path
    ) -> None:
        # Create an existing file
        source_file = tmp_path / "existing_image.png"
        binary_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00IHDR"
        source_file.write_bytes(binary_content)

        artifact = store.add_artifact(
            type_prefix="IM",
            title="Imported Image",
            author="dev",
            file_path=source_file,
            type_fields={"alt_text": "Imported image"},
        )

        # Verify content was copied
        assert artifact.file_path.read_bytes() == binary_content
        # Verify extension was preserved
        assert artifact.file_path.suffix == ".png"


class TestFilteringWorkflows:
    def test_filters_by_multiple_criteria(self, populated_store: ArtifactStore) -> None:
        # Filter by type and author
        decisions = populated_store.list_artifacts(type_filter="DC")
        assert len(decisions) == 2

        # All should be decisions
        assert all(a.type == "decision" for a in decisions)

    def test_filters_by_status(self, populated_store: ArtifactStore) -> None:
        # Update one artifact to complete
        populated_store.update_artifact("DC-0001", status="complete")

        drafts = populated_store.list_artifacts(status_filter="draft")
        complete = populated_store.list_artifacts(status_filter="complete")

        # DC-0002, AN-0001, IM-0001 are drafts
        assert len(drafts) == 3
        # Only DC-0001 is complete
        assert len(complete) == 1
        assert complete[0].id == "DC-0001"

    def test_filters_by_tags(self, populated_store: ArtifactStore) -> None:
        tagged = populated_store.list_artifacts(tag_filter="architecture")

        assert len(tagged) == 1
        assert tagged[0].id == "DC-0001"
