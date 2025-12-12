from pathlib import Path
from typing import TYPE_CHECKING

from oaps.templating._frontmatter import (
    _render_key,
    _render_value,
    load_frontmatter_file,
    parse_frontmatter,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestRenderKey:
    def test_string_key_renders_template(self):
        result = _render_key("{{ name }}_key", {"name": "test"})
        assert result == "test_key"

    def test_non_string_key_returns_unchanged(self):
        result = _render_key(42, {"name": "test"})
        assert result == 42

    def test_string_key_without_placeholders_returns_unchanged(self):
        result = _render_key("static_key", {"name": "test"})
        assert result == "static_key"


class TestRenderValue:
    def test_string_value_renders_template(self):
        result = _render_value("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_string_without_placeholders_returns_unchanged(self):
        result = _render_value("static value", {"name": "test"})
        assert result == "static value"

    def test_list_renders_all_items(self):
        result = _render_value(["{{ a }}", "{{ b }}", "static"], {"a": "x", "b": "y"})
        assert result == ["x", "y", "static"]

    def test_nested_list_renders_recursively(self):
        result = _render_value([["{{ a }}"], "{{ b }}"], {"a": "x", "b": "y"})
        assert result == [["x"], "y"]

    def test_dict_renders_keys_and_values(self):
        result = _render_value({"{{ key }}": "{{ value }}"}, {"key": "k", "value": "v"})
        assert result == {"k": "v"}

    def test_dict_with_non_string_key_preserves_key(self):
        result = _render_value({1: "{{ value }}"}, {"value": "v"})
        assert result == {1: "v"}

    def test_nested_dict_renders_recursively(self):
        result = _render_value(
            {"outer": {"inner": "{{ value }}"}},
            {"value": "nested"},
        )
        assert result == {"outer": {"inner": "nested"}}

    def test_dict_removes_empty_string_keys(self):
        result = _render_value(
            {
                "{% if show %}visible{% endif %}": "shown",
                "{% if not show %}hidden{% endif %}": "not shown",
                "static": "value",
            },
            {"show": True},
        )
        assert result == {"visible": "shown", "static": "value"}

    def test_nested_dict_removes_empty_string_keys(self):
        result = _render_value(
            {
                "outer": {
                    "{% if present %}key{% endif %}": "val",
                    "{% if not present %}missing{% endif %}": "gone",
                }
            },
            {"present": True},
        )
        assert result == {"outer": {"key": "val"}}

    def test_int_value_returns_unchanged(self):
        result = _render_value(42, {"name": "test"})
        assert result == 42

    def test_float_value_returns_unchanged(self):
        result = _render_value(3.14, {"name": "test"})
        assert result == 3.14

    def test_bool_value_returns_unchanged(self):
        result = _render_value(True, {"name": "test"})
        assert result is True

    def test_none_value_returns_unchanged(self):
        result = _render_value(None, {"name": "test"})
        assert result is None


class TestParseFrontmatter:
    def test_valid_frontmatter_returns_dict_and_body(self):
        content = """---
title: Test
author: User
---
Body content here."""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter == {"title": "Test", "author": "User"}
        assert body == "Body content here."

    def test_no_frontmatter_returns_none_and_full_content(self):
        content = "Just regular content"
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter is None
        assert body == "Just regular content"

    def test_unclosed_frontmatter_returns_none_and_full_content(self):
        content = """---
title: Test
author: User
Body without closing"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter is None
        assert body == content

    def test_invalid_yaml_returns_none_and_full_content(self):
        content = """---
title: [invalid yaml
---
Body content"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter is None
        assert body == content

    def test_non_dict_yaml_returns_none_and_full_content(self):
        content = """---
- item1
- item2
---
Body content"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter is None
        assert body == content

    def test_empty_frontmatter_returns_none(self):
        content = """---
---
Body content"""
        frontmatter, body = parse_frontmatter(content)
        assert frontmatter is None
        assert body == content

    def test_with_context_renders_string_values(self):
        content = """---
title: Hello {{ name }}
---
Body"""
        frontmatter, body = parse_frontmatter(content, context={"name": "World"})
        assert frontmatter == {"title": "Hello World"}
        assert body == "Body"

    def test_with_context_renders_list_items(self):
        content = """---
items:
  - "{{ item1 }}"
  - "{{ item2 }}"
  - static
---
Body"""
        frontmatter, _body = parse_frontmatter(
            content, context={"item1": "first", "item2": "second"}
        )
        assert frontmatter == {"items": ["first", "second", "static"]}

    def test_with_context_renders_dict_keys(self):
        content = """---
"{{ dynamic_key }}": value
---
Body"""
        frontmatter, _body = parse_frontmatter(content, context={"dynamic_key": "key"})
        assert frontmatter == {"key": "value"}

    def test_with_context_renders_nested_values(self):
        content = """---
outer:
  inner: "{{ value }}"
---
Body"""
        frontmatter, _body = parse_frontmatter(content, context={"value": "nested"})
        assert frontmatter == {"outer": {"inner": "nested"}}

    def test_with_none_context_skips_rendering(self):
        content = """---
title: Hello {{ name }}
---
Body"""
        frontmatter, _body = parse_frontmatter(content, context=None)
        assert frontmatter == {"title": "Hello {{ name }}"}

    def test_with_empty_context_skips_rendering(self):
        content = """---
title: Hello {{ name }}
---
Body"""
        frontmatter, _body = parse_frontmatter(content, context={})
        assert frontmatter == {"title": "Hello {{ name }}"}


class TestLoadFrontmatterFile:
    def test_loads_and_parses_file(self, fs: FakeFilesystem) -> None:
        content = """---
title: Test File
---
File body content."""
        test_file = Path("/test/test.md")
        fs.create_file(test_file, contents=content)
        frontmatter, body = load_frontmatter_file(test_file)
        assert frontmatter == {"title": "Test File"}
        assert body == "File body content."

    def test_with_context_renders_templates(self, fs: FakeFilesystem) -> None:
        content = """---
greeting: Hello {{ name }}
---
Body"""
        test_file = Path("/test/test.md")
        fs.create_file(test_file, contents=content)
        frontmatter, _body = load_frontmatter_file(test_file, context={"name": "World"})
        assert frontmatter == {"greeting": "Hello World"}

    def test_without_context_preserves_placeholders(self, fs: FakeFilesystem) -> None:
        content = """---
greeting: Hello {{ name }}
---
Body"""
        test_file = Path("/test/test.md")
        fs.create_file(test_file, contents=content)
        frontmatter, _body = load_frontmatter_file(test_file)
        assert frontmatter == {"greeting": "Hello {{ name }}"}

    def test_file_without_frontmatter_returns_none(self, fs: FakeFilesystem) -> None:
        test_file = Path("/test/test.md")
        fs.create_file(test_file, contents="Just content")
        frontmatter, body = load_frontmatter_file(test_file)
        assert frontmatter is None
        assert body == "Just content"
