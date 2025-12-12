# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Tests for TestManager operations."""

from pathlib import Path

import pytest

# Alias TestNotFoundError to avoid pytest collection (pytest treats "Test*" as tests)
from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
    TestNotFoundError as SpecTestNotFoundError,
)

# Alias to avoid pytest collection (pytest treats classes starting with "Test" as tests)
from oaps.spec import (
    RequirementManager,
    RequirementType,
    SpecManager,
    SpecType,
    TestManager as SpecTestManager,
)
from oaps.spec._models import (
    TestMethod as SpecTestMethod,
    TestResult as SpecTestResult,
    TestStatus as SpecTestStatus,
)


def setup_spec_with_requirements(
    tmp_path: Path,
) -> tuple[SpecManager, RequirementManager, str, str]:
    """Create a SpecManager with a spec and requirement, returning managers and IDs."""
    spec_manager = SpecManager(tmp_path)
    spec = spec_manager.create_spec(
        slug="test-spec",
        title="Test Specification",
        spec_type=SpecType.FEATURE,
        actor="test-user",
    )
    req_manager = RequirementManager(spec_manager)
    req = req_manager.add_requirement(
        spec.id,
        RequirementType.FUNCTIONAL,
        "Test Requirement",
        "A requirement for testing",
        actor="test-user",
    )
    return spec_manager, req_manager, spec.id, req.id


class TestSpecTestManagerInit:
    def test_accepts_spec_and_requirement_managers(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)
        assert manager._spec_manager is spec_manager
        assert manager._requirement_manager is req_manager


class TestAddSpecTest:
    def test_creates_test_with_required_fields(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        result = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test user login",
            [req_id],
            actor="test-user",
        )

        assert result.title == "Test user login"
        assert result.method == SpecTestMethod.UNIT
        assert result.tests_requirements == (req_id,)
        assert result.status == SpecTestStatus.PENDING

    def test_creates_test_with_optional_fields(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        result = manager.add_test(
            spec_id,
            SpecTestMethod.INTEGRATION,
            "Test user login",
            [req_id],
            file="tests/test_auth.py",
            function="test_user_login",
            description="Verify user can log in",
            tags=["auth", "login"],
            actor="test-user",
        )

        assert result.method == SpecTestMethod.INTEGRATION
        assert result.file == "tests/test_auth.py"
        assert result.function == "test_user_login"
        assert result.description == "Verify user can log in"
        assert result.tags == ("auth", "login")

    def test_generates_sequential_id(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test1 = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "First test",
            [req_id],
            actor="test-user",
        )
        test2 = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Second test",
            [req_id],
            actor="test-user",
        )

        assert test1.id < test2.id

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, req_id = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecNotFoundError):
            manager.add_test(
                "SPEC-9999",
                SpecTestMethod.UNIT,
                "Test",
                [req_id],
                actor="test-user",
            )

    def test_raises_for_nonexistent_requirement(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(RequirementNotFoundError):
            manager.add_test(
                spec_id,
                SpecTestMethod.UNIT,
                "Test",
                ["REQ-9999"],
                actor="test-user",
            )


class TestListSpecTests:
    def test_returns_empty_list_when_no_tests(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        result = manager.list_tests(spec_id)
        assert result == []

    def test_returns_all_tests(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "First",
            [req_id],
            actor="test-user",
        )
        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Second",
            [req_id],
            actor="test-user",
        )

        result = manager.list_tests(spec_id)
        assert len(result) == 2

    def test_filters_by_status(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        pending = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Pending",
            [req_id],
            actor="test-user",
        )
        manager.update_test(
            spec_id, pending.id, status=SpecTestStatus.IMPLEMENTED, actor="test-user"
        )
        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Still pending",
            [req_id],
            actor="test-user",
        )

        result = manager.list_tests(spec_id, filter_status=SpecTestStatus.IMPLEMENTED)
        assert len(result) == 1
        assert result[0].status == SpecTestStatus.IMPLEMENTED

    def test_filters_by_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Unit",
            [req_id],
            actor="test-user",
        )
        manager.add_test(
            spec_id,
            SpecTestMethod.INTEGRATION,
            "Integration",
            [req_id],
            actor="test-user",
        )

        result = manager.list_tests(spec_id, filter_method=SpecTestMethod.INTEGRATION)
        assert len(result) == 1
        assert result[0].method == SpecTestMethod.INTEGRATION

    def test_filters_by_requirements(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        req2 = req_manager.add_requirement(
            spec_id,
            RequirementType.FUNCTIONAL,
            "Second requirement",
            "Another requirement",
            actor="test-user",
        )

        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Tests first",
            [req_id],
            actor="test-user",
        )
        manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Tests second",
            [req2.id],
            actor="test-user",
        )

        result = manager.list_tests(spec_id, filter_requirements=[req_id])
        assert len(result) == 1
        assert req_id in result[0].tests_requirements

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecNotFoundError):
            manager.list_tests("SPEC-9999")


class TestGetSpecTest:
    def test_returns_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        created = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test case",
            [req_id],
            actor="test-user",
        )

        result = manager.get_test(spec_id, created.id)
        assert result.id == created.id
        assert result.title == "Test case"

    def test_raises_for_nonexistent_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecTestNotFoundError):
            manager.get_test(spec_id, "TST-9999")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecNotFoundError):
            manager.get_test("SPEC-9999", "TST-0001")


class TestSpecTestExists:
    def test_returns_true_for_existing_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        assert manager.test_exists(spec_id, test.id) is True

    def test_returns_false_for_nonexistent_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        assert manager.test_exists(spec_id, "TST-9999") is False

    def test_returns_false_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        assert manager.test_exists("SPEC-9999", "TST-0001") is False


class TestUpdateSpecTest:
    def test_updates_title(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Original",
            [req_id],
            actor="test-user",
        )

        result = manager.update_test(
            spec_id, test.id, title="Updated", actor="test-user"
        )

        assert result.title == "Updated"

    def test_updates_status(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.update_test(
            spec_id, test.id, status=SpecTestStatus.IMPLEMENTED, actor="test-user"
        )

        assert result.status == SpecTestStatus.IMPLEMENTED

    def test_updates_file_and_function(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.update_test(
            spec_id,
            test.id,
            file="tests/test_new.py",
            function="test_new_function",
            actor="test-user",
        )

        assert result.file == "tests/test_new.py"
        assert result.function == "test_new_function"

    def test_preserves_unmodified_fields(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Original",
            [req_id],
            description="Original description",
            actor="test-user",
        )

        result = manager.update_test(
            spec_id, test.id, title="Updated", actor="test-user"
        )

        assert result.title == "Updated"
        assert result.description == "Original description"

    def test_raises_for_nonexistent_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecTestNotFoundError):
            manager.update_test(spec_id, "TST-9999", title="Updated", actor="test-user")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecNotFoundError):
            manager.update_test(
                "SPEC-9999", "TST-0001", title="Updated", actor="test-user"
            )


class TestDeleteSpecTest:
    def test_removes_test_from_listing(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "To delete",
            [req_id],
            actor="test-user",
        )

        manager.delete_test(spec_id, test.id, actor="test-user")

        assert manager.test_exists(spec_id, test.id) is False

    def test_raises_for_nonexistent_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecTestNotFoundError):
            manager.delete_test(spec_id, "TST-9999", actor="test-user")

    def test_raises_for_nonexistent_spec(self, tmp_path: Path) -> None:
        spec_manager, req_manager, _, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecNotFoundError):
            manager.delete_test("SPEC-9999", "TST-0001", actor="test-user")


class TestRecordRun:
    def test_records_pass_result(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.record_run(
            spec_id, test.id, SpecTestResult.PASS, actor="test-user"
        )

        assert result.last_result == SpecTestResult.PASS
        assert result.last_run is not None

    def test_records_fail_result(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.record_run(
            spec_id, test.id, SpecTestResult.FAIL, actor="test-user"
        )

        assert result.last_result == SpecTestResult.FAIL

    def test_records_skip_result(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.record_run(
            spec_id, test.id, SpecTestResult.SKIP, actor="test-user"
        )

        assert result.last_result == SpecTestResult.SKIP

    def test_records_error_result(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        result = manager.record_run(
            spec_id, test.id, SpecTestResult.ERROR, actor="test-user"
        )

        assert result.last_result == SpecTestResult.ERROR

    def test_updates_run_count(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Test",
            [req_id],
            actor="test-user",
        )

        manager.record_run(spec_id, test.id, SpecTestResult.PASS, actor="test-user")
        result = manager.record_run(
            spec_id, test.id, SpecTestResult.FAIL, actor="test-user"
        )

        # record_run updates last_result and last_run
        assert result.last_result == SpecTestResult.FAIL
        assert result.last_run is not None

    def test_raises_for_nonexistent_test(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, _ = setup_spec_with_requirements(tmp_path)
        manager = SpecTestManager(spec_manager, req_manager)

        with pytest.raises(SpecTestNotFoundError):
            manager.record_run(
                spec_id, "TST-9999", SpecTestResult.PASS, actor="test-user"
            )


class TestSpecTestMethods:
    def test_supports_unit_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.UNIT,
            "Unit",
            [req_id],
            actor="test-user",
        )
        assert test.method == SpecTestMethod.UNIT

    def test_supports_integration_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.INTEGRATION,
            "Integration",
            [req_id],
            actor="test-user",
        )
        assert test.method == SpecTestMethod.INTEGRATION

    def test_supports_e2e_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.E2E,
            "E2E",
            [req_id],
            actor="test-user",
        )
        assert test.method == SpecTestMethod.E2E

    def test_supports_manual_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.MANUAL,
            "Manual",
            [req_id],
            actor="test-user",
        )
        assert test.method == SpecTestMethod.MANUAL

    def test_supports_performance_method(self, tmp_path: Path) -> None:
        spec_manager, req_manager, spec_id, req_id = setup_spec_with_requirements(
            tmp_path
        )
        manager = SpecTestManager(spec_manager, req_manager)

        test = manager.add_test(
            spec_id,
            SpecTestMethod.PERFORMANCE,
            "Performance",
            [req_id],
            actor="test-user",
        )
        assert test.method == SpecTestMethod.PERFORMANCE
