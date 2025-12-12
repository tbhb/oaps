"""Generic frontmatter parsing utilities for markdown files."""

from typing import TYPE_CHECKING, cast

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# Type aliases for YAML frontmatter data
type YAMLPrimitive = str | int | float | bool | None
type YAMLKey = str | int | float | bool
type YAMLValue = YAMLPrimitive | list[YAMLValue] | dict[YAMLKey, YAMLValue]
type YAMLFrontmatter = dict[str, YAMLValue]


def _render_jinja_string(template_str: str, context: dict[str, object]) -> str:
    """Render a Jinja2 template string.

    Args:
        template_str: Jinja2 template string.
        context: Mapping of values for template rendering.

    Returns:
        Rendered string.
    """
    from jinja2 import Template  # noqa: PLC0415

    template = Template(template_str)  # pyright: ignore[reportAny]
    return cast("str", template.render(context))  # pyright: ignore[reportAny]


def _render_key(key: YAMLKey, context: Mapping[str, object]) -> YAMLKey:
    """Render template placeholders in a dict key if it's a string."""
    if isinstance(key, str):
        return _render_jinja_string(key, dict(context))
    return key


def _render_value(value: YAMLValue, context: Mapping[str, object]) -> YAMLValue:
    """Recursively render template placeholders in a value.

    Args:
        value: The value to render (str, list, dict, or other).
        context: Dictionary of values to substitute.

    Returns:
        The value with all string templates rendered. Dict entries with empty
        string keys after rendering are removed.
    """
    if isinstance(value, str):
        return _render_jinja_string(value, dict(context))
    if isinstance(value, list):
        return [_render_value(item, context) for item in value]
    if isinstance(value, dict):
        result: dict[YAMLKey, YAMLValue] = {}
        for k, v in value.items():
            rendered_key = _render_key(k, context)
            # Skip entries where the key renders to an empty string
            if rendered_key == "":
                continue
            result[rendered_key] = _render_value(v, context)
        return result
    return value


def parse_frontmatter(
    content: str,
    context: Mapping[str, object] | None = None,
) -> tuple[YAMLFrontmatter | None, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The full markdown content including frontmatter.
        context: Optional dictionary of values to substitute in template placeholders.
            If None or empty, no template rendering is performed.

    Returns:
        A tuple of (frontmatter dict or None, body content).
        Returns None for frontmatter if no valid frontmatter block is found.
    """
    if not content.startswith("---"):
        return None, content

    # Find the closing ---
    end_marker = content.find("---", 3)
    if end_marker == -1:
        return None, content

    frontmatter_str = content[3:end_marker].strip()
    body = content[end_marker + 3 :].strip()

    try:
        frontmatter_data = yaml.safe_load(frontmatter_str)  # pyright: ignore[reportAny]
    except yaml.YAMLError:
        return None, content

    if not isinstance(frontmatter_data, dict):
        return None, content

    # Cast after validation - yaml.safe_load produces string keys at top level
    frontmatter: YAMLFrontmatter = cast("YAMLFrontmatter", frontmatter_data)

    if context:
        # Cast to YAMLValue for _render_value (dict invariance requires this)
        rendered = _render_value(cast("YAMLValue", frontmatter), context)
        # _render_value preserves dict structure
        frontmatter = cast("YAMLFrontmatter", rendered)

    return frontmatter, body


def load_frontmatter_file(
    path: Path,
    context: Mapping[str, object] | None = None,
) -> tuple[YAMLFrontmatter | None, str]:
    """Load and parse a markdown file's frontmatter.

    Args:
        path: Path to the markdown file.
        context: Optional dictionary of values to substitute in template placeholders.
            If None or empty, no template rendering is performed.

    Returns:
        A tuple of (frontmatter dict or None, body content).
    """
    content = path.read_text(encoding="utf-8")
    return parse_frontmatter(content, context)
