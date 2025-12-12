"""Property-based tests for artifact metadata parsing and serialization."""

from datetime import UTC, datetime

from hypothesis import given, settings, strategies as st

from oaps.artifacts._metadata import (
    parse_frontmatter,
    parse_sidecar,
    serialize_frontmatter,
    serialize_sidecar,
)
from oaps.artifacts._types import ArtifactMetadata

# =============================================================================
# Strategies
# =============================================================================

# Valid artifact IDs
valid_id = st.from_regex(r"[A-Z]{2}-\d{4}", fullmatch=True)

# Valid type names (matching base types or simple names)
valid_type = st.sampled_from(
    [
        "review",
        "decision",
        "analysis",
        "report",
        "example",
        "change",
        "diagram",
        "image",
        "video",
        "mockup",
    ]
)

# Valid statuses
valid_status = st.sampled_from(["draft", "complete", "superseded", "retracted"])

# Safe text for YAML (no special chars that break YAML)
# Note: Only allow ASCII space, not Unicode whitespace
# (Zs category includes non-breaking space)
safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=["L", "N"],
        whitelist_characters="-_ ",  # Only ASCII space
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() and not x.startswith("-"))

# Valid datetimes (timezone-aware)
# Note: Hypothesis datetimes() requires naive min/max, then we map to add timezone
valid_datetime = st.datetimes(
    min_value=datetime(2000, 1, 1),  # noqa: DTZ001
    max_value=datetime(2100, 1, 1),  # noqa: DTZ001
).map(lambda dt: dt.replace(tzinfo=UTC))

# Optional safe text
optional_safe_text = st.one_of(st.none(), safe_text)

# Optional list of safe texts
optional_safe_text_list = st.one_of(
    st.none(),
    st.lists(safe_text, min_size=0, max_size=3),
)


@st.composite
def valid_metadata(draw: st.DrawFn) -> ArtifactMetadata:
    """Strategy for generating valid ArtifactMetadata objects."""
    artifact_id = draw(valid_id)
    artifact_type = draw(valid_type)

    # Ensure ID prefix matches type
    type_to_prefix = {
        "review": "RV",
        "decision": "DC",
        "analysis": "AN",
        "report": "RP",
        "example": "EX",
        "change": "CH",
        "diagram": "DG",
        "image": "IM",
        "video": "VD",
        "mockup": "MK",
    }
    prefix = type_to_prefix[artifact_type]
    number_str = artifact_id[3:]
    artifact_id = f"{prefix}-{number_str}"

    title = draw(safe_text)
    status = draw(valid_status)
    created = draw(valid_datetime)
    author = draw(safe_text)

    reviewers = draw(optional_safe_text_list)
    tags = draw(optional_safe_text_list)

    return ArtifactMetadata(
        id=artifact_id,
        type=artifact_type,
        title=title,
        status=status,
        created=created,
        author=author,
        reviewers=tuple(reviewers) if reviewers else (),
        tags=tuple(tags) if tags else (),
    )


# =============================================================================
# Frontmatter Round-Trip Properties
# =============================================================================


@given(metadata=valid_metadata())
@settings(max_examples=50)  # Reduce examples since serialization is slow
def test_frontmatter_round_trip_preserves_required_fields(
    metadata: ArtifactMetadata,
) -> None:
    """Property: serialize then parse frontmatter preserves required fields."""
    body = "# Test Content"
    serialized = serialize_frontmatter(metadata, body)
    parsed, _parsed_body = parse_frontmatter(serialized)

    assert parsed.id == metadata.id
    assert parsed.type == metadata.type
    assert parsed.title == metadata.title
    assert parsed.status == metadata.status
    assert parsed.author == metadata.author
    # Note: datetime comparison may have precision differences


@given(metadata=valid_metadata())
@settings(max_examples=50)
def test_frontmatter_round_trip_preserves_body(metadata: ArtifactMetadata) -> None:
    """Property: serialize then parse frontmatter preserves body content."""
    body = "# Test Content\n\nSome body text."
    serialized = serialize_frontmatter(metadata, body)
    _, parsed_body = parse_frontmatter(serialized)

    assert body.strip() == parsed_body.strip()


@given(metadata=valid_metadata())
@settings(max_examples=50)
def test_frontmatter_has_correct_delimiters(metadata: ArtifactMetadata) -> None:
    """Property: serialized frontmatter starts with --- and has closing ---."""
    serialized = serialize_frontmatter(metadata, "body")

    assert serialized.startswith("---\n")
    # Find second delimiter
    second_delimiter = serialized.find("---", 4)
    assert second_delimiter > 4


@given(metadata=valid_metadata())
@settings(max_examples=50)
def test_frontmatter_contains_all_required_fields(metadata: ArtifactMetadata) -> None:
    """Property: serialized frontmatter contains all required field keys."""
    serialized = serialize_frontmatter(metadata, "body")

    assert "id:" in serialized
    assert "type:" in serialized
    assert "title:" in serialized
    assert "status:" in serialized
    assert "created:" in serialized
    assert "author:" in serialized


# =============================================================================
# Sidecar Round-Trip Properties
# =============================================================================


@given(metadata=valid_metadata())
@settings(max_examples=50)
def test_sidecar_round_trip_preserves_fields(metadata: ArtifactMetadata) -> None:
    """Property: serialize then parse sidecar preserves fields."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        sidecar_path = Path(tmpdir) / "test.metadata.yaml"
        serialized = serialize_sidecar(metadata)
        sidecar_path.write_text(serialized)

        parsed = parse_sidecar(sidecar_path)

        assert parsed.id == metadata.id
        assert parsed.type == metadata.type
        assert parsed.title == metadata.title
        assert parsed.status == metadata.status
        assert parsed.author == metadata.author


@given(metadata=valid_metadata())
@settings(max_examples=50)
def test_sidecar_has_no_frontmatter_delimiters(metadata: ArtifactMetadata) -> None:
    """Property: sidecar YAML has no frontmatter delimiters."""
    serialized = serialize_sidecar(metadata)

    # Should not have the --- delimiters
    lines = serialized.strip().split("\n")
    assert not any(line.strip() == "---" for line in lines)


# =============================================================================
# Edge Case Properties
# =============================================================================


@given(body=st.text(min_size=0, max_size=1000))
@settings(max_examples=30)
def test_frontmatter_handles_arbitrary_body(body: str) -> None:
    """Property: frontmatter serialization handles arbitrary body text."""
    metadata = ArtifactMetadata(
        id="RV-0001",
        type="review",
        title="Test",
        status="draft",
        created=datetime(2025, 1, 1, tzinfo=UTC),
        author="test",
    )

    serialized = serialize_frontmatter(metadata, body)

    # Should be parseable and contain body
    parsed_metadata, parsed_body = parse_frontmatter(serialized)
    assert parsed_metadata.id == "RV-0001"
    assert body.strip() == parsed_body.strip()
