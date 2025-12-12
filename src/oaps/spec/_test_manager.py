# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""Test manager for CRUD operations on tests.

This module provides the TestManager class for managing tests within
specifications. It handles test creation, updates, deletion, linking to
requirements, and synchronization with pytest results.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
    TestNotFoundError,
)
from oaps.spec._ids import next_test_id
from oaps.spec._io import append_jsonl, read_json, write_json_atomic
from oaps.spec._models import (
    PytestResults,
    Requirement,
    SyncResult,
    Test,
    TestMethod,
    TestResult,
    TestsContainer,
    TestStatus,
)

if TYPE_CHECKING:
    from pathlib import Path

    from oaps.config import SpecConfiguration
    from oaps.repository import OapsRepository
    from oaps.spec._requirement_manager import RequirementManager
    from oaps.spec._spec_manager import SpecManager

__all__ = ["TestManager"]

# Container schema version
_CONTAINER_VERSION = 1


class TestManager:
    """Manager for CRUD operations on tests within specifications.

    The TestManager provides methods for creating, reading, updating,
    and deleting tests. It maintains bidirectional links with requirements
    and supports synchronization with pytest results.

    Attributes:
        _spec_manager: The specification manager for accessing spec data.
        _requirement_manager: The requirement manager for bidirectional links.
        _config: Specification configuration.
        _tests_cache: Cache of loaded tests containers.
    """

    __slots__: Final = (
        "_config",
        "_oaps_repo",
        "_requirement_manager",
        "_spec_manager",
        "_tests_cache",
    )

    _config: SpecConfiguration | None
    _oaps_repo: OapsRepository | None
    _requirement_manager: RequirementManager
    _spec_manager: SpecManager
    _tests_cache: dict[str, TestsContainer]

    def __init__(
        self,
        spec_manager: SpecManager,
        requirement_manager: RequirementManager,
        *,
        oaps_repo: OapsRepository | None = None,
    ) -> None:
        """Initialize the test manager.

        Args:
            spec_manager: The specification manager for accessing spec data.
            requirement_manager: The requirement manager for bidirectional links.
            oaps_repo: Repository for committing changes. If None, falls back
                to spec_manager's repository if available.
        """
        self._spec_manager = spec_manager
        self._requirement_manager = requirement_manager
        self._oaps_repo = (
            oaps_repo
            if oaps_repo is not None
            else getattr(spec_manager, "_oaps_repo", None)
        )
        self._config = None
        self._tests_cache = {}

    # -------------------------------------------------------------------------
    # Path Properties
    # -------------------------------------------------------------------------

    def _get_spec_dir(self, spec_id: str) -> Path:
        """Get the directory path for a specification.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the specification directory.
        """
        spec = self._spec_manager.get_spec(spec_id)
        return self._spec_manager.base_path / f"{spec_id}-{spec.slug}"

    def _tests_path(self, spec_id: str) -> Path:
        """Get the path to the tests.json file for a spec.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the tests.json file.
        """
        return self._get_spec_dir(spec_id) / "tests.json"

    def _history_path(self, spec_id: str) -> Path:
        """Get the path to the history.jsonl file for a spec.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the history.jsonl file.
        """
        return self._get_spec_dir(spec_id) / "history.jsonl"

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _get_config(self) -> SpecConfiguration:
        """Get the specification configuration.

        Returns:
            The specification configuration, either from constructor or
            loaded from global context.
        """
        if self._config is None:
            from oaps.config import SpecConfiguration  # noqa: PLC0415

            self._config = SpecConfiguration()
        return self._config

    def _invalidate_cache(self, spec_id: str | None = None) -> None:
        """Invalidate cached data.

        Args:
            spec_id: If provided, only invalidate cache for this spec.
                If None, invalidate all caches.
        """
        if spec_id is None:
            self._tests_cache.clear()
        else:
            _ = self._tests_cache.pop(spec_id, None)

    def _commit(self, action: str, *, session_id: str | None = None) -> bool:
        """Commit changes to the OAPS repository.

        Args:
            action: The action description for the commit message.
            session_id: Optional session identifier for the commit trailer.

        Returns:
            True if commit was made, False if no repository or no changes.
        """
        if self._oaps_repo is None:
            return False

        result = self._oaps_repo.checkpoint(
            workflow="spec",
            action=action,
            session_id=session_id,
        )
        return not result.no_changes

    def _load_tests(self, spec_id: str) -> TestsContainer:
        """Load tests from disk.

        Args:
            spec_id: The specification ID.

        Returns:
            The tests container.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        if spec_id in self._tests_cache:
            return self._tests_cache[spec_id]

        path = self._tests_path(spec_id)

        if not path.exists():
            # Return empty container
            container = TestsContainer(
                version=_CONTAINER_VERSION,
                spec_id=spec_id,
                updated=datetime.now(UTC),
                tests=(),
            )
            self._tests_cache[spec_id] = container
            return container

        data = read_json(path)
        tests = tuple(
            self._dict_to_test(test_data) for test_data in data.get("tests", [])
        )
        container = TestsContainer(
            version=data.get("version", _CONTAINER_VERSION),
            spec_id=data.get("spec_id", spec_id),
            updated=datetime.fromisoformat(data["updated"]),
            tests=tests,
        )
        self._tests_cache[spec_id] = container
        return container

    def _write_tests(self, spec_id: str, tests: tuple[Test, ...]) -> None:
        """Write tests to disk atomically.

        Args:
            spec_id: The specification ID.
            tests: The tests to write.
        """
        path = self._tests_path(spec_id)
        now = datetime.now(UTC)
        data: dict[str, Any] = {
            "version": _CONTAINER_VERSION,
            "spec_id": spec_id,
            "updated": now.isoformat(),
            "tests": [self._test_to_dict(test) for test in tests],
        }
        write_json_atomic(path, data)
        _ = self._tests_cache.pop(spec_id, None)

    def _record_history(  # noqa: PLR0913
        self,
        spec_id: str,
        event: str,
        actor: str,
        test_id: str,
        *,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        """Record an event to the per-spec history log.

        Args:
            spec_id: The specification ID.
            event: The event type.
            actor: The actor who performed the action.
            test_id: The affected test ID.
            from_value: The previous value (for updates).
            to_value: The new value (for updates).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "actor": actor,
            "id": test_id,
        }
        if from_value is not None:
            entry["from_value"] = from_value
        if to_value is not None:
            entry["to_value"] = to_value

        append_jsonl(self._history_path(spec_id), entry)

    def _dict_to_test(self, data: dict[str, Any]) -> Test:
        """Convert a dictionary to a Test.

        Args:
            data: Dictionary from JSON storage.

        Returns:
            Test instance.
        """
        created = data["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = data["updated"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        last_run = data.get("last_run")
        if isinstance(last_run, str):
            last_run = datetime.fromisoformat(last_run)

        tested_on = data.get("tested_on")
        if isinstance(tested_on, str):
            tested_on = datetime.fromisoformat(tested_on)

        last_result_str = data.get("last_result")
        last_result = TestResult(last_result_str) if last_result_str else None

        return Test(
            id=data["id"],
            title=data["title"],
            method=TestMethod(data["method"]),
            status=TestStatus(data["status"]),
            created=created,
            updated=updated,
            author=data["author"],
            tests_requirements=tuple(data.get("tests_requirements", [])),
            description=data.get("description"),
            file=data.get("file"),
            function=data.get("function"),
            last_run=last_run,
            last_result=last_result,
            tags=tuple(data.get("tags", [])),
            last_value=data.get("last_value"),
            threshold=data.get("threshold"),
            perf_baseline=data.get("perf_baseline"),
            steps=tuple(data.get("steps", [])),
            expected_result=data.get("expected_result"),
            actual_result=data.get("actual_result"),
            tested_by=data.get("tested_by"),
            tested_on=tested_on,
        )

    def _test_to_dict(self, test: Test) -> dict[str, Any]:  # noqa: PLR0912
        """Convert a Test to a dictionary for JSON storage.

        Args:
            test: The Test to convert.

        Returns:
            Dictionary representation for JSON serialization.
        """
        data: dict[str, Any] = {
            "id": test.id,
            "title": test.title,
            "method": test.method.value,
            "status": test.status.value,
            "created": test.created.isoformat(),
            "updated": test.updated.isoformat(),
            "author": test.author,
            "tests_requirements": list(test.tests_requirements),
        }

        if test.description:
            data["description"] = test.description
        if test.file:
            data["file"] = test.file
        if test.function:
            data["function"] = test.function
        if test.last_run:
            data["last_run"] = test.last_run.isoformat()
        if test.last_result:
            data["last_result"] = test.last_result.value
        if test.tags:
            data["tags"] = list(test.tags)
        if test.last_value is not None:
            data["last_value"] = test.last_value
        if test.threshold is not None:
            data["threshold"] = test.threshold
        if test.perf_baseline is not None:
            data["perf_baseline"] = test.perf_baseline
        if test.steps:
            data["steps"] = list(test.steps)
        if test.expected_result:
            data["expected_result"] = test.expected_result
        if test.actual_result:
            data["actual_result"] = test.actual_result
        if test.tested_by:
            data["tested_by"] = test.tested_by
        if test.tested_on:
            data["tested_on"] = test.tested_on.isoformat()

        return data

    def _validate_requirements_exist(self, spec_id: str, req_ids: list[str]) -> None:
        """Validate that all requirements exist.

        Args:
            spec_id: The specification ID.
            req_ids: List of requirement IDs to validate.

        Raises:
            RequirementNotFoundError: If any requirement doesn't exist.
        """
        for req_id in req_ids:
            if not self._requirement_manager.requirement_exists(spec_id, req_id):
                msg = f"Requirement not found: {req_id}"
                raise RequirementNotFoundError(
                    msg, requirement_id=req_id, spec_id=spec_id
                )

    def _add_test_to_requirements(
        self, spec_id: str, test_id: str, req_ids: list[str]
    ) -> None:
        """Add a test ID to requirements' verified_by lists.

        Args:
            spec_id: The specification ID.
            test_id: The test ID to add.
            req_ids: List of requirement IDs to update.
        """
        for req_id in req_ids:
            req = self._requirement_manager.get_requirement(spec_id, req_id)
            if test_id not in req.verified_by:
                new_verified_by = [*req.verified_by, test_id]
                self._update_requirement_verified_by(spec_id, req, new_verified_by)

    def _remove_test_from_requirements(
        self, spec_id: str, test_id: str, req_ids: list[str]
    ) -> None:
        """Remove a test ID from requirements' verified_by lists.

        Args:
            spec_id: The specification ID.
            test_id: The test ID to remove.
            req_ids: List of requirement IDs to update.
        """
        for req_id in req_ids:
            req = self._requirement_manager.get_requirement(spec_id, req_id)
            if test_id in req.verified_by:
                new_verified_by = [v for v in req.verified_by if v != test_id]
                self._update_requirement_verified_by(spec_id, req, new_verified_by)

    def _update_requirement_verified_by(
        self, spec_id: str, req: Requirement, verified_by: list[str]
    ) -> None:
        """Update a requirement's verified_by field directly.

        This method bypasses the RequirementManager's update method to avoid
        triggering unnecessary history entries and validation for what is
        essentially an internal bookkeeping update.

        Args:
            spec_id: The specification ID.
            req: The requirement to update.
            verified_by: The new verified_by list.
        """
        # Load requirements
        # Access protected method for bidirectional link management
        container = self._requirement_manager._load_requirements(spec_id)  # noqa: SLF001

        # Create updated requirement
        now = datetime.now(UTC)
        updated = Requirement(
            id=req.id,
            title=req.title,
            req_type=req.req_type,
            status=req.status,
            created=req.created,
            updated=now,
            author=req.author,
            description=req.description,
            rationale=req.rationale,
            acceptance_criteria=req.acceptance_criteria,
            verified_by=tuple(verified_by),
            depends_on=req.depends_on,
            tags=req.tags,
            source_section=req.source_section,
            parent=req.parent,
            subtype=req.subtype,
            scale=req.scale,
            meter=req.meter,
            baseline=req.baseline,
            goal=req.goal,
            stretch=req.stretch,
            fail=req.fail,
        )

        # Replace in list
        new_requirements = tuple(
            updated if r.id == req.id else r for r in container.requirements
        )

        # Write directly - access protected methods for bidirectional link management
        self._requirement_manager._write_requirements(spec_id, new_requirements)  # noqa: SLF001
        # Invalidate requirement manager's cache
        self._requirement_manager._invalidate_cache(spec_id)  # noqa: SLF001

    def _result_to_status(self, result: TestResult) -> TestStatus:
        """Convert a TestResult to a TestStatus.

        Args:
            result: The test result.

        Returns:
            The corresponding test status.
        """
        mapping = {
            TestResult.PASS: TestStatus.PASSING,
            TestResult.FAIL: TestStatus.FAILING,
            TestResult.SKIP: TestStatus.SKIPPED,
            TestResult.ERROR: TestStatus.FAILING,
        }
        return mapping[result]

    def _parse_pytest_node_id(self, node_id: str) -> tuple[str | None, str | None]:
        """Parse a pytest node ID to extract file and function.

        Args:
            node_id: Pytest node ID (e.g., "tests/test_foo.py::test_bar").

        Returns:
            Tuple of (file, function) or (None, None) if parsing fails.
        """
        if "::" not in node_id:
            return None, None

        parts = node_id.split("::")
        file_path = parts[0]

        # Handle nested test classes: tests/test_foo.py::TestClass::test_method
        # We want just the function/method name
        function = parts[-1] if len(parts) > 1 else None

        # Strip parametrize suffix: test_bar[param1] -> test_bar
        if function and "[" in function:
            function = function.split("[")[0]

        return file_path, function

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def list_tests(
        self,
        spec_id: str,
        *,
        filter_method: TestMethod | None = None,
        filter_status: TestStatus | None = None,
        filter_requirements: list[str] | None = None,
    ) -> list[Test]:
        """List tests with optional filtering.

        Args:
            spec_id: The specification ID.
            filter_method: Filter by test method.
            filter_status: Filter by status.
            filter_requirements: Filter by requirements (tests must verify all listed).

        Returns:
            List of matching tests.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        container = self._load_tests(spec_id)

        results: list[Test] = []
        for test in container.tests:
            # Apply method filter
            if filter_method is not None and test.method != filter_method:
                continue

            # Apply status filter
            if filter_status is not None and test.status != filter_status:
                continue

            # Apply requirements filter
            if filter_requirements and not all(
                req in test.tests_requirements for req in filter_requirements
            ):
                continue

            results.append(test)

        return results

    def get_test(self, spec_id: str, test_id: str) -> Test:
        """Get a single test by ID.

        Args:
            spec_id: The specification ID.
            test_id: The test ID.

        Returns:
            The test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
        """
        container = self._load_tests(spec_id)

        for test in container.tests:
            if test.id == test_id:
                return test

        msg = f"Test not found: {test_id}"
        raise TestNotFoundError(msg, test_id=test_id, spec_id=spec_id)

    def test_exists(self, spec_id: str, test_id: str) -> bool:
        """Check if a test exists.

        Args:
            spec_id: The specification ID.
            test_id: The test ID.

        Returns:
            True if the test exists.
        """
        try:
            container = self._load_tests(spec_id)
        except SpecNotFoundError:
            return False

        return any(test.id == test_id for test in container.tests)

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def add_test(  # noqa: PLR0913
        self,
        spec_id: str,
        method: TestMethod,
        title: str,
        tests_requirements: list[str],
        *,
        description: str | None = None,
        file: str | None = None,
        function: str | None = None,
        tags: list[str] | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Test:
        """Create a new test.

        Args:
            spec_id: The specification ID.
            method: The test method.
            title: Human-readable test title.
            tests_requirements: IDs of requirements this test verifies (non-empty).
            description: Full test description.
            file: Path to test implementation file.
            function: Name of test function or method.
            tags: Freeform tags for filtering.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The created test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If any requirement doesn't exist.
            SpecValidationError: If tests_requirements is empty.
        """
        # Verify spec exists (this will raise SpecNotFoundError if not)
        _ = self._spec_manager.get_spec(spec_id)

        # Validate tests_requirements is non-empty
        if not tests_requirements:
            msg = "tests_requirements cannot be empty"
            raise SpecValidationError(
                msg, spec_id=spec_id, field="tests_requirements", expected="non-empty"
            )

        # Validate all requirements exist
        self._validate_requirements_exist(spec_id, tests_requirements)

        # Load existing tests
        container = self._load_tests(spec_id)
        existing_ids = {test.id for test in container.tests}

        # Generate ID
        config = self._get_config()
        test_id = next_test_id(spec_id, method, existing_ids, config)

        # Create test
        now = datetime.now(UTC)
        test = Test(
            id=test_id,
            title=title,
            method=method,
            status=TestStatus.PENDING,
            created=now,
            updated=now,
            author=actor,
            tests_requirements=tuple(tests_requirements),
            description=description,
            file=file,
            function=function,
            last_run=None,
            last_result=None,
            tags=tuple(tags) if tags else (),
            last_value=None,
            threshold=None,
            perf_baseline=None,
            steps=(),
            expected_result=None,
            actual_result=None,
            tested_by=None,
            tested_on=None,
        )

        # Save original requirements state for rollback
        original_requirements: dict[str, tuple[str, ...]] = {}
        for req_id in tests_requirements:
            req = self._requirement_manager.get_requirement(spec_id, req_id)
            original_requirements[req_id] = req.verified_by

        # Write test
        new_tests = (*container.tests, test)
        self._write_tests(spec_id, new_tests)

        # Update requirements' verified_by with rollback on failure
        try:
            self._add_test_to_requirements(spec_id, test_id, tests_requirements)
        except Exception:
            # Rollback: remove the test we just added
            self._write_tests(spec_id, container.tests)
            raise

        # Record history
        self._record_history(spec_id, "test_created", actor, test_id, to_value=title)

        # Commit changes
        _ = self._commit(f"add test {spec_id}:{test_id}", session_id=session_id)

        return test

    def update_test(  # noqa: PLR0913
        self,
        spec_id: str,
        test_id: str,
        *,
        title: str | None = None,
        status: TestStatus | None = None,
        description: str | None = None,
        file: str | None = None,
        function: str | None = None,
        tags: list[str] | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Test:
        """Update an existing test.

        Note: This method does NOT update tests_requirements. Use link_test
        for modifying requirement links.

        Args:
            spec_id: The specification ID.
            test_id: The test ID to update.
            title: New title (optional).
            status: New status (optional).
            description: New description (optional).
            file: New file path (optional).
            function: New function name (optional).
            tags: New tags (replaces existing).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
        """
        # Get existing test
        existing = self.get_test(spec_id, test_id)

        # Merge updates with existing values
        new_title = title if title is not None else existing.title
        new_status = status if status is not None else existing.status
        new_desc = description if description is not None else existing.description
        new_file = file if file is not None else existing.file
        new_function = function if function is not None else existing.function
        new_tags = tuple(tags) if tags is not None else existing.tags

        # Create updated test
        now = datetime.now(UTC)
        updated = Test(
            id=existing.id,
            title=new_title,
            method=existing.method,
            status=new_status,
            created=existing.created,
            updated=now,
            author=existing.author,
            tests_requirements=existing.tests_requirements,
            description=new_desc,
            file=new_file,
            function=new_function,
            last_run=existing.last_run,
            last_result=existing.last_result,
            tags=new_tags,
            last_value=existing.last_value,
            threshold=existing.threshold,
            perf_baseline=existing.perf_baseline,
            steps=existing.steps,
            expected_result=existing.expected_result,
            actual_result=existing.actual_result,
            tested_by=existing.tested_by,
            tested_on=existing.tested_on,
        )

        # Replace in list
        container = self._load_tests(spec_id)
        new_tests = tuple(
            updated if test.id == test_id else test for test in container.tests
        )

        # Write updated tests
        self._write_tests(spec_id, new_tests)

        # Record history
        from_val = existing.status.value if status else None
        to_val = new_status.value if status else None
        self._record_history(
            spec_id,
            "test_updated",
            actor,
            test_id,
            from_value=from_val,
            to_value=to_val,
        )

        # Commit changes
        _ = self._commit(f"update test {spec_id}:{test_id}", session_id=session_id)

        return updated

    def delete_test(
        self,
        spec_id: str,
        test_id: str,
        actor: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Delete a test with bidirectional cleanup.

        This method removes the test and also removes references to it
        from any requirements that list it in verified_by.

        Args:
            spec_id: The specification ID.
            test_id: The test ID to delete.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
        """
        # Get existing test to verify it exists
        existing = self.get_test(spec_id, test_id)

        # Save original requirements state for rollback
        original_requirements: dict[str, tuple[str, ...]] = {}
        for req_id in existing.tests_requirements:
            try:
                req = self._requirement_manager.get_requirement(spec_id, req_id)
                original_requirements[req_id] = req.verified_by
            except RequirementNotFoundError:
                # Requirement may have been deleted; skip it
                pass

        # Remove test from requirements' verified_by first
        # Track which requirements were updated for proper rollback
        requirements_updated: list[str] = []
        try:
            for req_id in existing.tests_requirements:
                try:
                    self._remove_test_from_requirements(spec_id, test_id, [req_id])
                    requirements_updated.append(req_id)
                except RequirementNotFoundError:
                    continue
        except Exception:
            # Rollback: restore requirements that were already updated
            for req_id in requirements_updated:
                if req_id in original_requirements:
                    try:
                        req = self._requirement_manager.get_requirement(spec_id, req_id)
                        self._update_requirement_verified_by(
                            spec_id, req, list(original_requirements[req_id])
                        )
                    except RequirementNotFoundError:
                        pass
            raise

        # Remove test from list with rollback on failure
        container = self._load_tests(spec_id)
        try:
            new_tests = tuple(test for test in container.tests if test.id != test_id)
            self._write_tests(spec_id, new_tests)
        except Exception:
            # Rollback: restore requirements' verified_by
            for req_id in requirements_updated:
                if req_id in original_requirements:
                    try:
                        req = self._requirement_manager.get_requirement(spec_id, req_id)
                        self._update_requirement_verified_by(
                            spec_id, req, list(original_requirements[req_id])
                        )
                    except RequirementNotFoundError:
                        pass
            raise

        # Record history
        self._record_history(
            spec_id, "test_deleted", actor, test_id, from_value=existing.title
        )

        # Commit changes
        _ = self._commit(f"delete test {spec_id}:{test_id}", session_id=session_id)

    def link_test(
        self,
        spec_id: str,
        test_id: str,
        req_ids: list[str],
        actor: str,
        *,
        session_id: str | None = None,
    ) -> Test:
        """Update the requirements a test verifies.

        Args:
            spec_id: The specification ID.
            test_id: The test ID to update.
            req_ids: New list of requirement IDs (non-empty).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
            RequirementNotFoundError: If any requirement doesn't exist.
            SpecValidationError: If req_ids is empty.
        """
        # Validate req_ids is non-empty
        if not req_ids:
            msg = "req_ids cannot be empty"
            raise SpecValidationError(
                msg, spec_id=spec_id, field="req_ids", expected="non-empty"
            )

        # Get existing test
        existing = self.get_test(spec_id, test_id)

        # Validate all new requirements exist
        self._validate_requirements_exist(spec_id, req_ids)

        # Calculate diff
        old_set = set(existing.tests_requirements)
        new_set = set(req_ids)
        to_add = new_set - old_set
        to_remove = old_set - new_set

        # Save original requirements state for rollback
        original_requirements: dict[str, tuple[str, ...]] = {}
        for req_id in old_set | new_set:
            try:
                req = self._requirement_manager.get_requirement(spec_id, req_id)
                original_requirements[req_id] = req.verified_by
            except RequirementNotFoundError:
                pass

        # Update requirements' verified_by
        try:
            self._remove_test_from_requirements(spec_id, test_id, list(to_remove))
            self._add_test_to_requirements(spec_id, test_id, list(to_add))
        except Exception:
            # Rollback requirements on failure
            for req_id, verified_by in original_requirements.items():
                try:
                    req = self._requirement_manager.get_requirement(spec_id, req_id)
                    self._update_requirement_verified_by(
                        spec_id, req, list(verified_by)
                    )
                except RequirementNotFoundError:
                    pass
            raise

        # Create updated test
        now = datetime.now(UTC)
        updated = Test(
            id=existing.id,
            title=existing.title,
            method=existing.method,
            status=existing.status,
            created=existing.created,
            updated=now,
            author=existing.author,
            tests_requirements=tuple(req_ids),
            description=existing.description,
            file=existing.file,
            function=existing.function,
            last_run=existing.last_run,
            last_result=existing.last_result,
            tags=existing.tags,
            last_value=existing.last_value,
            threshold=existing.threshold,
            perf_baseline=existing.perf_baseline,
            steps=existing.steps,
            expected_result=existing.expected_result,
            actual_result=existing.actual_result,
            tested_by=existing.tested_by,
            tested_on=existing.tested_on,
        )

        # Replace in list and write
        container = self._load_tests(spec_id)
        new_tests = tuple(
            updated if test.id == test_id else test for test in container.tests
        )

        try:
            self._write_tests(spec_id, new_tests)
        except Exception:
            # Rollback requirements on failure
            for req_id, verified_by in original_requirements.items():
                try:
                    req = self._requirement_manager.get_requirement(spec_id, req_id)
                    self._update_requirement_verified_by(
                        spec_id, req, list(verified_by)
                    )
                except RequirementNotFoundError:
                    pass
            raise

        # Record history
        old_reqs = ",".join(sorted(existing.tests_requirements))
        new_reqs = ",".join(sorted(req_ids))
        self._record_history(
            spec_id,
            "test_linked",
            actor,
            test_id,
            from_value=old_reqs,
            to_value=new_reqs,
        )

        # Commit changes
        _ = self._commit(f"link test {spec_id}:{test_id}", session_id=session_id)

        return updated

    def _record_run_impl(  # noqa: PLR0913
        self,
        spec_id: str,
        test_id: str,
        result: TestResult,
        *,
        value: float | None = None,
        duration_ms: float | None = None,
        message: str | None = None,
        actor: str,
    ) -> Test:
        """Internal implementation of record_run without commit.

        Args:
            spec_id: The specification ID.
            test_id: The test ID.
            result: The test result.
            value: Performance value for performance tests.
            duration_ms: Test duration in milliseconds.
            message: Optional message (e.g., error message).
            actor: The actor performing the action (for history).

        Returns:
            The updated test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
        """
        # Get existing test
        existing = self.get_test(spec_id, test_id)

        # Map result to status
        new_status = self._result_to_status(result)

        # Create updated test
        now = datetime.now(UTC)
        updated = Test(
            id=existing.id,
            title=existing.title,
            method=existing.method,
            status=new_status,
            created=existing.created,
            updated=now,
            author=existing.author,
            tests_requirements=existing.tests_requirements,
            description=existing.description,
            file=existing.file,
            function=existing.function,
            last_run=now,
            last_result=result,
            tags=existing.tags,
            last_value=value if value is not None else existing.last_value,
            threshold=existing.threshold,
            perf_baseline=existing.perf_baseline,
            steps=existing.steps,
            expected_result=existing.expected_result,
            actual_result=message if message else existing.actual_result,
            tested_by=existing.tested_by,
            tested_on=existing.tested_on,
        )

        # Replace in list
        container = self._load_tests(spec_id)
        new_tests = tuple(
            updated if test.id == test_id else test for test in container.tests
        )

        # Write updated tests
        self._write_tests(spec_id, new_tests)

        # Record history with duration if provided
        to_value = result.value
        if duration_ms is not None:
            to_value = f"{result.value} ({duration_ms:.0f}ms)"

        self._record_history(
            spec_id,
            "test_run",
            actor,
            test_id,
            from_value=existing.status.value,
            to_value=to_value,
        )

        return updated

    def record_run(  # noqa: PLR0913
        self,
        spec_id: str,
        test_id: str,
        result: TestResult,
        *,
        value: float | None = None,
        duration_ms: float | None = None,
        message: str | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Test:
        """Record a test run result.

        Args:
            spec_id: The specification ID.
            test_id: The test ID.
            result: The test result.
            value: Performance value for performance tests.
            duration_ms: Test duration in milliseconds.
            message: Optional message (e.g., error message).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated test.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            TestNotFoundError: If the test doesn't exist.
        """
        updated = self._record_run_impl(
            spec_id,
            test_id,
            result,
            value=value,
            duration_ms=duration_ms,
            message=message,
            actor=actor,
        )

        # Commit changes
        _ = self._commit(f"record run {spec_id}:{test_id}", session_id=session_id)

        return updated

    def sync(
        self,
        spec_id: str,
        pytest_results: PytestResults,
        actor: str,
        *,
        session_id: str | None = None,
    ) -> SyncResult:
        """Synchronize spec tests with pytest results.

        Matches pytest results to spec tests by file + function.
        Only matches tests that have BOTH file AND function set.

        Args:
            spec_id: The specification ID.
            pytest_results: Parsed pytest results.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            SyncResult with counts of updated, orphaned, and skipped tests.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Load tests
        container = self._load_tests(spec_id)

        # Build lookup index: (file, function) -> test
        test_lookup: dict[tuple[str, str], Test] = {}
        skipped_no_file = 0
        for test in container.tests:
            if test.file and test.function:
                test_lookup[(test.file, test.function)] = test
            else:
                skipped_no_file += 1

        # Track matched pytest tests
        matched_pytest_tests: set[str] = set()
        updated = 0
        errors: list[str] = []
        updated_tests: dict[str, Test] = {}

        # Match and update
        for pytest_test in pytest_results.tests:
            file_path, function = self._parse_pytest_node_id(pytest_test.node_id)
            if file_path is None or function is None:
                continue

            key = (file_path, function)
            if key in test_lookup:
                matched_pytest_tests.add(pytest_test.node_id)
                spec_test = test_lookup[key]

                # Map pytest outcome to TestResult
                outcome_mapping = {
                    "passed": TestResult.PASS,
                    "failed": TestResult.FAIL,
                    "skipped": TestResult.SKIP,
                    "error": TestResult.ERROR,
                }
                result = outcome_mapping.get(pytest_test.outcome.lower())
                if result is None:
                    msg = (
                        f"Unknown pytest outcome '{pytest_test.outcome}' "
                        f"for {pytest_test.node_id}"
                    )
                    errors.append(msg)
                    continue

                try:
                    updated_test = self._record_run_impl(
                        spec_id,
                        spec_test.id,
                        result,
                        duration_ms=pytest_test.duration * 1000,
                        message=pytest_test.message,
                        actor=actor,
                    )
                    updated_tests[spec_test.id] = updated_test
                    # Only count as updated if status actually changed
                    if updated_test.status != spec_test.status:
                        updated += 1
                except (SpecNotFoundError, TestNotFoundError) as e:
                    errors.append(f"Failed to update {spec_test.id}: {e}")

        # Count orphaned (pytest tests not matched to spec tests)
        orphaned = len(pytest_results.tests) - len(matched_pytest_tests)

        # Commit changes if any tests were synced (regardless of status change)
        if updated_tests:
            _ = self._commit(f"sync tests {spec_id}", session_id=session_id)

        return SyncResult(
            updated=updated,
            orphaned=orphaned,
            skipped_no_file=skipped_no_file,
            errors=tuple(errors),
        )
