"""Metadata parsing and serialization utilities.

This module provides functions for parsing and serializing artifact metadata
from YAML frontmatter (text artifacts) and sidecar files (binary artifacts).
It also includes utilities for artifact IDs, slugs, and filenames.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from oaps.artifacts._types import ArtifactMetadata

# =============================================================================
# Constants
# =============================================================================

PREFIX_LENGTH = 2
"""Length of artifact type prefixes."""

MAX_ARTIFACT_NUMBER = 9999
"""Maximum artifact number (NNNN format)."""

# =============================================================================
# Regex Patterns
# =============================================================================

_ARTIFACT_ID_PATTERN = re.compile(r"^([A-Z]{2})-(\d{4})$")
"""Pattern for artifact IDs: PREFIX-NNNN (e.g., RV-0001)."""

_FILENAME_PATTERN = re.compile(r"^(\d{14})-([A-Z]{2})-(\d{4})-(.+)\.(.+)$")
"""Pattern for artifact filenames: YYYYMMDDHHMMSS-PREFIX-NNNN-slug.ext."""

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9-]")
"""Pattern matching characters invalid in slugs."""

_SLUG_MULTIPLE_HYPHENS = re.compile(r"-+")
"""Pattern matching multiple consecutive hyphens."""

# =============================================================================
# ID Utilities
# =============================================================================


def parse_artifact_id(artifact_id: str) -> tuple[str, int]:
    """Parse artifact ID into prefix and number.

    Args:
        artifact_id: ID like "RV-0001".

    Returns:
        Tuple of (prefix, number).

    Raises:
        ValueError: If ID format is invalid.

    Example:
        >>> parse_artifact_id("RV-0001")
        ('RV', 1)
    """
    match = _ARTIFACT_ID_PATTERN.match(artifact_id)
    if not match:
        msg = f"Invalid artifact ID format: {artifact_id!r} (expected PREFIX-NNNN)"
        raise ValueError(msg)
    return match.group(1), int(match.group(2))


def format_artifact_id(prefix: str, number: int) -> str:
    """Format prefix and number into artifact ID.

    Args:
        prefix: Two-letter prefix.
        number: Sequential number (1-9999).

    Returns:
        Formatted ID like "RV-0001".

    Raises:
        ValueError: If prefix or number is invalid.

    Example:
        >>> format_artifact_id("RV", 1)
        'RV-0001'
    """
    if not prefix or len(prefix) != PREFIX_LENGTH or not prefix.isupper():
        msg = f"Invalid prefix: {prefix!r} (expected two uppercase letters)"
        raise ValueError(msg)
    if not 1 <= number <= MAX_ARTIFACT_NUMBER:
        msg = f"Invalid number: {number} (expected 1-9999)"
        raise ValueError(msg)
    return f"{prefix}-{number:04d}"


# =============================================================================
# Slug Utilities
# =============================================================================


def generate_slug(title: str, max_length: int = 50) -> str:
    """Generate URL-safe slug from title.

    Args:
        title: Human-readable title.
        max_length: Maximum slug length (default 50).

    Returns:
        Slug string (lowercase, alphanumeric, hyphens).

    Example:
        >>> generate_slug("Security Review of Token Handling")
        'security-review-of-token-handling'
    """
    # Convert to lowercase
    slug = title.lower()

    # Replace spaces and underscores with hyphens
    slug = slug.replace(" ", "-").replace("_", "-")

    # Remove invalid characters
    slug = _SLUG_INVALID_CHARS.sub("", slug)

    # Collapse multiple hyphens
    slug = _SLUG_MULTIPLE_HYPHENS.sub("-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to max length, but don't cut mid-word if possible
    if len(slug) > max_length:
        slug = slug[:max_length]
        # Try to cut at a hyphen boundary
        last_hyphen = slug.rfind("-")
        if last_hyphen > max_length // 2:
            slug = slug[:last_hyphen]
        slug = slug.rstrip("-")

    # Handle empty result
    if not slug:
        slug = "untitled"

    return slug


# =============================================================================
# Filename Utilities
# =============================================================================


def generate_filename(
    prefix: str,
    number: int,
    slug: str,
    extension: str,
    timestamp: datetime | None = None,
) -> str:
    """Generate artifact filename.

    Args:
        prefix: Two-letter type prefix.
        number: Sequential number (1-9999).
        slug: URL-safe slug.
        extension: File extension (without leading dot).
        timestamp: Creation timestamp (defaults to now UTC).

    Returns:
        Filename like "20251217143022-RV-0001-security-review.md".

    Example:
        >>> generate_filename("RV", 1, "security-review", "md")
        '20251217...-RV-0001-security-review.md'
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)

    # Format timestamp as YYYYMMDDHHMMSS
    ts_str = timestamp.strftime("%Y%m%d%H%M%S")

    # Format artifact ID
    artifact_id = format_artifact_id(prefix, number)

    # Ensure extension doesn't have leading dot
    extension = extension.lstrip(".")

    return f"{ts_str}-{artifact_id}-{slug}.{extension}"


def parse_filename(filename: str) -> tuple[datetime, str, int, str, str]:
    """Parse artifact filename into components.

    Args:
        filename: Filename like "20251217143022-RV-0001-security-review.md".

    Returns:
        Tuple of (timestamp, prefix, number, slug, extension).

    Raises:
        ValueError: If filename format is invalid.

    Example:
        >>> ts, prefix, num, slug, ext = parse_filename(
        ...     "20251217143022-RV-0001-security-review.md"
        ... )
        >>> prefix, num, slug, ext
        ('RV', 1, 'security-review', 'md')
    """
    match = _FILENAME_PATTERN.match(filename)
    if not match:
        msg = f"Invalid artifact filename format: {filename!r}"
        raise ValueError(msg)

    ts_str, prefix, number_str, slug, extension = match.groups()

    # Parse timestamp
    timestamp = datetime.strptime(ts_str, "%Y%m%d%H%M%S").replace(tzinfo=UTC)

    return timestamp, prefix, int(number_str), slug, extension


# =============================================================================
# Metadata Parsing
# =============================================================================


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse datetime from string or return as-is.

    Args:
        value: ISO 8601 string or datetime object.

    Returns:
        Parsed datetime or None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Parse ISO 8601 format
    try:
        return datetime.fromisoformat(value)
    except ValueError as e:
        msg = f"Invalid datetime format: {value!r}"
        raise ValueError(msg) from e


def _to_tuple(value: list[Any] | tuple[Any, ...] | None) -> tuple[Any, ...]:  # pyright: ignore[reportExplicitAny]
    """Convert list to tuple, or return empty tuple if None."""
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    return tuple(value)


def _parse_yaml_to_metadata(
    yaml_data: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> ArtifactMetadata:
    """Convert parsed YAML dict to ArtifactMetadata.

    Args:
        yaml_data: Dictionary from YAML parsing.

    Returns:
        ArtifactMetadata instance.

    Raises:
        ValueError: If required fields are missing.
    """
    # Extract required fields
    required = ("id", "type", "title", "status", "created", "author")
    missing = [f for f in required if f not in yaml_data]
    if missing:
        msg = f"Missing required metadata fields: {', '.join(missing)}"
        raise ValueError(msg)

    # Extract type-specific fields (anything not in standard fields)
    standard_fields = {
        "id",
        "type",
        "title",
        "status",
        "created",
        "author",
        "subtype",
        "updated",
        "reviewers",
        "references",
        "supersedes",
        "superseded_by",
        "tags",
        "summary",
    }
    type_fields = {k: v for k, v in yaml_data.items() if k not in standard_fields}

    return ArtifactMetadata(
        id=yaml_data["id"],
        type=yaml_data["type"],
        title=yaml_data["title"],
        status=yaml_data["status"],
        created=_parse_datetime(yaml_data["created"]),  # pyright: ignore[reportArgumentType]
        author=yaml_data["author"],
        subtype=yaml_data.get("subtype"),
        updated=_parse_datetime(yaml_data.get("updated")),
        reviewers=_to_tuple(yaml_data.get("reviewers")),
        references=_to_tuple(yaml_data.get("references")),
        supersedes=yaml_data.get("supersedes"),
        superseded_by=yaml_data.get("superseded_by"),
        tags=_to_tuple(yaml_data.get("tags")),
        summary=yaml_data.get("summary"),
        type_fields=type_fields,
    )


def parse_frontmatter(content: str) -> tuple[ArtifactMetadata, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content.

    Returns:
        Tuple of (metadata, body_content).

    Raises:
        ValueError: If frontmatter is missing or invalid.

    Example:
        >>> content = '''---
        ... id: RV-0001
        ... type: review
        ... title: Security Review
        ... status: draft
        ... created: 2025-01-15T10:30:00Z
        ... author: reviewer
        ... ---
        ... # Review Content
        ... '''
        >>> metadata, body = parse_frontmatter(content)
        >>> metadata.id
        'RV-0001'
    """
    if not content.startswith("---"):
        msg = "Frontmatter must start with '---'"
        raise ValueError(msg)

    # Find the closing ---
    end_marker = content.find("---", 3)
    if end_marker == -1:
        msg = "Frontmatter closing '---' not found"
        raise ValueError(msg)

    frontmatter_str = content[3:end_marker].strip()
    body = content[end_marker + 3 :].lstrip("\n")

    try:
        yaml_data = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML in frontmatter: {e}"
        raise ValueError(msg) from e

    if not isinstance(yaml_data, dict):
        msg = "Frontmatter must be a YAML dictionary"
        raise TypeError(msg)

    metadata = _parse_yaml_to_metadata(yaml_data)
    return metadata, body


def parse_sidecar(path: Path | str) -> ArtifactMetadata:
    """Parse sidecar metadata file.

    Args:
        path: Path to .metadata.yaml file.

    Returns:
        Parsed metadata.

    Raises:
        ValueError: If file is missing or invalid.
        FileNotFoundError: If file does not exist.
    """
    path = Path(path)
    if not path.exists():
        msg = f"Sidecar metadata file not found: {path}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")

    try:
        yaml_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML in sidecar file: {e}"
        raise ValueError(msg) from e

    if not isinstance(yaml_data, dict):
        msg = "Sidecar file must contain a YAML dictionary"
        raise TypeError(msg)

    return _parse_yaml_to_metadata(yaml_data)


# =============================================================================
# Metadata Serialization
# =============================================================================


def _format_datetime(dt: datetime | None) -> str | None:
    """Format datetime as ISO 8601 string."""
    if dt is None:
        return None
    return dt.isoformat()


def _metadata_to_dict(
    metadata: ArtifactMetadata,
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Convert ArtifactMetadata to serializable dict.

    Args:
        metadata: Artifact metadata.

    Returns:
        Dictionary suitable for YAML serialization.
    """
    result: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "id": metadata.id,
        "type": metadata.type,
        "title": metadata.title,
        "status": metadata.status,
        "created": _format_datetime(metadata.created),
        "author": metadata.author,
    }

    # Add optional fields if present
    if metadata.subtype:
        result["subtype"] = metadata.subtype
    if metadata.updated:
        result["updated"] = _format_datetime(metadata.updated)
    if metadata.reviewers:
        result["reviewers"] = list(metadata.reviewers)
    if metadata.references:
        result["references"] = list(metadata.references)
    if metadata.supersedes:
        result["supersedes"] = metadata.supersedes
    if metadata.superseded_by:
        result["superseded_by"] = metadata.superseded_by
    if metadata.tags:
        result["tags"] = list(metadata.tags)
    if metadata.summary:
        result["summary"] = metadata.summary

    # Add type-specific fields
    result.update(metadata.type_fields)

    return result


def serialize_frontmatter(metadata: ArtifactMetadata, body: str) -> str:
    """Serialize metadata and body to markdown with frontmatter.

    Args:
        metadata: Artifact metadata.
        body: Markdown body content.

    Returns:
        Complete markdown file content with YAML frontmatter.

    Example:
        >>> from datetime import datetime, timezone
        >>> metadata = ArtifactMetadata(
        ...     id="RV-0001",
        ...     type="review",
        ...     title="Security Review",
        ...     status="draft",
        ...     created=datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc),
        ...     author="reviewer",
        ... )
        >>> content = serialize_frontmatter(metadata, "# Review Content")
        >>> content.startswith("---")
        True
    """
    data = _metadata_to_dict(metadata)

    # Use default_flow_style=False for readable YAML
    yaml_str = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    # Ensure body has proper spacing
    body = body.strip()

    return f"---\n{yaml_str}---\n\n{body}\n"


def serialize_sidecar(metadata: ArtifactMetadata) -> str:
    """Serialize metadata to sidecar YAML.

    Args:
        metadata: Artifact metadata.

    Returns:
        YAML string (without frontmatter delimiters).

    Example:
        >>> from datetime import datetime, timezone
        >>> metadata = ArtifactMetadata(
        ...     id="IM-0001",
        ...     type="image",
        ...     title="Error Screenshot",
        ...     status="complete",
        ...     created=datetime(2025, 1, 30, 10, 0, tzinfo=timezone.utc),
        ...     author="developer",
        ... )
        >>> yaml_str = serialize_sidecar(metadata)
        >>> "id: IM-0001" in yaml_str
        True
    """
    data = _metadata_to_dict(metadata)

    return yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
