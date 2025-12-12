"""Tests for metadata parsing and serialization utilities."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.artifacts._metadata import (
    MAX_ARTIFACT_NUMBER,
    PREFIX_LENGTH,
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
from oaps.artifacts._types import ArtifactMetadata


class TestConstants:
    def test_prefix_length_is_two(self) -> None:
        assert PREFIX_LENGTH == 2

    def test_max_artifact_number(self) -> None:
        assert MAX_ARTIFACT_NUMBER == 9999


class TestParseArtifactId:
    def test_parses_valid_id(self) -> None:
        prefix, number = parse_artifact_id("RV-0001")

        assert prefix == "RV"
        assert number == 1

    def test_parses_larger_numbers(self) -> None:
        prefix, number = parse_artifact_id("DC-1234")

        assert prefix == "DC"
        assert number == 1234

    def test_parses_max_number(self) -> None:
        prefix, number = parse_artifact_id("AN-9999")

        assert prefix == "AN"
        assert number == 9999

    def test_raises_for_lowercase_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("rv-0001")

    def test_raises_for_single_letter_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("R-0001")

    def test_raises_for_three_letter_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("REV-0001")

    def test_raises_for_missing_hyphen(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("RV0001")

    def test_raises_for_too_few_digits(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("RV-001")

    def test_raises_for_too_many_digits(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("RV-00001")

    def test_raises_for_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ID format"):
            parse_artifact_id("")


class TestFormatArtifactId:
    def test_formats_simple_id(self) -> None:
        result = format_artifact_id("RV", 1)
        assert result == "RV-0001"

    def test_formats_larger_number(self) -> None:
        result = format_artifact_id("DC", 123)
        assert result == "DC-0123"

    def test_formats_max_number(self) -> None:
        result = format_artifact_id("AN", 9999)
        assert result == "AN-9999"

    def test_raises_for_lowercase_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid prefix"):
            format_artifact_id("rv", 1)

    def test_raises_for_single_letter_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid prefix"):
            format_artifact_id("R", 1)

    def test_raises_for_three_letter_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid prefix"):
            format_artifact_id("REV", 1)

    def test_raises_for_empty_prefix(self) -> None:
        with pytest.raises(ValueError, match="Invalid prefix"):
            format_artifact_id("", 1)

    def test_raises_for_zero_number(self) -> None:
        with pytest.raises(ValueError, match="Invalid number"):
            format_artifact_id("RV", 0)

    def test_raises_for_negative_number(self) -> None:
        with pytest.raises(ValueError, match="Invalid number"):
            format_artifact_id("RV", -1)

    def test_raises_for_number_over_max(self) -> None:
        with pytest.raises(ValueError, match="Invalid number"):
            format_artifact_id("RV", 10000)


class TestGenerateSlug:
    def test_converts_simple_title(self) -> None:
        result = generate_slug("Security Review")
        assert result == "security-review"

    def test_converts_longer_title(self) -> None:
        result = generate_slug("Security Review of Token Handling")
        assert result == "security-review-of-token-handling"

    def test_handles_underscores(self) -> None:
        result = generate_slug("api_endpoint_test")
        assert result == "api-endpoint-test"

    def test_removes_special_characters(self) -> None:
        result = generate_slug("Test: Example (v2.0)!")
        assert result == "test-example-v20"

    def test_collapses_multiple_hyphens(self) -> None:
        result = generate_slug("test---multiple---hyphens")
        assert result == "test-multiple-hyphens"

    def test_strips_leading_trailing_hyphens(self) -> None:
        result = generate_slug("---test---")
        assert result == "test"

    def test_truncates_long_titles_at_word_boundary(self) -> None:
        result = generate_slug(
            "This is a very long title that exceeds fifty chars", max_length=20
        )
        # Should truncate at a hyphen boundary
        assert len(result) <= 20
        assert not result.endswith("-")

    def test_truncates_single_long_word(self) -> None:
        result = generate_slug("supercalifragilisticexpialidocious", max_length=10)
        assert len(result) <= 10

    def test_returns_untitled_for_empty_result(self) -> None:
        result = generate_slug("!@#$%^&*()")
        assert result == "untitled"

    def test_returns_untitled_for_empty_string(self) -> None:
        result = generate_slug("")
        assert result == "untitled"


class TestGenerateFilename:
    def test_generates_standard_filename(self) -> None:
        timestamp = datetime(2025, 1, 15, 10, 30, 22, tzinfo=UTC)
        result = generate_filename("RV", 1, "security-review", "md", timestamp)

        assert result == "20250115103022-RV-0001-security-review.md"

    def test_generates_with_larger_number(self) -> None:
        timestamp = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
        result = generate_filename("DC", 123, "architecture-decision", "md", timestamp)

        assert result == "20251231235959-DC-0123-architecture-decision.md"

    def test_handles_extension_with_dot(self) -> None:
        timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = generate_filename("IM", 1, "screenshot", ".png", timestamp)

        assert result == "20250101000000-IM-0001-screenshot.png"

    def test_uses_current_time_when_not_provided(self) -> None:
        result = generate_filename("RV", 1, "test", "md")

        # Just verify format, not exact timestamp
        assert result.endswith("-RV-0001-test.md")
        assert len(result.split("-")[0]) == 14  # YYYYMMDDHHMMSS


class TestParseFilename:
    def test_parses_standard_filename(self) -> None:
        timestamp, prefix, number, slug, ext = parse_filename(
            "20250115103022-RV-0001-security-review.md"
        )

        assert timestamp == datetime(2025, 1, 15, 10, 30, 22, tzinfo=UTC)
        assert prefix == "RV"
        assert number == 1
        assert slug == "security-review"
        assert ext == "md"

    def test_parses_binary_filename(self) -> None:
        timestamp, prefix, number, slug, ext = parse_filename(
            "20251231235959-IM-0123-error-screenshot.png"
        )

        assert timestamp == datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)
        assert prefix == "IM"
        assert number == 123
        assert slug == "error-screenshot"
        assert ext == "png"

    def test_raises_for_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact filename format"):
            parse_filename("invalid-filename.md")

    def test_raises_for_missing_timestamp(self) -> None:
        with pytest.raises(ValueError, match="Invalid artifact filename format"):
            parse_filename("RV-0001-security-review.md")


class TestParseFrontmatter:
    def test_parses_minimal_frontmatter(self) -> None:
        content = """---
id: RV-0001
type: review
title: Security Review
status: draft
created: 2025-01-15T10:30:00+00:00
author: reviewer
---

# Content
"""
        metadata, body = parse_frontmatter(content)

        assert metadata.id == "RV-0001"
        assert metadata.type == "review"
        assert metadata.title == "Security Review"
        assert metadata.status == "draft"
        assert metadata.author == "reviewer"
        assert body.strip() == "# Content"

    def test_parses_full_frontmatter(self) -> None:
        content = """---
id: RV-0001
type: review
title: Security Review
status: complete
created: 2025-01-15T10:30:00+00:00
author: security-team
subtype: security
updated: 2025-01-20T14:00:00+00:00
reviewers:
  - alice
  - bob
references:
  - FR-0001
  - FR-0002
tags:
  - security
  - critical
summary: A security review
review_type: security
findings: 5
---

Body content here.
"""
        metadata, _body = parse_frontmatter(content)

        assert metadata.subtype == "security"
        assert metadata.reviewers == ("alice", "bob")
        assert metadata.references == ("FR-0001", "FR-0002")
        assert metadata.tags == ("security", "critical")
        assert metadata.summary == "A security review"
        assert metadata.type_fields["review_type"] == "security"
        assert metadata.type_fields["findings"] == 5

    def test_raises_for_missing_frontmatter_start(self) -> None:
        content = """id: RV-0001
type: review
---

Content
"""
        with pytest.raises(ValueError, match="Frontmatter must start"):
            parse_frontmatter(content)

    def test_raises_for_missing_frontmatter_end(self) -> None:
        content = """---
id: RV-0001
type: review

Content
"""
        with pytest.raises(ValueError, match="closing '---' not found"):
            parse_frontmatter(content)

    def test_raises_for_invalid_yaml(self) -> None:
        content = """---
id: RV-0001
type: review: invalid: yaml:
---

Content
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_frontmatter(content)

    def test_raises_for_missing_required_fields(self) -> None:
        content = """---
id: RV-0001
---

Content
"""
        with pytest.raises(ValueError, match="Missing required"):
            parse_frontmatter(content)


class TestParseSidecar:
    def test_parses_sidecar_file(self, tmp_path: Path) -> None:
        sidecar = tmp_path / "test.metadata.yaml"
        sidecar.write_text("""id: IM-0001
type: image
title: Error Screenshot
status: complete
created: 2025-01-15T10:30:00+00:00
author: developer
alt_text: Screenshot showing error
""")

        metadata = parse_sidecar(sidecar)

        assert metadata.id == "IM-0001"
        assert metadata.type == "image"
        assert metadata.type_fields["alt_text"] == "Screenshot showing error"

    def test_raises_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_sidecar(tmp_path / "nonexistent.metadata.yaml")

    def test_raises_for_invalid_yaml(self, tmp_path: Path) -> None:
        sidecar = tmp_path / "invalid.metadata.yaml"
        sidecar.write_text("not: valid: yaml: here:")

        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_sidecar(sidecar)


class TestSerializeFrontmatter:
    def test_serializes_minimal_metadata(
        self, sample_metadata: ArtifactMetadata
    ) -> None:
        result = serialize_frontmatter(sample_metadata, "# Body")

        assert result.startswith("---\n")
        assert "id: RV-0001" in result
        assert "type: review" in result
        assert "---\n\n# Body\n" in result

    def test_serializes_all_fields(
        self, sample_metadata_full: ArtifactMetadata
    ) -> None:
        result = serialize_frontmatter(sample_metadata_full, "Content")

        assert "subtype: security" in result
        assert "reviewers:" in result
        assert "- alice" in result
        assert "references:" in result
        assert "tags:" in result
        assert "summary: Comprehensive security" in result
        assert "review_type: security" in result

    def test_strips_body_whitespace(self, sample_metadata: ArtifactMetadata) -> None:
        result = serialize_frontmatter(sample_metadata, "  \n  Body  \n  ")

        assert result.endswith("Body\n")


class TestSerializeSidecar:
    def test_serializes_metadata(self, sample_metadata: ArtifactMetadata) -> None:
        result = serialize_sidecar(sample_metadata)

        assert "id: RV-0001" in result
        assert "type: review" in result
        assert "---" not in result  # No frontmatter delimiters


class TestRoundTrip:
    def test_frontmatter_round_trip(
        self, sample_metadata_full: ArtifactMetadata
    ) -> None:
        body = "# Original Content\n\nSome text."
        serialized = serialize_frontmatter(sample_metadata_full, body)
        parsed_metadata, parsed_body = parse_frontmatter(serialized)

        assert parsed_metadata.id == sample_metadata_full.id
        assert parsed_metadata.type == sample_metadata_full.type
        assert parsed_metadata.title == sample_metadata_full.title
        assert parsed_metadata.status == sample_metadata_full.status
        assert parsed_metadata.author == sample_metadata_full.author
        assert parsed_metadata.subtype == sample_metadata_full.subtype
        assert parsed_metadata.reviewers == sample_metadata_full.reviewers
        assert parsed_metadata.references == sample_metadata_full.references
        assert parsed_metadata.tags == sample_metadata_full.tags
        assert parsed_body.strip() == body.strip()

    def test_sidecar_round_trip(
        self, tmp_path: Path, sample_metadata_full: ArtifactMetadata
    ) -> None:
        serialized = serialize_sidecar(sample_metadata_full)
        sidecar_path = tmp_path / "test.metadata.yaml"
        sidecar_path.write_text(serialized)
        parsed = parse_sidecar(sidecar_path)

        assert parsed.id == sample_metadata_full.id
        assert parsed.type == sample_metadata_full.type
        assert parsed.title == sample_metadata_full.title

    def test_artifact_id_round_trip(self) -> None:
        for prefix in ("RV", "DC", "AN", "IM"):
            for number in (1, 42, 999, 9999):
                artifact_id = format_artifact_id(prefix, number)
                parsed_prefix, parsed_number = parse_artifact_id(artifact_id)

                assert parsed_prefix == prefix
                assert parsed_number == number

    def test_filename_round_trip(self) -> None:
        timestamp = datetime(2025, 6, 15, 12, 30, 45, tzinfo=UTC)
        filename = generate_filename("RV", 123, "test-slug", "md", timestamp)
        parsed_ts, parsed_prefix, parsed_num, parsed_slug, parsed_ext = parse_filename(
            filename
        )

        assert parsed_ts == timestamp
        assert parsed_prefix == "RV"
        assert parsed_num == 123
        assert parsed_slug == "test-slug"
        assert parsed_ext == "md"
