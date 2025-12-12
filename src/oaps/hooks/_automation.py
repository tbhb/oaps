"""Shared infrastructure for automation actions (script, python).

This module provides common utilities for executing external code
via subprocess (script) or in-process (python) with proper timeout
handling, output limiting, and result processing.

Note: This module is designed to be imported by _action.py. It avoids importing
from _action.py to prevent import cycles. The OutputAccumulator protocol is
defined inline to avoid the cycle.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from oaps.exceptions import BlockHook

from ._context import (
    is_permission_request_context,
    is_post_tool_use_context,
    is_pre_compact_context,
    is_pre_tool_use_context,
    is_session_start_context,
    is_user_prompt_submit_context,
)

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from oaps.hooks._context import HookContext


class _OutputAccumulatorProtocol(Protocol):
    """Protocol for output accumulator to avoid import cycle."""

    def set_deny(self, reason: str | None = None) -> None:
        """Set the permission decision to deny."""
        ...

    def set_allow(self) -> None:
        """Set the permission decision to allow."""
        ...

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        ...

    def add_context(self, content: str) -> None:
        """Add context content."""
        ...


# Default timeout in milliseconds
DEFAULT_TIMEOUT_MS: int = 10000  # 10 seconds

# Maximum output size in bytes (fallback when token counting unavailable)
MAX_OUTPUT_BYTES: int = 102400  # 100KB


@dataclass(frozen=True, slots=True)
class AutomationResult:
    """Result from an automation action execution.

    Captures the raw execution outcome before accumulator processing.

    Attributes:
        success: Whether the action executed without errors.
        output: Standard output from the action, if any.
        error: Error message if the action failed, None otherwise.
        return_value: Parsed JSON return value from stdout, if any.
    """

    success: bool
    output: str | None = None
    error: str | None = None
    return_value: dict[str, object] | None = None


def serialize_context(context: HookContext) -> str:
    """Serialize HookContext to JSON for stdin piping.

    Extends adapt_context() with full hook_input serialization.

    Args:
        context: The HookContext to serialize.

    Returns:
        JSON string containing context data suitable for stdin.
    """
    from ._expression import adapt_context  # noqa: PLC0415

    # Start with the base context from adapt_context
    base_context = adapt_context(context)

    # Add full hook_input via model_dump
    hook_input_data = context.hook_input.model_dump(mode="json")

    # Add OAPS-specific paths
    result: dict[str, object] = {
        **base_context,
        "hook_input": hook_input_data,
        "oaps_dir": str(context.oaps_dir),
        "oaps_state_file": str(context.oaps_state_file),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }

    # Prefer orjson if available for performance, fallback to stdlib json
    try:
        import orjson  # noqa: PLC0415

        return orjson.dumps(result).decode("utf-8")
    except ImportError:
        import json  # noqa: PLC0415

        return json.dumps(result)


def truncate_output(output: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncate output to max bytes, preserving valid UTF-8.

    Args:
        output: The string to truncate.
        max_bytes: Maximum size in bytes.

    Returns:
        Truncated string with indicator if truncated.
    """
    if not output:
        return output

    encoded = output.encode("utf-8")
    if len(encoded) <= max_bytes:
        return output

    # Truncate at byte boundary, then decode safely
    truncated_bytes = encoded[:max_bytes]

    # Decode with error handling to avoid breaking UTF-8 sequences
    # Use 'ignore' to skip incomplete multi-byte sequences at the end
    truncated = truncated_bytes.decode("utf-8", errors="ignore")

    return truncated + "\n... [output truncated]"


def supports_injection(context: HookContext) -> bool:
    """Check if the hook context supports context injection.

    Args:
        context: The hook context to check.

    Returns:
        True if the hook type supports additionalContext injection.
    """
    return (
        is_session_start_context(context)
        or is_post_tool_use_context(context)
        or is_pre_compact_context(context)
        or is_user_prompt_submit_context(context)
    )


def supports_modification(context: HookContext) -> bool:
    """Check if the hook context supports input modification.

    Args:
        context: The hook context to check.

    Returns:
        True if the hook type supports updatedInput modification.
    """
    return is_pre_tool_use_context(context) or is_permission_request_context(context)


def process_return_value(
    return_value: dict[str, object] | None,
    context: HookContext,
    accumulator: _OutputAccumulatorProtocol,
    logger: FilteringBoundLogger,
) -> None:
    """Process automation return value into accumulator modifications.

    Handles return value keys:
    - inject: str -> accumulator.add_context() for supported hooks
    - warn: str -> accumulator.add_warning()
    - deny: str | True -> accumulator.set_deny(), raise BlockHook
    - allow: True -> accumulator.set_allow()

    Args:
        return_value: The parsed return value from automation action.
        context: The hook context.
        accumulator: The output accumulator to modify.
        logger: Logger for warnings.

    Raises:
        BlockHook: If the return value contains a deny directive.
    """
    if return_value is None:
        return

    # Check for conflicting allow/deny directives
    if return_value.get("allow") is True and return_value.get("deny") is not None:
        logger.warning(
            "Automation action returned both allow and deny; deny takes precedence"
        )

    # Handle inject directive
    inject_value = return_value.get("inject")
    if inject_value is not None and isinstance(inject_value, str) and inject_value:
        if supports_injection(context):
            accumulator.add_context(inject_value)
        else:
            logger.warning(
                "Automation action: inject not supported for this hook type",
                hook_event_type=str(context.hook_event_type),
            )

    # Handle warn directive
    warn_value = return_value.get("warn")
    if warn_value is not None and isinstance(warn_value, str) and warn_value:
        accumulator.add_warning(warn_value)

    # Handle allow directive (must check before deny since deny raises)
    allow_value = return_value.get("allow")
    if allow_value is True:
        accumulator.set_allow()

    # Handle deny directive (raises BlockHook)
    deny_value = return_value.get("deny")
    if deny_value is not None:
        if deny_value is True:
            accumulator.set_deny()
            default_deny_msg = "Operation denied by automation action"
            raise BlockHook(default_deny_msg)
        if isinstance(deny_value, str) and deny_value:
            accumulator.set_deny(deny_value)
            raise BlockHook(deny_value)
