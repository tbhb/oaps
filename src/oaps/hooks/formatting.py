# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""File formatting actions for hook rules.

This module provides Python action entrypoints for hook rules that
auto-format files after edit operations.

Supported formats:
- Python: ruff format and ruff check --fix
- Markdown: markdownlint-cli2 --fix

All functions follow the hook action signature:
    def action_name(context: HookContext) -> dict[str, object] | None

Return values can include:
- "deny": str - Block the operation with message
- "warn": str - Warning message to display
- "inject": str - Content to inject into context
"""

import re
import subprocess
from typing import TYPE_CHECKING

# Pattern to match import statements
_IMPORT_PATTERN = re.compile(r"^\s*(import\s+|from\s+\S+\s+import\s+)")
# Pattern to match empty lines, comments, or string literals (for docstrings)
_IGNORABLE_PATTERN = re.compile(r'^\s*(#.*|""".*"""|\'\'\'.*\'\'\')?$')
# Maximum length for content preview in log messages
_CONTENT_PREVIEW_LENGTH = 100
# Triple-quote delimiters for docstrings
_DOCSTRING_DELIMITERS = ('"""', "'''")

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext


def auto_format_python(context: HookContext) -> dict[str, object] | None:
    """Auto-format a Python file with ruff after modification.

    Runs ruff format followed by ruff check --fix on the modified file.
    Uses fail-open semantics (silent failures, just log).

    Args:
        context: Hook context with tool_input containing file_path.

    Returns:
        None on success, or dict with warning on failure.
    """
    logger = context.hook_logger

    # Get file path from tool input
    tool_input = getattr(context.hook_input, "tool_input", None)
    if not isinstance(tool_input, dict):
        logger.debug("auto_format_python: no tool_input dict available")
        return None

    file_path = tool_input.get("file_path")
    if not file_path or not isinstance(file_path, str):
        logger.debug("auto_format_python: no file_path in tool_input")
        return None

    # Get working directory from context
    cwd = None
    if hasattr(context.hook_input, "cwd") and context.hook_input.cwd:
        cwd = str(context.hook_input.cwd)

    # Run ruff format
    try:
        result = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "format", file_path],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.debug(
                "ruff format returned non-zero",
                file_path=file_path,
                returncode=result.returncode,
                stderr=stderr[:500] if stderr else None,
            )
    except subprocess.TimeoutExpired:
        logger.warning("ruff format timed out", file_path=file_path)
    except FileNotFoundError:
        logger.debug("uv or ruff not found, skipping format")
        return None
    except Exception as e:  # noqa: BLE001
        logger.debug("ruff format failed", file_path=file_path, error=str(e))

    # Run ruff check --fix
    try:
        result = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "check", "--fix", "--unfixable", "401", file_path],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.debug(
                "ruff check --fix returned non-zero",
                file_path=file_path,
                returncode=result.returncode,
                stderr=stderr[:500] if stderr else None,
            )
    except subprocess.TimeoutExpired:
        logger.warning("ruff check --fix timed out", file_path=file_path)
    except FileNotFoundError:
        logger.debug("uv or ruff not found, skipping check")
        return None
    except Exception as e:  # noqa: BLE001
        logger.debug("ruff check --fix failed", file_path=file_path, error=str(e))

    logger.debug("auto_format_python completed", file_path=file_path)
    return None


def _is_import_only_content(content: str) -> bool:
    """Check if content contains only imports (no actual code).

    Args:
        content: Python source code to check.

    Returns:
        True if content only contains imports, comments, and whitespace.
    """
    lines = content.splitlines()
    has_imports = False
    in_multiline_string = False
    multiline_delim = None

    for line in lines:
        stripped = line.strip()

        # Handle multiline strings (docstrings)
        if in_multiline_string:
            if multiline_delim and multiline_delim in line:
                in_multiline_string = False
                multiline_delim = None
            continue

        # Check for start of multiline string
        if stripped.startswith(_DOCSTRING_DELIMITERS):
            delim = stripped[:3]
            # Check if it closes on the same line
            if stripped.count(delim) == 1:
                in_multiline_string = True
                multiline_delim = delim
            continue

        # Skip empty lines and single-line comments
        if not stripped or stripped.startswith("#"):
            continue

        # Check if this is an import statement
        if _IMPORT_PATTERN.match(line):
            has_imports = True
            continue

        # Any other non-empty line means there's actual code
        return False

    # Only block if there ARE imports (don't block empty files)
    return has_imports


def block_import_only_writes(context: HookContext) -> dict[str, object] | None:
    """Block Write/Edit operations that only contain import statements.

    This prevents the common pattern where Claude writes imports first,
    then Ruff removes them as unused before the actual code is written.

    Args:
        context: Hook context with tool_input containing content/new_string.

    Returns:
        Dict with "deny" key if content is import-only, None otherwise.
    """
    logger = context.hook_logger

    tool_input = getattr(context.hook_input, "tool_input", None)
    if not isinstance(tool_input, dict):
        logger.debug("block_import_only_writes: no tool_input dict available")
        return None

    # Get content based on tool type
    tool_name = getattr(context.hook_input, "tool_name", None)
    content: str | None = None

    if tool_name == "Write":
        content = tool_input.get("content")
    elif tool_name == "Edit":
        content = tool_input.get("new_string")

    if not content or not isinstance(content, str):
        logger.debug("block_import_only_writes: no content to check")
        return None

    if _is_import_only_content(content):
        preview_len = _CONTENT_PREVIEW_LENGTH
        logger.debug(
            "block_import_only_writes: blocking import-only content",
            tool_name=tool_name,
            content_preview=content[:preview_len]
            if len(content) > preview_len
            else content,
        )
        return {
            "deny": (
                "Write imports together with the code that uses them. "
                "Ruff will remove unused imports."
            )
        }

    return None


def auto_format_markdown(context: HookContext) -> dict[str, object] | None:
    """Auto-format a markdown file with markdownlint-cli2 after modification.

    Runs markdownlint-cli2 --fix on the file. Uses fail-open semantics.

    Args:
        context: Hook context with tool_input containing file_path.

    Returns:
        None on success, or dict with warning on failure.
    """
    logger = context.hook_logger

    tool_input = getattr(context.hook_input, "tool_input", None)
    if not isinstance(tool_input, dict):
        logger.debug("auto_format_markdown: no tool_input dict available")
        return None

    file_path = tool_input.get("file_path")
    if not file_path or not isinstance(file_path, str):
        logger.debug("auto_format_markdown: no file_path in tool_input")
        return None

    # Get working directory from context
    cwd = None
    if hasattr(context.hook_input, "cwd") and context.hook_input.cwd:
        cwd = str(context.hook_input.cwd)

    # Run markdownlint-cli2 --fix (modifies file in place)
    try:
        result = subprocess.run(  # noqa: S603
            ["pnpm", "exec", "markdownlint-cli2", "--fix", file_path],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            timeout=30,
            check=False,
        )
        # markdownlint-cli2 returns non-zero if there are unfixable issues
        # This is expected, so only log at debug level
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.debug(
                "markdownlint-cli2 returned non-zero",
                file_path=file_path,
                returncode=result.returncode,
                stderr=stderr[:500] if stderr else None,
            )
    except subprocess.TimeoutExpired:
        logger.warning("markdownlint-cli2 timed out", file_path=file_path)
    except FileNotFoundError:
        logger.debug("pnpm or markdownlint-cli2 not found, skipping format")
        return None
    except Exception as e:  # noqa: BLE001
        logger.debug("markdownlint-cli2 failed", file_path=file_path, error=str(e))

    logger.debug("auto_format_markdown completed", file_path=file_path)
    return None
