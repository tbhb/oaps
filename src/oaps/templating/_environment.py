"""Jinja2 Environment factory."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from jinja2 import Environment

    from ._paths import TemplateSearchPaths


@dataclass(slots=True, frozen=True)
class EnvironmentConfig:
    """Configuration for Jinja2 Environment.

    Attributes:
        autoescape: Enable autoescaping (default: False for markdown/text templates).
        trim_blocks: Remove first newline after a block tag.
        lstrip_blocks: Strip leading whitespace before block tags.
        keep_trailing_newline: Preserve trailing newline in templates.
    """

    autoescape: bool = False
    trim_blocks: bool = False
    lstrip_blocks: bool = False
    keep_trailing_newline: bool = True


def create_environment(
    search_paths: tuple[Path, ...] | TemplateSearchPaths,
    *,
    config: EnvironmentConfig | None = None,
) -> Environment:
    """Create a Jinja2 Environment with FileSystemLoader.

    The environment is configured for text/markdown templates by default,
    with no autoescaping and trailing newline preservation.

    Note: autoescape is disabled by default as this templating system is designed
    for markdown/text templates, not HTML. If you need XSS protection for HTML
    output, set autoescape=True in the config.

    Args:
        search_paths: Template search paths. Can be a tuple of Paths or
            a TemplateSearchPaths instance.
        config: Optional environment configuration. If None, uses defaults.

    Returns:
        Configured Jinja2 Environment.

    Example:
        from oaps.templating import build_search_paths, create_environment

        paths = build_search_paths(
            patterns=["{base}/templates"],
            variables={},
        )
        env = create_environment(paths)
        template = env.get_template("greeting.j2")
        result = template.render(name="World")
    """
    from jinja2 import Environment, FileSystemLoader  # noqa: PLC0415

    from ._paths import TemplateSearchPaths  # noqa: PLC0415

    # Extract paths tuple if TemplateSearchPaths
    if isinstance(search_paths, TemplateSearchPaths):
        paths = search_paths.paths
    else:
        paths = search_paths

    # Convert paths to strings for FileSystemLoader
    path_strs = [str(p) for p in paths]

    # Use default config if none provided
    if config is None:
        config = EnvironmentConfig()

    # Create the environment
    # Note: autoescape is intentionally disabled for markdown/text templates
    loader = FileSystemLoader(path_strs)
    env: Environment = Environment(
        loader=loader,
        autoescape=config.autoescape,  # noqa: S701
        trim_blocks=config.trim_blocks,
        lstrip_blocks=config.lstrip_blocks,
        keep_trailing_newline=config.keep_trailing_newline,
    )

    return env
