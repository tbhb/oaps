# pyright: reportImportCycles=false
r"""Artifact store for managing artifacts in a directory.

This module provides the ArtifactStore class for CRUD operations on artifacts
within a configurable base directory. It handles file creation, metadata
management, and index updates.

Example:
    >>> from pathlib import Path
    >>> from oaps.artifacts import ArtifactStore
    >>> store = ArtifactStore(Path(".oaps/docs/specs/my-spec"))
    >>> store.initialize()
    >>> artifact = store.add_artifact(
    ...     type_prefix="RV",
    ...     title="Security Review",
    ...     author="reviewer",
    ...     content="# Security Review\n\nContent here...",
    ... )
"""

import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oaps.artifacts._index import ArtifactIndex
from oaps.artifacts._metadata import (
    format_artifact_id,
    generate_filename,
    generate_slug,
    parse_frontmatter,
    parse_sidecar,
    serialize_frontmatter,
    serialize_sidecar,
)
from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._types import Artifact, ArtifactMetadata, ValidationError
from oaps.artifacts._validator import (
    VALID_STATUSES,
    raise_if_validation_errors,
    validate_artifact,
)
from oaps.exceptions import (
    ArtifactNotFoundError,
    ArtifactValidationError,
    TypeNotRegisteredError,
)


class ArtifactStore:
    """Store for managing artifacts in a directory.

    The ArtifactStore provides CRUD operations for artifacts within a
    configurable base directory. It maintains an index file (artifacts.json)
    for efficient queries and supports both text artifacts (with YAML
    frontmatter) and binary artifacts (with sidecar metadata files).

    Attributes:
        _base_path: Base directory for the artifact store.
        _registry: Type registry for artifact types.
        _auto_index: Whether to automatically rebuild index on changes.
        _index: Cached artifact index.
    """

    __slots__ = ("_auto_index", "_base_path", "_index", "_registry")

    def __init__(
        self,
        base_path: Path | str,
        *,
        registry: ArtifactRegistry | None = None,
        auto_index: bool = True,
    ) -> None:
        """Initialize artifact store.

        Args:
            base_path: Base directory for the artifact store.
            registry: Type registry to use (defaults to global).
            auto_index: Automatically rebuild index on changes.
        """
        self._base_path = Path(base_path)
        self._registry = registry
        self._auto_index = auto_index
        self._index: ArtifactIndex | None = None

    @property
    def base_path(self) -> Path:
        """Base path of the artifact store."""
        return self._base_path

    @property
    def artifacts_path(self) -> Path:
        """Path to artifacts/ subdirectory."""
        return self._base_path / "artifacts"

    @property
    def index_path(self) -> Path:
        """Path to artifacts.json index file."""
        return self._base_path / "artifacts.json"

    def _get_registry(self) -> ArtifactRegistry:
        """Get the type registry, initializing if needed."""
        if self._registry is None:
            self._registry = ArtifactRegistry.get_instance()
        return self._registry

    def initialize(self) -> None:
        """Initialize store directory structure.

        Creates artifacts/ subdirectory and empty artifacts.json if needed.
        """
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        if not self.index_path.exists():
            self._write_index([])

    def _write_index(
        self,
        artifacts: list[dict[str, Any]],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """Write index to file."""
        data = {
            "updated": datetime.now(UTC).isoformat(),
            "artifacts": artifacts,
        }
        self.index_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Invalidate cached index
        self._index = None

    def _artifact_to_summary(
        self,
        artifact: Artifact,
    ) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Convert Artifact to index summary dict."""
        summary: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
            "id": artifact.id,
            "type": artifact.type,
            "title": artifact.title,
            "status": artifact.status,
            "created": artifact.created.isoformat(),
            "author": artifact.author,
            "file_path": str(artifact.file_path.relative_to(self._base_path)),
        }

        if artifact.subtype:
            summary["subtype"] = artifact.subtype
        if artifact.updated:
            summary["updated"] = artifact.updated.isoformat()
        if artifact.reviewers:
            summary["reviewers"] = list(artifact.reviewers)
        if artifact.references:
            summary["references"] = list(artifact.references)
        if artifact.supersedes:
            summary["supersedes"] = artifact.supersedes
        if artifact.superseded_by:
            summary["superseded_by"] = artifact.superseded_by
        if artifact.tags:
            summary["tags"] = list(artifact.tags)
        if artifact.summary:
            summary["summary"] = artifact.summary
        if artifact.metadata_file_path:
            summary["metadata_file_path"] = str(
                artifact.metadata_file_path.relative_to(self._base_path)
            )
        if artifact.type_fields:
            summary.update(artifact.type_fields)

        return summary

    def _summary_to_artifact(
        self,
        summary: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    ) -> Artifact:
        """Convert index summary dict to Artifact."""
        # Parse created/updated datetimes
        created = summary["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)

        updated = summary.get("updated")
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        # Extract type fields (anything not in standard fields)
        standard_fields = {
            "id",
            "type",
            "title",
            "status",
            "created",
            "author",
            "file_path",
            "subtype",
            "updated",
            "reviewers",
            "references",
            "supersedes",
            "superseded_by",
            "tags",
            "summary",
            "metadata_file_path",
        }
        type_fields = {k: v for k, v in summary.items() if k not in standard_fields}

        metadata_path_str = summary.get("metadata_file_path")

        return Artifact(
            id=summary["id"],
            type=summary["type"],
            title=summary["title"],
            status=summary["status"],
            created=created,
            author=summary["author"],
            file_path=self._base_path / summary["file_path"],
            subtype=summary.get("subtype"),
            updated=updated,
            reviewers=tuple(summary.get("reviewers", [])),
            references=tuple(summary.get("references", [])),
            supersedes=summary.get("supersedes"),
            superseded_by=summary.get("superseded_by"),
            tags=tuple(summary.get("tags", [])),
            summary=summary.get("summary"),
            metadata_file_path=(
                self._base_path / metadata_path_str if metadata_path_str else None
            ),
            type_fields=type_fields,
        )

    # --- Query operations ---

    def list_artifacts(
        self,
        *,
        type_filter: str | None = None,
        status_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[Artifact]:
        """List artifacts with optional filtering.

        Args:
            type_filter: Filter by artifact type (prefix or name).
            status_filter: Filter by status.
            tag_filter: Filter by tag (artifact must have tag).

        Returns:
            List of matching artifacts.
        """
        index = self.get_index()
        summaries = index.filter(
            type_filter=type_filter,
            status_filter=status_filter,
            tag_filter=tag_filter,
        )
        return [self._summary_to_artifact(s) for s in summaries]

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        """Get artifact by ID.

        Args:
            artifact_id: Artifact ID (e.g., "RV-0001").

        Returns:
            Artifact or None if not found.
        """
        index = self.get_index()
        summary = index.get(artifact_id)
        if summary is None:
            return None
        return self._summary_to_artifact(summary)

    def get_artifact_or_raise(self, artifact_id: str) -> Artifact:
        """Get artifact by ID, raising if not found.

        Args:
            artifact_id: Artifact ID.

        Returns:
            Artifact.

        Raises:
            ArtifactNotFoundError: If artifact not found.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            msg = f"Artifact not found: {artifact_id!r}"
            raise ArtifactNotFoundError(msg, artifact_id=artifact_id)
        return artifact

    def get_artifact_content(self, artifact_id: str) -> str | bytes | None:
        """Get artifact file content.

        Args:
            artifact_id: Artifact ID.

        Returns:
            File content (str for text, bytes for binary) or None if not found.
        """
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            return None

        if artifact.is_binary:
            return artifact.file_path.read_bytes()
        return artifact.file_path.read_text(encoding="utf-8")

    def artifact_exists(self, artifact_id: str) -> bool:
        """Check if artifact exists.

        Args:
            artifact_id: Artifact ID.

        Returns:
            True if artifact exists.
        """
        index = self.get_index()
        return index.contains(artifact_id)

    # --- CRUD operations ---

    def add_artifact(  # noqa: PLR0912, PLR0913
        self,
        type_prefix: str,
        title: str,
        author: str,
        content: str | bytes | None = None,
        *,
        subtype: str | None = None,
        slug: str | None = None,
        references: list[str] | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        type_fields: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny]
        file_path: Path | str | None = None,
    ) -> Artifact:
        """Add a new artifact.

        Args:
            type_prefix: Two-letter type prefix.
            title: Artifact title.
            author: Author identifier.
            content: Content for text artifacts or binary data.
            subtype: Optional subtype.
            slug: Custom slug (auto-generated if not provided).
            references: List of reference IDs.
            tags: List of tags.
            summary: Brief description.
            type_fields: Type-specific metadata fields.
            file_path: Path to existing file to import (alternative to content).

        Returns:
            Created artifact.

        Raises:
            TypeNotRegisteredError: If type is unknown.
            ArtifactValidationError: If content or metadata is invalid.
            ValueError: If required fields missing.
        """
        registry = self._get_registry()
        type_def = registry.get_type(type_prefix)

        if type_def is None:
            msg = f"Unknown artifact type: {type_prefix!r}"
            raise TypeNotRegisteredError(msg, prefix=type_prefix)

        # Get next number for this type
        index = self.get_index()
        number = index.get_next_number(type_prefix)
        artifact_id = format_artifact_id(type_prefix, number)

        # Generate slug if not provided
        if slug is None:
            slug = generate_slug(title)

        # Determine file extension
        if type_def.category == "binary":
            if file_path:
                extension = Path(file_path).suffix.lstrip(".")
            elif type_def.formats:
                extension = type_def.formats[0]
            else:
                extension = "bin"
        else:
            extension = "md"

        # Generate filename and paths
        now = datetime.now(UTC)
        filename = generate_filename(type_prefix, number, slug, extension, now)
        artifact_path = self.artifacts_path / filename

        # Create metadata
        metadata = ArtifactMetadata(
            id=artifact_id,
            type=type_def.name,
            title=title,
            status="draft",
            created=now,
            author=author,
            subtype=subtype,
            references=tuple(references) if references else (),
            tags=tuple(tags) if tags else (),
            summary=summary,
            type_fields=type_fields or {},
        )

        # Validate
        errors = validate_artifact(metadata, registry=registry)
        raise_if_validation_errors(errors, artifact_id=artifact_id)

        # Ensure artifacts directory exists
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        # Create the artifact file
        metadata_path: Path | None = None

        if type_def.category == "binary":
            # Binary artifact: copy/write file and create sidecar
            if file_path:
                shutil.copy2(file_path, artifact_path)
            elif content:
                if isinstance(content, str):
                    artifact_path.write_text(content, encoding="utf-8")
                else:
                    artifact_path.write_bytes(content)
            else:
                # Create empty file
                artifact_path.touch()

            # Create sidecar metadata file
            metadata_path = artifact_path.with_suffix(
                artifact_path.suffix + ".metadata.yaml"
            )
            metadata_path.write_text(serialize_sidecar(metadata), encoding="utf-8")
        else:
            # Text artifact: write markdown with frontmatter
            body = content if isinstance(content, str) else ""
            artifact_path.write_text(
                serialize_frontmatter(metadata, body),
                encoding="utf-8",
            )

        # Create Artifact object
        artifact = Artifact(
            id=artifact_id,
            type=type_def.name,
            title=title,
            status="draft",
            created=now,
            author=author,
            file_path=artifact_path,
            subtype=subtype,
            references=tuple(references) if references else (),
            tags=tuple(tags) if tags else (),
            summary=summary,
            metadata_file_path=metadata_path,
            type_fields=type_fields or {},
        )

        # Update index
        if self._auto_index:
            self._add_to_index(artifact)

        return artifact

    def _add_to_index(self, artifact: Artifact) -> None:
        """Add artifact to index."""
        index = self.get_index()
        summaries = list(index.to_dict()["artifacts"])
        summaries.append(self._artifact_to_summary(artifact))
        self._write_index(summaries)

    def update_artifact(  # noqa: PLR0913
        self,
        artifact_id: str,
        *,
        title: str | None = None,
        content: str | bytes | None = None,
        subtype: str | None = None,
        status: str | None = None,
        references: list[str] | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        type_fields: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny]
    ) -> Artifact:
        """Update an existing artifact.

        Args:
            artifact_id: Artifact ID to update.
            title: New title (optional).
            content: New content (optional).
            subtype: New subtype (optional).
            status: New status (optional).
            references: New references (replaces existing).
            tags: New tags (replaces existing).
            summary: New summary (optional).
            type_fields: Type-specific fields to update (merged with existing).

        Returns:
            Updated artifact.

        Raises:
            ArtifactNotFoundError: If artifact not found.
            ArtifactValidationError: If updates are invalid.
        """
        artifact = self.get_artifact_or_raise(artifact_id)

        # Validate status if provided
        if status is not None and status not in VALID_STATUSES:
            msg = f"Invalid status: {status!r}"
            raise ArtifactValidationError(msg, artifact_id=artifact_id, field="status")

        # Merge type_fields with existing
        merged_type_fields = dict(artifact.type_fields)
        if type_fields:
            merged_type_fields.update(type_fields)

        # Build updated metadata
        updated_metadata = ArtifactMetadata(
            id=artifact.id,
            type=artifact.type,
            title=title if title is not None else artifact.title,
            status=status if status is not None else artifact.status,
            created=artifact.created,
            author=artifact.author,
            subtype=subtype if subtype is not None else artifact.subtype,
            updated=datetime.now(UTC),
            reviewers=artifact.reviewers,
            references=(
                tuple(references) if references is not None else artifact.references
            ),
            supersedes=artifact.supersedes,
            superseded_by=artifact.superseded_by,
            tags=tuple(tags) if tags is not None else artifact.tags,
            summary=summary if summary is not None else artifact.summary,
            type_fields=merged_type_fields,
        )

        # Validate
        errors = validate_artifact(updated_metadata, registry=self._get_registry())
        raise_if_validation_errors(errors, artifact_id=artifact_id)

        # Update file
        if artifact.is_binary:
            # Update sidecar
            if artifact.metadata_file_path:
                artifact.metadata_file_path.write_text(
                    serialize_sidecar(updated_metadata),
                    encoding="utf-8",
                )
            # Update content if provided
            if content is not None:
                if isinstance(content, str):
                    artifact.file_path.write_text(content, encoding="utf-8")
                else:
                    artifact.file_path.write_bytes(content)
        else:
            # Update markdown with frontmatter
            if content is not None:
                body = content if isinstance(content, str) else str(content)
            else:
                # Read existing body
                _, body = parse_frontmatter(
                    artifact.file_path.read_text(encoding="utf-8")
                )
            artifact.file_path.write_text(
                serialize_frontmatter(updated_metadata, body),
                encoding="utf-8",
            )

        # Create updated Artifact
        updated_artifact = replace(
            artifact,
            title=updated_metadata.title,
            status=updated_metadata.status,
            subtype=updated_metadata.subtype,
            updated=updated_metadata.updated,
            references=updated_metadata.references,
            tags=updated_metadata.tags,
            summary=updated_metadata.summary,
            type_fields=merged_type_fields,
        )

        # Update index
        if self._auto_index:
            self._update_in_index(updated_artifact)

        return updated_artifact

    def _update_in_index(self, artifact: Artifact) -> None:
        """Update artifact in index."""
        index = self.get_index()
        summaries = [
            s if s.get("id") != artifact.id else self._artifact_to_summary(artifact)
            for s in index.to_dict()["artifacts"]
        ]
        self._write_index(summaries)

    def delete_artifact(self, artifact_id: str, *, force: bool = False) -> None:
        """Delete an artifact.

        Args:
            artifact_id: Artifact ID to delete.
            force: Delete even if artifact has references.

        Raises:
            ArtifactNotFoundError: If artifact not found.
            ValueError: If artifact has references and force=False.
        """
        artifact = self.get_artifact_or_raise(artifact_id)

        # Check for references
        if not force:
            index = self.get_index()
            referencing = index.get_references_to(artifact_id)
            if referencing:
                msg = (
                    f"Cannot delete artifact {artifact_id!r}: "
                    f"referenced by {', '.join(referencing)}"
                )
                raise ValueError(msg)

        # Delete files
        if artifact.file_path.exists():
            artifact.file_path.unlink()
        if artifact.metadata_file_path and artifact.metadata_file_path.exists():
            artifact.metadata_file_path.unlink()

        # Update index
        if self._auto_index:
            self._remove_from_index(artifact_id)

    def _remove_from_index(self, artifact_id: str) -> None:
        """Remove artifact from index."""
        index = self.get_index()
        summaries = [
            s for s in index.to_dict()["artifacts"] if s.get("id") != artifact_id
        ]
        self._write_index(summaries)

    # --- Lifecycle operations ---

    def supersede_artifact(
        self,
        old_artifact_id: str,
        new_artifact_id: str,
    ) -> tuple[Artifact, Artifact]:
        """Mark one artifact as superseding another.

        Args:
            old_artifact_id: ID of artifact being superseded.
            new_artifact_id: ID of superseding artifact.

        Returns:
            Tuple of (old_artifact, new_artifact) after update.

        Raises:
            ArtifactNotFoundError: If either artifact not found.
            ValueError: If types don't match or circular supersession.
        """
        old = self.get_artifact_or_raise(old_artifact_id)
        new = self.get_artifact_or_raise(new_artifact_id)

        # Validate same type
        if old.type != new.type:
            msg = f"Cannot supersede: types don't match ({old.type} vs {new.type})"
            raise ValueError(msg)

        # Check for circular supersession
        if new.supersedes == old_artifact_id:
            msg = (
                f"Circular supersession detected: "
                f"{old_artifact_id} and {new_artifact_id}"
            )
            raise ValueError(msg)
        if old.superseded_by:
            msg = (
                f"Artifact {old_artifact_id} is already superseded "
                f"by {old.superseded_by}"
            )
            raise ValueError(msg)

        # Update old artifact
        old_metadata = self._read_metadata(old)
        old_metadata = ArtifactMetadata(
            id=old_metadata.id,
            type=old_metadata.type,
            title=old_metadata.title,
            status="superseded",
            created=old_metadata.created,
            author=old_metadata.author,
            subtype=old_metadata.subtype,
            updated=datetime.now(UTC),
            reviewers=old_metadata.reviewers,
            references=old_metadata.references,
            supersedes=old_metadata.supersedes,
            superseded_by=new_artifact_id,
            tags=old_metadata.tags,
            summary=old_metadata.summary,
            type_fields=old_metadata.type_fields,
        )
        self._write_metadata(old, old_metadata)

        # Update new artifact
        new_metadata = self._read_metadata(new)
        new_metadata = ArtifactMetadata(
            id=new_metadata.id,
            type=new_metadata.type,
            title=new_metadata.title,
            status=new_metadata.status,
            created=new_metadata.created,
            author=new_metadata.author,
            subtype=new_metadata.subtype,
            updated=datetime.now(UTC),
            reviewers=new_metadata.reviewers,
            references=new_metadata.references,
            supersedes=old_artifact_id,
            superseded_by=new_metadata.superseded_by,
            tags=new_metadata.tags,
            summary=new_metadata.summary,
            type_fields=new_metadata.type_fields,
        )
        self._write_metadata(new, new_metadata)

        # Rebuild index to capture changes
        if self._auto_index:
            self.rebuild_index()

        return (
            self.get_artifact_or_raise(old_artifact_id),
            self.get_artifact_or_raise(new_artifact_id),
        )

    def _read_metadata(self, artifact: Artifact) -> ArtifactMetadata:
        """Read metadata from artifact file."""
        if artifact.is_binary and artifact.metadata_file_path:
            return parse_sidecar(artifact.metadata_file_path)
        metadata, _ = parse_frontmatter(artifact.file_path.read_text(encoding="utf-8"))
        return metadata

    def _write_metadata(self, artifact: Artifact, metadata: ArtifactMetadata) -> None:
        """Write metadata to artifact file."""
        if artifact.is_binary and artifact.metadata_file_path:
            artifact.metadata_file_path.write_text(
                serialize_sidecar(metadata),
                encoding="utf-8",
            )
        else:
            # Preserve body content
            _, body = parse_frontmatter(artifact.file_path.read_text(encoding="utf-8"))
            artifact.file_path.write_text(
                serialize_frontmatter(metadata, body),
                encoding="utf-8",
            )

    def retract_artifact(
        self,
        artifact_id: str,
        *,
        reason: str | None = None,
    ) -> Artifact:
        """Retract an artifact.

        Args:
            artifact_id: Artifact ID to retract.
            reason: Optional reason for retraction.

        Returns:
            Retracted artifact.

        Note:
            Retracted artifacts are not deleted; they remain in the store
            with status='retracted'.
        """
        artifact = self.get_artifact_or_raise(artifact_id)

        # Build type fields with reason if provided
        type_fields = dict(artifact.type_fields)
        if reason:
            type_fields["retraction_reason"] = reason

        return self.update_artifact(
            artifact_id,
            status="retracted",
            type_fields=type_fields,
        )

    # --- Index operations ---

    def rebuild_index(self) -> None:
        """Rebuild the artifacts.json index from filesystem.

        Scans the artifacts/ directory for all artifact files and
        rebuilds the index from their metadata.
        """
        artifacts: list[dict[str, Any]] = []  # pyright: ignore[reportExplicitAny]

        if not self.artifacts_path.exists():
            self._write_index(artifacts)
            return

        # Find all artifact files
        for file_path in sorted(self.artifacts_path.iterdir()):
            if file_path.name.startswith("."):
                continue

            # Skip sidecar metadata files
            if file_path.name.endswith(".metadata.yaml"):
                continue

            try:
                artifact = self._load_artifact_from_file(file_path)
                if artifact:
                    artifacts.append(self._artifact_to_summary(artifact))
            except (ValueError, OSError):
                # Skip invalid files
                continue

        self._write_index(artifacts)

    def _load_artifact_from_file(self, file_path: Path) -> Artifact | None:
        """Load artifact from a file path."""
        # Check for sidecar metadata (binary artifact)
        sidecar_path = file_path.with_suffix(file_path.suffix + ".metadata.yaml")

        if sidecar_path.exists():
            # Binary artifact
            metadata = parse_sidecar(sidecar_path)
            return Artifact(
                id=metadata.id,
                type=metadata.type,
                title=metadata.title,
                status=metadata.status,
                created=metadata.created,
                author=metadata.author,
                file_path=file_path,
                subtype=metadata.subtype,
                updated=metadata.updated,
                reviewers=metadata.reviewers,
                references=metadata.references,
                supersedes=metadata.supersedes,
                superseded_by=metadata.superseded_by,
                tags=metadata.tags,
                summary=metadata.summary,
                metadata_file_path=sidecar_path,
                type_fields=metadata.type_fields,
            )

        # Text artifact (markdown with frontmatter)
        if file_path.suffix == ".md":
            content = file_path.read_text(encoding="utf-8")
            metadata, _ = parse_frontmatter(content)
            return Artifact(
                id=metadata.id,
                type=metadata.type,
                title=metadata.title,
                status=metadata.status,
                created=metadata.created,
                author=metadata.author,
                file_path=file_path,
                subtype=metadata.subtype,
                updated=metadata.updated,
                reviewers=metadata.reviewers,
                references=metadata.references,
                supersedes=metadata.supersedes,
                superseded_by=metadata.superseded_by,
                tags=metadata.tags,
                summary=metadata.summary,
                metadata_file_path=None,
                type_fields=metadata.type_fields,
            )

        return None

    def get_index(self) -> ArtifactIndex:
        """Get the index object for direct queries.

        Returns:
            ArtifactIndex for the store.
        """
        if self._index is None:
            self._index = ArtifactIndex(self.index_path)
        return self._index

    # --- Validation ---

    def validate(self, *, strict: bool = False) -> list[ValidationError]:
        """Validate store integrity.

        Checks all artifacts for metadata validity, type compliance,
        and reference integrity.

        Args:
            strict: Fail on warnings (e.g., number gaps).

        Returns:
            List of validation errors/warnings.
        """
        errors: list[ValidationError] = []
        registry = self._get_registry()

        # Validate all artifacts
        for artifact in self.list_artifacts():
            # Read full metadata
            try:
                metadata = self._read_metadata(artifact)
            except (ValueError, OSError) as e:
                errors.append(
                    ValidationError(
                        level="error",
                        message=f"Failed to read metadata: {e}",
                        artifact_id=artifact.id,
                        field=None,
                    )
                )
                continue

            artifact_errors = validate_artifact(
                metadata,
                registry=registry,
                store=self,
            )
            errors.extend(artifact_errors)

        # Check for number gaps in strict mode
        if strict:
            index = self.get_index()
            for type_prefix in {a.prefix for a in self.list_artifacts()}:
                artifacts_of_type = index.get_by_type(type_prefix)
                numbers = sorted(
                    int(a["id"].split("-")[1])
                    for a in artifacts_of_type
                    if "-" in a.get("id", "")
                )
                for i, num in enumerate(numbers, 1):
                    if num != i:
                        errors.append(
                            ValidationError(
                                level="warning",
                                message=(
                                    f"Number gap in {type_prefix} artifacts: "
                                    f"missing {type_prefix}-{i:04d}"
                                ),
                                artifact_id=None,
                                field=None,
                            )
                        )
                        break

        return errors

    def validate_artifact(self, artifact_id: str) -> list[ValidationError]:
        """Validate a specific artifact.

        Args:
            artifact_id: Artifact ID to validate.

        Returns:
            List of validation errors.

        Raises:
            ArtifactNotFoundError: If artifact not found.
        """
        artifact = self.get_artifact_or_raise(artifact_id)
        metadata = self._read_metadata(artifact)
        return validate_artifact(metadata, registry=self._get_registry(), store=self)
