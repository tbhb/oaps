# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""Query manager for read-only specification analysis.

This module provides the QueryManager class for computing progress,
coverage, orphans, and relationship graphs across specifications.
"""

from collections import defaultdict
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

import rustworkx as rx

from oaps.exceptions import SpecNotFoundError
from oaps.spec._models import (
    CoverageReport,
    DependencyGraph,
    DependencyNode,
    MethodCoverage,
    OrphanReport,
    ProgressReport,
    RelationshipEdge,
    RelationshipGraph,
    RelationshipType,
    Requirement,
    RequirementStatus,
    RequirementType,
    SpecNode,
    SpecStatus,
    SpecSummary,
    Test,
    TestMethod,
    TestResult,
    TypeCoverage,
    TypeProgress,
)

if TYPE_CHECKING:
    from oaps.spec._artifact_manager import ArtifactManager
    from oaps.spec._requirement_manager import RequirementManager
    from oaps.spec._spec_manager import SpecManager
    from oaps.spec._test_manager import TestManager

__all__ = ["QueryManager"]


class QueryManager:
    """Manager for read-only query operations on specifications.

    The QueryManager provides methods for analyzing specification progress,
    test coverage, orphaned tests/artifacts, and dependency/relationship graphs.
    All operations are read-only and return frozen, immutable dataclasses.
    """

    __slots__: Final = (
        "_artifact_manager",
        "_requirement_manager",
        "_spec_manager",
        "_test_manager",
    )

    _spec_manager: SpecManager
    _requirement_manager: RequirementManager
    _test_manager: TestManager
    _artifact_manager: ArtifactManager | None

    def __init__(
        self,
        spec_manager: SpecManager,
        requirement_manager: RequirementManager,
        test_manager: TestManager,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        """Initialize the query manager.

        Args:
            spec_manager: The specification manager for spec metadata.
            requirement_manager: The requirement manager for requirement data.
            test_manager: The test manager for test data.
            artifact_manager: Optional artifact manager for orphan detection.
        """
        self._spec_manager = spec_manager
        self._requirement_manager = requirement_manager
        self._test_manager = test_manager
        self._artifact_manager = artifact_manager

    # -------------------------------------------------------------------------
    # Progress Helper Methods
    # -------------------------------------------------------------------------

    def _build_type_progress(
        self,
        by_type_dict: dict[RequirementType, list[Requirement]],
        implemented_statuses: tuple[RequirementStatus, ...],
    ) -> list[TypeProgress]:
        """Build progress breakdown by requirement type."""
        type_progress: list[TypeProgress] = []
        for req_type, reqs in by_type_dict.items():
            type_total = len(reqs)
            type_implemented = sum(
                1 for req in reqs if req.status in implemented_statuses
            )
            type_verified = sum(
                1 for req in reqs if req.status == RequirementStatus.VERIFIED
            )
            type_percentage = (
                (type_implemented / type_total * 100.0) if type_total > 0 else 0.0
            )
            type_progress.append(
                TypeProgress(
                    req_type=req_type,
                    total=type_total,
                    implemented=type_implemented,
                    verified=type_verified,
                    percentage=type_percentage,
                )
            )
        return type_progress

    # -------------------------------------------------------------------------
    # Coverage Helper Methods
    # -------------------------------------------------------------------------

    def _build_method_coverage(
        self,
        by_method_dict: dict[TestMethod, list[Test]],
        valid_req_ids: set[str],
    ) -> list[MethodCoverage]:
        """Build coverage breakdown by test method."""
        method_coverage: list[MethodCoverage] = []
        for method, method_tests in by_method_dict.items():
            method_total = len(method_tests)
            method_passing = sum(
                1 for test in method_tests if test.last_result == TestResult.PASS
            )
            # Count unique requirements covered by passing tests of this method
            covered_reqs: set[str] = set()
            for test in method_tests:
                if test.last_result == TestResult.PASS:
                    covered_reqs.update(
                        req_id
                        for req_id in test.tests_requirements
                        if req_id in valid_req_ids
                    )
            method_coverage.append(
                MethodCoverage(
                    method=method,
                    total_tests=method_total,
                    passing_tests=method_passing,
                    requirements_covered=len(covered_reqs),
                )
            )
        return method_coverage

    def _build_type_coverage(
        self,
        by_type_dict: dict[RequirementType, list[Requirement]],
        passing_tests_by_req: dict[str, list[str]],
    ) -> list[TypeCoverage]:
        """Build coverage breakdown by requirement type."""
        type_coverage: list[TypeCoverage] = []
        for req_type, reqs in by_type_dict.items():
            type_total = len(reqs)
            type_covered = sum(1 for req in reqs if passing_tests_by_req.get(req.id))
            type_percentage = (
                (type_covered / type_total * 100.0) if type_total > 0 else 0.0
            )
            type_coverage.append(
                TypeCoverage(
                    req_type=req_type,
                    total_requirements=type_total,
                    covered_requirements=type_covered,
                    coverage_percentage=type_percentage,
                )
            )
        return type_coverage

    # -------------------------------------------------------------------------
    # Dependency Graph Helper Methods
    # -------------------------------------------------------------------------

    def _build_dependency_graph_structure(
        self,
        specs: list[SpecSummary],
    ) -> tuple[
        rx.PyDiGraph[str, None], dict[str, int], dict[str, tuple[str, SpecStatus]]
    ]:
        """Build the dependency graph structure from specs."""
        graph: rx.PyDiGraph[str, None] = rx.PyDiGraph(check_cycle=False)
        node_indices: dict[str, int] = {}
        spec_data: dict[str, tuple[str, SpecStatus]] = {}

        # Add nodes
        for spec in specs:
            idx = graph.add_node(spec.id)
            node_indices[spec.id] = idx
            spec_data[spec.id] = (spec.title, spec.status)

        # Add edges (A depends on B means edge A -> B)
        for spec in specs:
            for dep_id in spec.depends_on:
                if dep_id in node_indices:
                    _ = graph.add_edge(
                        node_indices[spec.id], node_indices[dep_id], None
                    )

        return graph, node_indices, spec_data

    def _filter_to_subgraph(
        self,
        graph: rx.PyDiGraph[str, None],
        node_indices: dict[str, int],
        spec_id: str,
    ) -> set[str]:
        """Filter to subgraph reachable from spec_id."""
        spec_idx = node_indices[spec_id]
        ancestors = rx.ancestors(graph, spec_idx)
        descendants = rx.descendants(graph, spec_idx)
        included_indices = {spec_idx} | ancestors | descendants
        return {graph[idx] for idx in included_indices if idx in graph.node_indices()}

    def _detect_cycles(
        self,
        graph: rx.PyDiGraph[str, None],
    ) -> tuple[bool, tuple[str, ...]]:
        """Detect cycles in the graph and return cycle path if found."""
        cycle_edges = rx.digraph_find_cycle(graph)
        has_cycles = len(cycle_edges) > 0

        cycle_path: tuple[str, ...] = ()
        if has_cycles and cycle_edges:
            # cycle_edges is a list of (source, target) index tuples
            # Build path from source nodes, then close with target of last edge
            cycle_ids = [graph[source_idx] for source_idx, _ in cycle_edges]
            _, last_target = cycle_edges[-1]
            cycle_ids.append(graph[last_target])
            cycle_path = tuple(cycle_ids)

        return has_cycles, cycle_path

    def _compute_roots_and_leaves(
        self,
        graph: rx.PyDiGraph[str, None],
        node_indices: dict[str, int],
        included_spec_ids: set[str],
    ) -> tuple[list[str], list[str]]:
        """Compute roots and leaves from the filtered set."""
        roots: list[str] = []
        leaves: list[str] = []
        for spec_node_id in included_spec_ids:
            if spec_node_id in node_indices:
                idx = node_indices[spec_node_id]
                if graph.in_degree(idx) == 0:
                    roots.append(spec_node_id)
                if graph.out_degree(idx) == 0:
                    leaves.append(spec_node_id)
        return roots, leaves

    def _compute_topological_order(
        self,
        graph: rx.PyDiGraph[str, None],
        included_spec_ids: set[str],
        *,
        has_cycles: bool,
    ) -> tuple[str, ...]:
        """Compute topological order if no cycles."""
        if has_cycles:
            return ()
        try:
            topo_indices = rx.topological_sort(graph)
            return tuple(
                graph[idx] for idx in topo_indices if graph[idx] in included_spec_ids
            )
        except rx.DAGHasCycle:
            return ()

    def _compute_depths(
        self,
        graph: rx.PyDiGraph[str, None],
        node_indices: dict[str, int],
        roots: list[str],
    ) -> dict[str, int]:
        """Compute depths using BFS from roots."""
        from collections import deque  # noqa: PLC0415

        depths: dict[str, int] = {}
        for root_id in roots:
            if root_id not in depths:
                depths[root_id] = 0
            # BFS to compute depths using deque for O(1) popleft
            queue: deque[str] = deque([root_id])
            while queue:
                current = queue.popleft()
                current_depth = depths[current]
                if current in node_indices:
                    idx = node_indices[current]
                    for successor_idx in graph.predecessor_indices(idx):
                        successor_id = graph[successor_idx]
                        new_depth = current_depth + 1
                        if (
                            successor_id not in depths
                            or depths[successor_id] < new_depth
                        ):
                            depths[successor_id] = new_depth
                            queue.append(successor_id)
        return depths

    def _build_dependency_nodes(
        self,
        included_spec_ids: set[str],
        spec_data: dict[str, tuple[str, SpecStatus]],
        depths: dict[str, int],
    ) -> list[DependencyNode]:
        """Build DependencyNode list from included specs."""
        return [
            DependencyNode(
                spec_id=spec_node_id,
                title=title,
                status=status,
                depth=depths.get(spec_node_id, 0),
            )
            for spec_node_id in included_spec_ids
            if spec_node_id in spec_data
            for title, status in [spec_data[spec_node_id]]
        ]

    def _build_dependency_edges(
        self,
        graph: rx.PyDiGraph[str, None],
        node_indices: dict[str, int],
        included_spec_ids: set[str],
    ) -> list[tuple[str, str]]:
        """Build edge tuples from included specs."""
        edges: list[tuple[str, str]] = []
        for spec_node_id in included_spec_ids:
            if spec_node_id in node_indices:
                idx = node_indices[spec_node_id]
                for target_idx in graph.successor_indices(idx):
                    target_id = graph[target_idx]
                    if target_id in included_spec_ids:
                        edges.append((spec_node_id, target_id))
        return edges

    # -------------------------------------------------------------------------
    # Relationship Graph Helper Methods
    # -------------------------------------------------------------------------

    def _should_include_type(
        self,
        rel_type: RelationshipType,
        relationship_types: tuple[RelationshipType, ...] | None,
    ) -> bool:
        """Check if a relationship type should be included."""
        return relationship_types is None or rel_type in relationship_types

    def _collect_relationship_edges(
        self,
        spec_summaries: list[SpecSummary],
        valid_spec_ids: set[str],
        relationship_types: tuple[RelationshipType, ...] | None,
    ) -> list[RelationshipEdge]:
        """Collect all relationship edges from specs."""
        edges: list[RelationshipEdge] = []

        for spec_summary in spec_summaries:
            try:
                spec_meta = self._spec_manager.get_spec(spec_summary.id)
            except SpecNotFoundError:
                continue

            rel = spec_meta.relationships

            # depends_on edges
            if self._should_include_type(
                RelationshipType.DEPENDS_ON, relationship_types
            ):
                edges.extend(
                    RelationshipEdge(
                        from_spec_id=spec_summary.id,
                        to_spec_id=dep_id,
                        relationship_type=RelationshipType.DEPENDS_ON,
                    )
                    for dep_id in rel.depends_on
                    if dep_id in valid_spec_ids
                )

            # extends edge
            if (
                self._should_include_type(RelationshipType.EXTENDS, relationship_types)
                and rel.extends
                and rel.extends in valid_spec_ids
            ):
                edges.append(
                    RelationshipEdge(
                        from_spec_id=spec_summary.id,
                        to_spec_id=rel.extends,
                        relationship_type=RelationshipType.EXTENDS,
                    )
                )

            # supersedes edge
            if (
                self._should_include_type(
                    RelationshipType.SUPERSEDES, relationship_types
                )
                and rel.supersedes
                and rel.supersedes in valid_spec_ids
            ):
                edges.append(
                    RelationshipEdge(
                        from_spec_id=spec_summary.id,
                        to_spec_id=rel.supersedes,
                        relationship_type=RelationshipType.SUPERSEDES,
                    )
                )

            # integrates edges
            if self._should_include_type(
                RelationshipType.INTEGRATES, relationship_types
            ):
                edges.extend(
                    RelationshipEdge(
                        from_spec_id=spec_summary.id,
                        to_spec_id=int_id,
                        relationship_type=RelationshipType.INTEGRATES,
                    )
                    for int_id in rel.integrates
                    if int_id in valid_spec_ids
                )

        return edges

    def _filter_relationship_graph(
        self,
        spec_id: str,
        spec_summaries: list[SpecSummary],
        nodes: list[SpecNode],
        edges: list[RelationshipEdge],
    ) -> tuple[list[SpecNode], list[RelationshipEdge], dict[str, SpecNode]]:
        """Filter relationship graph to subgraph reachable from spec_id."""
        graph: rx.PyDiGraph[str, RelationshipType] = rx.PyDiGraph()
        idx_map: dict[str, int] = {}

        for spec_summary in spec_summaries:
            idx = graph.add_node(spec_summary.id)
            idx_map[spec_summary.id] = idx

        for edge in edges:
            if edge.from_spec_id in idx_map and edge.to_spec_id in idx_map:
                _ = graph.add_edge(
                    idx_map[edge.from_spec_id],
                    idx_map[edge.to_spec_id],
                    edge.relationship_type,
                )

        if spec_id not in idx_map:
            return nodes, edges, {n.spec_id: n for n in nodes}

        spec_idx = idx_map[spec_id]
        ancestors = rx.ancestors(graph, spec_idx)
        descendants = rx.descendants(graph, spec_idx)
        included_indices = {spec_idx} | ancestors | descendants
        included_spec_ids = {graph[idx] for idx in included_indices}

        filtered_nodes = [n for n in nodes if n.spec_id in included_spec_ids]
        filtered_edges = [
            e
            for e in edges
            if e.from_spec_id in included_spec_ids and e.to_spec_id in included_spec_ids
        ]
        node_index_dict = {n.spec_id: n for n in filtered_nodes}

        return filtered_nodes, filtered_edges, node_index_dict

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def progress(self, spec_id: str) -> ProgressReport:
        """Get implementation progress for a specification.

        Args:
            spec_id: The specification ID.

        Returns:
            ProgressReport with implementation metrics.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get requirements (raises SpecNotFoundError if spec doesn't exist)
        requirements = self._requirement_manager.list_requirements(spec_id)

        # Count totals
        total = len(requirements)
        implemented_statuses = (
            RequirementStatus.IMPLEMENTED,
            RequirementStatus.VERIFIED,
        )
        implemented = sum(
            1 for req in requirements if req.status in implemented_statuses
        )
        verified = sum(
            1 for req in requirements if req.status == RequirementStatus.VERIFIED
        )

        # Group by RequirementType
        by_type_dict: dict[RequirementType, list[Requirement]] = defaultdict(list)
        for req in requirements:
            by_type_dict[req.req_type].append(req)
        type_progress = self._build_type_progress(by_type_dict, implemented_statuses)

        # Overall percentage
        overall_percentage = (implemented / total * 100.0) if total > 0 else 0.0

        return ProgressReport(
            spec_id=spec_id,
            total_requirements=total,
            implemented_requirements=implemented,
            verified_requirements=verified,
            overall_percentage=overall_percentage,
            by_type=tuple(type_progress),
        )

    def coverage(self, spec_id: str) -> CoverageReport:
        """Get test coverage report for a specification.

        Args:
            spec_id: The specification ID.

        Returns:
            CoverageReport with coverage metrics.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get requirements and tests (raises SpecNotFoundError if spec doesn't exist)
        requirements = self._requirement_manager.list_requirements(spec_id)
        tests = self._test_manager.list_tests(spec_id)

        # Build passing_tests_by_req: dict[req_id, list[test_id]]
        passing_tests_by_req: dict[str, list[str]] = defaultdict(list)
        for test in tests:
            if test.last_result == TestResult.PASS:
                for req_id in test.tests_requirements:
                    passing_tests_by_req[req_id].append(test.id)

        # Build requirement ID set for validation
        valid_req_ids = {req.id for req in requirements}

        # Count covered requirements
        covered_requirements = sum(
            1 for req in requirements if passing_tests_by_req.get(req.id)
        )

        # Build requirement_to_tests mapping
        req_to_tests_dict: dict[str, tuple[str, ...]] = {
            req.id: tuple(passing_tests_by_req[req.id])
            for req in requirements
            if req.id in passing_tests_by_req
        }

        # Group by TestMethod
        by_method_dict: dict[TestMethod, list[Test]] = defaultdict(list)
        for test in tests:
            by_method_dict[test.method].append(test)
        method_coverage = self._build_method_coverage(by_method_dict, valid_req_ids)

        # Group by RequirementType
        by_type_dict: dict[RequirementType, list[Requirement]] = defaultdict(list)
        for req in requirements:
            by_type_dict[req.req_type].append(req)
        type_coverage = self._build_type_coverage(by_type_dict, passing_tests_by_req)

        # Overall coverage
        total = len(requirements)
        overall_coverage = (covered_requirements / total * 100.0) if total > 0 else 0.0

        return CoverageReport(
            spec_id=spec_id,
            total_requirements=total,
            covered_requirements=covered_requirements,
            overall_coverage=overall_coverage,
            by_method=tuple(method_coverage),
            by_type=tuple(type_coverage),
            requirement_to_tests=MappingProxyType(req_to_tests_dict),
        )

    def unverified(self, spec_id: str) -> tuple[Requirement, ...]:
        """Find requirements without passing tests.

        Args:
            spec_id: The specification ID.

        Returns:
            Tuple of requirements without passing tests.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get requirements and tests (raises SpecNotFoundError if spec doesn't exist)
        requirements = self._requirement_manager.list_requirements(spec_id)
        tests = self._test_manager.list_tests(spec_id)

        # Build set of covered requirement IDs (requirements with passing tests)
        covered_reqs: set[str] = set()
        for test in tests:
            if test.last_result == TestResult.PASS:
                covered_reqs.update(test.tests_requirements)

        # Return requirements that are not covered
        return tuple(req for req in requirements if req.id not in covered_reqs)

    def orphans(self, spec_id: str) -> OrphanReport:
        """Find orphaned tests and artifacts.

        Args:
            spec_id: The specification ID.

        Returns:
            OrphanReport with orphaned tests and artifacts.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Get requirements and tests (raises SpecNotFoundError if spec doesn't exist)
        requirements = self._requirement_manager.list_requirements(spec_id)
        tests = self._test_manager.list_tests(spec_id)

        # Build valid requirement IDs set
        valid_req_ids = {req.id for req in requirements}

        # Find orphaned tests (tests where no tests_requirements entry is valid)
        orphaned_tests = [
            test
            for test in tests
            if not any(req_id in valid_req_ids for req_id in test.tests_requirements)
        ]

        # Find tests missing file (tests without file and function)
        tests_missing_file = [
            test for test in tests if not test.file or not test.function
        ]

        # Find orphaned artifacts (if artifact_manager provided)
        orphaned_artifacts: list[str] = []
        if self._artifact_manager is not None:
            artifacts = self._artifact_manager.list_artifacts(spec_id)
            orphaned_artifacts = [
                artifact.id
                for artifact in artifacts
                if artifact.references
                and not any(ref in valid_req_ids for ref in artifact.references)
            ]

        return OrphanReport(
            spec_id=spec_id,
            orphaned_tests=tuple(orphaned_tests),
            orphaned_artifacts=tuple(orphaned_artifacts),
            tests_missing_file=tuple(tests_missing_file),
        )

    def dependency_graph(self, spec_id: str | None = None) -> DependencyGraph:
        """Get the dependency graph for specifications.

        Args:
            spec_id: If provided, return only the subgraph reachable from this spec.
                If None, return the complete dependency graph.

        Returns:
            DependencyGraph with nodes, edges, roots, leaves, and cycle info.

        Raises:
            SpecNotFoundError: If spec_id is provided but doesn't exist.
        """
        # Validate spec_id exists if provided
        if spec_id is not None:
            _ = self._spec_manager.get_spec(spec_id)

        # Get all specs and build graph structure
        specs = self._spec_manager.list_specs(include_archived=True)
        graph, node_indices, spec_data = self._build_dependency_graph_structure(specs)

        # Filter to subgraph if spec_id provided
        if spec_id is not None and spec_id in node_indices:
            included_spec_ids = self._filter_to_subgraph(graph, node_indices, spec_id)
        else:
            included_spec_ids = set(node_indices.keys())

        # Cycle detection
        has_cycles, cycle_path = self._detect_cycles(graph)

        # Roots and leaves
        roots, leaves = self._compute_roots_and_leaves(
            graph, node_indices, included_spec_ids
        )

        # Topological sort
        topological_order = self._compute_topological_order(
            graph, included_spec_ids, has_cycles=has_cycles
        )

        # Compute depths
        depths = self._compute_depths(graph, node_indices, roots)

        # Build nodes and edges
        nodes = self._build_dependency_nodes(included_spec_ids, spec_data, depths)
        edges = self._build_dependency_edges(graph, node_indices, included_spec_ids)

        return DependencyGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            roots=tuple(roots),
            leaves=tuple(leaves),
            topological_order=topological_order,
            has_cycles=has_cycles,
            cycle_path=cycle_path,
        )

    def relationship_graph(
        self,
        spec_id: str | None = None,
        relationship_types: tuple[RelationshipType, ...] | None = None,
    ) -> RelationshipGraph:
        """Get the relationship graph for specifications.

        Args:
            spec_id: If provided, return only the subgraph reachable from this spec.
            relationship_types: If provided, include only these relationship types.
                If None, include all types.

        Returns:
            RelationshipGraph with all nodes and filtered edges.

        Raises:
            SpecNotFoundError: If spec_id is provided but doesn't exist.
        """
        # Validate spec_id exists if provided
        if spec_id is not None:
            _ = self._spec_manager.get_spec(spec_id)

        # Get all specs
        spec_summaries = self._spec_manager.list_specs(include_archived=True)
        valid_spec_ids = {spec.id for spec in spec_summaries}

        # Build nodes
        nodes = [
            SpecNode(
                spec_id=spec_summary.id,
                title=spec_summary.title,
                spec_type=spec_summary.spec_type,
                status=spec_summary.status,
            )
            for spec_summary in spec_summaries
        ]
        node_index_dict = {n.spec_id: n for n in nodes}

        # Collect edges
        edges = self._collect_relationship_edges(
            spec_summaries, valid_spec_ids, relationship_types
        )

        # Filter to subgraph if spec_id provided
        if spec_id is not None:
            nodes, edges, node_index_dict = self._filter_relationship_graph(
                spec_id, spec_summaries, nodes, edges
            )

        return RelationshipGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
            node_index=MappingProxyType(node_index_dict),
        )
