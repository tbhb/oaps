# pyright: reportAny=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false
"""Tests for QueryManager operations."""

from datetime import UTC, datetime
from types import MappingProxyType
from unittest.mock import MagicMock, Mock

import pytest

from oaps.exceptions import SpecNotFoundError
from oaps.spec import (
    CoverageReport,
    DependencyGraph,
    OrphanReport,
    ProgressReport,
    QueryManager,
    RelationshipGraph,
    Relationships,
    RelationshipType,
    Requirement,
    RequirementStatus,
    RequirementType,
    SpecMetadata,
    SpecStatus,
    SpecSummary,
    SpecType,
)

# Alias these to avoid pytest collection conflicts
from oaps.spec._models import (
    Test as SpecTest,
    TestMethod as SpecTestMethod,
    TestResult as SpecTestResult,
    TestStatus as SpecTestStatus,
)


@pytest.fixture
def mock_spec_manager() -> Mock:
    """Create a mock SpecManager."""
    return MagicMock()


@pytest.fixture
def mock_requirement_manager() -> Mock:
    """Create a mock RequirementManager."""
    return MagicMock()


@pytest.fixture
def mock_test_manager() -> Mock:
    """Create a mock TestManager."""
    return MagicMock()


@pytest.fixture
def mock_artifact_manager() -> Mock:
    """Create a mock ArtifactManager."""
    return MagicMock()


@pytest.fixture
def query_manager(
    mock_spec_manager: Mock,
    mock_requirement_manager: Mock,
    mock_test_manager: Mock,
) -> QueryManager:
    """Create a QueryManager with mock dependencies."""
    return QueryManager(
        spec_manager=mock_spec_manager,
        requirement_manager=mock_requirement_manager,
        test_manager=mock_test_manager,
    )


@pytest.fixture
def query_manager_with_artifacts(
    mock_spec_manager: Mock,
    mock_requirement_manager: Mock,
    mock_test_manager: Mock,
    mock_artifact_manager: Mock,
) -> QueryManager:
    """Create a QueryManager with artifact manager."""
    return QueryManager(
        spec_manager=mock_spec_manager,
        requirement_manager=mock_requirement_manager,
        test_manager=mock_test_manager,
        artifact_manager=mock_artifact_manager,
    )


def create_requirement(
    req_id: str,
    req_type: RequirementType = RequirementType.FUNCTIONAL,
    status: RequirementStatus = RequirementStatus.PROPOSED,
) -> Requirement:
    """Helper to create a Requirement with minimal data."""
    return Requirement(
        id=req_id,
        req_type=req_type,
        title=f"Requirement {req_id}",
        description="Description",
        status=status,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
        author="test-author",
    )


def create_spec_test(
    test_id: str,
    method: SpecTestMethod = SpecTestMethod.UNIT,
    result: SpecTestResult = SpecTestResult.PASS,
    requirements: tuple[str, ...] = (),
    file: str | None = "test_file.py",
    function: str | None = "test_function",
) -> SpecTest:
    """Helper to create a SpecTest with minimal data."""
    return SpecTest(
        id=test_id,
        title=f"Test {test_id}",
        method=method,
        status=SpecTestStatus.IMPLEMENTED,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
        author="test-author",
        tests_requirements=requirements,
        last_result=result,
        file=file,
        function=function,
    )


def create_spec_summary(
    spec_id: str,
    title: str = "Spec",
    status: SpecStatus = SpecStatus.DRAFT,
    spec_type: SpecType = SpecType.FEATURE,
    depends_on: tuple[str, ...] = (),
) -> SpecSummary:
    """Helper to create a SpecSummary."""
    return SpecSummary(
        id=spec_id,
        slug=f"test-{spec_id.lower()}",
        title=title,
        spec_type=spec_type,
        status=status,
        depends_on=depends_on,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
    )


def create_spec_metadata(
    spec_id: str,
    title: str = "Spec",
    status: SpecStatus = SpecStatus.DRAFT,
    spec_type: SpecType = SpecType.FEATURE,
    relationships: Relationships | None = None,
) -> SpecMetadata:
    """Helper to create SpecMetadata."""
    if relationships is None:
        relationships = Relationships(
            depends_on=(),
            extends=None,
            supersedes=None,
            integrates=(),
        )
    return SpecMetadata(
        id=spec_id,
        slug=f"test-{spec_id.lower()}",
        title=title,
        spec_type=spec_type,
        status=status,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
        relationships=relationships,
    )


class TestQueryManagerInit:
    def test_accepts_managers(
        self,
        mock_spec_manager: Mock,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        manager = QueryManager(
            spec_manager=mock_spec_manager,
            requirement_manager=mock_requirement_manager,
            test_manager=mock_test_manager,
        )
        assert manager._spec_manager is mock_spec_manager
        assert manager._requirement_manager is mock_requirement_manager
        assert manager._test_manager is mock_test_manager
        assert manager._artifact_manager is None

    def test_accepts_optional_artifact_manager(
        self,
        mock_spec_manager: Mock,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
        mock_artifact_manager: Mock,
    ) -> None:
        manager = QueryManager(
            spec_manager=mock_spec_manager,
            requirement_manager=mock_requirement_manager,
            test_manager=mock_test_manager,
            artifact_manager=mock_artifact_manager,
        )
        assert manager._artifact_manager is mock_artifact_manager


class TestProgress:
    def test_returns_progress_report_for_empty_spec(
        self, query_manager: QueryManager, mock_requirement_manager: Mock
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []

        result = query_manager.progress("SPEC-0001")

        assert isinstance(result, ProgressReport)
        assert result.spec_id == "SPEC-0001"
        assert result.total_requirements == 0
        assert result.implemented_requirements == 0
        assert result.verified_requirements == 0
        assert result.overall_percentage == 0.0

    def test_calculates_implementation_percentage(
        self, query_manager: QueryManager, mock_requirement_manager: Mock
    ) -> None:
        requirements = [
            create_requirement("REQ-0001", status=RequirementStatus.PROPOSED),
            create_requirement("REQ-0002", status=RequirementStatus.IMPLEMENTED),
            create_requirement("REQ-0003", status=RequirementStatus.VERIFIED),
            create_requirement("REQ-0004", status=RequirementStatus.PROPOSED),
        ]
        mock_requirement_manager.list_requirements.return_value = requirements

        result = query_manager.progress("SPEC-0001")

        assert result.total_requirements == 4
        assert result.implemented_requirements == 2
        assert result.verified_requirements == 1
        assert result.overall_percentage == 50.0

    def test_groups_by_requirement_type(
        self, query_manager: QueryManager, mock_requirement_manager: Mock
    ) -> None:
        requirements = [
            create_requirement(
                "REQ-0001",
                req_type=RequirementType.FUNCTIONAL,
                status=RequirementStatus.IMPLEMENTED,
            ),
            create_requirement(
                "REQ-0002",
                req_type=RequirementType.FUNCTIONAL,
                status=RequirementStatus.PROPOSED,
            ),
            create_requirement(
                "REQ-0003",
                req_type=RequirementType.QUALITY,
                status=RequirementStatus.VERIFIED,
            ),
        ]
        mock_requirement_manager.list_requirements.return_value = requirements

        result = query_manager.progress("SPEC-0001")

        assert len(result.by_type) == 2
        type_dict = {tp.req_type: tp for tp in result.by_type}
        assert type_dict[RequirementType.FUNCTIONAL].total == 2
        assert type_dict[RequirementType.FUNCTIONAL].implemented == 1
        assert type_dict[RequirementType.QUALITY].total == 1
        assert type_dict[RequirementType.QUALITY].implemented == 1

    def test_raises_for_nonexistent_spec(
        self, query_manager: QueryManager, mock_requirement_manager: Mock
    ) -> None:
        mock_requirement_manager.list_requirements.side_effect = SpecNotFoundError(
            "Not found", spec_id="SPEC-9999"
        )

        with pytest.raises(SpecNotFoundError):
            query_manager.progress("SPEC-9999")


class TestCoverage:
    def test_returns_coverage_report_for_empty_spec(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []
        mock_test_manager.list_tests.return_value = []

        result = query_manager.coverage("SPEC-0001")

        assert isinstance(result, CoverageReport)
        assert result.spec_id == "SPEC-0001"
        assert result.total_requirements == 0
        assert result.covered_requirements == 0
        assert result.overall_coverage == 0.0

    def test_calculates_coverage_from_passing_tests(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        requirements = [
            create_requirement("REQ-0001"),
            create_requirement("REQ-0002"),
            create_requirement("REQ-0003"),
        ]
        tests = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            ),
            create_spec_test(
                "TEST-0002", result=SpecTestResult.FAIL, requirements=("REQ-0002",)
            ),
            create_spec_test(
                "TEST-0003", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            ),
        ]
        mock_requirement_manager.list_requirements.return_value = requirements
        mock_test_manager.list_tests.return_value = tests

        result = query_manager.coverage("SPEC-0001")

        assert result.total_requirements == 3
        assert result.covered_requirements == 1
        assert result.overall_coverage == pytest.approx(33.33, rel=0.1)

    def test_builds_requirement_to_tests_mapping(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        requirements = [create_requirement("REQ-0001"), create_requirement("REQ-0002")]
        tests = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            ),
            create_spec_test(
                "TEST-0002", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            ),
        ]
        mock_requirement_manager.list_requirements.return_value = requirements
        mock_test_manager.list_tests.return_value = tests

        result = query_manager.coverage("SPEC-0001")

        assert isinstance(result.requirement_to_tests, MappingProxyType)
        assert "REQ-0001" in result.requirement_to_tests
        assert set(result.requirement_to_tests["REQ-0001"]) == {
            "TEST-0001",
            "TEST-0002",
        }
        assert "REQ-0002" not in result.requirement_to_tests

    def test_groups_by_test_method(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        requirements = [create_requirement("REQ-0001")]
        tests = [
            create_spec_test(
                "TEST-0001",
                method=SpecTestMethod.UNIT,
                result=SpecTestResult.PASS,
                requirements=("REQ-0001",),
            ),
            create_spec_test(
                "TEST-0002",
                method=SpecTestMethod.UNIT,
                result=SpecTestResult.FAIL,
                requirements=("REQ-0001",),
            ),
            create_spec_test(
                "TEST-0003",
                method=SpecTestMethod.INTEGRATION,
                result=SpecTestResult.PASS,
                requirements=("REQ-0001",),
            ),
        ]
        mock_requirement_manager.list_requirements.return_value = requirements
        mock_test_manager.list_tests.return_value = tests

        result = query_manager.coverage("SPEC-0001")

        assert len(result.by_method) == 2
        method_dict = {mc.method: mc for mc in result.by_method}
        assert method_dict[SpecTestMethod.UNIT].total_tests == 2
        assert method_dict[SpecTestMethod.UNIT].passing_tests == 1
        assert method_dict[SpecTestMethod.INTEGRATION].total_tests == 1
        assert method_dict[SpecTestMethod.INTEGRATION].passing_tests == 1

    def test_groups_by_requirement_type(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        requirements = [
            create_requirement("REQ-0001", req_type=RequirementType.FUNCTIONAL),
            create_requirement("REQ-0002", req_type=RequirementType.QUALITY),
        ]
        tests = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            )
        ]
        mock_requirement_manager.list_requirements.return_value = requirements
        mock_test_manager.list_tests.return_value = tests

        result = query_manager.coverage("SPEC-0001")

        type_dict = {tc.req_type: tc for tc in result.by_type}
        assert type_dict[RequirementType.FUNCTIONAL].covered_requirements == 1
        assert type_dict[RequirementType.FUNCTIONAL].coverage_percentage == 100.0
        assert type_dict[RequirementType.QUALITY].covered_requirements == 0
        assert type_dict[RequirementType.QUALITY].coverage_percentage == 0.0


class TestUnverified:
    def test_returns_empty_for_all_covered(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        requirements = [create_requirement("REQ-0001")]
        tests = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            )
        ]
        mock_requirement_manager.list_requirements.return_value = requirements
        mock_test_manager.list_tests.return_value = tests

        result = query_manager.unverified("SPEC-0001")

        assert result == ()

    def test_returns_uncovered_requirements(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        req1 = create_requirement("REQ-0001")
        req2 = create_requirement("REQ-0002")
        mock_requirement_manager.list_requirements.return_value = [req1, req2]
        mock_test_manager.list_tests.return_value = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.PASS, requirements=("REQ-0001",)
            )
        ]

        result = query_manager.unverified("SPEC-0001")

        assert len(result) == 1
        assert result[0].id == "REQ-0002"

    def test_excludes_requirements_with_failing_tests_only(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        req1 = create_requirement("REQ-0001")
        mock_requirement_manager.list_requirements.return_value = [req1]
        mock_test_manager.list_tests.return_value = [
            create_spec_test(
                "TEST-0001", result=SpecTestResult.FAIL, requirements=("REQ-0001",)
            )
        ]

        result = query_manager.unverified("SPEC-0001")

        assert len(result) == 1
        assert result[0].id == "REQ-0001"


class TestOrphans:
    def test_returns_empty_report_for_valid_spec(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = [
            create_requirement("REQ-0001")
        ]
        mock_test_manager.list_tests.return_value = [
            create_spec_test("TEST-0001", requirements=("REQ-0001",))
        ]

        result = query_manager.orphans("SPEC-0001")

        assert isinstance(result, OrphanReport)
        assert result.orphaned_tests == ()
        assert result.orphaned_artifacts == ()
        assert result.tests_missing_file == ()

    def test_finds_orphaned_tests(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = [
            create_requirement("REQ-0001")
        ]
        orphan_test = create_spec_test("TEST-0001", requirements=("REQ-9999",))
        valid_test = create_spec_test("TEST-0002", requirements=("REQ-0001",))
        mock_test_manager.list_tests.return_value = [orphan_test, valid_test]

        result = query_manager.orphans("SPEC-0001")

        assert len(result.orphaned_tests) == 1
        assert result.orphaned_tests[0].id == "TEST-0001"

    def test_finds_tests_missing_file(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = [
            create_requirement("REQ-0001")
        ]
        test_no_file = create_spec_test(
            "TEST-0001", requirements=("REQ-0001",), file=None, function=None
        )
        mock_test_manager.list_tests.return_value = [test_no_file]

        result = query_manager.orphans("SPEC-0001")

        assert len(result.tests_missing_file) == 1
        assert result.tests_missing_file[0].id == "TEST-0001"

    def test_finds_orphaned_artifacts_when_artifact_manager_present(
        self,
        query_manager_with_artifacts: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
        mock_artifact_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = [
            create_requirement("REQ-0001")
        ]
        mock_test_manager.list_tests.return_value = []

        artifact_mock = MagicMock()
        artifact_mock.id = "ART-0001"
        artifact_mock.references = ("REQ-9999",)
        mock_artifact_manager.list_artifacts.return_value = [artifact_mock]

        result = query_manager_with_artifacts.orphans("SPEC-0001")

        assert len(result.orphaned_artifacts) == 1
        assert result.orphaned_artifacts[0] == "ART-0001"

    def test_ignores_artifacts_with_no_references(
        self,
        query_manager_with_artifacts: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
        mock_artifact_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []
        mock_test_manager.list_tests.return_value = []

        artifact_mock = MagicMock()
        artifact_mock.id = "ART-0001"
        artifact_mock.references = ()
        mock_artifact_manager.list_artifacts.return_value = [artifact_mock]

        result = query_manager_with_artifacts.orphans("SPEC-0001")

        assert result.orphaned_artifacts == ()


class TestDependencyGraph:
    def test_returns_empty_graph_for_no_specs(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.list_specs.return_value = []

        result = query_manager.dependency_graph()

        assert isinstance(result, DependencyGraph)
        assert result.nodes == ()
        assert result.edges == ()
        assert result.roots == ()
        assert result.leaves == ()
        assert result.topological_order == ()
        assert not result.has_cycles

    def test_builds_graph_with_dependencies(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001", depends_on=()),
            create_spec_summary("SPEC-0002", depends_on=("SPEC-0001",)),
            create_spec_summary("SPEC-0003", depends_on=("SPEC-0002",)),
        ]
        mock_spec_manager.list_specs.return_value = specs

        result = query_manager.dependency_graph()

        assert len(result.nodes) == 3
        assert len(result.edges) == 2
        node_ids = {n.spec_id for n in result.nodes}
        assert node_ids == {"SPEC-0001", "SPEC-0002", "SPEC-0003"}

    def test_identifies_roots_and_leaves(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        # SPEC-0002 depends on SPEC-0001, so edge is SPEC-0002 -> SPEC-0001
        # SPEC-0002 has no incoming edges (no one depends on it) = root
        # SPEC-0001 has no outgoing edges (doesn't depend on anything) = leaf
        specs = [
            create_spec_summary("SPEC-0001", depends_on=()),
            create_spec_summary("SPEC-0002", depends_on=("SPEC-0001",)),
        ]
        mock_spec_manager.list_specs.return_value = specs

        result = query_manager.dependency_graph()

        assert "SPEC-0002" in result.roots  # No incoming edges
        assert "SPEC-0001" in result.leaves  # No outgoing edges

    def test_computes_topological_order(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        # SPEC-0003 depends on SPEC-0002 depends on SPEC-0001
        # Edges: SPEC-0003 -> SPEC-0002 -> SPEC-0001
        # Topological order: SPEC-0003, SPEC-0002, SPEC-0001 (from roots to leaves)
        specs = [
            create_spec_summary("SPEC-0001", depends_on=()),
            create_spec_summary("SPEC-0002", depends_on=("SPEC-0001",)),
            create_spec_summary("SPEC-0003", depends_on=("SPEC-0002",)),
        ]
        mock_spec_manager.list_specs.return_value = specs

        result = query_manager.dependency_graph()

        assert len(result.topological_order) == 3
        idx_1 = result.topological_order.index("SPEC-0001")
        idx_2 = result.topological_order.index("SPEC-0002")
        idx_3 = result.topological_order.index("SPEC-0003")
        # Topological order: SPEC-0003 first (root), SPEC-0002 middle, SPEC-0001 (leaf)
        assert idx_3 < idx_2 < idx_1

    def test_detects_cycle_in_dependencies(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        # SPEC-0001 depends on SPEC-0002, SPEC-0002 depends on SPEC-0001 = cycle
        specs = [
            create_spec_summary("SPEC-0001", depends_on=("SPEC-0002",)),
            create_spec_summary("SPEC-0002", depends_on=("SPEC-0001",)),
        ]
        mock_spec_manager.list_specs.return_value = specs

        result = query_manager.dependency_graph()

        assert result.has_cycles is True
        assert len(result.cycle_path) > 0
        # Cycle path should contain both specs and close the loop
        assert "SPEC-0001" in result.cycle_path
        assert "SPEC-0002" in result.cycle_path
        # Topological order is empty when cycles exist
        assert result.topological_order == ()

    def test_filters_to_subgraph_when_spec_id_provided(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001", depends_on=()),
            create_spec_summary("SPEC-0002", depends_on=("SPEC-0001",)),
            create_spec_summary("SPEC-0003", depends_on=()),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.return_value = create_spec_metadata("SPEC-0002")

        result = query_manager.dependency_graph(spec_id="SPEC-0002")

        node_ids = {n.spec_id for n in result.nodes}
        assert "SPEC-0002" in node_ids
        assert "SPEC-0001" in node_ids
        assert "SPEC-0003" not in node_ids

    def test_raises_for_nonexistent_spec_id(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.get_spec.side_effect = SpecNotFoundError(
            "Not found", spec_id="SPEC-9999"
        )

        with pytest.raises(SpecNotFoundError):
            query_manager.dependency_graph(spec_id="SPEC-9999")


class TestRelationshipGraph:
    def test_returns_empty_graph_for_no_specs(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.list_specs.return_value = []

        result = query_manager.relationship_graph()

        assert isinstance(result, RelationshipGraph)
        assert result.nodes == ()
        assert result.edges == ()

    def test_builds_nodes_from_specs(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001", spec_type=SpecType.FEATURE),
            create_spec_summary("SPEC-0002", spec_type=SpecType.INTEGRATION),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata("SPEC-0001"),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph()

        assert len(result.nodes) == 2
        assert "SPEC-0001" in result.node_index
        assert "SPEC-0002" in result.node_index

    def test_collects_depends_on_edges(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=("SPEC-0002",),
                    extends=None,
                    supersedes=None,
                    integrates=(),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph()

        assert len(result.edges) == 1
        edge = result.edges[0]
        assert edge.from_spec_id == "SPEC-0001"
        assert edge.to_spec_id == "SPEC-0002"
        assert edge.relationship_type == RelationshipType.DEPENDS_ON

    def test_collects_extends_edges(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=(),
                    extends="SPEC-0002",
                    supersedes=None,
                    integrates=(),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph()

        assert len(result.edges) == 1
        assert result.edges[0].relationship_type == RelationshipType.EXTENDS

    def test_collects_supersedes_edges(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=(),
                    extends=None,
                    supersedes="SPEC-0002",
                    integrates=(),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph()

        assert len(result.edges) == 1
        assert result.edges[0].relationship_type == RelationshipType.SUPERSEDES

    def test_collects_integrates_edges(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=(),
                    extends=None,
                    supersedes=None,
                    integrates=("SPEC-0002",),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph()

        assert len(result.edges) == 1
        assert result.edges[0].relationship_type == RelationshipType.INTEGRATES

    def test_filters_by_relationship_types(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=("SPEC-0002",),
                    extends="SPEC-0002",
                    supersedes=None,
                    integrates=(),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
        ]

        result = query_manager.relationship_graph(
            relationship_types=(RelationshipType.DEPENDS_ON,)
        )

        assert len(result.edges) == 1
        assert result.edges[0].relationship_type == RelationshipType.DEPENDS_ON

    def test_filters_to_subgraph_when_spec_id_provided(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        specs = [
            create_spec_summary("SPEC-0001"),
            create_spec_summary("SPEC-0002"),
            create_spec_summary("SPEC-0003"),
        ]
        mock_spec_manager.list_specs.return_value = specs
        mock_spec_manager.get_spec.side_effect = [
            create_spec_metadata("SPEC-0001"),
            create_spec_metadata(
                "SPEC-0001",
                relationships=Relationships(
                    depends_on=("SPEC-0002",),
                    extends=None,
                    supersedes=None,
                    integrates=(),
                ),
            ),
            create_spec_metadata("SPEC-0002"),
            create_spec_metadata("SPEC-0003"),
        ]

        result = query_manager.relationship_graph(spec_id="SPEC-0001")

        node_ids = {n.spec_id for n in result.nodes}
        assert "SPEC-0001" in node_ids
        assert "SPEC-0002" in node_ids
        assert "SPEC-0003" not in node_ids

    def test_raises_for_nonexistent_spec_id(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.get_spec.side_effect = SpecNotFoundError(
            "Not found", spec_id="SPEC-9999"
        )

        with pytest.raises(SpecNotFoundError):
            query_manager.relationship_graph(spec_id="SPEC-9999")


class TestDataclassImmutability:
    def test_progress_report_is_frozen(
        self, query_manager: QueryManager, mock_requirement_manager: Mock
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []
        result = query_manager.progress("SPEC-0001")

        with pytest.raises(AttributeError):
            result.spec_id = "changed"  # type: ignore[misc]

    def test_coverage_report_is_frozen(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []
        mock_test_manager.list_tests.return_value = []
        result = query_manager.coverage("SPEC-0001")

        with pytest.raises(AttributeError):
            result.spec_id = "changed"  # type: ignore[misc]

    def test_orphan_report_is_frozen(
        self,
        query_manager: QueryManager,
        mock_requirement_manager: Mock,
        mock_test_manager: Mock,
    ) -> None:
        mock_requirement_manager.list_requirements.return_value = []
        mock_test_manager.list_tests.return_value = []
        result = query_manager.orphans("SPEC-0001")

        with pytest.raises(AttributeError):
            result.spec_id = "changed"  # type: ignore[misc]

    def test_dependency_graph_is_frozen(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.list_specs.return_value = []
        result = query_manager.dependency_graph()

        with pytest.raises(AttributeError):
            result.has_cycles = True  # type: ignore[misc]

    def test_relationship_graph_is_frozen(
        self, query_manager: QueryManager, mock_spec_manager: Mock
    ) -> None:
        mock_spec_manager.list_specs.return_value = []
        result = query_manager.relationship_graph()

        with pytest.raises(AttributeError):
            result.nodes = ()  # type: ignore[misc]
