"""Tests for artifact data classes and type definitions."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.artifacts._types import (
    BASE_TYPES,
    RESERVED_PREFIXES,
    Artifact,
    ArtifactMetadata,
    TypeDefinition,
    TypeField,
    ValidationError,
)


class TestTypeField:
    def test_creates_with_required_fields(self) -> None:
        field = TypeField(
            name="review_type",
            field_type="string",
            description="Type of review",
        )

        assert field.name == "review_type"
        assert field.field_type == "string"
        assert field.description == "Type of review"
        assert field.required is False
        assert field.allowed_values is None

    def test_creates_with_optional_fields(self) -> None:
        field = TypeField(
            name="severity",
            field_type="string",
            description="Severity level",
            required=True,
            allowed_values=("critical", "high", "medium", "low"),
        )

        assert field.required is True
        assert field.allowed_values == ("critical", "high", "medium", "low")

    def test_is_frozen(self) -> None:
        field = TypeField(name="test", field_type="string", description="test")

        with pytest.raises(AttributeError):
            field.name = "changed"  # pyright: ignore[reportAttributeAccessIssue]


class TestTypeDefinition:
    def test_creates_text_type(self) -> None:
        type_def = TypeDefinition(
            prefix="RV",
            name="review",
            description="Formal examination",
            category="text",
        )

        assert type_def.prefix == "RV"
        assert type_def.name == "review"
        assert type_def.category == "text"
        assert type_def.subtypes == ()
        assert type_def.type_fields == ()
        assert type_def.formats == ()
        assert type_def.template is None

    def test_creates_binary_type(self) -> None:
        type_def = TypeDefinition(
            prefix="IM",
            name="image",
            description="Visual references",
            category="binary",
            formats=("png", "jpg", "webp"),
        )

        assert type_def.category == "binary"
        assert type_def.formats == ("png", "jpg", "webp")

    def test_creates_with_subtypes(self) -> None:
        type_def = TypeDefinition(
            prefix="RV",
            name="review",
            description="Formal examination",
            category="text",
            subtypes=("design", "security", "code"),
        )

        assert type_def.subtypes == ("design", "security", "code")

    def test_creates_with_type_fields(self) -> None:
        field = TypeField(name="severity", field_type="string", description="Severity")
        type_def = TypeDefinition(
            prefix="RV",
            name="review",
            description="Formal examination",
            category="text",
            type_fields=(field,),
        )

        assert len(type_def.type_fields) == 1
        assert type_def.type_fields[0].name == "severity"

    def test_is_frozen(self) -> None:
        type_def = TypeDefinition(
            prefix="RV", name="review", description="test", category="text"
        )

        with pytest.raises(AttributeError):
            type_def.prefix = "XX"  # pyright: ignore[reportAttributeAccessIssue]


class TestArtifactMetadata:
    def test_creates_with_required_fields(self) -> None:
        now = datetime.now(UTC)
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Security Review",
            status="draft",
            created=now,
            author="reviewer",
        )

        assert metadata.id == "RV-0001"
        assert metadata.type == "review"
        assert metadata.title == "Security Review"
        assert metadata.status == "draft"
        assert metadata.created == now
        assert metadata.author == "reviewer"

    def test_optional_fields_default_to_none_or_empty(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        assert metadata.subtype is None
        assert metadata.updated is None
        assert metadata.reviewers == ()
        assert metadata.references == ()
        assert metadata.supersedes is None
        assert metadata.superseded_by is None
        assert metadata.tags == ()
        assert metadata.summary is None
        assert metadata.type_fields == {}

    def test_creates_with_all_fields(
        self, sample_metadata_full: ArtifactMetadata
    ) -> None:
        assert sample_metadata_full.subtype == "security"
        assert sample_metadata_full.reviewers == ("alice", "bob")
        assert sample_metadata_full.references == ("FR-0001", "FR-0002")
        assert sample_metadata_full.tags == ("security", "auth", "critical")
        assert sample_metadata_full.type_fields["severity"] == "high"

    def test_is_frozen(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        with pytest.raises(AttributeError):
            metadata.status = "complete"  # pyright: ignore[reportAttributeAccessIssue]


class TestArtifact:
    def test_creates_text_artifact(self, sample_artifact: Artifact) -> None:
        assert sample_artifact.id == "RV-0001"
        assert sample_artifact.type == "review"
        assert (
            sample_artifact.file_path.name
            == "20250115103000-RV-0001-security-review.md"
        )
        assert sample_artifact.metadata_file_path is None

    def test_creates_binary_artifact(self, sample_binary_artifact: Artifact) -> None:
        assert sample_binary_artifact.id == "IM-0001"
        assert sample_binary_artifact.type == "image"
        assert sample_binary_artifact.metadata_file_path is not None
        assert sample_binary_artifact.metadata_file_path.name.endswith(".metadata.yaml")

    def test_is_binary_returns_true_for_binary_artifact(
        self, sample_binary_artifact: Artifact
    ) -> None:
        assert sample_binary_artifact.is_binary is True
        assert sample_binary_artifact.is_text is False

    def test_is_text_returns_true_for_text_artifact(
        self, sample_artifact: Artifact
    ) -> None:
        assert sample_artifact.is_text is True
        assert sample_artifact.is_binary is False

    def test_prefix_extracts_from_id(self, sample_artifact: Artifact) -> None:
        assert sample_artifact.prefix == "RV"

    def test_number_extracts_from_id(self, sample_artifact: Artifact) -> None:
        assert sample_artifact.number == 1

    def test_number_extracts_larger_numbers(self, tmp_path: Path) -> None:
        artifact = Artifact(
            id="RV-0123",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            file_path=tmp_path / "test.md",
        )

        assert artifact.number == 123

    def test_is_frozen(self, sample_artifact: Artifact) -> None:
        with pytest.raises(AttributeError):
            sample_artifact.status = "complete"  # pyright: ignore[reportAttributeAccessIssue]


class TestValidationError:
    def test_creates_error(self) -> None:
        error = ValidationError(
            level="error",
            message="Missing required field: title",
            artifact_id="RV-0001",
            field="title",
        )

        assert error.level == "error"
        assert error.message == "Missing required field: title"
        assert error.artifact_id == "RV-0001"
        assert error.field == "title"

    def test_creates_warning(self) -> None:
        error = ValidationError(
            level="warning",
            message="Reference to non-existent artifact",
        )

        assert error.level == "warning"
        assert error.artifact_id is None
        assert error.field is None

    def test_is_frozen(self) -> None:
        error = ValidationError(level="error", message="test")

        with pytest.raises(AttributeError):
            error.level = "warning"  # pyright: ignore[reportAttributeAccessIssue]


class TestBaseTypes:
    def test_has_ten_base_types(self) -> None:
        assert len(BASE_TYPES) == 10

    def test_all_base_types_have_unique_prefixes(self) -> None:
        prefixes = [t.prefix for t in BASE_TYPES]
        assert len(prefixes) == len(set(prefixes))

    def test_all_base_types_have_unique_names(self) -> None:
        names = [t.name for t in BASE_TYPES]
        assert len(names) == len(set(names))

    def test_reserved_prefixes_matches_base_types(self) -> None:
        expected = frozenset(t.prefix for t in BASE_TYPES)
        assert expected == RESERVED_PREFIXES

    def test_text_types_have_template(self) -> None:
        text_types = [t for t in BASE_TYPES if t.category == "text"]
        for t in text_types:
            assert t.template is not None, f"{t.prefix} missing template"

    def test_binary_types_have_formats(self) -> None:
        binary_types = [t for t in BASE_TYPES if t.category == "binary"]
        for t in binary_types:
            assert len(t.formats) > 0, f"{t.prefix} missing formats"

    def test_review_type_configuration(self) -> None:
        review = next(t for t in BASE_TYPES if t.prefix == "RV")

        assert review.name == "review"
        assert review.category == "text"
        assert "design" in review.subtypes
        assert "security" in review.subtypes
        assert any(f.name == "review_type" and f.required for f in review.type_fields)

    def test_image_type_requires_alt_text(self) -> None:
        image = next(t for t in BASE_TYPES if t.prefix == "IM")

        alt_text_field = next(
            (f for f in image.type_fields if f.name == "alt_text"), None
        )
        assert alt_text_field is not None
        assert alt_text_field.required is True
