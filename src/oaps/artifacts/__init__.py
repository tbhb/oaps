r"""Artifact management system for OAPS.

This module provides a unified foundation for managing ancillary documents
across OAPS subsystems (spec-system, planning-system, review agents).

The artifact system provides:
- Extensible type registry with 10 base artifact types
- Filesystem-based storage with configurable base paths
- YAML frontmatter for text artifacts, sidecar files for binary assets
- Python API for CRUD operations and index management

Example:
    >>> from pathlib import Path
    >>> from oaps.artifacts import ArtifactStore, ArtifactRegistry

    # Get the global registry
    >>> registry = ArtifactRegistry.get_instance()

    # Check if a type is registered
    >>> if registry.has_type("RV"):
    ...     type_def = registry.get_type("RV")
    ...     print(f"Review type: {type_def.name}")

    # Create and use an artifact store
    >>> store = ArtifactStore(Path(".oaps/docs/specs/my-spec"))
    >>> store.initialize()

    # Add a review artifact
    >>> review = store.add_artifact(
    ...     type_prefix="RV",
    ...     title="Security Review",
    ...     author="security-team",
    ...     content="# Security Review\n\nContent here...",
    ...     subtype="security",
    ... )
    >>> print(f"Created: {review.id}")

    # Query artifacts
    >>> all_reviews = store.list_artifacts(type_filter="RV")
    >>> complete = store.list_artifacts(status_filter="complete")

    # Update artifact
    >>> updated = store.update_artifact(review.id, status="complete")

    # Validate store
    >>> errors = store.validate()
    >>> if errors:
    ...     print(f"Found {len(errors)} validation issues")
"""

from oaps.artifacts._index import ArtifactIndex
from oaps.artifacts._metadata import (
    format_artifact_id,
    generate_filename,
    generate_slug,
    parse_artifact_id,
    parse_filename,
    parse_frontmatter,
    parse_sidecar,
    serialize_frontmatter,
    serialize_sidecar,
)
from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._store import ArtifactStore
from oaps.artifacts._types import (
    BASE_TYPES,
    RESERVED_PREFIXES,
    Artifact,
    ArtifactMetadata,
    TypeDefinition,
    TypeField,
    ValidationError,
)
from oaps.artifacts._validator import (
    VALID_STATUSES,
    raise_if_validation_errors,
    validate_artifact,
    validate_artifact_type,
    validate_metadata,
    validate_references,
)

__all__ = [
    "BASE_TYPES",
    "RESERVED_PREFIXES",
    "VALID_STATUSES",
    "Artifact",
    "ArtifactIndex",
    "ArtifactMetadata",
    "ArtifactRegistry",
    "ArtifactStore",
    "TypeDefinition",
    "TypeField",
    "ValidationError",
    "format_artifact_id",
    "generate_filename",
    "generate_slug",
    "parse_artifact_id",
    "parse_filename",
    "parse_frontmatter",
    "parse_sidecar",
    "raise_if_validation_errors",
    "serialize_frontmatter",
    "serialize_sidecar",
    "validate_artifact",
    "validate_artifact_type",
    "validate_metadata",
    "validate_references",
]
