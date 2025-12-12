"""Validation functions for artifacts and metadata.

This module provides validation functions that check artifacts against
metadata schemas, type definitions, and reference integrity rules.

Example:
    >>> from oaps.artifacts import ArtifactMetadata, validate_metadata
    >>> errors = validate_metadata(metadata)
    >>> if errors:
    ...     print(f"Found {len(errors)} validation errors")
"""

from typing import TYPE_CHECKING

from oaps.artifacts._metadata import parse_artifact_id
from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._types import ArtifactMetadata, ValidationError
from oaps.exceptions import ArtifactValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from oaps.artifacts._store import ArtifactStore

# Valid artifact statuses
VALID_STATUSES: frozenset[str] = frozenset(
    {"draft", "complete", "superseded", "retracted"}
)


def validate_metadata(metadata: ArtifactMetadata) -> list[ValidationError]:
    """Validate metadata field values.

    Checks that required fields are present and valid, status is in
    the valid set, and ID format matches PREFIX-NNNN.

    Args:
        metadata: Artifact metadata to validate.

    Returns:
        List of validation errors. Empty list indicates valid metadata.

    Example:
        >>> from datetime import datetime, UTC
        >>> metadata = ArtifactMetadata(
        ...     id="RV-0001",
        ...     type="review",
        ...     title="Security Review",
        ...     status="draft",
        ...     created=datetime.now(UTC),
        ...     author="reviewer",
        ... )
        >>> errors = validate_metadata(metadata)
        >>> len(errors)
        0
    """
    errors: list[ValidationError] = []

    # Required fields - these are enforced by the dataclass, but check anyway
    if not metadata.id:
        errors.append(
            ValidationError(
                level="error",
                message="Missing required field: id",
                artifact_id=metadata.id or None,
                field="id",
            )
        )

    if not metadata.type:
        errors.append(
            ValidationError(
                level="error",
                message="Missing required field: type",
                artifact_id=metadata.id,
                field="type",
            )
        )

    if not metadata.title:
        errors.append(
            ValidationError(
                level="error",
                message="Missing required field: title",
                artifact_id=metadata.id,
                field="title",
            )
        )

    if not metadata.status:
        errors.append(
            ValidationError(
                level="error",
                message="Missing required field: status",
                artifact_id=metadata.id,
                field="status",
            )
        )

    if not metadata.author:
        errors.append(
            ValidationError(
                level="error",
                message="Missing required field: author",
                artifact_id=metadata.id,
                field="author",
            )
        )

    # Validate ID format
    if metadata.id:
        try:
            parse_artifact_id(metadata.id)
        except ValueError:
            errors.append(
                ValidationError(
                    level="error",
                    message=(
                        f"Invalid artifact ID format: {metadata.id!r} "
                        "(expected PREFIX-NNNN)"
                    ),
                    artifact_id=metadata.id,
                    field="id",
                )
            )

    # Validate status
    if metadata.status and metadata.status not in VALID_STATUSES:
        errors.append(
            ValidationError(
                level="error",
                message=(
                    f"Invalid status: {metadata.status!r} "
                    f"(expected one of: {', '.join(sorted(VALID_STATUSES))})"
                ),
                artifact_id=metadata.id,
                field="status",
            )
        )

    return errors


def validate_artifact_type(
    metadata: ArtifactMetadata,
    registry: ArtifactRegistry | None = None,
) -> list[ValidationError]:
    """Validate artifact against its type definition.

    Checks that:
    - Type prefix is registered
    - ID prefix matches declared type
    - Subtype is valid for type (if provided)
    - Required type-specific fields are present
    - Type field values are valid (allowed_values check)
    - Image artifacts have required alt_text field

    Args:
        metadata: Artifact metadata to validate.
        registry: Type registry (defaults to global).

    Returns:
        List of validation errors. Empty list indicates valid type usage.

    Example:
        >>> from oaps.artifacts import ArtifactRegistry
        >>> registry = ArtifactRegistry.get_instance()
        >>> errors = validate_artifact_type(metadata, registry)
    """
    errors: list[ValidationError] = []

    # Get registry
    if registry is None:
        registry = ArtifactRegistry.get_instance()

    # Get type definition
    type_def = registry.get_type(metadata.type) if metadata.type else None

    # Also try to get by name if prefix lookup failed
    if type_def is None and metadata.type:
        prefix = registry.type_name_to_prefix(metadata.type)
        if prefix:
            type_def = registry.get_type(prefix)

    if type_def is None:
        errors.append(
            ValidationError(
                level="error",
                message=f"Unknown artifact type: {metadata.type!r}",
                artifact_id=metadata.id,
                field="type",
            )
        )
        return errors

    # Validate ID prefix matches type
    if metadata.id and "-" in metadata.id:
        id_prefix = metadata.id.split("-")[0]
        if id_prefix != type_def.prefix:
            errors.append(
                ValidationError(
                    level="error",
                    message=(
                        f"ID prefix '{id_prefix}' does not match "
                        f"type prefix '{type_def.prefix}'"
                    ),
                    artifact_id=metadata.id,
                    field="id",
                )
            )

    # Validate subtype
    if (
        metadata.subtype
        and type_def.subtypes
        and metadata.subtype not in type_def.subtypes
    ):
        errors.append(
            ValidationError(
                level="error",
                message=(
                    f"Invalid subtype: {metadata.subtype!r} "
                    f"(expected one of: {', '.join(type_def.subtypes)})"
                ),
                artifact_id=metadata.id,
                field="subtype",
            )
        )

    # Validate type-specific fields
    for type_field in type_def.type_fields:
        field_value = metadata.type_fields.get(type_field.name)

        # Check required fields
        if type_field.required and field_value is None:
            errors.append(
                ValidationError(
                    level="error",
                    message=f"Missing required type field: {type_field.name!r}",
                    artifact_id=metadata.id,
                    field=type_field.name,
                )
            )
            continue

        # Check allowed values
        if (
            field_value is not None
            and type_field.allowed_values is not None
            and str(field_value) not in type_field.allowed_values
        ):
            errors.append(
                ValidationError(
                    level="error",
                    message=(
                        f"Invalid value for {type_field.name!r}: {field_value!r} "
                        f"(expected one of: {', '.join(type_field.allowed_values)})"
                    ),
                    artifact_id=metadata.id,
                    field=type_field.name,
                )
            )

    # Special validation: Image artifacts MUST have alt_text
    if type_def.prefix == "IM" and not metadata.type_fields.get("alt_text"):
        errors.append(
            ValidationError(
                level="error",
                message="Image artifacts must have 'alt_text' field for accessibility",
                artifact_id=metadata.id,
                field="alt_text",
            )
        )

    return errors


def validate_references(
    references: Sequence[str],
    store: ArtifactStore,
) -> list[ValidationError]:
    """Validate that references resolve to existing artifacts.

    Args:
        references: List of reference IDs.
        store: Artifact store for lookup.

    Returns:
        List of validation errors for unresolved references.

    Example:
        >>> errors = validate_references(["RV-0001", "XX-9999"], store)
        >>> len(errors)  # XX-9999 doesn't exist
        1
    """
    return [
        ValidationError(
            level="warning",
            message=f"Reference to non-existent artifact: {ref!r}",
            artifact_id=None,
            field="references",
        )
        for ref in references
        if not store.artifact_exists(ref)
    ]


def validate_artifact(
    metadata: ArtifactMetadata,
    *,
    registry: ArtifactRegistry | None = None,
    store: ArtifactStore | None = None,
) -> list[ValidationError]:
    """Validate all aspects of an artifact.

    Combines metadata validation, type validation, and optionally
    reference validation into a single call.

    Args:
        metadata: Artifact metadata to validate.
        registry: Type registry (defaults to global).
        store: Artifact store for reference validation (optional).

    Returns:
        List of all validation errors.

    Example:
        >>> errors = validate_artifact(metadata)
        >>> error_count = sum(1 for e in errors if e.level == "error")
    """
    errors: list[ValidationError] = []

    # Basic metadata validation
    errors.extend(validate_metadata(metadata))

    # Type validation
    errors.extend(validate_artifact_type(metadata, registry))

    # Reference validation (if store provided)
    if store and metadata.references:
        errors.extend(validate_references(metadata.references, store))

    return errors


def raise_if_validation_errors(
    errors: list[ValidationError],
    *,
    artifact_id: str | None = None,
) -> None:
    """Raise ArtifactValidationError if any validation errors exist.

    This is a convenience function that checks a list of validation errors
    and raises an exception for the first error found.

    Args:
        errors: List of ValidationError objects to check.
        artifact_id: Optional artifact ID to use in the exception.

    Raises:
        ArtifactValidationError: If any errors have level="error".

    Example:
        >>> errors = validate_metadata(metadata)
        >>> raise_if_validation_errors(errors, artifact_id=metadata.id)
    """
    actual_errors = [e for e in errors if e.level == "error"]
    if actual_errors:
        error = actual_errors[0]
        raise ArtifactValidationError(
            error.message,
            artifact_id=artifact_id or error.artifact_id,
            field=error.field,
        )
