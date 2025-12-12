r"""OAPS Templating System.

A flexible template rendering system with multi-location search paths,
context composition, and Jinja2-based rendering.

Basic usage:
    from oaps.templating import build_search_paths, create_environment, render_template

    # Build search paths for a flow's templates
    paths = build_search_paths(
        patterns=[
            "{base}/overrides/flows/{namespace}/_templates",
            "{base}/flows/{namespace}/_templates",
        ],
        variables={"namespace": "dev"},
    )

    # Create a Jinja2 environment
    env = create_environment(paths)

    # Render a template
    result = render_template(
        template_path=paths.paths[0] / "greeting.j2",
        context={"name": "World"},
        env=env,
    )

With context composition:
    from oaps.templating import (
        BaseContext,
        get_base_context,
        compose_context,
        render_template_string,
    )

    # Get auto-detected base context
    base = get_base_context()

    # Compose with component and user context
    context = compose_context(
        base={"today": base.today, "author_name": base.author_name},
        component={"title": "My Feature"},
        user={"version": "2.0.0"},
    )

    # Render inline template
    result = render_template_string(
        "# {{ title }} ({{ version }})\nBy {{ author_name }}",
        context,
    )
"""

from ._context import BaseContext, compose_context, get_base_context
from ._discovery import (
    TemplateInfo,
    discover_skill_templates,
    find_skill_template,
)
from ._environment import EnvironmentConfig, create_environment
from ._frontmatter import (
    YAMLFrontmatter,
    YAMLValue,
    load_frontmatter_file,
    parse_frontmatter,
)
from ._models import BaseTemplateContext, SpecContext
from ._paths import BasePathConfig, TemplateSearchPaths, build_search_paths
from ._renderer import render_braces_template, render_template, render_template_string

__all__ = [
    "BaseContext",
    "BasePathConfig",
    "BaseTemplateContext",
    "EnvironmentConfig",
    "SpecContext",
    "TemplateInfo",
    "TemplateSearchPaths",
    "YAMLFrontmatter",
    "YAMLValue",
    "build_search_paths",
    "compose_context",
    "create_environment",
    "discover_skill_templates",
    "find_skill_template",
    "get_base_context",
    "load_frontmatter_file",
    "parse_frontmatter",
    "render_braces_template",
    "render_template",
    "render_template_string",
]
