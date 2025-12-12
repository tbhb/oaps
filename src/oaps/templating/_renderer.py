"""Template rendering engine."""

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from jinja2 import Environment


def render_template(
    template_path: Path,
    context: BaseModel | Mapping[str, object],
    *,
    env: Environment | None = None,
    strip_frontmatter: bool = True,
) -> str:
    """Render a Jinja2 template file with context.

    Args:
        template_path: Path to the template file.
        context: Pydantic model or dict for template variables.
        env: Optional Jinja2 Environment. If not provided, creates a simple
            environment with the template's parent directory in the search path.
        strip_frontmatter: If True (default), strips YAML frontmatter before
            rendering. Set to False if the template has no frontmatter.

    Returns:
        Rendered template content.

    Raises:
        FileNotFoundError: If template file does not exist.
    """
    from jinja2 import Template  # noqa: PLC0415

    from ._frontmatter import parse_frontmatter  # noqa: PLC0415

    # Convert Pydantic model to dict if needed
    if isinstance(context, BaseModel):
        context_dict = context.model_dump()
    else:
        context_dict = dict(context)

    # Read the template content
    content = template_path.read_text(encoding="utf-8")

    # Strip frontmatter if requested
    if strip_frontmatter:
        _, body = parse_frontmatter(content)
    else:
        body = content

    # Render using provided environment or a standalone Template
    template = env.from_string(body) if env is not None else Template(body)

    return cast("str", template.render(context_dict))


def render_template_string(
    template_str: str,
    context: BaseModel | Mapping[str, object],
    *,
    env: Environment | None = None,
) -> str:
    """Render a Jinja2 template string with context.

    Lower-level API for rendering inline templates without file lookup.

    Args:
        template_str: The Jinja2 template string.
        context: Pydantic model or dict for template variables.
        env: Optional Jinja2 Environment. If not provided, creates a standalone
            Template instance.

    Returns:
        Rendered string.
    """
    from jinja2 import Template  # noqa: PLC0415

    # Convert Pydantic model to dict if needed
    if isinstance(context, BaseModel):
        context_dict = context.model_dump()
    else:
        context_dict = dict(context)

    if env is not None:
        template = env.from_string(template_str)
    else:
        template = Template(template_str)  # pyright: ignore[reportAny]

    return cast("str", template.render(context_dict))


def render_braces_template(
    template_str: str,
    context: Mapping[str, object],
) -> str:
    """Render a brace-style template using str.format_map.

    For simple {key} placeholder substitution without Jinja2 features.

    Args:
        template_str: Template string with {key} placeholders.
        context: Mapping of values for template rendering.

    Returns:
        Rendered string.

    Example:
        result = render_braces_template("Hello {name}!", {"name": "World"})
        # Returns: "Hello World!"
    """
    return template_str.format_map(context)
