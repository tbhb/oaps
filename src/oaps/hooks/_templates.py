"""Template rendering for hook action messages.

This module provides template substitution for permission action messages,
supporting ${variable} and ${tool_input.field} syntax.
"""

import re
from typing import TYPE_CHECKING

from ._expression import adapt_context

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext


# Pattern for ${variable} or ${variable.field} syntax
_TEMPLATE_PATTERN = re.compile(
    r"\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\}"
)


def _resolve_path(context_dict: dict[str, object], path: str) -> str:
    """Resolve a dotted path against the context dictionary.

    Args:
        context_dict: The context dictionary from adapt_context.
        path: A variable path like "tool_name" or "tool_input.command".

    Returns:
        The string value at the path, or empty string if not found.
    """
    parts = path.split(".", 1)
    key = parts[0]

    value = context_dict.get(key)
    if value is None:
        return ""

    # Single-level access (e.g., "tool_name")
    if len(parts) == 1:
        return str(value)

    # Nested access (e.g., "tool_input.command")
    nested_key = parts[1]

    # Handle dict-like access
    if isinstance(value, dict):
        # Cast to dict[str, object] for proper typing
        value_dict: dict[str, object] = value  # pyright: ignore[reportUnknownVariableType]
        nested_value: object = value_dict.get(nested_key)
        if nested_value is None:
            return ""
        return str(nested_value)

    # Handle attribute access on objects
    nested_attr: object = getattr(value, nested_key, None)
    if nested_attr is None:
        return ""
    return str(nested_attr)


def substitute_template(template: str, context: HookContext) -> str:
    """Substitute template variables with values from the hook context.

    Supports ${variable} and ${tool_input.field} syntax. Unknown variables
    are replaced with empty strings (fail-safe behavior).

    Available variables:
        - hook_type: The type of hook event
        - session_id: The Claude session ID
        - cwd: Current working directory
        - permission_mode: The permission mode
        - tool_name: Name of the tool (for tool hooks)
        - tool_input: Tool input object (access fields with tool_input.field)
        - prompt: User prompt (for UserPromptSubmit)
        - git_branch, git_is_dirty, git_head_commit, git_is_detached: Git context

    Args:
        template: The template string with ${variable} placeholders.
        context: The HookContext providing values.

    Returns:
        The template with all placeholders replaced.
    """
    if not template:
        return ""

    context_dict = adapt_context(context)

    def replacer(match: re.Match[str]) -> str:
        path = match.group(1)
        return _resolve_path(context_dict, path)

    return _TEMPLATE_PATTERN.sub(replacer, template)
