"""Tests for artifact index functionality."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.artifacts._index import ArtifactIndex


@pytest.fixture
def sample_index_data() -> dict[str, object]:
    """Sample index data for testing."""
    return {
        "updated": "2025-01-15T10:30:00+00:00",
        "artifacts": [
            {
                "id": "RV-0001",
                "type": "review",
                "title": "Security Review",
                "status": "complete",
                "created": "2025-01-10T10:00:00+00:00",
                "author": "alice",
                "file_path": "artifacts/20250110-RV-0001-security-review.md",
                "tags": ["security", "critical"],
                "references": ["FR-0001"],
            },
            {
                "id": "RV-0002",
                "type": "review",
                "title": "Code Review",
                "status": "draft",
                "created": "2025-01-12T14:00:00+00:00",
                "author": "bob",
                "file_path": "artifacts/20250112-RV-0002-code-review.md",
                "tags": ["code"],
            },
            {
                "id": "DC-0001",
                "type": "decision",
                "title": "Architecture Decision",
                "status": "complete",
                "created": "2025-01-15T09:00:00+00:00",
                "author": "alice",
                "file_path": "artifacts/20250115-DC-0001-architecture-decision.md",
                "references": ["RV-0001"],
            },
        ],
    }


@pytest.fixture
def index_file(tmp_path: Path, sample_index_data: dict[str, object]) -> Path:
    """Create index file with sample data."""
    index_path = tmp_path / "artifacts.json"
    index_path.write_text(json.dumps(sample_index_data))
    return index_path


class TestIndexLoading:
    def test_loads_from_file(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.count == 3

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        index = ArtifactIndex(tmp_path / "nonexistent.json")

        assert index.count == 0

    def test_handles_invalid_json(self, tmp_path: Path) -> None:
        index_path = tmp_path / "invalid.json"
        index_path.write_text("not valid json")

        index = ArtifactIndex(index_path)

        assert index.count == 0

    def test_handles_non_dict_json(self, tmp_path: Path) -> None:
        index_path = tmp_path / "invalid.json"
        index_path.write_text(json.dumps(["not", "a", "dict"]))

        index = ArtifactIndex(index_path)

        assert index.count == 0

    def test_handles_non_list_artifacts(self, tmp_path: Path) -> None:
        index_path = tmp_path / "invalid.json"
        index_path.write_text(json.dumps({"artifacts": "not a list"}))

        index = ArtifactIndex(index_path)

        assert index.count == 0


class TestUpdatedProperty:
    def test_returns_parsed_timestamp(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.updated == datetime(2025, 1, 15, 10, 30, tzinfo=UTC)

    def test_defaults_to_now_for_invalid_timestamp(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"updated": "invalid", "artifacts": []}))

        index = ArtifactIndex(index_path)

        # Should default to a recent time
        assert (datetime.now(UTC) - index.updated).total_seconds() < 10


class TestGet:
    def test_returns_artifact_summary(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        summary = index.get("RV-0001")

        assert summary is not None
        assert summary["id"] == "RV-0001"
        assert summary["title"] == "Security Review"

    def test_returns_none_for_nonexistent(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.get("XX-9999") is None


class TestContains:
    def test_returns_true_for_existing(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.contains("RV-0001") is True

    def test_returns_false_for_nonexistent(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.contains("XX-9999") is False


class TestAllIds:
    def test_returns_all_ids_sorted(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        ids = index.all_ids()

        assert ids == ["DC-0001", "RV-0001", "RV-0002"]


class TestFilter:
    def test_filters_by_type(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(type_filter="RV")

        assert len(results) == 2
        assert all(r["id"].startswith("RV") for r in results)

    def test_filters_by_type_name(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(type_filter="review")

        assert len(results) == 2

    def test_filters_by_status(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(status_filter="complete")

        assert len(results) == 2
        assert all(r["status"] == "complete" for r in results)

    def test_filters_by_author(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(author_filter="alice")

        assert len(results) == 2
        assert all(r["author"] == "alice" for r in results)

    def test_filters_by_tag(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(tag_filter="security")

        assert len(results) == 1
        assert results[0]["id"] == "RV-0001"

    def test_filters_by_created_after(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(created_after=datetime(2025, 1, 12, 0, 0, tzinfo=UTC))

        assert len(results) == 2
        assert "RV-0001" not in [r["id"] for r in results]

    def test_filters_by_created_before(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(created_before=datetime(2025, 1, 12, 0, 0, tzinfo=UTC))

        assert len(results) == 1
        assert results[0]["id"] == "RV-0001"

    def test_combines_multiple_filters(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(
            type_filter="review",
            status_filter="complete",
            author_filter="alice",
        )

        assert len(results) == 1
        assert results[0]["id"] == "RV-0001"

    def test_returns_empty_for_no_matches(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.filter(type_filter="XX")

        assert results == []


class TestGetByType:
    def test_returns_artifacts_of_type(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.get_by_type("RV")

        assert len(results) == 2

    def test_returns_empty_for_unknown_type(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        results = index.get_by_type("XX")

        assert results == []


class TestGetNextNumber:
    def test_returns_next_sequential_number(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.get_next_number("RV") == 3
        assert index.get_next_number("DC") == 2

    def test_returns_one_for_new_type(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)

        assert index.get_next_number("AN") == 1


class TestGetReferencesTo:
    def test_returns_referencing_artifacts(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        refs = index.get_references_to("FR-0001")

        assert refs == ["RV-0001"]

    def test_returns_multiple_references(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        refs = index.get_references_to("RV-0001")

        assert refs == ["DC-0001"]

    def test_returns_empty_for_no_references(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        refs = index.get_references_to("XX-9999")

        assert refs == []


class TestToDict:
    def test_serializes_to_dict(self, index_file: Path) -> None:
        index = ArtifactIndex(index_file)
        data = index.to_dict()

        assert "updated" in data
        assert "artifacts" in data
        assert len(data["artifacts"]) == 3


class TestFromArtifacts:
    def test_creates_from_list(self) -> None:
        artifacts = [
            {"id": "RV-0001", "type": "review", "title": "Test"},
            {"id": "DC-0001", "type": "decision", "title": "Test 2"},
        ]

        index = ArtifactIndex.from_artifacts(artifacts)

        assert index.count == 2
        assert index.contains("RV-0001")
        assert index.contains("DC-0001")

    def test_builds_indexes(self) -> None:
        artifacts = [
            {"id": "RV-0001", "references": ["DC-0001"]},
            {"id": "RV-0002", "references": ["DC-0001"]},
            {"id": "DC-0001"},
        ]

        index = ArtifactIndex.from_artifacts(artifacts)

        assert len(index.get_by_type("RV")) == 2
        assert index.get_references_to("DC-0001") == ["RV-0001", "RV-0002"]

    def test_skips_invalid_entries(self) -> None:
        artifacts = [
            {"id": "RV-0001", "type": "review"},
            "not a dict",
            {"no_id": "field"},
            {"id": 123},  # Non-string ID
        ]

        index = ArtifactIndex.from_artifacts(artifacts)  # pyright: ignore[reportArgumentType]

        assert index.count == 1

    def test_accepts_custom_path(self, tmp_path: Path) -> None:
        index = ArtifactIndex.from_artifacts([], index_path=tmp_path / "custom.json")

        assert index._index_path == tmp_path / "custom.json"


class TestFilterEdgeCases:
    def test_skips_artifact_with_missing_created(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {
                            "id": "RV-0001",
                            "type": "review",
                            "title": "No Created Field",
                            "status": "draft",
                            "author": "alice",
                        }
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Filtering by date should skip artifacts without created field
        results = index.filter(created_after=datetime(2025, 1, 1, tzinfo=UTC))

        assert len(results) == 0

    def test_skips_artifact_with_invalid_created(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {
                            "id": "RV-0001",
                            "type": "review",
                            "title": "Invalid Created",
                            "status": "draft",
                            "author": "alice",
                            "created": "not-a-date",
                        }
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Filtering by date should skip artifacts with invalid created field
        results = index.filter(created_after=datetime(2025, 1, 1, tzinfo=UTC))

        assert len(results) == 0


class TestGetNextNumberEdgeCases:
    def test_handles_artifact_id_without_hyphen(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [{"id": "INVALID"}],  # No hyphen
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Should return 1 since no valid number could be extracted
        assert index.get_next_number("RV") == 1

    def test_handles_artifact_id_with_invalid_number(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [{"id": "RV-XXXX"}],  # Non-numeric
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Should return 1 since number parsing failed
        assert index.get_next_number("RV") == 1


class TestLoadingEdgeCases:
    def test_skips_non_dict_artifact_entry(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {"id": "RV-0001", "type": "review"},
                        "not a dict",  # Should be skipped
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        assert index.count == 1

    def test_skips_artifact_without_id(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {"id": "RV-0001", "type": "review"},
                        {"type": "review", "title": "No ID"},  # No id field
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        assert index.count == 1

    def test_skips_artifact_with_non_string_id(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {"id": "RV-0001", "type": "review"},
                        {"id": 12345, "type": "review"},  # Numeric id
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        assert index.count == 1

    def test_handles_non_list_references(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {
                            "id": "RV-0001",
                            "type": "review",
                            "references": "not-a-list",  # Should be skipped
                        },
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Should not crash and should have zero references
        refs = index.get_references_to("XX-0001")
        assert refs == []

    def test_handles_non_string_reference(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.json"
        index_path.write_text(
            json.dumps(
                {
                    "updated": "2025-01-15T10:30:00+00:00",
                    "artifacts": [
                        {
                            "id": "RV-0001",
                            "type": "review",
                            "references": [123, "DC-0001"],  # Mixed types
                        },
                    ],
                }
            )
        )
        index = ArtifactIndex(index_path)

        # Only the valid string reference should be indexed
        refs = index.get_references_to("DC-0001")
        assert refs == ["RV-0001"]
        # Numeric reference should not be indexed
        refs_to_123 = index.get_references_to(123)  # pyright: ignore[reportArgumentType]
        assert refs_to_123 == []
