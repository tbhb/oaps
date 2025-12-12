"""Property-based tests for artifact ID and filename utilities."""

import pytest
from hypothesis import given, strategies as st

from oaps.artifacts._metadata import (
    MAX_ARTIFACT_NUMBER,
    PREFIX_LENGTH,
    format_artifact_id,
    generate_slug,
    parse_artifact_id,
)

# =============================================================================
# Strategies
# =============================================================================

# Valid two-letter uppercase prefixes
valid_prefix = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    min_size=PREFIX_LENGTH,
    max_size=PREFIX_LENGTH,
)

# Valid artifact numbers (1-9999)
valid_number = st.integers(min_value=1, max_value=MAX_ARTIFACT_NUMBER)

# Valid artifact IDs in PREFIX-NNNN format
valid_artifact_id = st.builds(
    format_artifact_id,
    prefix=valid_prefix,
    number=valid_number,
)

# Titles that should produce valid slugs
valid_title = st.text(
    alphabet=st.characters(whitelist_categories=["L", "N", "Zs"]),
    min_size=1,
    max_size=100,
)


# =============================================================================
# ID Round-Trip Properties
# =============================================================================


@given(prefix=valid_prefix, number=valid_number)
def test_id_format_parse_round_trip(prefix: str, number: int) -> None:
    """Property: format_artifact_id then parse_artifact_id returns original values."""
    artifact_id = format_artifact_id(prefix, number)
    parsed_prefix, parsed_number = parse_artifact_id(artifact_id)

    assert parsed_prefix == prefix
    assert parsed_number == number


@given(artifact_id=valid_artifact_id)
def test_id_parse_format_round_trip(artifact_id: str) -> None:
    """Property: parse_artifact_id then format_artifact_id returns original ID."""
    prefix, number = parse_artifact_id(artifact_id)
    reconstructed = format_artifact_id(prefix, number)

    assert reconstructed == artifact_id


@given(prefix=valid_prefix, number=valid_number)
def test_formatted_id_has_correct_structure(prefix: str, number: int) -> None:
    """Property: formatted ID always has structure PREFIX-NNNN."""
    artifact_id = format_artifact_id(prefix, number)

    assert len(artifact_id) == 7  # XX-NNNN
    assert artifact_id[2] == "-"
    assert artifact_id[:2] == prefix
    assert artifact_id[3:].isdigit()
    assert len(artifact_id[3:]) == 4


@given(artifact_id=valid_artifact_id)
def test_parsed_prefix_is_uppercase_alpha(artifact_id: str) -> None:
    """Property: parsed prefix is always two uppercase letters."""
    prefix, _ = parse_artifact_id(artifact_id)

    assert len(prefix) == 2
    assert prefix.isupper()
    assert prefix.isalpha()


@given(artifact_id=valid_artifact_id)
def test_parsed_number_in_valid_range(artifact_id: str) -> None:
    """Property: parsed number is always in range 1-9999."""
    _, number = parse_artifact_id(artifact_id)

    assert 1 <= number <= MAX_ARTIFACT_NUMBER


# =============================================================================
# ID Validation Properties
# =============================================================================


@given(
    prefix=st.text(min_size=1, max_size=10).filter(
        lambda x: len(x) != 2 or not x.isupper()
    )
)
def test_format_rejects_invalid_prefix(prefix: str) -> None:
    """Property: format_artifact_id rejects invalid prefixes."""
    if not prefix or len(prefix) != 2 or not prefix.isupper() or not prefix.isalpha():
        with pytest.raises(ValueError, match=r"[Pp]refix"):
            format_artifact_id(prefix, 1)


@given(number=st.integers().filter(lambda x: x < 1 or x > MAX_ARTIFACT_NUMBER))
def test_format_rejects_invalid_number(number: int) -> None:
    """Property: format_artifact_id rejects numbers outside 1-9999."""
    with pytest.raises(ValueError, match=r"[Nn]umber"):
        format_artifact_id("RV", number)


# =============================================================================
# Slug Properties
# =============================================================================


@given(title=valid_title)
def test_slug_is_lowercase(title: str) -> None:
    """Property: generated slug is always lowercase."""
    slug = generate_slug(title)
    # All alpha chars should be lowercase; digits don't have case
    assert all(c.islower() or c.isdigit() or c == "-" for c in slug)


@given(title=valid_title)
def test_slug_contains_only_valid_chars(title: str) -> None:
    """Property: generated slug contains only lowercase alphanumeric and hyphens."""
    slug = generate_slug(title)

    for char in slug:
        assert char.islower() or char.isdigit() or char == "-", (
            f"Invalid char: {char!r}"
        )


@given(title=valid_title)
def test_slug_has_no_consecutive_hyphens(title: str) -> None:
    """Property: generated slug never has consecutive hyphens."""
    slug = generate_slug(title)
    assert "--" not in slug


@given(title=valid_title)
def test_slug_has_no_leading_trailing_hyphens(title: str) -> None:
    """Property: generated slug never starts or ends with hyphen."""
    slug = generate_slug(title)
    if slug != "untitled":
        assert not slug.startswith("-")
        assert not slug.endswith("-")


@given(title=valid_title, max_length=st.integers(min_value=10, max_value=100))
def test_slug_respects_max_length(title: str, max_length: int) -> None:
    """Property: generated slug never exceeds max_length (unless 'untitled')."""
    slug = generate_slug(title, max_length=max_length)
    # 'untitled' fallback is always 8 chars, which may exceed very small max_length
    assert len(slug) <= max_length or slug == "untitled"


@given(title=valid_title)
def test_slug_is_never_empty(title: str) -> None:
    """Property: generated slug is never empty (returns 'untitled' for empty result)."""
    slug = generate_slug(title)
    assert len(slug) > 0


@given(title=valid_title)
def test_slug_idempotence(title: str) -> None:
    """Property: generating slug from a slug produces the same slug."""
    slug = generate_slug(title)
    slug_of_slug = generate_slug(slug)

    # The slug of a slug should be the same or shorter (if it contains only valid chars)
    assert slug_of_slug in {slug, "untitled"}


# =============================================================================
# Edge Cases
# =============================================================================


def test_slug_handles_empty_string() -> None:
    """Edge case: empty string produces 'untitled'."""
    assert generate_slug("") == "untitled"


def test_slug_handles_only_special_chars() -> None:
    """Edge case: string with only special chars produces 'untitled'."""
    assert generate_slug("!@#$%^&*()") == "untitled"


def test_slug_handles_unicode() -> None:
    """Edge case: unicode characters are handled gracefully."""
    # These should be removed or converted
    slug = generate_slug("Café résumé")
    assert slug  # Should produce something, not crash
