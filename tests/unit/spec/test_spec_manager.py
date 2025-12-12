# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Tests for SpecManager operations."""

from pathlib import Path

import pytest

from oaps.exceptions import (
    CircularDependencyError,
    DuplicateIdError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec import SpecManager, SpecStatus, SpecType


class TestSpecManagerInit:
    def test_accepts_path_string(self, tmp_path: Path) -> None:
        manager = SpecManager(str(tmp_path))
        assert manager.base_path == tmp_path

    def test_accepts_path_object(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)
        assert manager.base_path == tmp_path

    def test_index_path_is_correct(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)
        assert manager.index_path.name == "index.json"

    def test_history_path_is_correct(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)
        assert manager.history_path.name == "history.jsonl"


class TestCreateSpec:
    def test_creates_spec_with_required_fields(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        result = manager.create_spec(
            slug="test-spec",
            title="Test Specification",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        assert result.slug == "test-spec"
        assert result.title == "Test Specification"
        assert result.spec_type == SpecType.FEATURE
        assert result.status == SpecStatus.DRAFT

    def test_creates_spec_with_optional_fields(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        result = manager.create_spec(
            slug="test-spec",
            title="Test Specification",
            spec_type=SpecType.FEATURE,
            summary="A test summary",
            tags=["tag1", "tag2"],
            authors=["author1"],
            version="1.0.0",
            actor="test-user",
        )

        assert result.summary == "A test summary"
        assert result.tags == ("tag1", "tag2")
        assert result.authors == ("author1",)
        assert result.version == "1.0.0"

    def test_generates_sequential_id(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec1 = manager.create_spec(
            slug="spec-one",
            title="First Spec",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec2 = manager.create_spec(
            slug="spec-two",
            title="Second Spec",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        assert spec1.id < spec2.id

    def test_raises_for_invalid_slug_format(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError, match="Invalid slug format"):
            manager.create_spec(
                slug="Invalid Slug!",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_raises_for_duplicate_slug(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="test-spec",
            title="First",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        with pytest.raises(DuplicateIdError, match="already exists"):
            manager.create_spec(
                slug="test-spec",
                title="Second",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_creates_spec_directory_and_files(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        result = manager.create_spec(
            slug="test-spec",
            title="Test Specification",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        spec_dir = tmp_path / f"{result.id}-test-spec"
        assert spec_dir.exists()
        assert (spec_dir / "index.json").exists()

    def test_records_history_entry(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        assert (tmp_path / "history.jsonl").exists()

    def test_enhancement_requires_extends(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError, match=r"ENHANCEMENT.*extends"):
            manager.create_spec(
                slug="enhancement",
                title="Enhancement",
                spec_type=SpecType.ENHANCEMENT,
                actor="test-user",
            )

    def test_integration_requires_minimum_integrates(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="spec-one",
            title="First",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        with pytest.raises(SpecValidationError, match=r"INTEGRATION.*at least"):
            manager.create_spec(
                slug="integration",
                title="Integration",
                spec_type=SpecType.INTEGRATION,
                integrates=["SPEC-0001"],
                actor="test-user",
            )


class TestCreateSpecWithDependencies:
    def test_creates_spec_with_valid_dependencies(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        dep_spec = manager.create_spec(
            slug="dependency",
            title="Dependency",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.create_spec(
            slug="dependent",
            title="Dependent",
            spec_type=SpecType.FEATURE,
            depends_on=[dep_spec.id],
            actor="test-user",
        )

        assert result.relationships.depends_on == (dep_spec.id,)

    def test_raises_for_nonexistent_dependency(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecNotFoundError):
            manager.create_spec(
                slug="test-spec",
                title="Test",
                spec_type=SpecType.FEATURE,
                depends_on=["SPEC-9999"],
                actor="test-user",
            )

    def test_raises_for_circular_dependency(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec_a = manager.create_spec(
            slug="spec-a",
            title="Spec A",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec_b = manager.create_spec(
            slug="spec-b",
            title="Spec B",
            spec_type=SpecType.FEATURE,
            depends_on=[spec_a.id],
            actor="test-user",
        )

        with pytest.raises(CircularDependencyError):
            manager.update_spec(
                spec_a.id,
                depends_on=[spec_b.id],
                actor="test-user",
            )


class TestListSpecs:
    def test_returns_empty_list_when_no_specs(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        result = manager.list_specs()
        assert result == []

    def test_returns_all_specs(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="spec-one",
            title="First",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.create_spec(
            slug="spec-two",
            title="Second",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.list_specs()
        assert len(result) == 2

    def test_filters_by_status(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="spec-one",
            title="First",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec = manager.create_spec(
            slug="spec-two",
            title="Second",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.update_spec(spec.id, status=SpecStatus.APPROVED, actor="test-user")

        result = manager.list_specs(filter_status=SpecStatus.APPROVED)
        assert len(result) == 1
        assert result[0].status == SpecStatus.APPROVED

    def test_filters_by_type(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="feature",
            title="Feature",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        dep = manager.create_spec(
            slug="base",
            title="Base",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.create_spec(
            slug="enhancement",
            title="Enhancement",
            spec_type=SpecType.ENHANCEMENT,
            extends=dep.id,
            actor="test-user",
        )

        result = manager.list_specs(filter_type=SpecType.ENHANCEMENT)
        assert len(result) == 1
        assert result[0].spec_type == SpecType.ENHANCEMENT

    def test_filters_by_tags(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="tagged",
            title="Tagged",
            spec_type=SpecType.FEATURE,
            tags=["important", "api"],
            actor="test-user",
        )
        manager.create_spec(
            slug="other",
            title="Other",
            spec_type=SpecType.FEATURE,
            tags=["other"],
            actor="test-user",
        )

        result = manager.list_specs(filter_tags=["important"])
        assert len(result) == 1
        assert "important" in result[0].tags

    def test_excludes_archived_by_default(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="archived",
            title="Archived",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.update_spec(spec.id, status=SpecStatus.DEPRECATED, actor="test-user")

        result = manager.list_specs()
        assert len(result) == 0

    def test_includes_archived_when_requested(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="archived",
            title="Archived",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.update_spec(spec.id, status=SpecStatus.DEPRECATED, actor="test-user")

        result = manager.list_specs(include_archived=True)
        assert len(result) == 1


class TestGetSpec:
    def test_returns_spec_metadata(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        created = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.get_spec(created.id)
        assert result.id == created.id
        assert result.title == "Test"

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecNotFoundError):
            manager.get_spec("SPEC-9999")

    def test_returns_computed_inverse_relationships(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        base = manager.create_spec(
            slug="base",
            title="Base",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        dependent = manager.create_spec(
            slug="dependent",
            title="Dependent",
            spec_type=SpecType.FEATURE,
            depends_on=[base.id],
            actor="test-user",
        )

        base_data = manager.get_spec(base.id)
        assert dependent.id in base_data.relationships.dependents


class TestSpecExists:
    def test_returns_true_for_existing_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        assert manager.spec_exists(spec.id) is True

    def test_returns_false_for_nonexistent_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        assert manager.spec_exists("SPEC-9999") is False


class TestUpdateSpec:
    def test_updates_title(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Original",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.update_spec(
            spec.id,
            title="Updated",
            actor="test-user",
        )

        assert result.title == "Updated"

    def test_updates_status(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.update_spec(
            spec.id,
            status=SpecStatus.APPROVED,
            actor="test-user",
        )

        assert result.status == SpecStatus.APPROVED

    def test_updates_tags(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            tags=["old"],
            actor="test-user",
        )

        result = manager.update_spec(
            spec.id,
            tags=["new", "tags"],
            actor="test-user",
        )

        assert result.tags == ("new", "tags")

    def test_updates_dependencies(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        dep = manager.create_spec(
            slug="dependency",
            title="Dependency",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.update_spec(
            spec.id,
            depends_on=[dep.id],
            actor="test-user",
        )

        assert result.relationships.depends_on == (dep.id,)

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecNotFoundError):
            manager.update_spec(
                "SPEC-9999",
                title="Updated",
                actor="test-user",
            )

    def test_preserves_unmodified_fields(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Original",
            spec_type=SpecType.FEATURE,
            summary="A summary",
            actor="test-user",
        )

        result = manager.update_spec(
            spec.id,
            title="Updated",
            actor="test-user",
        )

        assert result.title == "Updated"
        assert result.summary == "A summary"


class TestDeleteSpec:
    def test_removes_spec_from_listing(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        manager.delete_spec(spec.id, actor="test-user")

        assert manager.spec_exists(spec.id) is False

    def test_removes_spec_directory(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec_dir = tmp_path / f"{spec.id}-test-spec"
        assert spec_dir.exists()

        manager.delete_spec(spec.id, actor="test-user")

        assert not spec_dir.exists()

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecNotFoundError):
            manager.delete_spec("SPEC-9999", actor="test-user")

    def test_raises_for_spec_with_dependents(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        base = manager.create_spec(
            slug="base",
            title="Base",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.create_spec(
            slug="dependent",
            title="Dependent",
            spec_type=SpecType.FEATURE,
            depends_on=[base.id],
            actor="test-user",
        )

        with pytest.raises(SpecValidationError, match="depended on"):
            manager.delete_spec(base.id, actor="test-user")

    def test_force_deletes_spec_with_dependents(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        base = manager.create_spec(
            slug="base",
            title="Base",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        manager.create_spec(
            slug="dependent",
            title="Dependent",
            spec_type=SpecType.FEATURE,
            depends_on=[base.id],
            actor="test-user",
        )

        manager.delete_spec(base.id, force=True, actor="test-user")

        assert manager.spec_exists(base.id) is False


class TestRenameSpec:
    def test_changes_slug(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="old-slug",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.rename_spec(spec.id, "new-slug", actor="test-user")

        assert result.slug == "new-slug"

    def test_moves_directory(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="old-slug",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        old_dir = tmp_path / f"{spec.id}-old-slug"
        assert old_dir.exists()

        manager.rename_spec(spec.id, "new-slug", actor="test-user")

        new_dir = tmp_path / f"{spec.id}-new-slug"
        assert new_dir.exists()
        assert not old_dir.exists()

    def test_returns_unchanged_for_same_slug(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-slug",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.rename_spec(spec.id, "test-slug", actor="test-user")

        assert result.slug == "test-slug"

    def test_raises_for_invalid_slug(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="old-slug",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        with pytest.raises(SpecValidationError, match="Invalid slug format"):
            manager.rename_spec(spec.id, "Invalid Slug!", actor="test-user")

    def test_raises_for_duplicate_slug(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="existing",
            title="Existing",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )
        spec = manager.create_spec(
            slug="to-rename",
            title="To Rename",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        with pytest.raises(DuplicateIdError, match="already exists"):
            manager.rename_spec(spec.id, "existing", actor="test-user")


class TestArchiveSpec:
    def test_sets_status_to_deprecated(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        result = manager.archive_spec(spec.id, actor="test-user")

        assert result.status == SpecStatus.DEPRECATED


class TestValidateSpec:
    def test_returns_empty_for_valid_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="valid-spec",
            title="Valid Spec",
            spec_type=SpecType.FEATURE,
            summary="A summary",
            authors=["author"],
            actor="test-user",
        )

        issues = manager.validate_spec(spec.id)

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_warns_for_missing_summary(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        issues = manager.validate_spec(spec.id)

        warnings = [
            i for i in issues if i.severity == "warning" and i.field == "summary"
        ]
        assert len(warnings) == 1

    def test_warns_for_missing_authors(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        issues = manager.validate_spec(spec.id)

        warnings = [
            i for i in issues if i.severity == "warning" and i.field == "authors"
        ]
        assert len(warnings) == 1

    def test_strict_mode_treats_warnings_as_errors(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        issues = manager.validate_spec(spec.id, strict=True)

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecNotFoundError):
            manager.validate_spec("SPEC-9999")


class TestCaching:
    def test_caches_root_index(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        manager.list_specs()
        assert manager._root_index_cache is not None

    def test_invalidates_cache_on_mutation(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        spec = manager.create_spec(
            slug="test-spec",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

        manager.list_specs()
        assert manager._root_index_cache is not None

        manager.update_spec(spec.id, title="Updated", actor="test-user")
        assert manager._root_index_cache is None


class TestSlugValidation:
    def test_accepts_lowercase_letters(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="lowercase",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

    def test_accepts_digits(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="spec123",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

    def test_accepts_hyphens_between_words(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        manager.create_spec(
            slug="my-spec-name",
            title="Test",
            spec_type=SpecType.FEATURE,
            actor="test-user",
        )

    def test_rejects_uppercase(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError):
            manager.create_spec(
                slug="Uppercase",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_rejects_leading_hyphen(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError):
            manager.create_spec(
                slug="-leading",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_rejects_trailing_hyphen(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError):
            manager.create_spec(
                slug="trailing-",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_rejects_consecutive_hyphens(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError):
            manager.create_spec(
                slug="double--hyphen",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )

    def test_rejects_special_characters(self, tmp_path: Path) -> None:
        manager = SpecManager(tmp_path)

        with pytest.raises(SpecValidationError):
            manager.create_spec(
                slug="special!chars",
                title="Test",
                spec_type=SpecType.FEATURE,
                actor="test-user",
            )
