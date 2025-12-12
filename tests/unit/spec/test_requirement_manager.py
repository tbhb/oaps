# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Tests for RequirementManager operations."""

from pathlib import Path

import pytest

from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
)
from oaps.spec import (
    RequirementManager,
    RequirementStatus,
    RequirementType,
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


class TestRequirementManagerInit:
    def test_accepts_spec_manager(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)
        assert manager._spec_manager is spec_manager


class TestAddRequirement:
    def test_creates_requirement_with_required_fields(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        result = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "User authentication",
            "System must authenticate users",
            actor="test-user",
        )

        assert result.title == "User authentication"
        assert result.req_type == RequirementType.FUNCTIONAL
        assert result.description == "System must authenticate users"

    def test_creates_requirement_with_optional_fields(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        result = manager.add_requirement(
            spec_id,
            RequirementType.QUALITY,
            "Performance requirement",
            "Response time under 200ms",
            rationale="Critical for user experience",
            tags=["performance", "api"],
            actor="test-user",
        )

        assert result.tags == ("performance", "api")
        assert result.rationale == "Critical for user experience"

    def test_generates_sequential_id(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req1 = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "First",
            "First requirement",
            actor="test-user",
        )
        req2 = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Second",
            "Second requirement",
            actor="test-user",
        )

        assert req1.id < req2.id

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.add_requirement(
                "SPEC-9999",
                RequirementType.FUNCTIONAL,
                "Test",
                "Description",
                actor="test-user",
            )


class TestListRequirements:
    def test_returns_empty_list_when_no_requirements(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        result = manager.list_requirements(spec_id)
        assert result == []

    def test_returns_all_requirements(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "First",
            "First requirement",
            actor="test-user",
        )
        manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Second",
            "Second requirement",
            actor="test-user",
        )

        result = manager.list_requirements(spec_id)
        assert len(result) == 2

    def test_filters_by_status(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Proposed",
            "A proposed requirement",
            actor="test-user",
        )
        manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.APPROVED, actor="test-user"
        )
        manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Still proposed",
            "Another requirement",
            actor="test-user",
        )

        result = manager.list_requirements(
            spec_id, filter_status=RequirementStatus.APPROVED
        )
        assert len(result) == 1
        assert result[0].status == RequirementStatus.APPROVED

    def test_filters_by_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Functional",
            "Functional requirement",
            actor="test-user",
        )
        manager.add_requirement(
            spec_id,
            RequirementType.QUALITY,
            "Quality",
            "Quality requirement",
            actor="test-user",
        )

        result = manager.list_requirements(spec_id, filter_type=RequirementType.QUALITY)
        assert len(result) == 1
        assert result[0].req_type == RequirementType.QUALITY

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.list_requirements("SPEC-9999")


class TestGetRequirement:
    def test_returns_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        created = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test requirement",
            "A test requirement",
            actor="test-user",
        )

        result = manager.get_requirement(spec_id, created.id)
        assert result.id == created.id
        assert result.title == "Test requirement"

    def test_raises_for_nonexistent_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(RequirementNotFoundError):
            manager.get_requirement(spec_id, "REQ-9999")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.get_requirement("SPEC-9999", "REQ-0001")


class TestRequirementExists:
    def test_returns_true_for_existing_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            actor="test-user",
        )

        assert manager.requirement_exists(spec_id, req.id) is True

    def test_returns_false_for_nonexistent_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        assert manager.requirement_exists(spec_id, "REQ-9999") is False

    def test_returns_false_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        assert manager.requirement_exists("SPEC-9999", "REQ-0001") is False


class TestUpdateRequirement:
    def test_updates_title(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Original",
            "Description",
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id,
            req.id,
            title="Updated",
            actor="test-user",
        )

        assert result.title == "Updated"

    def test_updates_status(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id,
            req.id,
            status=RequirementStatus.IMPLEMENTED,
            actor="test-user",
        )

        assert result.status == RequirementStatus.IMPLEMENTED

    def test_updates_tags(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            tags=["old"],
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id,
            req.id,
            tags=["new", "tags"],
            actor="test-user",
        )

        assert result.tags == ("new", "tags")

    def test_updates_description(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Original description",
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id,
            req.id,
            description="Updated description",
            actor="test-user",
        )

        assert result.description == "Updated description"

    def test_preserves_unmodified_fields(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Original",
            "Original description",
            rationale="Original rationale",
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id,
            req.id,
            title="Updated",
            actor="test-user",
        )

        assert result.title == "Updated"
        assert result.description == "Original description"
        assert result.rationale == "Original rationale"

    def test_raises_for_nonexistent_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(RequirementNotFoundError):
            manager.update_requirement(
                spec_id,
                "REQ-9999",
                title="Updated",
                actor="test-user",
            )

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.update_requirement(
                "SPEC-9999",
                "REQ-0001",
                title="Updated",
                actor="test-user",
            )


class TestDeleteRequirement:
    def test_removes_requirement_from_listing(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "To delete",
            "Will be deleted",
            actor="test-user",
        )

        manager.delete_requirement(spec_id, req.id, actor="test-user")

        assert manager.requirement_exists(spec_id, req.id) is False

    def test_raises_for_nonexistent_requirement(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(RequirementNotFoundError):
            manager.delete_requirement(spec_id, "REQ-9999", actor="test-user")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, _ = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        with pytest.raises(SpecNotFoundError):
            manager.delete_requirement("SPEC-9999", "REQ-0001", actor="test-user")


class TestRequirementTypes:
    def test_supports_functional_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Functional",
            "Functional requirement",
            actor="test-user",
        )
        assert req.req_type == RequirementType.FUNCTIONAL

    def test_supports_quality_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.QUALITY,
            "Quality",
            "Quality requirement",
            actor="test-user",
        )
        assert req.req_type == RequirementType.QUALITY

    def test_supports_constraint_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.CONSTRAINT,
            "Constraint",
            "Constraint requirement",
            actor="test-user",
        )
        assert req.req_type == RequirementType.CONSTRAINT

    def test_supports_interface_type(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.INTERFACE,
            "Interface",
            "Interface requirement",
            actor="test-user",
        )
        assert req.req_type == RequirementType.INTERFACE


class TestStatusTransitions:
    def test_transitions_from_proposed_to_approved(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            actor="test-user",
        )

        result = manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.APPROVED, actor="test-user"
        )
        assert result.status == RequirementStatus.APPROVED

    def test_transitions_from_approved_to_implemented(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            actor="test-user",
        )
        manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.APPROVED, actor="test-user"
        )

        result = manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.IMPLEMENTED, actor="test-user"
        )
        assert result.status == RequirementStatus.IMPLEMENTED

    def test_transitions_from_implemented_to_verified(self, tmp_path: Path) -> None:
        spec_manager, spec_id = setup_spec_manager(tmp_path)
        manager = RequirementManager(spec_manager)

        req = manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Test",
            "Description",
            actor="test-user",
        )
        manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.IMPLEMENTED, actor="test-user"
        )

        result = manager.update_requirement(
            spec_id, req.id, status=RequirementStatus.VERIFIED, actor="test-user"
        )
        assert result.status == RequirementStatus.VERIFIED
