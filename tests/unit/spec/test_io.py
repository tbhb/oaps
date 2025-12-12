"""Unit tests for spec file I/O utilities."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.exceptions import SpecIOError, SpecParseError
from oaps.spec._io import (
    append_jsonl,
    read_json,
    read_jsonl,
    read_markdown_frontmatter,
    write_json_atomic,
    write_markdown_with_frontmatter,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestReadJson:
    def test_reads_valid_json_object(self, fs: FakeFilesystem) -> None:
        path = Path("/test/data.json")
        fs.create_file(path, contents='{"key": "value", "number": 42}')

        result = read_json(path)

        assert result == {"key": "value", "number": 42}

    def test_reads_nested_json_object(self, fs: FakeFilesystem) -> None:
        path = Path("/test/nested.json")
        fs.create_file(path, contents='{"outer": {"inner": "deep"}, "list": [1, 2, 3]}')

        result = read_json(path)

        assert result == {"outer": {"inner": "deep"}, "list": [1, 2, 3]}

    def test_raises_spec_io_error_for_missing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/missing.json")
        # Ensure fs fixture is used but file is not created

        with pytest.raises(SpecIOError) as exc_info:
            read_json(path)

        assert exc_info.value.path == path
        assert exc_info.value.operation == "read"
        assert exc_info.value.cause is not None

    def test_raises_spec_parse_error_for_invalid_json(self, fs: FakeFilesystem) -> None:
        path = Path("/test/invalid.json")
        fs.create_file(path, contents="not valid json {")

        with pytest.raises(SpecParseError) as exc_info:
            read_json(path)

        assert exc_info.value.path == path
        assert exc_info.value.content_type == "json"
        assert exc_info.value.cause is not None

    def test_raises_spec_parse_error_for_json_array(self, fs: FakeFilesystem) -> None:
        path = Path("/test/array.json")
        fs.create_file(path, contents="[1, 2, 3]")

        with pytest.raises(SpecParseError) as exc_info:
            read_json(path)

        assert exc_info.value.path == path
        assert exc_info.value.content_type == "json"
        assert "Expected JSON object" in str(exc_info.value)

    def test_raises_spec_parse_error_for_json_string(self, fs: FakeFilesystem) -> None:
        path = Path("/test/string.json")
        fs.create_file(path, contents='"just a string"')

        with pytest.raises(SpecParseError) as exc_info:
            read_json(path)

        assert exc_info.value.path == path
        assert "Expected JSON object" in str(exc_info.value)


class TestWriteJsonAtomic:
    def test_writes_json_to_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/output.json")
        fs.create_dir("/test")
        data = {"key": "value", "number": 42}

        write_json_atomic(path, data)

        assert path.exists()
        content = path.read_text()
        assert '"key": "value"' in content
        assert '"number": 42' in content

    def test_creates_parent_directories(self, fs: FakeFilesystem) -> None:
        path = Path("/test/nested/deep/output.json")
        data = {"created": True}

        write_json_atomic(path, data)

        assert path.exists()
        assert path.parent.exists()

    def test_overwrites_existing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/existing.json")
        fs.create_file(path, contents='{"old": "data"}')

        write_json_atomic(path, {"new": "data"})

        content = path.read_text()
        assert '"new": "data"' in content
        assert "old" not in content

    def test_atomic_write_no_temp_file_on_success(self, fs: FakeFilesystem) -> None:
        path = Path("/test/output.json")
        fs.create_dir("/test")

        write_json_atomic(path, {"key": "value"})

        # Check no temp files left behind
        temp_files = list(path.parent.glob("*.tmp"))
        assert temp_files == []

    def test_raises_spec_io_error_for_unserializable_data(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/output.json")
        fs.create_dir("/test")
        # Sets are not JSON serializable
        data = {"set": {1, 2, 3}}

        with pytest.raises(SpecIOError) as exc_info:
            write_json_atomic(path, data)

        assert exc_info.value.path == path
        assert exc_info.value.operation == "write"


class TestReadJsonl:
    def test_reads_multiple_json_lines(self, fs: FakeFilesystem) -> None:
        path = Path("/test/history.jsonl")
        lines = '{"event": "created"}\n{"event": "updated"}\n{"event": "deleted"}\n'
        fs.create_file(path, contents=lines)

        result = read_jsonl(path)

        assert len(result) == 3
        assert result[0] == {"event": "created"}
        assert result[1] == {"event": "updated"}
        assert result[2] == {"event": "deleted"}

    def test_returns_empty_list_for_missing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/missing.jsonl")
        # Ensure fs fixture is active

        result = read_jsonl(path)

        assert result == []

    def test_returns_empty_list_for_empty_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/empty.jsonl")
        fs.create_file(path, contents="")

        result = read_jsonl(path)

        assert result == []

    def test_returns_empty_list_for_whitespace_only_file(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/whitespace.jsonl")
        fs.create_file(path, contents="   \n\n   \n")

        result = read_jsonl(path)

        assert result == []

    def test_skips_blank_lines(self, fs: FakeFilesystem) -> None:
        path = Path("/test/sparse.jsonl")
        fs.create_file(
            path,
            contents='{"first": 1}\n\n{"second": 2}\n  \n{"third": 3}\n',
        )

        result = read_jsonl(path)

        assert len(result) == 3
        assert result[0] == {"first": 1}
        assert result[1] == {"second": 2}
        assert result[2] == {"third": 3}

    def test_raises_spec_parse_error_for_invalid_json_line(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/invalid.jsonl")
        fs.create_file(
            path,
            contents='{"valid": true}\nnot json\n{"also_valid": true}\n',
        )

        with pytest.raises(SpecParseError) as exc_info:
            read_jsonl(path)

        assert exc_info.value.path == path
        assert exc_info.value.content_type == "jsonl"
        assert exc_info.value.line == 2
        assert exc_info.value.cause is not None

    def test_raises_spec_parse_error_for_json_array_line(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/array_line.jsonl")
        fs.create_file(
            path,
            contents='{"valid": true}\n[1, 2, 3]\n',
        )

        with pytest.raises(SpecParseError) as exc_info:
            read_jsonl(path)

        assert exc_info.value.path == path
        assert exc_info.value.line == 2
        assert "Expected JSON object" in str(exc_info.value)


class TestAppendJsonl:
    def test_appends_entry_to_new_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/new.jsonl")
        fs.create_dir("/test")

        append_jsonl(path, {"event": "created"})

        content = path.read_text()
        assert content.strip() == '{"event":"created"}'

    def test_appends_entry_to_existing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/existing.jsonl")
        fs.create_file(path, contents='{"event": "first"}\n')

        append_jsonl(path, {"event": "second"})

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert '"event": "first"' in lines[0] or '"event":"first"' in lines[0]
        assert '"event":"second"' in lines[1]

    def test_creates_parent_directories(self, fs: FakeFilesystem) -> None:
        path = Path("/test/nested/deep/history.jsonl")

        append_jsonl(path, {"event": "created"})

        assert path.exists()
        assert path.parent.exists()

    def test_multiple_appends(self, fs: FakeFilesystem) -> None:
        path = Path("/test/multi.jsonl")
        fs.create_dir("/test")

        append_jsonl(path, {"n": 1})
        append_jsonl(path, {"n": 2})
        append_jsonl(path, {"n": 3})

        result = read_jsonl(path)
        assert len(result) == 3
        assert result[0] == {"n": 1}
        assert result[1] == {"n": 2}
        assert result[2] == {"n": 3}

    def test_raises_spec_io_error_for_unserializable_data(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/output.jsonl")
        fs.create_dir("/test")
        # Sets are not JSON serializable
        entry = {"set": {1, 2, 3}}

        with pytest.raises(SpecIOError) as exc_info:
            append_jsonl(path, entry)

        assert exc_info.value.path == path
        assert exc_info.value.operation == "append"


class TestReadMarkdownFrontmatter:
    def test_reads_valid_frontmatter(self, fs: FakeFilesystem) -> None:
        path = Path("/test/doc.md")
        content = """---
title: Test Document
author: Test Author
tags:
  - tag1
  - tag2
---

# Document Body

This is the body content."""
        fs.create_file(path, contents=content)

        frontmatter, body = read_markdown_frontmatter(path)

        assert frontmatter == {
            "title": "Test Document",
            "author": "Test Author",
            "tags": ["tag1", "tag2"],
        }
        assert "# Document Body" in body
        assert "This is the body content." in body

    def test_returns_empty_dict_for_no_frontmatter(self, fs: FakeFilesystem) -> None:
        path = Path("/test/no_frontmatter.md")
        content = """# Just a Header

Some content without frontmatter."""
        fs.create_file(path, contents=content)

        frontmatter, body = read_markdown_frontmatter(path)

        assert frontmatter == {}
        assert body == content

    def test_returns_empty_dict_for_unclosed_frontmatter(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/unclosed.md")
        content = """---
title: Unclosed
author: Test

# No closing delimiter"""
        fs.create_file(path, contents=content)

        frontmatter, body = read_markdown_frontmatter(path)

        assert frontmatter == {}
        assert body == content

    def test_raises_spec_parse_error_for_malformed_yaml(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/malformed.md")
        content = """---
title: [malformed yaml
author: missing bracket
---

Body content."""
        fs.create_file(path, contents=content)

        with pytest.raises(SpecParseError) as exc_info:
            read_markdown_frontmatter(path)

        assert exc_info.value.path == path
        assert exc_info.value.content_type == "frontmatter"
        assert exc_info.value.cause is not None

    def test_raises_spec_parse_error_for_non_dict_yaml(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/list.md")
        content = """---
- item1
- item2
- item3
---

Body content."""
        fs.create_file(path, contents=content)

        with pytest.raises(SpecParseError) as exc_info:
            read_markdown_frontmatter(path)

        assert exc_info.value.path == path
        assert exc_info.value.content_type == "frontmatter"
        assert "Expected YAML mapping" in str(exc_info.value)

    def test_returns_empty_dict_for_empty_frontmatter(self, fs: FakeFilesystem) -> None:
        path = Path("/test/empty_fm.md")
        content = """---
---

Body content."""
        fs.create_file(path, contents=content)

        frontmatter, body = read_markdown_frontmatter(path)

        assert frontmatter == {}
        assert "Body content." in body

    def test_raises_spec_io_error_for_missing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/missing.md")
        # Ensure fs fixture is active

        with pytest.raises(SpecIOError) as exc_info:
            read_markdown_frontmatter(path)

        assert exc_info.value.path == path
        assert exc_info.value.operation == "read"

    def test_handles_frontmatter_without_trailing_newline(
        self, fs: FakeFilesystem
    ) -> None:
        path = Path("/test/compact.md")
        content = "---\ntitle: Compact\n---\nBody"
        fs.create_file(path, contents=content)

        frontmatter, body = read_markdown_frontmatter(path)

        assert frontmatter == {"title": "Compact"}
        assert body == "Body"


class TestWriteMarkdownWithFrontmatter:
    def test_writes_file_with_frontmatter(self, fs: FakeFilesystem) -> None:
        path = Path("/test/output.md")
        fs.create_dir("/test")
        frontmatter = {"title": "Test", "author": "Author"}
        content = "# Body\n\nContent here."

        write_markdown_with_frontmatter(path, frontmatter, content)

        result = path.read_text()
        assert result.startswith("---\n")
        assert "title: Test" in result
        assert "author: Author" in result
        assert "---\n\n# Body" in result

    def test_creates_parent_directories(self, fs: FakeFilesystem) -> None:
        path = Path("/test/nested/deep/doc.md")
        frontmatter = {"created": True}
        content = "Body"

        write_markdown_with_frontmatter(path, frontmatter, content)

        assert path.exists()
        assert path.parent.exists()

    def test_strips_trailing_whitespace_from_content(self, fs: FakeFilesystem) -> None:
        path = Path("/test/trimmed.md")
        fs.create_dir("/test")
        frontmatter = {"title": "Test"}
        content = "Body content   \n\n\n"

        write_markdown_with_frontmatter(path, frontmatter, content)

        result = path.read_text()
        assert result.endswith("Body content\n")

    def test_roundtrip_read_write(self, fs: FakeFilesystem) -> None:
        path = Path("/test/roundtrip.md")
        fs.create_dir("/test")
        original_frontmatter = {"title": "Roundtrip", "version": 1}
        original_content = "# Test Content\n\nWith multiple lines."

        write_markdown_with_frontmatter(path, original_frontmatter, original_content)
        read_frontmatter, read_body = read_markdown_frontmatter(path)

        assert read_frontmatter == original_frontmatter
        assert "# Test Content" in read_body
        assert "With multiple lines." in read_body

    def test_sorts_frontmatter_keys(self, fs: FakeFilesystem) -> None:
        path = Path("/test/sorted.md")
        fs.create_dir("/test")
        frontmatter = {"zebra": 1, "alpha": 2, "beta": 3}

        write_markdown_with_frontmatter(path, frontmatter, "Body")

        result = path.read_text()
        alpha_pos = result.find("alpha")
        beta_pos = result.find("beta")
        zebra_pos = result.find("zebra")
        assert alpha_pos < beta_pos < zebra_pos

    def test_overwrites_existing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/existing.md")
        fs.create_file(
            path,
            contents="---\nold: data\n---\n\nOld content.",
        )

        write_markdown_with_frontmatter(path, {"new": "data"}, "New content")

        result = path.read_text()
        assert "new: data" in result
        assert "New content" in result
        assert "old" not in result
        assert "Old content" not in result

    def test_atomic_write_no_temp_file_on_success(self, fs: FakeFilesystem) -> None:
        path = Path("/test/output.md")
        fs.create_dir("/test")

        write_markdown_with_frontmatter(path, {"key": "value"}, "Body")

        temp_files = list(path.parent.glob("*.tmp"))
        assert temp_files == []
