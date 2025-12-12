"""Adapter for converting between spec and generic artifact models.

This module provides the SpecArtifactAdapter class for bidirectional conversion
between the spec system's Artifact model (with enums and MappingProxyType) and
the generic oaps.artifacts Artifact model (with strings and dict).
"""

from datetime import datetime  # noqa: TC003
from pathlib import Path  # noqa: TC003
from types import MappingProxyType
from typing import Any, ClassVar, Final

from oaps.artifacts import Artifact as GenericArtifact
from oaps.spec._models import Artifact as SpecArtifact, ArtifactStatus, ArtifactType

__all__ = ["SpecArtifactAdapter"]


class SpecArtifactAdapter:
    """Converts between spec and generic artifact models.

    The adapter handles the differences between the two artifact representations:
    - Type: spec uses ArtifactType enum, generic uses string
    - Status: spec uses ArtifactStatus enum, generic uses string
    - file_path: spec uses relative str, generic uses absolute Path
    - type_fields: spec uses MappingProxyType, generic uses dict

    This class is stateless and can be instantiated once and reused.
    """

    __slots__: Final = ()

    # Bidirectional type mapping
    _TYPE_TO_GENERIC: ClassVar[dict[ArtifactType, str]] = {
        ArtifactType.REVIEW: "review",
        ArtifactType.CHANGE: "change",
        ArtifactType.ANALYSIS: "analysis",
        ArtifactType.DECISION: "decision",
        ArtifactType.DIAGRAM: "diagram",
        ArtifactType.EXAMPLE: "example",
        ArtifactType.MOCKUP: "mockup",
        ArtifactType.IMAGE: "image",
        ArtifactType.VIDEO: "video",
    }

    _TYPE_FROM_GENERIC: ClassVar[dict[str, ArtifactType]] = {
        v: k for k, v in _TYPE_TO_GENERIC.items()
    }

    # Type prefix mapping (for ID generation)
    _TYPE_TO_PREFIX: ClassVar[dict[ArtifactType, str]] = {
        ArtifactType.REVIEW: "RV",
        ArtifactType.CHANGE: "CH",
        ArtifactType.ANALYSIS: "AN",
        ArtifactType.DECISION: "DC",
        ArtifactType.DIAGRAM: "DG",
        ArtifactType.EXAMPLE: "EX",
        ArtifactType.MOCKUP: "MK",
        ArtifactType.IMAGE: "IM",
        ArtifactType.VIDEO: "VD",
    }

    # Bidirectional status mapping
    _STATUS_TO_GENERIC: ClassVar[dict[ArtifactStatus, str]] = {
        ArtifactStatus.DRAFT: "draft",
        ArtifactStatus.COMPLETE: "complete",
        ArtifactStatus.SUPERSEDED: "superseded",
        ArtifactStatus.RETRACTED: "retracted",
    }

    _STATUS_FROM_GENERIC: ClassVar[dict[str, ArtifactStatus]] = {
        v: k for k, v in _STATUS_TO_GENERIC.items()
    }

    def spec_type_to_generic(self, artifact_type: ArtifactType) -> str:
        """Convert spec ArtifactType enum to generic type string.

        Args:
            artifact_type: Spec artifact type enum value.

        Returns:
            Generic type string (e.g., "review").
        """
        return self._TYPE_TO_GENERIC[artifact_type]

    def generic_type_to_spec(self, type_name: str) -> ArtifactType:
        """Convert generic type string to spec ArtifactType enum.

        Args:
            type_name: Generic type string (e.g., "review").

        Returns:
            Spec artifact type enum value.

        Raises:
            KeyError: If type_name is not a valid artifact type.
        """
        return self._TYPE_FROM_GENERIC[type_name]

    def spec_type_to_prefix(self, artifact_type: ArtifactType) -> str:
        """Get the ID prefix for an artifact type.

        Args:
            artifact_type: Spec artifact type enum value.

        Returns:
            Two-letter prefix (e.g., "RV" for review).
        """
        return self._TYPE_TO_PREFIX[artifact_type]

    def spec_status_to_generic(self, status: ArtifactStatus) -> str:
        """Convert spec ArtifactStatus enum to generic status string.

        Args:
            status: Spec artifact status enum value.

        Returns:
            Generic status string (e.g., "draft").
        """
        return self._STATUS_TO_GENERIC[status]

    def generic_status_to_spec(self, status: str) -> ArtifactStatus:
        """Convert generic status string to spec ArtifactStatus enum.

        Args:
            status: Generic status string (e.g., "draft").

        Returns:
            Spec artifact status enum value.

        Raises:
            KeyError: If status is not a valid artifact status.
        """
        return self._STATUS_FROM_GENERIC[status]

    def spec_to_generic(
        self,
        artifact: SpecArtifact,
        artifacts_dir: Path,
    ) -> GenericArtifact:
        """Convert spec Artifact to generic Artifact.

        Args:
            artifact: Spec artifact model instance.
            artifacts_dir: Absolute path to the artifacts/ directory.

        Returns:
            Generic artifact model instance.
        """
        return GenericArtifact(
            id=artifact.id,
            type=self.spec_type_to_generic(artifact.artifact_type),
            title=artifact.title,
            status=self.spec_status_to_generic(artifact.status),
            created=artifact.created,
            author=artifact.author,
            file_path=artifacts_dir / artifact.file_path,
            subtype=artifact.subtype,
            updated=artifact.updated,
            reviewers=(),  # Spec doesn't have reviewers
            references=artifact.references,
            supersedes=artifact.supersedes,
            superseded_by=artifact.superseded_by,
            tags=artifact.tags,
            summary=artifact.summary,
            metadata_file_path=(
                artifacts_dir / artifact.metadata_file_path
                if artifact.metadata_file_path
                else None
            ),
            type_fields=dict(artifact.type_fields),
        )

    def generic_to_spec(
        self,
        artifact: GenericArtifact,
        artifacts_dir: Path,
    ) -> SpecArtifact:
        """Convert generic Artifact to spec Artifact.

        Args:
            artifact: Generic artifact model instance.
            artifacts_dir: Absolute path to the artifacts/ directory.

        Returns:
            Spec artifact model instance.
        """
        # Convert absolute paths to relative (relative to artifacts_dir)
        file_path = str(artifact.file_path.relative_to(artifacts_dir))
        metadata_file_path = (
            str(artifact.metadata_file_path.relative_to(artifacts_dir))
            if artifact.metadata_file_path
            else None
        )

        # Handle updated: spec requires datetime, generic allows None
        updated = artifact.updated if artifact.updated else artifact.created

        # Convert type_fields from dict to MappingProxyType
        type_fields: MappingProxyType[str, Any] = MappingProxyType(  # pyright: ignore[reportExplicitAny]
            artifact.type_fields
        )

        return SpecArtifact(
            id=artifact.id,
            artifact_type=self.generic_type_to_spec(artifact.type),
            title=artifact.title,
            status=self.generic_status_to_spec(artifact.status),
            created=artifact.created,
            updated=updated,
            author=artifact.author,
            file_path=file_path,
            description=None,  # Generic doesn't have description
            subtype=artifact.subtype,
            references=artifact.references,
            tags=artifact.tags,
            supersedes=artifact.supersedes,
            superseded_by=artifact.superseded_by,
            summary=artifact.summary,
            type_fields=type_fields,
            metadata_file_path=metadata_file_path,
        )

    def create_generic_artifact(  # noqa: PLR0913
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        title: str,
        status: ArtifactStatus,
        created: datetime,
        author: str,
        file_path: Path,
        *,
        subtype: str | None = None,
        updated: datetime | None = None,
        references: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        supersedes: str | None = None,
        superseded_by: str | None = None,
        summary: str | None = None,
        metadata_file_path: Path | None = None,
        type_fields: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny]
    ) -> GenericArtifact:
        """Create a generic Artifact from spec-style parameters.

        This is a convenience method for creating generic artifacts using
        spec enum types, which are then converted to strings.

        Args:
            artifact_id: Unique artifact identifier.
            artifact_type: Spec artifact type enum.
            title: Human-readable title.
            status: Spec artifact status enum.
            created: Creation timestamp.
            author: Author identifier.
            file_path: Absolute path to artifact file.
            subtype: Optional subtype.
            updated: Optional update timestamp.
            references: IDs of related entities.
            tags: Freeform tags.
            supersedes: ID of artifact this supersedes.
            superseded_by: ID of superseding artifact.
            summary: Brief description.
            metadata_file_path: Path to sidecar metadata.
            type_fields: Type-specific fields.

        Returns:
            Generic artifact model instance.
        """
        return GenericArtifact(
            id=artifact_id,
            type=self.spec_type_to_generic(artifact_type),
            title=title,
            status=self.spec_status_to_generic(status),
            created=created,
            author=author,
            file_path=file_path,
            subtype=subtype,
            updated=updated,
            reviewers=(),
            references=references,
            supersedes=supersedes,
            superseded_by=superseded_by,
            tags=tags,
            summary=summary,
            metadata_file_path=metadata_file_path,
            type_fields=type_fields or {},
        )
