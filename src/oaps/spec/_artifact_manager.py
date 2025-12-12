# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false
"""Artifact manager for CRUD operations on specification artifacts.

This module provides the ArtifactManager class for managing artifacts within
specifications. It handles artifact creation, updates, deletion, and supports
both text-based (Markdown with frontmatter) and binary artifacts (with sidecar
metadata files).

This manager delegates to the generic oaps.artifacts.ArtifactStore for
file I/O and index management, while handling spec-specific concerns
like history logging and SpecManager integration.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from oaps.exceptions import (
    SpecArtifactNotFoundError,
    SpecNotFoundError,
    SpecValidationError,
)
from oaps.spec._io import append_jsonl
from oaps.spec._models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    RebuildResult,
)

if TYPE_CHECKING:
    from oaps.artifacts import ArtifactStore
    from oaps.repository import OapsRepository
    from oaps.spec._artifact_adapter import SpecArtifactAdapter
    from oaps.spec._spec_manager import SpecManager

__all__ = ["ArtifactManager"]

# Binary file extensions
_BINARY_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".mp4",
        ".webm",
        ".mov",
        ".avi",
        ".pdf",
        ".zip",
    }
)

# Default text artifact types
_TEXT_ARTIFACT_TYPES: Final[frozenset[ArtifactType]] = frozenset(
    {
        ArtifactType.REVIEW,
        ArtifactType.CHANGE,
        ArtifactType.ANALYSIS,
        ArtifactType.DECISION,
        ArtifactType.DIAGRAM,
        ArtifactType.EXAMPLE,
    }
)

# Default binary artifact types
_BINARY_ARTIFACT_TYPES: Final[frozenset[ArtifactType]] = frozenset(
    {
        ArtifactType.IMAGE,
        ArtifactType.VIDEO,
    }
)


def _is_binary_file(extension: str) -> bool:
    """Check if a file extension indicates a binary file.

    Args:
        extension: The file extension (including dot).

    Returns:
        True if the extension indicates a binary file.
    """
    return extension.lower() in _BINARY_EXTENSIONS


def _is_binary_artifact_type(artifact_type: ArtifactType, extension: str) -> bool:
    """Determine if an artifact should be treated as binary.

    Args:
        artifact_type: The artifact type.
        extension: The file extension (for mockup type detection).

    Returns:
        True if the artifact should be treated as binary.
    """
    if artifact_type in _BINARY_ARTIFACT_TYPES:
        return True
    if artifact_type in _TEXT_ARTIFACT_TYPES:
        return False
    # Mockup can be either - check extension
    return _is_binary_file(extension)


class ArtifactManager:
    """Manager for CRUD operations on artifacts within specifications.

    The ArtifactManager provides methods for creating, reading, updating,
    and deleting artifacts. It supports both text artifacts (Markdown with
    frontmatter) and binary artifacts (with sidecar metadata files).

    This manager delegates to the generic oaps.artifacts.ArtifactStore for
    file I/O and index management, while handling spec-specific concerns
    like history logging and SpecManager integration.

    Attributes:
        _spec_manager: The specification manager for accessing spec data.
        _stores_cache: Cache of ArtifactStore instances per spec.
        _adapter: Adapter for model conversion.
    """

    __slots__: Final = (
        "_adapter",
        "_oaps_repo",
        "_spec_manager",
        "_stores_cache",
    )

    _adapter: SpecArtifactAdapter
    _oaps_repo: OapsRepository | None
    _spec_manager: SpecManager
    _stores_cache: dict[str, ArtifactStore]

    def __init__(
        self,
        spec_manager: SpecManager,
        *,
        oaps_repo: OapsRepository | None = None,
    ) -> None:
        """Initialize the artifact manager.

        Args:
            spec_manager: The specification manager for accessing spec data.
            oaps_repo: Repository for committing changes. If None, falls back
                to spec_manager's repository if available.
        """
        from oaps.spec._artifact_adapter import (  # noqa: PLC0415 - avoid circular
            SpecArtifactAdapter,
        )

        self._spec_manager = spec_manager
        self._oaps_repo = (
            oaps_repo
            if oaps_repo is not None
            else getattr(spec_manager, "_oaps_repo", None)
        )
        self._stores_cache = {}
        self._adapter = SpecArtifactAdapter()

    # -------------------------------------------------------------------------
    # Path Helpers
    # -------------------------------------------------------------------------

    def _get_spec_dir(self, spec_id: str) -> Path:
        """Get the directory path for a specification.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the specification directory.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        spec = self._spec_manager.get_spec(spec_id)
        return self._spec_manager.base_path / f"{spec_id}-{spec.slug}"

    def _history_path(self, spec_id: str) -> Path:
        """Get the path to the history.jsonl file for a spec.

        Args:
            spec_id: The specification ID.

        Returns:
            Path to the history.jsonl file.
        """
        return self._get_spec_dir(spec_id) / "history.jsonl"

    # -------------------------------------------------------------------------
    # Store Management
    # -------------------------------------------------------------------------

    def _get_or_create_store(self, spec_id: str) -> ArtifactStore:
        """Get or create an ArtifactStore for the given spec.

        This lazily creates ArtifactStore instances for each spec and caches
        them for reuse. The store is configured for the spec's directory.

        Args:
            spec_id: The specification ID.

        Returns:
            ArtifactStore instance for the spec.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        if spec_id in self._stores_cache:
            return self._stores_cache[spec_id]

        # Validate spec exists and get spec directory
        spec_dir = self._get_spec_dir(spec_id)

        # Import at runtime to avoid circular imports
        from oaps.artifacts import ArtifactStore  # noqa: PLC0415

        # Create store with auto_index disabled - we manage index ourselves
        store = ArtifactStore(spec_dir, auto_index=True)
        store.initialize()

        self._stores_cache[spec_id] = store
        return store

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    def _invalidate_cache(self, spec_id: str | None = None) -> None:
        """Invalidate cached store data.

        Args:
            spec_id: If provided, only invalidate cache for this spec.
                If None, invalidate all caches.
        """
        if spec_id is None:
            self._stores_cache.clear()
        else:
            _ = self._stores_cache.pop(spec_id, None)

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

    def _record_history(  # noqa: PLR0913
        self,
        spec_id: str,
        event: str,
        actor: str,
        artifact_id: str,
        *,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        """Record an event to the per-spec history log.

        Args:
            spec_id: The specification ID.
            event: The event type.
            actor: The actor who performed the action.
            artifact_id: The affected artifact ID.
            from_value: The previous value (for updates).
            to_value: The new value (for updates).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "actor": actor,
            "id": artifact_id,
        }
        if from_value is not None:
            entry["from_value"] = from_value
        if to_value is not None:
            entry["to_value"] = to_value

        append_jsonl(self._history_path(spec_id), entry)

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def list_artifacts(
        self,
        spec_id: str,
        *,
        filter_type: ArtifactType | None = None,
        filter_status: ArtifactStatus | None = None,
        filter_tags: list[str] | None = None,
    ) -> list[Artifact]:
        """List artifacts with optional filtering.

        Args:
            spec_id: The specification ID.
            filter_type: Filter by artifact type.
            filter_status: Filter by status.
            filter_tags: Filter by tags (artifacts must have all listed tags).

        Returns:
            List of matching artifacts.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        store = self._get_or_create_store(spec_id)

        # Convert enum filters to strings for generic store
        type_filter = (
            self._adapter.spec_type_to_generic(filter_type)
            if filter_type is not None
            else None
        )
        status_filter = (
            self._adapter.spec_status_to_generic(filter_status)
            if filter_status is not None
            else None
        )

        # Get artifacts from store with basic filtering
        # Note: generic store only supports single tag, so we filter tags ourselves
        generic_artifacts = store.list_artifacts(
            type_filter=type_filter,
            status_filter=status_filter,
        )

        # Convert to spec artifacts and apply tags filter
        results: list[Artifact] = []
        for generic_artifact in generic_artifacts:
            spec_artifact = self._adapter.generic_to_spec(
                generic_artifact, store.artifacts_path
            )

            # Apply multi-tag filter (store only supports single tag)
            if filter_tags and not all(
                tag in spec_artifact.tags for tag in filter_tags
            ):
                continue

            results.append(spec_artifact)

        return results

    def get_artifact(self, spec_id: str, artifact_id: str) -> Artifact:
        """Get a single artifact by ID.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID.

        Returns:
            The artifact.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If the artifact doesn't exist.
        """
        store = self._get_or_create_store(spec_id)
        generic_artifact = store.get_artifact(artifact_id)

        if generic_artifact is None:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            )

        return self._adapter.generic_to_spec(generic_artifact, store.artifacts_path)

    def artifact_exists(self, spec_id: str, artifact_id: str) -> bool:
        """Check if an artifact exists.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID.

        Returns:
            True if the artifact exists.
        """
        try:
            store = self._get_or_create_store(spec_id)
        except SpecNotFoundError:
            return False

        return store.artifact_exists(artifact_id)

    def get_artifact_content(self, spec_id: str, artifact_id: str) -> str:
        """Get the content of a text artifact.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID.

        Returns:
            The artifact content (Markdown body without frontmatter).

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If the artifact doesn't exist.
            SpecValidationError: If the artifact is binary.
        """
        store = self._get_or_create_store(spec_id)
        generic_artifact = store.get_artifact(artifact_id)

        if generic_artifact is None:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            )

        # Check if binary artifact
        if generic_artifact.is_binary:
            msg = f"Cannot read content of binary artifact: {artifact_id}"
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="artifact_type",
                value=generic_artifact.type,
                expected="text artifact type",
            )

        # Get raw content and parse to extract body (without frontmatter)
        raw_content = store.get_artifact_content(artifact_id)
        if raw_content is None:
            msg = f"Artifact file not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            )

        # Parse frontmatter to get just the body
        if isinstance(raw_content, bytes):
            raw_content = raw_content.decode("utf-8")

        # Extract body by splitting on frontmatter delimiters
        # Frontmatter format: ---\n<yaml>\n---\n<body>
        _frontmatter_parts_count = 3  # empty, frontmatter yaml, body
        if raw_content.startswith("---"):
            parts = raw_content.split("---", 2)
            if len(parts) >= _frontmatter_parts_count:
                # parts[0] is empty, parts[1] is frontmatter, parts[2] is body
                return parts[2].lstrip("\n")
        return raw_content

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def add_artifact(  # noqa: PLR0913
        self,
        spec_id: str,
        artifact_type: ArtifactType,
        title: str,
        *,
        content: str | None = None,
        source_path: str | Path | None = None,
        description: str | None = None,
        subtype: str | None = None,
        references: list[str] | None = None,
        tags: list[str] | None = None,
        type_fields: dict[str, Any] | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Artifact:
        """Create a new artifact.

        Either content or source_path must be provided:
        - content mode: Create new text artifact with provided content
        - import mode: Copy existing file to artifacts/, add frontmatter/sidecar

        Args:
            spec_id: The specification ID.
            artifact_type: The artifact type.
            title: Human-readable artifact title.
            content: Content for new text artifact (mutually exclusive with
                source_path).
            source_path: Path to existing file to import (mutually exclusive
                with content).
            description: Brief description of the artifact.
            subtype: Further categorization within type.
            references: IDs of related requirements or other artifacts.
            tags: Freeform tags for filtering.
            type_fields: Type-specific metadata fields.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The created artifact.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecValidationError: If validation fails or both/neither content
                and source_path provided.
        """
        # Validate content/source_path mutually exclusive
        if content is not None and source_path is not None:
            msg = "Cannot specify both content and source_path"
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="content",
                expected="either content or source_path, not both",
            )
        if content is None and source_path is None:
            msg = "Must specify either content or source_path"
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="content",
                expected="either content or source_path",
            )

        # Validate source file exists if provided
        if source_path is not None:
            source = Path(source_path)
            if not source.exists():
                msg = f"Source file not found: {source_path}"
                raise SpecValidationError(
                    msg,
                    spec_id=spec_id,
                    field="source_path",
                    value=str(source_path),
                )
            extension = source.suffix or ".bin"
        else:
            extension = ".md"

        is_binary = _is_binary_artifact_type(artifact_type, extension)

        # Validate text artifacts can't be created with content for binary types
        if is_binary and content is not None:
            msg = (
                f"Cannot create binary artifact type {artifact_type.value} with content"
            )
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="artifact_type",
                value=artifact_type.value,
                expected="text artifact type for content mode",
            )

        # Get or create store (validates spec exists)
        store = self._get_or_create_store(spec_id)

        # Get type prefix for the artifact type
        type_prefix = self._adapter.spec_type_to_prefix(artifact_type)

        # Delegate to store
        generic_artifact = store.add_artifact(
            type_prefix=type_prefix,
            title=title,
            author=actor,
            content=content,
            subtype=subtype,
            references=references,
            tags=tags,
            summary=description,  # spec's description maps to generic's summary
            type_fields=type_fields,
            file_path=source_path,  # import mode
        )

        # Convert to spec artifact
        spec_artifact = self._adapter.generic_to_spec(
            generic_artifact, store.artifacts_path
        )

        # Record history
        self._record_history(
            spec_id, "artifact_created", actor, generic_artifact.id, to_value=title
        )

        # Commit changes
        _ = self._commit(
            f"add artifact {spec_id}:{generic_artifact.id}", session_id=session_id
        )

        return spec_artifact

    def update_artifact(  # noqa: PLR0913
        self,
        spec_id: str,
        artifact_id: str,
        *,
        title: str | None = None,
        status: ArtifactStatus | None = None,
        description: str | None = None,
        subtype: str | None = None,
        references: list[str] | None = None,
        tags: list[str] | None = None,
        type_fields: dict[str, Any] | None = None,
        actor: str,
        session_id: str | None = None,
    ) -> Artifact:
        """Update an existing artifact's metadata.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID to update.
            title: New title (optional).
            status: New status (optional).
            description: New description (optional).
            subtype: New subtype (optional).
            references: New references (replaces existing).
            tags: New tags (replaces existing).
            type_fields: New type fields (replaces existing).
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated artifact.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If the artifact doesn't exist.
        """
        from oaps.exceptions import ArtifactNotFoundError  # noqa: PLC0415

        # Get existing artifact for history recording
        existing = self.get_artifact(spec_id, artifact_id)

        # Get or create store
        store = self._get_or_create_store(spec_id)

        # Convert status enum to string for generic store
        status_str = (
            self._adapter.spec_status_to_generic(status) if status is not None else None
        )

        # Delegate to store
        try:
            generic_artifact = store.update_artifact(
                artifact_id,
                title=title,
                status=status_str,
                subtype=subtype,
                references=references,
                tags=tags,
                summary=description,  # spec's description maps to generic's summary
                type_fields=type_fields,
            )
        except ArtifactNotFoundError as exc:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            ) from exc

        # Convert to spec artifact
        spec_artifact = self._adapter.generic_to_spec(
            generic_artifact, store.artifacts_path
        )

        # Record history
        from_val = existing.status.value if status else None
        to_val = spec_artifact.status.value if status else None
        self._record_history(
            spec_id,
            "artifact_updated",
            actor,
            artifact_id,
            from_value=from_val,
            to_value=to_val,
        )

        # Commit changes
        _ = self._commit(
            f"update artifact {spec_id}:{artifact_id}", session_id=session_id
        )

        return spec_artifact

    def update_artifact_content(
        self,
        spec_id: str,
        artifact_id: str,
        content: str,
        *,
        actor: str,
        session_id: str | None = None,
    ) -> Artifact:
        """Update the content of a text artifact.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID.
            content: New content for the artifact.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated artifact.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If the artifact doesn't exist.
            SpecValidationError: If the artifact is binary.
        """
        from oaps.exceptions import ArtifactNotFoundError  # noqa: PLC0415

        # Get store (validates spec exists)
        store = self._get_or_create_store(spec_id)
        generic_artifact = store.get_artifact(artifact_id)

        if generic_artifact is None:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            )

        # Check if binary
        if generic_artifact.is_binary:
            msg = f"Cannot update content of binary artifact: {artifact_id}"
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="artifact_type",
                value=generic_artifact.type,
                expected="text artifact type",
            )

        # Delegate to store (update with new content)
        try:
            updated_generic = store.update_artifact(artifact_id, content=content)
        except ArtifactNotFoundError as exc:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            ) from exc

        # Convert to spec artifact
        spec_artifact = self._adapter.generic_to_spec(
            updated_generic, store.artifacts_path
        )

        # Record history
        self._record_history(spec_id, "artifact_content_updated", actor, artifact_id)

        # Commit changes
        _ = self._commit(
            f"update artifact content {spec_id}:{artifact_id}", session_id=session_id
        )

        return spec_artifact

    def delete_artifact(
        self,
        spec_id: str,
        artifact_id: str,
        *,
        _delete_file: bool = False,
        actor: str,
        session_id: str | None = None,
    ) -> None:
        """Delete an artifact.

        Args:
            spec_id: The specification ID.
            artifact_id: The artifact ID to delete.
            delete_file: If True, also delete the artifact file(s).
                Note: The underlying store always deletes files when removing
                from the index. This parameter is kept for API compatibility.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If the artifact doesn't exist.
        """
        from oaps.exceptions import ArtifactNotFoundError  # noqa: PLC0415

        # Get existing artifact for history (validates spec and artifact exist)
        existing = self.get_artifact(spec_id, artifact_id)

        # Get or create store
        store = self._get_or_create_store(spec_id)

        # Delegate to store (force=True skips reference checks, matching spec behavior)
        # Note: store always deletes files
        try:
            store.delete_artifact(artifact_id, force=True)
        except ArtifactNotFoundError as exc:
            msg = f"Artifact not found: {artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=artifact_id, spec_id=spec_id
            ) from exc

        # Record history
        self._record_history(
            spec_id, "artifact_deleted", actor, artifact_id, from_value=existing.title
        )

        # Commit changes
        _ = self._commit(
            f"delete artifact {spec_id}:{artifact_id}", session_id=session_id
        )

    def supersede_artifact(
        self,
        spec_id: str,
        old_artifact_id: str,
        new_artifact_id: str,
        *,
        actor: str,
        session_id: str | None = None,
    ) -> tuple[Artifact, Artifact]:
        """Mark an artifact as superseded by another.

        Args:
            spec_id: The specification ID.
            old_artifact_id: The artifact ID being superseded.
            new_artifact_id: The artifact ID that supersedes.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            Tuple of (old_artifact, new_artifact) with updated relationships.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
            SpecArtifactNotFoundError: If either artifact doesn't exist.
            SpecValidationError: If old artifact is already superseded or
                types don't match.
        """
        from oaps.exceptions import ArtifactNotFoundError  # noqa: PLC0415

        # Get or create store (validates spec exists)
        store = self._get_or_create_store(spec_id)

        # Delegate to store
        try:
            old_generic, new_generic = store.supersede_artifact(
                old_artifact_id, new_artifact_id
            )
        except ArtifactNotFoundError as exc:
            # Determine which artifact is missing
            if store.get_artifact(old_artifact_id) is None:
                msg = f"Artifact not found: {old_artifact_id}"
                raise SpecArtifactNotFoundError(
                    msg, artifact_id=old_artifact_id, spec_id=spec_id
                ) from exc
            msg = f"Artifact not found: {new_artifact_id}"
            raise SpecArtifactNotFoundError(
                msg, artifact_id=new_artifact_id, spec_id=spec_id
            ) from exc
        except ValueError as exc:
            # Store raises ValueError for validation issues
            msg = str(exc)
            raise SpecValidationError(
                msg,
                spec_id=spec_id,
                field="superseded_by",
            ) from exc

        # Convert to spec artifacts
        updated_old = self._adapter.generic_to_spec(old_generic, store.artifacts_path)
        updated_new = self._adapter.generic_to_spec(new_generic, store.artifacts_path)

        # Record history
        self._record_history(
            spec_id,
            "artifact_superseded",
            actor,
            old_artifact_id,
            to_value=new_artifact_id,
        )

        # Commit changes
        _ = self._commit(
            f"supersede artifact {spec_id}:{old_artifact_id}", session_id=session_id
        )

        return updated_old, updated_new

    def rebuild_index(
        self, spec_id: str, *, actor: str, session_id: str | None = None
    ) -> RebuildResult:
        """Rebuild the artifacts index from files in the artifacts directory.

        Scans the artifacts directory for files and rebuilds the artifacts.json
        index based on frontmatter/sidecar metadata found in files.

        Args:
            spec_id: The specification ID.
            actor: The actor performing the action (for history).
            session_id: Optional session ID for commit trailer.

        Returns:
            RebuildResult with counts of scanned, indexed, skipped files and errors.

        Raises:
            SpecNotFoundError: If the specification doesn't exist.
        """
        # Validate spec exists
        _ = self._spec_manager.get_spec(spec_id)

        # Get or create store
        store = self._get_or_create_store(spec_id)
        artifacts_dir = store.artifacts_path

        if not artifacts_dir.exists():
            # No artifacts directory - store.rebuild_index handles this
            store.rebuild_index()
            return RebuildResult(scanned=0, indexed=0, skipped=0, errors=())

        # Count files before rebuild (excluding sidecar files)
        scanned = sum(
            1
            for f in artifacts_dir.iterdir()
            if f.is_file() and not f.name.endswith(".metadata.yaml")
        )

        # Delegate to store
        store.rebuild_index()

        # Invalidate cache to pick up new index
        self._invalidate_cache(spec_id)

        # Count indexed artifacts
        indexed = len(store.list_artifacts())

        # Calculate skipped (files without valid metadata)
        skipped = scanned - indexed

        # Record history
        self._record_history(
            spec_id,
            "artifacts_index_rebuilt",
            actor,
            spec_id,
            to_value=str(indexed),
        )

        # Commit changes
        _ = self._commit(f"rebuild artifacts index {spec_id}", session_id=session_id)

        return RebuildResult(
            scanned=scanned,
            indexed=indexed,
            skipped=skipped,
            errors=(),  # Store doesn't report individual errors
        )
