# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""Requirement manager for CRUD operations on requirements.

This module provides the RequirementManager class for managing requirements
within specifications. It handles requirement creation, updates, deletion,
and maintains bidirectional links with tests.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

from oaps.exceptions import (
    RequirementNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec._ids import next_requirement_id, next_sub_requirement_id
from oaps.spec._io import append_jsonl, read_json, write_json_atomic
from oaps.spec._models import (
    Requirement,
    RequirementsContainer,
    RequirementStatus,
    RequirementType,
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
    from oaps.spec._spec_manager import SpecManager

__all__ = ["RequirementManager"]

# Container schema version
_CONTAINER_VERSION = 1


class RequirementManager:
    """Manager for CRUD operations on requirements within specifications.

    The RequirementManager provides methods for creating, reading, updating,
    and deleting requirements. It maintains bidirectional links with tests
    and supports hierarchical sub-requirements.

    Attributes:
        _spec_manager: The specification manager for accessing spec data.
        _config: Specification configuration.
        _requirements_cache: Cache of loaded requirements containers.
        _tests_cache: Cache of loaded tests containers.
    """

    __slots__: Final = (
        "_config",
        "_oaps_repo",
        "_requirements_cache",
        "_spec_manager",
        "_tests_cache",
    )

    _config: SpecConfiguration | None
    _oaps_repo: OapsRepository | None
    _requirements_cache: dict[str, RequirementsContainer]
    _spec_manager: SpecManager
    _tests_cache: dict[str, TestsContainer]

    def __init__(
        self,
        spec_manager: SpecManager,
        *,
        oaps_repo: OapsRepository | None = None,
    ) -> None:
        """Initialize the requirement manager.

        Args:
            spec_manager: The specification manager for accessing spec data.
            oaps_repo: Repository for committing changes. If None, falls back
                to spec_manager's repository if available.
        """
        self._spec_manager = spec_manager
        self._oaps_repo = (
            oaps_repo
            if oaps_repo is not None
            else getattr(spec_manager, "_oaps_repo", None)
        )
        self._config = None
        self._requirements_cache = {}
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

    def _requirements_path(self, spec_id: str) -> Path:
        """Get the path to the requirements.json file for a spec.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the requirements.json file.
        """
        return self._get_spec_dir(spec_id) / "requirements.json"

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
            self._requirements_cache.clear()
            self._tests_cache.clear()
        else:
            _ = self._requirements_cache.pop(spec_id, None)
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

    def _load_requirements(self, spec_id: str) -> RequirementsContainer:
        """Load requirements from disk.

        Args:
            spec_id: The specification ID.

        Returns:
            The requirements container.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        if spec_id in self._requirements_cache:
            return self._requirements_cache[spec_id]

        path = self._requirements_path(spec_id)

        if not path.exists():
            # Return empty container
            container = RequirementsContainer(
                version=_CONTAINER_VERSION,
                spec_id=spec_id,
                updated=datetime.now(UTC),
                requirements=(),
            )
            self._requirements_cache[spec_id] = container
            return container

        data = read_json(path)
        requirements = tuple(
            self._dict_to_requirement(req_data)
            for req_data in data.get("requirements", [])
        )
        container = RequirementsContainer(
            version=data.get("version", _CONTAINER_VERSION),
            spec_id=data.get("spec_id", spec_id),
            updated=datetime.fromisoformat(data["updated"]),
            requirements=requirements,
        )
        self._requirements_cache[spec_id] = container
        return container

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

    def _write_requirements(
        self, spec_id: str, requirements: tuple[Requirement, ...]
    ) -> None:
        """Write requirements to disk atomically.

        Args:
            spec_id: The specification ID.
            requirements: The requirements to write.
        """
        path = self._requirements_path(spec_id)
        now = datetime.now(UTC)
        data: dict[str, Any] = {
            "version": _CONTAINER_VERSION,
            "spec_id": spec_id,
            "updated": now.isoformat(),
            "requirements": [self._requirement_to_dict(req) for req in requirements],
        }
        write_json_atomic(path, data)
        _ = self._requirements_cache.pop(spec_id, None)

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
        req_id: str,
        *,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        """Record an event to the per-spec history log.

        Args:
            spec_id: The specification ID.
            event: The event type.
            actor: The actor who performed the action.
            req_id: The affected requirement ID.
            from_value: The previous value (for updates).
            to_value: The new value (for updates).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "actor": actor,
            "id": req_id,
        }
        if from_value is not None:
            entry["from_value"] = from_value
        if to_value is not None:
            entry["to_value"] = to_value

        append_jsonl(self._history_path(spec_id), entry)

    def _dict_to_requirement(self, data: dict[str, Any]) -> Requirement:
        """Convert a dictionary to a Requirement.

        Args:
            data: Dictionary from JSON storage.

        Returns:
            Requirement instance.
        """
        created = data["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = data["updated"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        return Requirement(
            id=data["id"],
            title=data["title"],
            req_type=RequirementType(data["req_type"]),
            status=RequirementStatus(data["status"]),
            created=created,
            updated=updated,
            author=data["author"],
            description=data["description"],
            rationale=data.get("rationale"),
            acceptance_criteria=tuple(data.get("acceptance_criteria", [])),
            verified_by=tuple(data.get("verified_by", [])),
            depends_on=tuple(data.get("depends_on", [])),
            tags=tuple(data.get("tags", [])),
            source_section=data.get("source_section"),
            parent=data.get("parent"),
            subtype=data.get("subtype"),
            scale=data.get("scale"),
            meter=data.get("meter"),
            baseline=data.get("baseline"),
            goal=data.get("goal"),
            stretch=data.get("stretch"),
            fail=data.get("fail"),
        )

    def _requirement_to_dict(self, req: Requirement) -> dict[str, Any]:  # noqa: PLR0912
        """Convert a Requirement to a dictionary for JSON storage.

        Args:
            req: The Requirement to convert.

        Returns:
            Dictionary representation for JSON serialization.
        """
        data: dict[str, Any] = {
            "id": req.id,
            "title": req.title,
            "req_type": req.req_type.value,
            "status": req.status.value,
            "created": req.created.isoformat(),
            "updated": req.updated.isoformat(),
            "author": req.author,
            "description": req.description,
        }

        if req.rationale:
            data["rationale"] = req.rationale
        if req.acceptance_criteria:
            data["acceptance_criteria"] = list(req.acceptance_criteria)
        if req.verified_by:
            data["verified_by"] = list(req.verified_by)
        if req.depends_on:
            data["depends_on"] = list(req.depends_on)
        if req.tags:
            data["tags"] = list(req.tags)
        if req.source_section:
            data["source_section"] = req.source_section
        if req.parent:
            data["parent"] = req.parent
        if req.subtype:
            data["subtype"] = req.subtype
        if req.scale:
            data["scale"] = req.scale
        if req.meter:
            data["meter"] = req.meter
        if req.baseline is not None:
            data["baseline"] = req.baseline
        if req.goal is not None:
            data["goal"] = req.goal
        if req.stretch is not None:
            data["stretch"] = req.stretch
        if req.fail is not None:
            data["fail"] = req.fail

        return data

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

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def list_requirements(
        self,
        spec_id: str,
        *,
        filter_type: RequirementType | None = None,
        filter_status: RequirementStatus | None = None,
        filter_tags: list[str] | None = None,
    ) -> list[Requirement]:
        """List requirements with optional filtering.

        Args:
            spec_id: The specification ID.
            filter_type: Filter by requirement type.
            filter_status: Filter by status.
            filter_tags: Filter by tags (requirements must have all listed tags).

        Returns:
            List of matching requirements.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        container = self._load_requirements(spec_id)

        results: list[Requirement] = []
        for req in container.requirements:
            # Apply type filter
            if filter_type is not None and req.req_type != filter_type:
                continue

            # Apply status filter
            if filter_status is not None and req.status != filter_status:
                continue

            # Apply tags filter
            if filter_tags and not all(tag in req.tags for tag in filter_tags):
                continue

            results.append(req)

        return results

    def get_requirement(self, spec_id: str, req_id: str) -> Requirement:
        """Get a single requirement by ID.

        Args:
            spec_id: The specification ID.
            req_id: The requirement ID.

        Returns:
            The requirement.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the requirement doesn't exist.
        """
        container = self._load_requirements(spec_id)

        for req in container.requirements:
            if req.id == req_id:
                return req

        msg = f"Requirement not found: {req_id}"
        raise RequirementNotFoundError(msg, requirement_id=req_id, spec_id=spec_id)

    def requirement_exists(self, spec_id: str, req_id: str) -> bool:
        """Check if a requirement exists.

        Args:
            spec_id: The specification ID.
            req_id: The requirement ID.

        Returns:
            True if the requirement exists.
        """
        try:
            container = self._load_requirements(spec_id)
        except SpecNotFoundError:
            return False

        return any(req.id == req_id for req in container.requirements)

    def get_children(self, spec_id: str, parent_id: str) -> list[Requirement]:
        """Get sub-requirements of a parent requirement.

        Args:
            spec_id: The specification ID.
            parent_id: The parent requirement ID.

        Returns:
            List of child requirements.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the parent requirement doesn't exist.
        """
        # Verify parent exists
        _ = self.get_requirement(spec_id, parent_id)

        container = self._load_requirements(spec_id)
        return [req for req in container.requirements if req.parent == parent_id]

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def add_requirement(  # noqa: PLR0913
        self,
        spec_id: str,
        req_type: RequirementType,
        title: str,
        description: str,
        *,
        rationale: str | None = None,
        acceptance_criteria: list[str] | None = None,
        depends_on: list[str] | None = None,
        tags: list[str] | None = None,
        source_section: str | None = None,
        parent: str | None = None,
        subtype: str | None = None,
        scale: str | None = None,
        meter: str | None = None,
        baseline: float | None = None,
        goal: float | None = None,
        stretch: float | None = None,
        fail: float | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Requirement:
        """Create a new requirement.

        Args:
            spec_id: The specification ID.
            req_type: The requirement type.
            title: Human-readable requirement title.
            description: Full requirement description.
            rationale: Explanation of why this requirement exists.
            acceptance_criteria: Criteria for verifying the requirement.
            depends_on: IDs of requirements this depends on.
            tags: Freeform tags for filtering.
            source_section: Section of source document where requirement originated.
            parent: ID of parent requirement for sub-requirements.
            subtype: Further categorization within type.
            scale: Planguage scale definition for measurement.
            meter: Planguage meter definition for measurement method.
            baseline: Planguage baseline value (current state).
            goal: Planguage goal value (target to achieve).
            stretch: Planguage stretch value (aspirational target).
            fail: Planguage fail value (unacceptable threshold).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The created requirement.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the parent requirement doesn't exist.
            SpecValidationError: If validation fails.
        """
        # Verify spec exists (this will raise SpecNotFoundError if not)
        _ = self._spec_manager.get_spec(spec_id)

        # Load existing requirements
        container = self._load_requirements(spec_id)
        existing_ids = {req.id for req in container.requirements}

        # Validate parent exists if specified
        if parent is not None:
            parent_req = next(
                (req for req in container.requirements if req.id == parent), None
            )
            if parent_req is None:
                msg = f"Parent requirement not found: {parent}"
                raise RequirementNotFoundError(
                    msg, requirement_id=parent, spec_id=spec_id
                )
            # Nested sub-requirements not supported: parent cannot be a sub-requirement
            if parent_req.parent is not None:
                msg = (
                    f"Nested sub-requirements not supported: "
                    f"'{parent}' is already a sub-requirement of '{parent_req.parent}'"
                )
                raise SpecValidationError(
                    msg, spec_id=spec_id, field="parent", value=parent
                )

        # Generate ID
        config = self._get_config()
        if parent is not None:
            req_id = next_sub_requirement_id(parent, existing_ids, config.numbering)
        else:
            req_id = next_requirement_id(spec_id, req_type, existing_ids, config)

        # Create requirement
        now = datetime.now(UTC)
        acceptance = tuple(acceptance_criteria) if acceptance_criteria else ()
        requirement = Requirement(
            id=req_id,
            title=title,
            req_type=req_type,
            status=RequirementStatus.PROPOSED,
            created=now,
            updated=now,
            author=actor,
            description=description,
            rationale=rationale,
            acceptance_criteria=acceptance,
            verified_by=(),
            depends_on=tuple(depends_on) if depends_on else (),
            tags=tuple(tags) if tags else (),
            source_section=source_section,
            parent=parent,
            subtype=subtype,
            scale=scale,
            meter=meter,
            baseline=baseline,
            goal=goal,
            stretch=stretch,
            fail=fail,
        )

        # Write updated requirements
        new_requirements = (*container.requirements, requirement)
        self._write_requirements(spec_id, new_requirements)

        # Record history
        self._record_history(
            spec_id, "requirement_created", actor, req_id, to_value=title
        )

        # Commit changes
        _ = self._commit(f"add requirement {spec_id}:{req_id}", session_id=session_id)

        return requirement

    def update_requirement(  # noqa: PLR0913
        self,
        spec_id: str,
        req_id: str,
        *,
        title: str | None = None,
        status: RequirementStatus | None = None,
        description: str | None = None,
        rationale: str | None = None,
        acceptance_criteria: list[str] | None = None,
        depends_on: list[str] | None = None,
        tags: list[str] | None = None,
        source_section: str | None = None,
        subtype: str | None = None,
        scale: str | None = None,
        meter: str | None = None,
        baseline: float | None = None,
        goal: float | None = None,
        stretch: float | None = None,
        fail: float | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Requirement:
        """Update an existing requirement.

        Args:
            spec_id: The specification ID.
            req_id: The requirement ID to update.
            title: New title (optional).
            status: New status (optional).
            description: New description (optional).
            rationale: New rationale (optional).
            acceptance_criteria: New acceptance criteria (replaces existing).
            depends_on: New dependencies (replaces existing).
            tags: New tags (replaces existing).
            source_section: New source section (optional).
            subtype: New subtype (optional).
            scale: New Planguage scale (optional).
            meter: New Planguage meter (optional).
            baseline: New Planguage baseline (optional).
            goal: New Planguage goal (optional).
            stretch: New Planguage stretch (optional).
            fail: New Planguage fail (optional).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated requirement.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the requirement doesn't exist.
        """
        # Get existing requirement
        existing = self.get_requirement(spec_id, req_id)

        # Merge updates with existing values
        new_title = title if title is not None else existing.title
        new_status = status if status is not None else existing.status
        new_desc = description if description is not None else existing.description
        new_rationale = rationale if rationale is not None else existing.rationale
        new_acceptance = (
            tuple(acceptance_criteria)
            if acceptance_criteria is not None
            else existing.acceptance_criteria
        )
        new_depends = (
            tuple(depends_on) if depends_on is not None else existing.depends_on
        )
        new_tags = tuple(tags) if tags is not None else existing.tags
        new_source = (
            source_section if source_section is not None else existing.source_section
        )
        new_subtype = subtype if subtype is not None else existing.subtype
        new_scale = scale if scale is not None else existing.scale
        new_meter = meter if meter is not None else existing.meter
        new_baseline = baseline if baseline is not None else existing.baseline
        new_goal = goal if goal is not None else existing.goal
        new_stretch = stretch if stretch is not None else existing.stretch
        new_fail = fail if fail is not None else existing.fail

        # Create updated requirement
        now = datetime.now(UTC)
        updated = Requirement(
            id=existing.id,
            title=new_title,
            req_type=existing.req_type,
            status=new_status,
            created=existing.created,
            updated=now,
            author=existing.author,
            description=new_desc,
            rationale=new_rationale,
            acceptance_criteria=new_acceptance,
            verified_by=existing.verified_by,
            depends_on=new_depends,
            tags=new_tags,
            source_section=new_source,
            parent=existing.parent,
            subtype=new_subtype,
            scale=new_scale,
            meter=new_meter,
            baseline=new_baseline,
            goal=new_goal,
            stretch=new_stretch,
            fail=new_fail,
        )

        # Replace in list
        container = self._load_requirements(spec_id)
        new_requirements = tuple(
            updated if req.id == req_id else req for req in container.requirements
        )

        # Write updated requirements
        self._write_requirements(spec_id, new_requirements)

        # Record history
        from_val = existing.status.value if status else None
        to_val = new_status.value if status else None
        self._record_history(
            spec_id,
            "requirement_updated",
            actor,
            req_id,
            from_value=from_val,
            to_value=to_val,
        )

        # Commit changes
        _ = self._commit(
            f"update requirement {spec_id}:{req_id}", session_id=session_id
        )

        return updated

    def delete_requirement(
        self,
        spec_id: str,
        req_id: str,
        actor: str,
        *,
        session_id: str | None = None,
    ) -> None:
        """Delete a requirement with bidirectional cleanup.

        This method removes the requirement and also removes references to it
        from any tests that verify this requirement.

        Args:
            spec_id: The specification ID.
            req_id: The requirement ID to delete.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the requirement doesn't exist.
            SpecValidationError: If the requirement has child sub-requirements.
        """
        # Get existing requirement to verify it exists
        existing = self.get_requirement(spec_id, req_id)

        # Check for children (sub-requirements)
        container = self._load_requirements(spec_id)
        children = [req for req in container.requirements if req.parent == req_id]
        if children:
            child_ids = ", ".join(child.id for child in children)
            msg = f"Cannot delete requirement {req_id}: has children ({child_ids})"
            raise SpecValidationError(
                msg, spec_id=spec_id, field="parent", value=req_id
            )

        # Load original tests for potential rollback
        tests_container = self._load_tests(spec_id)
        original_tests = tests_container.tests

        # Update tests to remove references to this requirement
        updated_tests = self._remove_requirement_from_tests(
            tests_container.tests, req_id
        )
        tests_modified = updated_tests != list(tests_container.tests)

        # Write updated tests first if there were modifications
        if tests_modified:
            self._write_tests(spec_id, tuple(updated_tests))

        # Remove requirement from list with error recovery
        try:
            new_reqs = tuple(req for req in container.requirements if req.id != req_id)
            self._write_requirements(spec_id, new_reqs)
        except Exception:
            # Rollback: restore original tests if requirements write failed
            if tests_modified:
                self._write_tests(spec_id, original_tests)
            raise

        # Record history
        self._record_history(
            spec_id, "requirement_deleted", actor, req_id, from_value=existing.title
        )

        # Commit changes
        _ = self._commit(
            f"delete requirement {spec_id}:{req_id}", session_id=session_id
        )

    def _remove_requirement_from_tests(
        self, tests: tuple[Test, ...], req_id: str
    ) -> list[Test]:
        """Remove a requirement ID from all tests that reference it.

        Args:
            tests: The tests to update.
            req_id: The requirement ID to remove.

        Returns:
            Updated list of tests with the requirement ID removed.
        """
        updated_tests: list[Test] = []
        for test in tests:
            if req_id in test.tests_requirements:
                new_reqs = tuple(r for r in test.tests_requirements if r != req_id)
                updated_test = Test(
                    id=test.id,
                    title=test.title,
                    method=test.method,
                    status=test.status,
                    created=test.created,
                    updated=datetime.now(UTC),
                    author=test.author,
                    tests_requirements=new_reqs,
                    description=test.description,
                    file=test.file,
                    function=test.function,
                    last_run=test.last_run,
                    last_result=test.last_result,
                    tags=test.tags,
                    last_value=test.last_value,
                    threshold=test.threshold,
                    perf_baseline=test.perf_baseline,
                    steps=test.steps,
                    expected_result=test.expected_result,
                    actual_result=test.actual_result,
                    tested_by=test.tested_by,
                    tested_on=test.tested_on,
                )
                updated_tests.append(updated_test)
            else:
                updated_tests.append(test)
        return updated_tests

    def link_requirement(  # noqa: PLR0913
        self,
        spec_id: str,
        req_id: str,
        *,
        commit_sha: str | None = None,
        pr_number: int | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Requirement:
        """Link a requirement to its implementation.

        At least one of commit_sha or pr_number must be provided.

        Args:
            spec_id: The specification ID.
            req_id: The requirement ID.
            commit_sha: Git commit SHA of the implementation.
            pr_number: GitHub PR number of the implementation.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated requirement.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            RequirementNotFoundError: If the requirement doesn't exist.
            SpecValidationError: If neither commit_sha nor pr_number is provided.
        """
        # Validate at least one link is provided
        if commit_sha is None and pr_number is None:
            msg = "At least one of commit_sha or pr_number is required"
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="link",
                expected="commit_sha or pr_number",
            )

        # Get existing requirement
        existing = self.get_requirement(spec_id, req_id)

        # Update status to IMPLEMENTING if currently APPROVED
        new_status = existing.status
        if existing.status == RequirementStatus.APPROVED:
            new_status = RequirementStatus.IMPLEMENTING

        # Create updated requirement
        now = datetime.now(UTC)
        updated = Requirement(
            id=existing.id,
            title=existing.title,
            req_type=existing.req_type,
            status=new_status,
            created=existing.created,
            updated=now,
            author=existing.author,
            description=existing.description,
            rationale=existing.rationale,
            acceptance_criteria=existing.acceptance_criteria,
            verified_by=existing.verified_by,
            depends_on=existing.depends_on,
            tags=existing.tags,
            source_section=existing.source_section,
            parent=existing.parent,
            subtype=existing.subtype,
            scale=existing.scale,
            meter=existing.meter,
            baseline=existing.baseline,
            goal=existing.goal,
            stretch=existing.stretch,
            fail=existing.fail,
        )

        # Replace in list
        container = self._load_requirements(spec_id)
        new_requirements = tuple(
            updated if req.id == req_id else req for req in container.requirements
        )

        # Write updated requirements
        self._write_requirements(spec_id, new_requirements)

        # Build link info for history
        link_info_parts: list[str] = []
        if commit_sha:
            link_info_parts.append(f"commit:{commit_sha[:8]}")
        if pr_number:
            link_info_parts.append(f"pr:{pr_number}")
        link_info = ", ".join(link_info_parts)

        # Record history
        self._record_history(
            spec_id, "requirement_linked", actor, req_id, to_value=link_info
        )

        # Commit changes
        _ = self._commit(f"link requirement {spec_id}:{req_id}", session_id=session_id)

        return updated
