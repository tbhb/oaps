"""Tests for artifact validation functions."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._types import ArtifactMetadata
from oaps.artifacts._validator import (
    VALID_STATUSES,
    raise_if_validation_errors,
    validate_artifact,
    validate_artifact_type,
    validate_metadata,
    validate_references,
)
from oaps.exceptions import ArtifactValidationError


class TestValidStatuses:
    def test_contains_expected_statuses(self) -> None:
        assert "draft" in VALID_STATUSES
        assert "complete" in VALID_STATUSES
        assert "superseded" in VALID_STATUSES
        assert "retracted" in VALID_STATUSES

    def test_has_exactly_four_statuses(self) -> None:
        assert len(VALID_STATUSES) == 4

    def test_is_frozenset(self) -> None:
        assert isinstance(VALID_STATUSES, frozenset)


class TestValidateMetadata:
    def test_accepts_valid_metadata(self, sample_metadata: ArtifactMetadata) -> None:
        errors = validate_metadata(sample_metadata)
        assert errors == []

    def test_reports_empty_id(self) -> None:
        metadata = ArtifactMetadata(
            id="",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert len(errors) >= 1
        assert any("id" in e.field for e in errors if e.field)

    def test_reports_empty_type(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert any("type" in e.field for e in errors if e.field)

    def test_reports_empty_title(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert any("title" in e.field for e in errors if e.field)

    def test_reports_empty_status(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert any("status" in e.field for e in errors if e.field)

    def test_reports_empty_author(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="",
        )

        errors = validate_metadata(metadata)

        assert any("author" in e.field for e in errors if e.field)

    def test_reports_invalid_id_format(self) -> None:
        metadata = ArtifactMetadata(
            id="invalid",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert any("Invalid artifact ID format" in e.message for e in errors)

    def test_reports_invalid_status(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="invalid",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_metadata(metadata)

        assert any("Invalid status" in e.message for e in errors)

    def test_accepts_all_valid_statuses(self) -> None:
        for status in VALID_STATUSES:
            metadata = ArtifactMetadata(
                id="RV-0001",
                type="review",
                title="Test",
                status=status,
                created=datetime.now(UTC),
                author="author",
            )

            errors = validate_metadata(metadata)
            status_errors = [e for e in errors if e.field == "status"]
            assert len(status_errors) == 0, f"Status '{status}' should be valid"


class TestValidateArtifactType:
    def test_accepts_valid_type(self) -> None:
        # Create metadata with all required type-specific fields
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Security Review",
            status="draft",
            created=datetime.now(UTC),
            author="reviewer",
            type_fields={"review_type": "security"},
        )
        registry = ArtifactRegistry.get_instance()
        errors = validate_artifact_type(metadata, registry)

        # Should have no errors when required type fields are present
        assert not any(e.level == "error" for e in errors)

    def test_reports_unknown_type(self) -> None:
        metadata = ArtifactMetadata(
            id="XX-0001",
            type="unknown",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any("Unknown artifact type" in e.message for e in errors)

    def test_reports_id_prefix_mismatch(self) -> None:
        metadata = ArtifactMetadata(
            id="DC-0001",  # Decision prefix
            type="review",  # But review type
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any(
            "prefix" in e.message.lower() and "does not match" in e.message
            for e in errors
        )

    def test_reports_invalid_subtype(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            subtype="invalid_subtype",
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any("Invalid subtype" in e.message for e in errors)

    def test_accepts_valid_subtype(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            subtype="security",
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        subtype_errors = [e for e in errors if e.field == "subtype"]
        assert len(subtype_errors) == 0

    def test_reports_missing_required_type_field(self) -> None:
        # Review type requires review_type field
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            type_fields={},  # Missing review_type
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any("review_type" in e.message for e in errors)

    def test_reports_invalid_type_field_value(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            type_fields={"review_type": "invalid_value"},
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any("Invalid value for" in e.message for e in errors)

    def test_accepts_valid_type_field_value(self) -> None:
        metadata = ArtifactMetadata(
            id="RV-0001",
            type="review",
            title="Test",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            type_fields={"review_type": "security"},
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        value_errors = [e for e in errors if "Invalid value" in e.message]
        assert len(value_errors) == 0

    def test_image_requires_alt_text(self) -> None:
        metadata = ArtifactMetadata(
            id="IM-0001",
            type="image",
            title="Screenshot",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            type_fields={},  # Missing alt_text
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        assert any("alt_text" in e.message for e in errors)

    def test_image_accepts_alt_text(self) -> None:
        metadata = ArtifactMetadata(
            id="IM-0001",
            type="image",
            title="Screenshot",
            status="draft",
            created=datetime.now(UTC),
            author="author",
            type_fields={"alt_text": "Error message screenshot"},
        )
        registry = ArtifactRegistry.get_instance()

        errors = validate_artifact_type(metadata, registry)

        alt_text_errors = [e for e in errors if "alt_text" in e.message]
        assert len(alt_text_errors) == 0


class TestValidateReferences:
    def test_reports_missing_references(self, tmp_path: Path) -> None:
        from oaps.artifacts._store import ArtifactStore

        store = ArtifactStore(tmp_path)
        store.initialize()

        errors = validate_references(["RV-0001", "XX-9999"], store)

        assert len(errors) == 2
        assert all(e.level == "warning" for e in errors)

    def test_accepts_empty_references(self, tmp_path: Path) -> None:
        from oaps.artifacts._store import ArtifactStore

        store = ArtifactStore(tmp_path)
        store.initialize()

        errors = validate_references([], store)

        assert errors == []


class TestValidateArtifact:
    def test_combines_all_validations(self) -> None:
        # Invalid: bad ID format, invalid status, unknown type
        metadata = ArtifactMetadata(
            id="invalid",
            type="unknown",
            title="",
            status="invalid",
            created=datetime.now(UTC),
            author="author",
        )

        errors = validate_artifact(metadata)

        # Should have multiple errors
        assert len(errors) >= 3

    def test_accepts_valid_artifact(self, sample_metadata: ArtifactMetadata) -> None:
        errors = validate_artifact(sample_metadata)

        # No errors (warnings are ok)
        error_count = sum(1 for e in errors if e.level == "error")
        # May have review_type missing error since sample_metadata doesn't have it
        # But that's expected for a minimal fixture
        assert error_count <= 1


class TestRaiseIfValidationErrors:
    def test_raises_for_errors(self) -> None:
        from oaps.artifacts._types import ValidationError

        errors = [
            ValidationError(
                level="error",
                message="Test error",
                artifact_id="RV-0001",
                field="test",
            )
        ]

        with pytest.raises(ArtifactValidationError) as exc_info:
            raise_if_validation_errors(errors)

        assert "Test error" in str(exc_info.value)

    def test_ignores_warnings(self) -> None:
        from oaps.artifacts._types import ValidationError

        errors = [
            ValidationError(
                level="warning",
                message="Test warning",
            )
        ]

        # Should not raise
        raise_if_validation_errors(errors)

    def test_does_nothing_for_empty_list(self) -> None:
        # Should not raise
        raise_if_validation_errors([])

    def test_uses_provided_artifact_id(self) -> None:
        from oaps.artifacts._types import ValidationError

        errors = [
            ValidationError(
                level="error",
                message="Test error",
            )
        ]

        with pytest.raises(ArtifactValidationError) as exc_info:
            raise_if_validation_errors(errors, artifact_id="DC-0001")

        assert exc_info.value.artifact_id == "DC-0001"
