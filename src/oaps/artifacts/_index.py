"""Artifact index for O(1) lookup.

This module provides the ArtifactIndex class for efficient queries over
the artifacts.json index file. It supports lookup by ID, filtering by
various criteria, and reference tracking.

Example:
    >>> from pathlib import Path
    >>> from oaps.artifacts._index import ArtifactIndex
    >>> index = ArtifactIndex(Path("artifacts.json"))
    >>> artifact = index.get("RV-0001")
    >>> index.get_next_number("RV")
    2
"""

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

# Type alias for artifact summary dict stored in index
type ArtifactSummary = dict[str, Any]


class ArtifactIndex:
    """Index for O(1) artifact lookup.

    The index loads artifact summaries from artifacts.json and provides
    efficient lookup by ID, type, and other criteria. It also tracks
    references between artifacts for dependency analysis.

    Attributes:
        _index_path: Path to the artifacts.json file.
        _by_id: Dict mapping artifact IDs to summary dicts.
        _by_type: Dict mapping type prefixes to lists of summaries.
        _references: Dict mapping artifact IDs to lists of referencing IDs.
        _updated: Timestamp when index was last loaded.
    """

    __slots__ = ("_by_id", "_by_type", "_index_path", "_references", "_updated")

    def __init__(self, index_path: Path | str) -> None:
        """Load index from file.

        Args:
            index_path: Path to artifacts.json.

        Note:
            If the index file doesn't exist or is invalid, an empty index
            is created.
        """
        self._index_path = Path(index_path)
        self._by_id: dict[str, ArtifactSummary] = {}
        self._by_type: dict[str, list[ArtifactSummary]] = {}
        self._references: dict[str, list[str]] = {}
        self._updated = datetime.now(UTC)

        self._load()

    def _load(self) -> None:
        """Load index data from file."""
        if not self._index_path.exists():
            return

        try:
            content = self._index_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        # Extract updated timestamp
        if "updated" in data:
            with contextlib.suppress(ValueError, TypeError):
                self._updated = datetime.fromisoformat(data["updated"])

        # Load artifact summaries
        artifacts = data.get("artifacts", [])
        if not isinstance(artifacts, list):
            return

        for artifact in artifacts:
            self._index_artifact(artifact)

    def _index_artifact(self, artifact: object) -> None:
        """Index a single artifact entry.

        Populates _by_id, _by_type, and _references for a single artifact.

        Args:
            artifact: Artifact dict from the index file.
        """
        if not isinstance(artifact, dict):
            return

        artifact_id = artifact.get("id")
        if not artifact_id or not isinstance(artifact_id, str):
            return

        # Index by ID
        self._by_id[artifact_id] = artifact

        # Index by type
        prefix = artifact_id.split("-")[0] if "-" in artifact_id else ""
        if prefix:
            if prefix not in self._by_type:
                self._by_type[prefix] = []
            self._by_type[prefix].append(artifact)

        # Index references
        refs = artifact.get("references", [])
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, str):
                    if ref not in self._references:
                        self._references[ref] = []
                    self._references[ref].append(artifact_id)

    @property
    def updated(self) -> datetime:
        """When index was last updated."""
        return self._updated

    @property
    def count(self) -> int:
        """Number of artifacts in index."""
        return len(self._by_id)

    def get(self, artifact_id: str) -> ArtifactSummary | None:
        """Get artifact summary by ID.

        Args:
            artifact_id: Artifact ID (e.g., "RV-0001").

        Returns:
            Artifact summary dict or None if not found.

        Example:
            >>> index = ArtifactIndex(Path("artifacts.json"))
            >>> summary = index.get("RV-0001")
            >>> summary["title"] if summary else None
            'Security Review'
        """
        return self._by_id.get(artifact_id)

    def filter(  # noqa: PLR0913
        self,
        *,
        type_filter: str | None = None,
        status_filter: str | None = None,
        author_filter: str | None = None,
        tag_filter: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[ArtifactSummary]:
        """Filter artifacts by criteria.

        All filters are combined with AND logic. Only artifacts matching
        all specified criteria are returned.

        Args:
            type_filter: Filter by artifact type (prefix or name).
            status_filter: Filter by status.
            author_filter: Filter by author.
            tag_filter: Filter by tag (artifact must have tag).
            created_after: Include only artifacts created after this datetime.
            created_before: Include only artifacts created before this datetime.

        Returns:
            List of matching artifact summaries.

        Example:
            >>> index = ArtifactIndex(Path("artifacts.json"))
            >>> reviews = index.filter(type_filter="RV", status_filter="complete")
        """
        results: list[ArtifactSummary] = []

        for artifact in self._by_id.values():
            # Type filter
            if type_filter:
                artifact_id = artifact.get("id", "")
                prefix = artifact_id.split("-")[0] if "-" in artifact_id else ""
                artifact_type = artifact.get("type", "")
                if type_filter not in (prefix, artifact_type):
                    continue

            # Status filter
            if status_filter and artifact.get("status") != status_filter:
                continue

            # Author filter
            if author_filter and artifact.get("author") != author_filter:
                continue

            # Tag filter
            if tag_filter:
                tags = artifact.get("tags", [])
                if not isinstance(tags, list) or tag_filter not in tags:
                    continue

            # Date filters
            if created_after or created_before:
                created_str = artifact.get("created")
                if not created_str:
                    continue
                try:
                    created = datetime.fromisoformat(created_str)
                except (ValueError, TypeError):
                    continue

                if created_after and created < created_after:
                    continue
                if created_before and created > created_before:
                    continue

            results.append(artifact)

        return results

    def get_by_type(self, type_prefix: str) -> list[ArtifactSummary]:
        """Get all artifacts of a type.

        Args:
            type_prefix: Two-letter prefix (e.g., "RV").

        Returns:
            List of artifact summaries for that type.

        Example:
            >>> index = ArtifactIndex(Path("artifacts.json"))
            >>> reviews = index.get_by_type("RV")
        """
        return list(self._by_type.get(type_prefix, []))

    def get_next_number(self, type_prefix: str) -> int:
        """Get next available number for a type.

        Finds the highest number currently used for the type and returns
        the next sequential number.

        Args:
            type_prefix: Two-letter prefix.

        Returns:
            Next sequential number (1 if no artifacts of this type exist).

        Example:
            >>> index = ArtifactIndex(Path("artifacts.json"))
            >>> index.get_next_number("RV")  # If RV-0003 is highest
            4
        """
        artifacts = self._by_type.get(type_prefix, [])
        if not artifacts:
            return 1

        max_number = 0
        for artifact in artifacts:
            artifact_id = artifact.get("id", "")
            if "-" in artifact_id:
                try:
                    number = int(artifact_id.split("-")[1])
                    max_number = max(max_number, number)
                except ValueError:
                    pass

        return max_number + 1

    def get_references_to(self, target_id: str) -> list[str]:
        """Find artifacts that reference a target.

        Args:
            target_id: ID being referenced.

        Returns:
            List of artifact IDs that reference target.

        Example:
            >>> index = ArtifactIndex(Path("artifacts.json"))
            >>> refs = index.get_references_to("FR-0001")
            ['RV-0001', 'AN-0002']
        """
        return list(self._references.get(target_id, []))

    def all_ids(self) -> list[str]:
        """Get all artifact IDs in the index.

        Returns:
            List of all artifact IDs, sorted.
        """
        return sorted(self._by_id.keys())

    def contains(self, artifact_id: str) -> bool:
        """Check if an artifact exists in the index.

        Args:
            artifact_id: Artifact ID to check.

        Returns:
            True if artifact exists in index.
        """
        return artifact_id in self._by_id

    def to_dict(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Convert index to serializable dict.

        Returns:
            Dict suitable for JSON serialization.
        """
        return {
            "updated": self._updated.isoformat(),
            "artifacts": list(self._by_id.values()),
        }

    @classmethod
    def from_artifacts(
        cls,
        artifacts: Sequence[ArtifactSummary],
        *,
        index_path: Path | str | None = None,
    ) -> ArtifactIndex:
        """Create an index from a list of artifact summaries.

        This is useful for building an index in memory without reading
        from a file.

        Args:
            artifacts: List of artifact summary dicts.
            index_path: Optional path (used for reference only).

        Returns:
            New ArtifactIndex populated with the artifacts.
        """
        # Create instance without loading from file
        # Note: Accessing private members is intentional here since we're
        # initializing our own class without calling __init__
        instance = cls.__new__(cls)
        instance._index_path = (  # noqa: SLF001
            Path(index_path) if index_path else Path("artifacts.json")
        )
        instance._by_id = {}  # noqa: SLF001
        instance._by_type = {}  # noqa: SLF001
        instance._references = {}  # noqa: SLF001
        instance._updated = datetime.now(UTC)  # noqa: SLF001

        # Populate from artifacts using the helper method
        for artifact in artifacts:
            instance._index_artifact(artifact)  # noqa: SLF001

        return instance
