# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""Specification manager for CRUD operations on specifications.

This module provides the SpecManager class for managing specifications in
`.oaps/docs/specs/`. It maintains dual indexes (root and per-spec) with
computed inverse relationships.
"""

import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal

from oaps.exceptions import (
    CircularDependencyError,
    DuplicateIdError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec._ids import next_spec_id, validate_spec_id
from oaps.spec._io import append_jsonl, read_json, write_json_atomic
from oaps.spec._models import (
    Counts,
    Relationships,
    SpecMetadata,
    SpecStatus,
    SpecSummary,
    SpecType,
)

if TYPE_CHECKING:
    from oaps.config import SpecConfiguration
    from oaps.repository import OapsRepository

__all__ = ["SpecManager", "SpecValidationIssue"]

# Slug validation pattern: lowercase letters, digits, hyphens between words
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Root index schema version
_INDEX_VERSION = 1

# Minimum items required for integration specs
_MIN_INTEGRATION_ITEMS = 2


# =============================================================================
# Helper Dataclasses
# =============================================================================


@dataclass(slots=True)
class _RelationshipInverses:
    """Computed inverse relationships for a specification.

    Attributes:
        dependents: IDs of specs that depend on this spec.
        extended_by: IDs of specs that extend this spec.
        superseded_by: ID of spec that supersedes this spec.
        integrated_by: IDs of specs that integrate with this spec.
    """

    dependents: list[str] = field(default_factory=list)
    extended_by: list[str] = field(default_factory=list)
    superseded_by: str | None = None
    integrated_by: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SpecValidationIssue:
    """Validation issue for a specification.

    Attributes:
        spec_id: ID of the spec with the issue.
        field: Field that has the issue.
        message: Human-readable description of the issue.
        severity: Whether this is an error or warning.
        related_id: ID of a related entity, if applicable.
    """

    spec_id: str
    field: str
    message: str
    severity: Literal["error", "warning"]
    related_id: str | None = None


# =============================================================================
# SpecManager Class
# =============================================================================


class SpecManager:
    """Manager for CRUD operations on specifications.

    The SpecManager provides methods for creating, reading, updating, and
    deleting specifications in `.oaps/docs/specs/`. It maintains dual indexes:
    a root index for fast listing and per-spec indexes for full metadata.

    Attributes:
        _base_path: Base directory for specifications.
        _config: Specification configuration.
        _relationship_graph: Cached inverse relationship graph.
        _root_index_cache: Cached root index data.
        _spec_cache: Cached per-spec index data.
    """

    __slots__: Final = (
        "_base_path",
        "_config",
        "_oaps_repo",
        "_relationship_graph",
        "_root_index_cache",
        "_spec_cache",
    )

    _base_path: Path
    _config: SpecConfiguration | None
    _oaps_repo: OapsRepository | None
    _relationship_graph: dict[str, _RelationshipInverses] | None
    _root_index_cache: dict[str, Any] | None
    _spec_cache: dict[str, dict[str, Any]]

    def __init__(
        self,
        base_path: Path | str,
        *,
        config: SpecConfiguration | None = None,
        oaps_repo: OapsRepository | None = None,
    ) -> None:
        """Initialize the specification manager.

        Args:
            base_path: Base directory for specifications (`.oaps/docs/specs/`).
            config: Specification configuration. If None, loaded lazily from
                global context.
            oaps_repo: Repository for committing changes. If None, mutations
                work but changes are not committed. For testing, pass None
                to skip commits entirely.
        """
        self._base_path = Path(base_path)
        self._config = config
        self._oaps_repo = oaps_repo
        self._relationship_graph = None
        self._root_index_cache = None
        self._spec_cache = {}

    # -------------------------------------------------------------------------
    # Path Properties
    # -------------------------------------------------------------------------

    @property
    def base_path(self) -> Path:
        """Path to the specifications base directory."""
        return self._base_path

    @property
    def index_path(self) -> Path:
        """Path to the root index.json file."""
        return self._base_path / "index.json"

    @property
    def history_path(self) -> Path:
        """Path to the history.jsonl file."""
        return self._base_path / "history.jsonl"

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

    def _invalidate_caches(self, spec_id: str | None = None) -> None:
        """Invalidate cached data.

        Args:
            spec_id: If provided, only invalidate cache for this spec.
                If None, invalidate all caches.
        """
        if spec_id is None:
            self._root_index_cache = None
            self._spec_cache.clear()
            self._relationship_graph = None
        else:
            self._root_index_cache = None
            _ = self._spec_cache.pop(spec_id, None)
            self._relationship_graph = None

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

    def _load_root_index(self) -> dict[str, Any]:
        """Load the root index from disk.

        Returns:
            The root index data as a dictionary.

        Raises:
            SpecIOError: If the index cannot be read.
        """
        if self._root_index_cache is not None:
            return self._root_index_cache

        if not self.index_path.exists():
            # Return empty index structure
            self._root_index_cache = {
                "version": _INDEX_VERSION,
                "updated": datetime.now(UTC).isoformat(),
                "specs": [],
            }
            return self._root_index_cache

        self._root_index_cache = read_json(self.index_path)
        return self._root_index_cache

    def _load_spec_index(self, spec_id: str, slug: str) -> dict[str, Any]:
        """Load a per-spec index from disk.

        Args:
            spec_id: The specification ID.
            slug: The specification slug.

        Returns:
            The spec index data as a dictionary.

        Raises:
            SpecNotFoundError: If the spec directory or index doesn't exist.
            SpecIOError: If the index cannot be read.
        """
        if spec_id in self._spec_cache:
            return self._spec_cache[spec_id]

        spec_dir = self._spec_dir_path(spec_id, slug)
        index_path = spec_dir / "index.json"

        if not index_path.exists():
            msg = f"Specification index not found: {spec_id}"
            raise SpecNotFoundError(msg, spec_id=spec_id)

        data = read_json(index_path)
        self._spec_cache[spec_id] = data
        return data

    def _spec_dir_path(self, spec_id: str, slug: str) -> Path:
        """Get the directory path for a specification.

        Args:
            spec_id: The specification ID.
            slug: The specification slug.

        Returns:
            Path to the specification directory.
        """
        return self._base_path / f"{spec_id}-{slug}"

    def _write_root_index(self, specs: list[dict[str, Any]]) -> None:
        """Write the root index to disk.

        Args:
            specs: List of spec summary dictionaries.
        """
        data = {
            "version": _INDEX_VERSION,
            "updated": datetime.now(UTC).isoformat(),
            "specs": specs,
        }
        self._base_path.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self.index_path, data)
        self._root_index_cache = None

    def _write_spec_index(self, spec_id: str, slug: str, data: dict[str, Any]) -> None:
        """Write a per-spec index to disk.

        Args:
            spec_id: The specification ID.
            slug: The specification slug.
            data: The spec index data.
        """
        spec_dir = self._spec_dir_path(spec_id, slug)
        _ = spec_dir.mkdir(parents=True, exist_ok=True)
        index_path = spec_dir / "index.json"
        write_json_atomic(index_path, data)
        _ = self._spec_cache.pop(spec_id, None)

    def _record_history(
        self,
        event: str,
        actor: str,
        spec_id: str,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        """Record an event to the history log.

        Args:
            event: The event type (e.g., "created", "updated", "deleted").
            actor: The actor who performed the action.
            spec_id: The affected specification ID.
            from_value: The previous value (for updates).
            to_value: The new value (for updates).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "actor": actor,
            "id": spec_id,
        }
        if from_value is not None:
            entry["from_value"] = from_value
        if to_value is not None:
            entry["to_value"] = to_value

        append_jsonl(self.history_path, entry)

    def _get_relationship_graph(self) -> dict[str, _RelationshipInverses]:
        """Build the inverse relationship graph.

        Returns:
            Dictionary mapping spec IDs to their inverse relationships.
        """
        if self._relationship_graph is not None:
            return self._relationship_graph

        root_index = self._load_root_index()
        specs = root_index.get("specs", [])

        # Initialize inverse relationships for all specs
        graph: dict[str, _RelationshipInverses] = {}
        for spec in specs:
            spec_id = spec.get("id", "")
            if spec_id:
                graph[spec_id] = _RelationshipInverses()

        # Build inverse relationships
        for spec in specs:
            spec_id = spec.get("id", "")
            if not spec_id:
                continue

            # Load full spec data to get relationships
            slug = spec.get("slug", "")
            try:
                spec_data = self._load_spec_index(spec_id, slug)
            except SpecNotFoundError:
                continue

            relationships = spec_data.get("relationships", {})

            # depends_on -> dependents
            for dep_id in relationships.get("depends_on", []):
                if dep_id in graph:
                    graph[dep_id].dependents.append(spec_id)

            # extends -> extended_by
            extends_id = relationships.get("extends")
            if extends_id and extends_id in graph:
                graph[extends_id].extended_by.append(spec_id)

            # supersedes -> superseded_by
            supersedes_id = relationships.get("supersedes")
            if supersedes_id and supersedes_id in graph:
                graph[supersedes_id].superseded_by = spec_id

            # integrates -> integrated_by
            for int_id in relationships.get("integrates", []):
                if int_id in graph:
                    graph[int_id].integrated_by.append(spec_id)

        self._relationship_graph = graph
        return graph

    def _check_circular_dependencies(self, spec_id: str, depends_on: list[str]) -> None:
        """Check for circular dependencies using DFS.

        Args:
            spec_id: The specification being updated.
            depends_on: The proposed dependency list.

        Raises:
            CircularDependencyError: If adding these dependencies would create
                a cycle.
        """
        if not depends_on:
            return

        # Build adjacency list from current root index
        root_index = self._load_root_index()
        specs = root_index.get("specs", [])

        adjacency: dict[str, list[str]] = {}
        for spec in specs:
            sid = spec.get("id", "")
            if sid:
                adjacency[sid] = list(spec.get("depends_on", []))

        # Add proposed dependencies (temporarily)
        adjacency[spec_id] = depends_on

        # DFS to detect cycles
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result is not None:
                        return result
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    return [*path[cycle_start:], neighbor]

            _ = path.pop()
            rec_stack.remove(node)
            return None

        # Start DFS from spec_id
        cycle = dfs(spec_id)
        if cycle is not None:
            msg = f"Circular dependency detected: {' -> '.join(cycle)}"
            raise CircularDependencyError(msg, cycle=cycle, entity_type="spec")

    def _validate_slug(self, slug: str) -> None:
        """Validate a specification slug.

        Args:
            slug: The slug to validate.

        Raises:
            SpecValidationError: If the slug is invalid.
        """
        if not _SLUG_PATTERN.match(slug):
            msg = (
                f"Invalid slug format: {slug!r}. "
                "Slugs must contain only lowercase letters, digits, and "
                "hyphens between words."
            )
            raise SpecValidationError(
                msg,
                field="slug",
                value=slug,
                expected="lowercase letters, digits, hyphens between words",
            )

    def _validate_type_constraints(
        self,
        spec_type: SpecType,
        extends: str | None,
        integrates: list[str],
    ) -> None:
        """Validate type-specific constraints.

        Args:
            spec_type: The specification type.
            extends: The spec this extends (if any).
            integrates: List of specs this integrates with.

        Raises:
            SpecValidationError: If constraints are violated.
        """
        if spec_type == SpecType.ENHANCEMENT and not extends:
            msg = "ENHANCEMENT specifications must have 'extends' set"
            raise SpecValidationError(
                msg,
                field="extends",
                value=None,
                expected="a valid spec ID",
            )

        if (
            spec_type == SpecType.INTEGRATION
            and len(integrates) < _MIN_INTEGRATION_ITEMS
        ):
            msg = (
                f"INTEGRATION specifications must have at least "
                f"{_MIN_INTEGRATION_ITEMS} items in 'integrates', "
                f"got {len(integrates)}"
            )
            raise SpecValidationError(
                msg,
                field="integrates",
                value=integrates,
                expected=f"at least {_MIN_INTEGRATION_ITEMS} spec IDs",
            )

    def _validate_targets_exist(
        self,
        depends_on: list[str],
        extends: str | None,
        integrates: list[str],
        supersedes: str | None,
    ) -> None:
        """Validate that referenced specs exist.

        Args:
            depends_on: List of dependency spec IDs.
            extends: The spec this extends (if any).
            integrates: List of specs this integrates with.
            supersedes: The spec this supersedes (if any).

        Raises:
            SpecNotFoundError: If a referenced spec doesn't exist.
        """
        root_index = self._load_root_index()
        existing_ids = {spec.get("id") for spec in root_index.get("specs", [])}

        for dep_id in depends_on:
            if dep_id not in existing_ids:
                msg = f"Dependency target not found: {dep_id}"
                raise SpecNotFoundError(msg, spec_id=dep_id)

        if extends and extends not in existing_ids:
            msg = f"Extends target not found: {extends}"
            raise SpecNotFoundError(msg, spec_id=extends)

        for int_id in integrates:
            if int_id not in existing_ids:
                msg = f"Integrates target not found: {int_id}"
                raise SpecNotFoundError(msg, spec_id=int_id)

        if supersedes and supersedes not in existing_ids:
            msg = f"Supersedes target not found: {supersedes}"
            raise SpecNotFoundError(msg, spec_id=supersedes)

    def _spec_summary_to_dict(self, summary: SpecSummary) -> dict[str, Any]:
        """Convert a SpecSummary to a dictionary for index storage.

        Args:
            summary: The SpecSummary to convert.

        Returns:
            Dictionary representation for JSON serialization.
        """
        data: dict[str, Any] = {
            "id": summary.id,
            "slug": summary.slug,
            "title": summary.title,
            "spec_type": summary.spec_type.value,
            "status": summary.status.value,
            "created": summary.created.isoformat(),
            "updated": summary.updated.isoformat(),
        }
        if summary.depends_on:
            data["depends_on"] = list(summary.depends_on)
        if summary.tags:
            data["tags"] = list(summary.tags)
        return data

    def _dict_to_spec_summary(self, data: dict[str, Any]) -> SpecSummary:
        """Convert a dictionary to a SpecSummary.

        Args:
            data: Dictionary from index storage.

        Returns:
            SpecSummary instance.
        """
        created = data["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = data["updated"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        return SpecSummary(
            id=data["id"],
            slug=data["slug"],
            title=data["title"],
            spec_type=SpecType(data["spec_type"]),
            status=SpecStatus(data["status"]),
            created=created,
            updated=updated,
            depends_on=tuple(data.get("depends_on", [])),
            tags=tuple(data.get("tags", [])),
        )

    def _dict_to_spec_metadata(self, data: dict[str, Any]) -> SpecMetadata:
        """Convert a dictionary to a SpecMetadata.

        Args:
            data: Dictionary from per-spec index storage.

        Returns:
            SpecMetadata instance.
        """
        created = data["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = data["updated"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        # Parse relationships
        rel_data = data.get("relationships", {})
        graph = self._get_relationship_graph()
        inverses = graph.get(data["id"], _RelationshipInverses())

        relationships = Relationships(
            depends_on=tuple(rel_data.get("depends_on", [])),
            extends=rel_data.get("extends"),
            supersedes=rel_data.get("supersedes"),
            integrates=tuple(rel_data.get("integrates", [])),
            # Computed inverses
            dependents=tuple(inverses.dependents),
            extended_by=tuple(inverses.extended_by),
            superseded_by=inverses.superseded_by,
            integrated_by=tuple(inverses.integrated_by),
        )

        # Parse counts
        counts_data = data.get("counts", {})
        counts = Counts(
            requirements=counts_data.get("requirements", 0),
            tests=counts_data.get("tests", 0),
            artifacts=counts_data.get("artifacts", 0),
        )

        return SpecMetadata(
            id=data["id"],
            slug=data["slug"],
            title=data["title"],
            spec_type=SpecType(data["spec_type"]),
            status=SpecStatus(data["status"]),
            created=created,
            updated=updated,
            version=data.get("version"),
            authors=tuple(data.get("authors", [])),
            reviewers=tuple(data.get("reviewers", [])),
            relationships=relationships,
            tags=tuple(data.get("tags", [])),
            summary=data.get("summary"),
            documents=(),  # Documents are loaded separately
            external_refs=(),  # External refs are loaded separately
            counts=counts,
        )

    def _spec_metadata_to_dict(self, metadata: SpecMetadata) -> dict[str, Any]:
        """Convert a SpecMetadata to a dictionary for index storage.

        Args:
            metadata: The SpecMetadata to convert.

        Returns:
            Dictionary representation for JSON serialization.
        """
        data: dict[str, Any] = {
            "id": metadata.id,
            "slug": metadata.slug,
            "title": metadata.title,
            "spec_type": metadata.spec_type.value,
            "status": metadata.status.value,
            "created": metadata.created.isoformat(),
            "updated": metadata.updated.isoformat(),
        }

        if metadata.version:
            data["version"] = metadata.version
        if metadata.authors:
            data["authors"] = list(metadata.authors)
        if metadata.reviewers:
            data["reviewers"] = list(metadata.reviewers)
        if metadata.tags:
            data["tags"] = list(metadata.tags)
        if metadata.summary:
            data["summary"] = metadata.summary

        # Store only outgoing relationships (not computed inverses)
        rel = metadata.relationships
        relationships: dict[str, Any] = {}
        if rel.depends_on:
            relationships["depends_on"] = list(rel.depends_on)
        if rel.extends:
            relationships["extends"] = rel.extends
        if rel.supersedes:
            relationships["supersedes"] = rel.supersedes
        if rel.integrates:
            relationships["integrates"] = list(rel.integrates)
        if relationships:
            data["relationships"] = relationships

        # Store counts
        counts = metadata.counts
        if counts.requirements or counts.tests or counts.artifacts:
            data["counts"] = {
                "requirements": counts.requirements,
                "tests": counts.tests,
                "artifacts": counts.artifacts,
            }

        return data

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def list_specs(
        self,
        *,
        filter_status: SpecStatus | None = None,
        filter_type: SpecType | None = None,
        filter_tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[SpecSummary]:
        """List specifications with optional filtering.

        Args:
            filter_status: Filter by status.
            filter_type: Filter by type.
            filter_tags: Filter by tags (specs must have all listed tags).
            include_archived: Include archived (deprecated/superseded) specs.

        Returns:
            List of matching specification summaries.
        """
        root_index = self._load_root_index()
        specs = root_index.get("specs", [])

        results: list[SpecSummary] = []
        for spec_data in specs:
            summary = self._dict_to_spec_summary(spec_data)

            # Apply status filter
            if filter_status is not None and summary.status != filter_status:
                continue

            # Apply type filter
            if filter_type is not None and summary.spec_type != filter_type:
                continue

            # Apply tags filter
            if filter_tags and not all(tag in summary.tags for tag in filter_tags):
                continue

            # Apply archived filter
            archived_statuses = (SpecStatus.DEPRECATED, SpecStatus.SUPERSEDED)
            if not include_archived and summary.status in archived_statuses:
                continue

            results.append(summary)

        return results

    def get_spec(self, spec_id: str) -> SpecMetadata:
        """Get full metadata for a specification.

        Args:
            spec_id: The specification ID.

        Returns:
            Full specification metadata.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # First look up the slug from root index
        root_index = self._load_root_index()
        spec_entry: dict[str, Any] | None = None

        for spec in root_index.get("specs", []):
            if spec.get("id") == spec_id:
                spec_entry = spec
                break

        if spec_entry is None:
            msg = f"Specification not found: {spec_id}"
            raise SpecNotFoundError(msg, spec_id=spec_id)

        slug = spec_entry.get("slug", "")
        spec_data = self._load_spec_index(spec_id, slug)
        return self._dict_to_spec_metadata(spec_data)

    def spec_exists(self, spec_id: str) -> bool:
        """Check if a specification exists.

        Args:
            spec_id: The specification ID.

        Returns:
            True if the specification exists.
        """
        root_index = self._load_root_index()
        return any(spec.get("id") == spec_id for spec in root_index.get("specs", []))

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def create_spec(  # noqa: PLR0913
        self,
        slug: str,
        title: str,
        spec_type: SpecType,
        *,
        summary: str | None = None,
        tags: list[str] | None = None,
        depends_on: list[str] | None = None,
        extends: str | None = None,
        integrates: list[str] | None = None,
        authors: list[str] | None = None,
        version: str | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> SpecMetadata:
        """Create a new specification.

        Args:
            slug: URL-friendly specification name.
            title: Human-readable specification title.
            spec_type: Architectural type of the specification.
            summary: Brief description for listings.
            tags: Freeform tags for filtering.
            depends_on: IDs of specs this spec depends on.
            extends: ID of spec this spec extends.
            integrates: IDs of specs this spec integrates with.
            authors: List of author identifiers.
            version: Specification version string.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The created specification metadata.

        Raises:
            SpecValidationError: If validation fails.
            CircularDependencyError: If dependencies would create a cycle.
            SpecNotFoundError: If referenced specs don't exist.
            DuplicateIdError: If a spec with this slug already exists.
        """
        # Validate slug format
        self._validate_slug(slug)

        # Check for duplicate slug
        root_index = self._load_root_index()
        for spec in root_index.get("specs", []):
            if spec.get("slug") == slug:
                msg = f"Specification with slug {slug!r} already exists"
                raise DuplicateIdError(msg, entity_id=slug, entity_type="spec")

        # Normalize optional lists
        depends_on = depends_on or []
        integrates = integrates or []
        tags = tags or []
        authors = authors or []

        # Validate type constraints
        self._validate_type_constraints(spec_type, extends, integrates)

        # Validate referenced specs exist
        self._validate_targets_exist(depends_on, extends, integrates, None)

        # Generate next ID
        config = self._get_config()
        existing_ids = {spec.get("id") for spec in root_index.get("specs", [])}
        spec_id = next_spec_id(existing_ids, config.numbering)

        # Check for circular dependencies
        self._check_circular_dependencies(spec_id, depends_on)

        # Create metadata
        now = datetime.now(UTC)
        relationships = Relationships(
            depends_on=tuple(depends_on),
            extends=extends,
            supersedes=None,
            integrates=tuple(integrates),
        )
        metadata = SpecMetadata(
            id=spec_id,
            slug=slug,
            title=title,
            spec_type=spec_type,
            status=SpecStatus.DRAFT,
            created=now,
            updated=now,
            version=version,
            authors=tuple(authors),
            reviewers=(),
            relationships=relationships,
            tags=tuple(tags),
            summary=summary,
            documents=(),
            external_refs=(),
            counts=Counts(),
        )

        # Write per-spec index first (atomic)
        spec_data = self._spec_metadata_to_dict(metadata)
        spec_dir = self._spec_dir_path(spec_id, slug)
        self._write_spec_index(spec_id, slug, spec_data)

        # Update root index with error recovery
        try:
            summary_data = self._spec_summary_to_dict(
                SpecSummary(
                    id=spec_id,
                    slug=slug,
                    title=title,
                    spec_type=spec_type,
                    status=SpecStatus.DRAFT,
                    created=now,
                    updated=now,
                    depends_on=tuple(depends_on),
                    tags=tuple(tags),
                )
            )
            specs_list = list(root_index.get("specs", []))
            specs_list.append(summary_data)
            self._write_root_index(specs_list)
        except Exception:
            # Cleanup: remove orphaned spec directory
            if spec_dir.exists():
                shutil.rmtree(spec_dir)
            raise

        # Record history
        self._record_history("created", actor, spec_id, to_value=slug)

        # Commit changes
        _ = self._commit(f"create {spec_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches()

        return metadata

    def update_spec(  # noqa: PLR0913
        self,
        spec_id: str,
        *,
        title: str | None = None,
        spec_type: SpecType | None = None,
        summary: str | None = None,
        status: SpecStatus | None = None,
        tags: list[str] | None = None,
        depends_on: list[str] | None = None,
        extends: str | None = None,
        integrates: list[str] | None = None,
        supersedes: str | None = None,
        version: str | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> SpecMetadata:
        """Update an existing specification.

        Args:
            spec_id: The specification ID to update.
            title: New title (optional).
            spec_type: New type (optional).
            summary: New summary (optional).
            status: New status (optional).
            tags: New tags (replaces existing).
            depends_on: New dependencies (replaces existing).
            extends: New extends target (optional).
            integrates: New integrates targets (replaces existing).
            supersedes: New supersedes target (optional).
            version: New version string (optional).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated specification metadata.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecValidationError: If validation fails.
            CircularDependencyError: If dependencies would create a cycle.
        """
        # Get existing spec
        existing = self.get_spec(spec_id)

        # Merge updates with existing values
        new_title = title if title is not None else existing.title
        new_type = spec_type if spec_type is not None else existing.spec_type
        new_summary = summary if summary is not None else existing.summary
        new_status = status if status is not None else existing.status
        new_tags = tuple(tags) if tags is not None else existing.tags
        new_version = version if version is not None else existing.version

        # Handle relationship updates
        existing_deps = list(existing.relationships.depends_on)
        new_depends_on = depends_on if depends_on is not None else existing_deps
        new_extends = extends if extends is not None else existing.relationships.extends
        existing_ints = list(existing.relationships.integrates)
        new_integrates = integrates if integrates is not None else existing_ints
        new_supersedes = (
            supersedes if supersedes is not None else existing.relationships.supersedes
        )

        # Validate type constraints
        self._validate_type_constraints(new_type, new_extends, new_integrates)

        # Validate referenced specs exist
        self._validate_targets_exist(
            new_depends_on, new_extends, new_integrates, new_supersedes
        )

        # Check for circular dependencies
        self._check_circular_dependencies(spec_id, new_depends_on)

        # Create updated metadata
        now = datetime.now(UTC)
        relationships = Relationships(
            depends_on=tuple(new_depends_on),
            extends=new_extends,
            supersedes=new_supersedes,
            integrates=tuple(new_integrates),
        )
        updated = SpecMetadata(
            id=existing.id,
            slug=existing.slug,
            title=new_title,
            spec_type=new_type,
            status=new_status,
            created=existing.created,
            updated=now,
            version=new_version,
            authors=existing.authors,
            reviewers=existing.reviewers,
            relationships=relationships,
            tags=new_tags,
            summary=new_summary,
            documents=existing.documents,
            external_refs=existing.external_refs,
            counts=existing.counts,
        )

        # Save original spec data for potential rollback
        original_spec_data = self._spec_metadata_to_dict(existing)

        # Write per-spec index first (atomic)
        spec_data = self._spec_metadata_to_dict(updated)
        self._write_spec_index(spec_id, existing.slug, spec_data)

        # Update root index with error recovery
        try:
            root_index = self._load_root_index()
            specs_list = list(root_index.get("specs", []))
            for i, spec in enumerate(specs_list):
                if spec.get("id") == spec_id:
                    specs_list[i] = self._spec_summary_to_dict(
                        SpecSummary(
                            id=updated.id,
                            slug=updated.slug,
                            title=updated.title,
                            spec_type=updated.spec_type,
                            status=updated.status,
                            created=updated.created,
                            updated=updated.updated,
                            depends_on=tuple(new_depends_on),
                            tags=updated.tags,
                        )
                    )
                    break
            self._write_root_index(specs_list)
        except Exception:
            # Rollback: restore original per-spec index
            self._write_spec_index(spec_id, existing.slug, original_spec_data)
            raise

        # Record history
        self._record_history(
            "updated",
            actor,
            spec_id,
            from_value=existing.status.value if status else None,
            to_value=new_status.value if status else None,
        )

        # Commit changes
        _ = self._commit(f"update {spec_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(spec_id)

        return updated

    def delete_spec(
        self,
        spec_id: str,
        *,
        force: bool = False,
        actor: str,
        session_id: str | None = None,
    ) -> None:
        """Delete a specification.

        Args:
            spec_id: The specification ID to delete.
            force: Delete even if spec has dependents.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecValidationError: If spec has dependents and force=False.
        """
        # Get existing spec
        existing = self.get_spec(spec_id)

        # Check for dependents
        if not force:
            graph = self._get_relationship_graph()
            inverses = graph.get(spec_id, _RelationshipInverses())
            if inverses.dependents:
                msg = (
                    f"Cannot delete spec {spec_id}: "
                    f"depended on by {', '.join(inverses.dependents)}"
                )
                raise SpecValidationError(msg, spec_id=spec_id, field="dependents")
            if inverses.extended_by:
                msg = (
                    f"Cannot delete spec {spec_id}: "
                    f"extended by {', '.join(inverses.extended_by)}"
                )
                raise SpecValidationError(msg, spec_id=spec_id, field="extended_by")
            if inverses.integrated_by:
                msg = (
                    f"Cannot delete spec {spec_id}: "
                    f"integrated by {', '.join(inverses.integrated_by)}"
                )
                raise SpecValidationError(msg, spec_id=spec_id, field="integrated_by")
            if inverses.superseded_by:
                msg = (
                    f"Cannot delete spec {spec_id}: "
                    f"superseded by {inverses.superseded_by}"
                )
                raise SpecValidationError(msg, spec_id=spec_id, field="superseded_by")

        # Update root index FIRST (so spec is removed from listing)
        root_index = self._load_root_index()
        specs_list = [
            spec for spec in root_index.get("specs", []) if spec.get("id") != spec_id
        ]
        self._write_root_index(specs_list)

        # Then remove spec directory (safe to fail - spec already removed from index)
        spec_dir = self._spec_dir_path(spec_id, existing.slug)
        if spec_dir.exists():
            shutil.rmtree(spec_dir)

        # Record history
        self._record_history("deleted", actor, spec_id, from_value=existing.slug)

        # Commit changes
        _ = self._commit(f"delete {spec_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches()

    def rename_spec(
        self,
        spec_id: str,
        new_slug: str,
        *,
        actor: str,
        session_id: str | None = None,
    ) -> SpecMetadata:
        """Rename a specification (change its slug).

        Args:
            spec_id: The specification ID to rename.
            new_slug: The new slug.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated specification metadata.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecValidationError: If the new slug is invalid.
            DuplicateIdError: If a spec with the new slug already exists.
        """
        # Get existing spec
        existing = self.get_spec(spec_id)
        old_slug = existing.slug

        if new_slug == old_slug:
            return existing

        # Validate new slug format
        self._validate_slug(new_slug)

        # Check for duplicate slug
        root_index = self._load_root_index()
        for spec in root_index.get("specs", []):
            if spec.get("slug") == new_slug:
                msg = f"Specification with slug {new_slug!r} already exists"
                raise DuplicateIdError(msg, entity_id=new_slug, entity_type="spec")

        # Create updated metadata
        now = datetime.now(UTC)
        updated = SpecMetadata(
            id=existing.id,
            slug=new_slug,
            title=existing.title,
            spec_type=existing.spec_type,
            status=existing.status,
            created=existing.created,
            updated=now,
            version=existing.version,
            authors=existing.authors,
            reviewers=existing.reviewers,
            relationships=existing.relationships,
            tags=existing.tags,
            summary=existing.summary,
            documents=existing.documents,
            external_refs=existing.external_refs,
            counts=existing.counts,
        )

        # Create new directory and write per-spec index
        new_dir = self._spec_dir_path(spec_id, new_slug)
        spec_data = self._spec_metadata_to_dict(updated)
        self._write_spec_index(spec_id, new_slug, spec_data)

        # Update root index with error recovery
        try:
            specs_list = list(root_index.get("specs", []))
            for i, spec in enumerate(specs_list):
                if spec.get("id") == spec_id:
                    specs_list[i]["slug"] = new_slug
                    specs_list[i]["updated"] = now.isoformat()
                    break
            self._write_root_index(specs_list)
        except Exception:
            # Cleanup new directory on failure
            if new_dir.exists():
                shutil.rmtree(new_dir)
            raise

        # Remove old directory (safe to fail - spec already updated in index)
        old_dir = self._spec_dir_path(spec_id, old_slug)
        if old_dir.exists():
            shutil.rmtree(old_dir)

        # Record history
        self._record_history(
            "renamed", actor, spec_id, from_value=old_slug, to_value=new_slug
        )

        # Commit changes
        _ = self._commit(f"rename {spec_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(spec_id)

        return updated

    def archive_spec(
        self,
        spec_id: str,
        *,
        actor: str,
        session_id: str | None = None,
    ) -> SpecMetadata:
        """Archive a specification by setting its status to deprecated.

        Args:
            spec_id: The specification ID to archive.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated specification metadata.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        return self.update_spec(
            spec_id,
            status=SpecStatus.DEPRECATED,
            actor=actor,
            session_id=session_id,
        )

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _validate_id_and_slug(
        self, spec_id: str, metadata: SpecMetadata
    ) -> list[SpecValidationIssue]:
        """Validate spec ID and slug format."""
        issues: list[SpecValidationIssue] = []
        config = self._get_config()

        result = validate_spec_id(spec_id, config.numbering)
        if not result.is_valid:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="id",
                    message=result.error_message or "Invalid spec ID format",
                    severity="error",
                )
            )

        if not _SLUG_PATTERN.match(metadata.slug):
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="slug",
                    message=f"Invalid slug format: {metadata.slug!r}",
                    severity="error",
                )
            )

        return issues

    def _validate_type_constraints_for_spec(
        self, spec_id: str, metadata: SpecMetadata
    ) -> list[SpecValidationIssue]:
        """Validate type-specific constraints."""
        issues: list[SpecValidationIssue] = []

        is_enhancement = metadata.spec_type == SpecType.ENHANCEMENT
        if is_enhancement and not metadata.relationships.extends:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="extends",
                    message="ENHANCEMENT specifications must have 'extends' set",
                    severity="error",
                )
            )

        is_integration = metadata.spec_type == SpecType.INTEGRATION
        has_enough = len(metadata.relationships.integrates) >= _MIN_INTEGRATION_ITEMS
        if is_integration and not has_enough:
            msg = (
                f"INTEGRATION specifications must have at least "
                f"{_MIN_INTEGRATION_ITEMS} items in 'integrates'"
            )
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="integrates",
                    message=msg,
                    severity="error",
                )
            )

        return issues

    def _validate_relationship_targets(
        self, spec_id: str, metadata: SpecMetadata, existing_ids: set[str | None]
    ) -> list[SpecValidationIssue]:
        """Validate that relationship targets exist."""
        issues: list[SpecValidationIssue] = []
        rel = metadata.relationships

        # Check depends_on targets
        issues.extend(
            SpecValidationIssue(
                spec_id=spec_id,
                field="depends_on",
                message=f"Dependency target not found: {dep_id}",
                severity="error",
                related_id=dep_id,
            )
            for dep_id in rel.depends_on
            if dep_id not in existing_ids
        )

        # Check extends target
        if rel.extends and rel.extends not in existing_ids:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="extends",
                    message=f"Extends target not found: {rel.extends}",
                    severity="error",
                    related_id=rel.extends,
                )
            )

        # Check integrates targets
        issues.extend(
            SpecValidationIssue(
                spec_id=spec_id,
                field="integrates",
                message=f"Integrates target not found: {int_id}",
                severity="error",
                related_id=int_id,
            )
            for int_id in rel.integrates
            if int_id not in existing_ids
        )

        # Check supersedes target
        if rel.supersedes and rel.supersedes not in existing_ids:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="supersedes",
                    message=f"Supersedes target not found: {rel.supersedes}",
                    severity="error",
                    related_id=rel.supersedes,
                )
            )

        return issues

    def _validate_optional_fields(
        self, spec_id: str, metadata: SpecMetadata, *, strict: bool
    ) -> list[SpecValidationIssue]:
        """Validate optional fields that generate warnings."""
        issues: list[SpecValidationIssue] = []
        severity: Literal["error", "warning"] = "error" if strict else "warning"

        if not metadata.title.strip():
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="title",
                    message="Specification has empty title",
                    severity=severity,
                )
            )

        if not metadata.summary:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="summary",
                    message="Specification has no summary",
                    severity=severity,
                )
            )

        if not metadata.authors:
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="authors",
                    message="Specification has no authors",
                    severity=severity,
                )
            )

        return issues

    def validate_spec(
        self,
        spec_id: str,
        *,
        strict: bool = False,
    ) -> list[SpecValidationIssue]:
        """Validate a specification.

        Args:
            spec_id: The specification ID to validate.
            strict: Include warnings as errors.

        Returns:
            List of validation issues.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        metadata = self.get_spec(spec_id)
        issues: list[SpecValidationIssue] = []

        # Validate ID and slug format
        issues.extend(self._validate_id_and_slug(spec_id, metadata))

        # Validate type constraints
        issues.extend(self._validate_type_constraints_for_spec(spec_id, metadata))

        # Validate relationship targets exist
        root_index = self._load_root_index()
        existing_ids = {spec.get("id") for spec in root_index.get("specs", [])}
        issues.extend(
            self._validate_relationship_targets(spec_id, metadata, existing_ids)
        )

        # Validate optional fields (warnings)
        issues.extend(self._validate_optional_fields(spec_id, metadata, strict=strict))

        # Verify spec directory exists
        spec_dir = self._spec_dir_path(spec_id, metadata.slug)
        if not spec_dir.exists():
            issues.append(
                SpecValidationIssue(
                    spec_id=spec_id,
                    field="directory",
                    message=f"Specification directory not found: {spec_dir}",
                    severity="error",
                )
            )

        return issues
