"""Action implementations for hook rules.

This module provides action handlers for different hook rule action types,
including basic actions (python, shell), permission actions (deny, allow, warn),
and feedback actions (log, suggest, inject).
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

from oaps.exceptions import BlockHook

from ._context import (
    is_permission_request_context,
    is_pre_tool_use_context,
)
from ._outputs import PermissionRequestDecision
from ._templates import substitute_template

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from oaps.config import HookRuleActionConfiguration
    from oaps.hooks._context import HookContext


# Note: OutputAccumulator is defined here to avoid circular imports with _executor.py
@dataclass(slots=True)
class OutputAccumulator:
    """Mutable accumulator for action outputs.

    Tracks permission decisions, warning messages, and injected context
    during action execution. Used by permission and feedback actions
    to communicate results back to the executor.

    Attributes:
        permission_decision: The permission decision for PreToolUse hooks.
        permission_decision_reason: Human-readable reason for the decision.
        permission_request_decision: Full decision for PermissionRequest hooks.
        system_messages: List of warning/suggestion messages to display.
        additional_context_items: List of context items to inject into output.
        updated_input: Modified tool input for PreToolUse/PermissionRequest hooks.
    """

    permission_decision: Literal["deny", "allow", "ask"] | None = None
    permission_decision_reason: str | None = None
    permission_request_decision: PermissionRequestDecision | None = None
    system_messages: list[str] = field(default_factory=list)
    additional_context_items: list[str] = field(default_factory=list)
    updated_input: dict[str, object] | None = None

    def set_deny(self, reason: str | None = None) -> None:
        """Set the permission decision to deny.

        Args:
            reason: Optional human-readable reason for denial.
        """
        self.permission_decision = "deny"
        if reason:
            self.permission_decision_reason = reason

    def set_allow(self) -> None:
        """Set the permission decision to allow."""
        self.permission_decision = "allow"

    def add_warning(self, message: str) -> None:
        """Add a warning message to the system messages.

        Args:
            message: The warning message to add.
        """
        self.system_messages.append(message)

    def add_context(self, content: str) -> None:
        """Add context content to the additional context items.

        Args:
            content: The context content to add.
        """
        self.additional_context_items.append(content)

    def set_updated_input(self, updates: dict[str, object]) -> None:
        """Merge updates into the updated_input dictionary.

        Args:
            updates: Field modifications to merge into updated_input.
        """
        if self.updated_input is None:
            self.updated_input = {}
        self.updated_input.update(updates)


class Action(Protocol):
    """Protocol for basic hook actions."""

    def run(self, context: HookContext, config: HookRuleActionConfiguration) -> None:
        """Execute the action.

        Args:
            context: The hook context.
            config: The action configuration.
        """
        ...


class PermissionAction(Protocol):
    """Protocol for permission-related hook actions.

    Permission actions receive an OutputAccumulator to record decisions
    and may raise BlockHook to stop further processing.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the permission action.

        Args:
            context: The hook context.
            config: The action configuration.
            accumulator: The output accumulator for recording decisions.

        Raises:
            BlockHook: If the action should block further processing.
        """
        ...


class NoOpAction:
    """Action that does nothing."""

    def run(
        self,
        context: HookContext,  # pyright: ignore[reportUnusedParameter]
        config: HookRuleActionConfiguration,  # pyright: ignore[reportUnusedParameter]
    ) -> None:
        """Execute a no-op action (does nothing)."""


class LogAction:
    """Action that logs structured entries using the hook logger.

    Writes log entries at the configured level (debug, info, warning, error)
    with template-substituted messages. Non-blocking.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the log action.

        Args:
            context: The hook context containing the logger.
            config: The action configuration with level and message.
            accumulator: The output accumulator (not modified by this action).
        """
        del accumulator  # Explicitly mark as unused
        # Render the message template
        message = ""
        if config.message:
            message = substitute_template(config.message, context)

        if not message:
            return

        # Get log level, defaulting to info for invalid/missing values
        level = config.level or "info"
        logger = context.hook_logger

        # Dispatch to appropriate log method
        if level == "debug":
            logger.debug(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            # Default to info for "info" and any unrecognized level
            logger.info(message)


class ScriptAction:
    """Action that executes a shell script.

    Supports both `command` (single line) and `script` (multi-line) fields.
    Passes HookContext as JSON to stdin when stdin="json".
    """

    def _process_output(
        self,
        config: HookRuleActionConfiguration,
        stdout: str,
        stderr: str,
        logger: FilteringBoundLogger,
    ) -> str:
        """Process and handle stdout/stderr based on config."""
        from oaps.utils import truncate_output  # noqa: PLC0415

        if config.stderr == "append_to_stdout" and stderr:
            stdout = stdout + "\n" + stderr if stdout else stderr
        elif config.stderr == "log" and stderr:
            logger.warning("ScriptAction stderr", stderr=truncate_output(stderr))

        stdout = truncate_output(stdout)

        if config.stdout == "log" and stdout:
            logger.info("ScriptAction stdout", stdout=stdout)

        return stdout

    def _parse_json_return_value(self, stdout: str) -> dict[str, object] | None:
        """Parse stdout as JSON return value if possible."""
        import orjson  # noqa: PLC0415

        if not stdout.strip():
            return None

        try:
            parsed = orjson.loads(stdout)  # pyright: ignore[reportAny]
            if isinstance(parsed, dict):
                return dict(parsed)  # pyright: ignore[reportUnknownArgumentType]
        except orjson.JSONDecodeError:
            pass
        return None

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the script action."""
        from oaps.utils import ScriptConfig, run_script  # noqa: PLC0415

        from ._automation import (  # noqa: PLC0415
            DEFAULT_TIMEOUT_MS,
            process_return_value,
            serialize_context,
        )

        logger = context.hook_logger

        if not config.command and not config.script:
            logger.debug("ScriptAction: no command or script specified")
            return

        cwd = str(config.cwd) if config.cwd else None
        if not cwd and hasattr(context.hook_input, "cwd") and context.hook_input.cwd:
            cwd = str(context.hook_input.cwd)

        stdin_data = (
            serialize_context(context).encode("utf-8")
            if config.stdin == "json"
            else None
        )

        script_config = ScriptConfig(
            command=config.command,
            script=config.script,
            shell=config.shell,
            cwd=cwd,
            env=config.env,
            stdin=stdin_data,
            timeout_ms=config.timeout_ms or DEFAULT_TIMEOUT_MS,
        )

        result = run_script(script_config)

        if result.timed_out:
            logger.warning(
                "ScriptAction: command timed out",
                timeout=script_config.timeout_ms / 1000.0,
            )
            return

        if result.command_not_found:
            logger.warning("ScriptAction: command not found", error=result.error)
            return

        if not result.success:
            logger.warning("ScriptAction: execution failed", error=result.error)
            return

        stdout = self._process_output(config, result.stdout, result.stderr, logger)

        return_value = self._parse_json_return_value(stdout)
        process_return_value(return_value, context, accumulator, logger)


class PythonAction:
    """Action that executes a Python function in-process.

    Uses dynamic import via importlib. Function signature:
    def hook_function(context: HookContext, **kwargs) -> dict | None
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the python action.

        Args:
            context: The hook context.
            config: The action configuration.
            accumulator: The output accumulator for recording decisions.
        """
        from oaps.utils import PythonConfig, PythonResult, run_python  # noqa: PLC0415

        from ._automation import (  # noqa: PLC0415
            DEFAULT_TIMEOUT_MS,
            process_return_value,
        )

        logger = context.hook_logger

        entrypoint = config.entrypoint
        if not entrypoint:
            logger.debug("PythonAction: no entrypoint specified")
            return

        python_config = PythonConfig(
            entrypoint=entrypoint,
            timeout_ms=config.timeout_ms or DEFAULT_TIMEOUT_MS,
        )

        # BlockHook should propagate - it's used for control flow
        result: PythonResult[dict[str, object]] = run_python(
            python_config, context, reraise=(BlockHook,)
        )

        if not result.success:
            # Map error types to appropriate log messages
            if result.error_type == "invalid_entrypoint":
                logger.warning(
                    "PythonAction: invalid entrypoint format",
                    entrypoint=entrypoint,
                )
            elif result.error_type == "import_error":
                logger.warning(
                    "PythonAction: failed to import module",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            elif result.error_type == "not_found":
                logger.warning(
                    "PythonAction: function not found in module",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            elif result.error_type == "not_callable":
                logger.warning(
                    "PythonAction: entrypoint is not callable",
                    entrypoint=entrypoint,
                )
            elif result.error_type == "timeout":
                timeout_seconds = python_config.timeout_ms / 1000.0
                logger.warning(
                    "PythonAction: function timed out",
                    entrypoint=entrypoint,
                    timeout_seconds=timeout_seconds,
                )
            elif result.error_type == "execution_error":
                logger.warning(
                    "PythonAction: execution failed",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            # Fail-open: continue without blocking
            return

        # Process return value if it's a dict
        return_value: dict[str, object] | None = None
        if isinstance(result.result, dict):
            return_value = dict(result.result)

        process_return_value(return_value, context, accumulator, logger)


class DenyAction:
    """Action that denies permission for the hook operation.

    For PreToolUse: Sets permission_decision="deny" and raises BlockHook.
    For PermissionRequest: Sets permission_request_decision with deny behavior
        and raises BlockHook.
    For other hooks: Raises BlockHook with the rendered message.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the deny action.

        Args:
            context: The hook context.
            config: The action configuration containing message template.
            accumulator: The output accumulator for recording decisions.

        Raises:
            BlockHook: Always raised to stop further processing.
        """
        # Render the message template
        message = ""
        if config.message:
            message = substitute_template(config.message, context)

        if is_pre_tool_use_context(context):
            # For PreToolUse: set permission decision and raise BlockHook
            accumulator.set_deny(message or None)
            raise BlockHook(message or "Operation denied by hook rule")

        if is_permission_request_context(context):
            # For PermissionRequest: set decision with behavior="deny"
            accumulator.permission_request_decision = PermissionRequestDecision(
                behavior="deny",
                message=message or None,
                interrupt=config.interrupt,
            )
            raise BlockHook(message or "Permission request denied by hook rule")

        # For other hooks (UserPromptSubmit, etc.): just raise BlockHook
        raise BlockHook(message or "Operation blocked by hook rule")


class AllowAction:
    """Action that explicitly allows permission for the hook operation.

    For PreToolUse: Sets permission_decision="allow".
    For PermissionRequest: Sets permission_request_decision with allow behavior.
    For other hooks: No-op (returns without action).
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the allow action.

        Args:
            context: The hook context.
            config: The action configuration (message ignored for allow).
            accumulator: The output accumulator for recording decisions.
        """
        del config  # Explicitly mark as unused
        if is_pre_tool_use_context(context):
            # For PreToolUse: set permission decision to allow
            accumulator.set_allow()
            return

        if is_permission_request_context(context):
            # For PermissionRequest: set decision with behavior="allow"
            accumulator.permission_request_decision = PermissionRequestDecision(
                behavior="allow",
                message=None,
            )
            return

        # For other hooks: no-op
        return


class WarnAction:
    """Action that adds a warning message without blocking.

    For all hooks: Adds the rendered message to system_messages in the
    accumulator. Does NOT block execution or set permission decisions.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the warn action.

        Args:
            context: The hook context.
            config: The action configuration containing message template.
            accumulator: The output accumulator for recording warnings.
        """
        # Render the message template
        message = ""
        if config.message:
            message = substitute_template(config.message, context)

        if message:
            accumulator.add_warning(message)


class SuggestAction:
    """Action that provides a suggestion message to Claude.

    For hooks that support context injection (UserPromptSubmit, SessionStart,
    PostToolUse, PreCompact): Adds the rendered message to additionalContext
    so it is fed to Claude as part of the prompt context.

    For other hooks: Logs a warning since suggestions cannot be delivered.
    Does NOT block execution or set permission decisions.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the suggest action.

        Args:
            context: The hook context.
            config: The action configuration containing message template.
            accumulator: The output accumulator for recording suggestions.
        """
        from ._automation import supports_injection  # noqa: PLC0415

        # Render the message template
        message = ""
        if config.message:
            message = substitute_template(config.message, context)

        if not message:
            return

        # Check if hook type supports injection
        if supports_injection(context):
            accumulator.add_context(message)
        else:
            # Log warning - suggestions not supported for this hook type
            context.hook_logger.warning(
                "SuggestAction: hook type does not support context injection",
                hook_event_type=str(context.hook_event_type),
            )


class InjectAction:
    """Action that injects additional context into hook output.

    Adds content to the additionalContext field for supported hook types:
    SessionStart, PostToolUse, PreCompact, UserPromptSubmit.

    For unsupported hook types, logs a warning and continues (fail-open).
    Does NOT block execution.
    """

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the inject action.

        Args:
            context: The hook context.
            config: The action configuration containing content template.
            accumulator: The output accumulator for recording injected context.
        """
        from ._automation import supports_injection  # noqa: PLC0415

        # Check if hook type supports injection
        if not supports_injection(context):
            context.hook_logger.warning(
                "InjectAction: unsupported hook type for context injection",
                hook_event_type=str(context.hook_event_type),
            )
            return

        # Render the content template (prefer 'content' field, fallback to 'message')
        content = ""
        if config.content:
            content = substitute_template(config.content, context)
        elif config.message:
            # Fallback to message for backwards compatibility
            content = substitute_template(config.message, context)

        if content:
            accumulator.add_context(content)


class ModifyAction:
    """Action that modifies tool input fields.

    Supports operations:
    - set: Replace field value entirely
    - append: Add to end of string field
    - prepend: Add to beginning of string field
    - replace: Regex substitution on string field

    Only valid for PreToolUse and PermissionRequest hooks.
    Logs warning and returns for other hook types (fail-open).
    """

    def _get_nested_value(self, obj: dict[str, object], path: str) -> object | None:
        """Get a value from a nested dict using dot notation.

        Args:
            obj: The dictionary to access.
            path: The dot-separated path (e.g., "command" or "nested.field").

        Returns:
            The value at the path, or None if not found.
        """
        parts = path.split(".")
        current: object = obj
        for part in parts:
            if not isinstance(current, dict):
                return None
            current_dict: dict[str, object] = current
            current = current_dict.get(part)
            if current is None:
                return None
        return current

    def _set_nested_value(
        self, obj: dict[str, object], path: str, value: object
    ) -> None:
        """Set a value in a nested dict using dot notation.

        Args:
            obj: The dictionary to modify.
            path: The dot-separated path (e.g., "command" or "nested.field").
            value: The value to set.
        """
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            next_val = current[part]
            if isinstance(next_val, dict):
                current = next_val  # pyright: ignore[reportUnknownVariableType]
            else:
                # Cannot traverse into non-dict
                return
        current[parts[-1]] = value

    def _apply_operation(  # noqa: PLR0911
        self,
        current: object,
        operation: str,
        value: str,
        pattern: str | None,
        logger: FilteringBoundLogger,
    ) -> object:
        """Apply the specified operation to the current value.

        Args:
            current: The current field value.
            operation: The operation to apply (set, append, prepend, replace).
            value: The value to use for the operation.
            pattern: Regex pattern for replace operation.
            logger: Logger for warnings.

        Returns:
            The new value after applying the operation.
        """
        import re  # noqa: PLC0415

        if operation == "set":
            return value

        if operation == "append":
            if current is None:
                return value
            if not isinstance(current, str):
                logger.warning(
                    "ModifyAction: append requires string field",
                    current_type=type(current).__name__,
                )
                return current
            return current + value

        if operation == "prepend":
            if current is None:
                return value
            if not isinstance(current, str):
                logger.warning(
                    "ModifyAction: prepend requires string field",
                    current_type=type(current).__name__,
                )
                return current
            return value + current

        if operation == "replace":
            if pattern is None:
                logger.warning("ModifyAction: replace requires pattern")
                return current
            if current is None:
                return current
            if not isinstance(current, str):
                logger.warning(
                    "ModifyAction: replace requires string field",
                    current_type=type(current).__name__,
                )
                return current
            try:
                return re.sub(pattern, value, current)
            except re.error as e:
                logger.warning("ModifyAction: invalid regex pattern", error=str(e))
                return current

        logger.warning("ModifyAction: unknown operation", operation=operation)
        return current

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the modify action.

        Args:
            context: The hook context.
            config: The action configuration with field, operation, value, pattern.
            accumulator: The output accumulator for recording modifications.
        """
        from ._automation import supports_modification  # noqa: PLC0415

        logger = context.hook_logger

        # Validate hook type
        if not supports_modification(context):
            logger.warning(
                "ModifyAction: unsupported hook type for input modification",
                hook_event_type=str(context.hook_event_type),
            )
            return

        # Validate required config fields
        if not config.field:
            logger.warning("ModifyAction: no field specified")
            return

        if not config.operation:
            logger.warning("ModifyAction: no operation specified")
            return

        # Get tool_input from context
        tool_input = getattr(context.hook_input, "tool_input", None)
        if not isinstance(tool_input, dict):
            logger.warning("ModifyAction: tool_input is not a dict")
            return

        # Get current value from accumulator if already modified, else from original
        tool_input_typed: dict[str, object] = tool_input
        effective_input = (
            accumulator.updated_input
            if accumulator.updated_input is not None
            else tool_input_typed
        )
        current_value = self._get_nested_value(effective_input, config.field)

        # Render value template
        rendered_value = ""
        if config.value:
            rendered_value = substitute_template(config.value, context)

        # Apply operation
        new_value = self._apply_operation(
            current_value, config.operation, rendered_value, config.pattern, logger
        )

        # Store only the modified field in accumulator (enables composition)
        accumulator.set_updated_input({config.field: new_value})


class TransformAction:
    """Action that transforms tool inputs via script or python code.

    Executes the configured script/python, receives JSON on stdout containing
    field modifications, and merges them into the accumulator's updated_input.

    For PreToolUse: Output merged into hookSpecificOutput.updatedInput
    For PermissionRequest: Output merged into decision.updatedInput

    Fail-open behavior: Invalid JSON or execution errors log warnings but
    do not block the hook.
    """

    def _parse_transform_output(  # noqa: PLR0911
        self, stdout: str, logger: FilteringBoundLogger
    ) -> dict[str, object] | None:
        """Parse stdout as transform JSON, returning None on failure.

        Args:
            stdout: The stdout string to parse.
            logger: Logger for warnings.

        Returns:
            The transform_input dict if valid, None otherwise.
        """
        import json  # noqa: PLC0415

        if not stdout.strip():
            return None

        try:
            parsed = json.loads(stdout)  # pyright: ignore[reportAny]
            if not isinstance(parsed, dict):
                logger.warning("TransformAction: output is not a JSON object")
                return None

            parsed_dict: dict[str, object] = parsed
            transform_input: object = parsed_dict.get("transform_input")
            if transform_input is None:
                # No transform_input key - this is valid, just means no transformation
                return None

            if not isinstance(transform_input, dict):
                logger.warning("TransformAction: transform_input is not a dict")
                return None

            # Validate all keys are strings
            transform_dict: dict[str, object] = transform_input
            if not all(isinstance(k, str) for k in transform_dict):
                logger.warning("TransformAction: transform_input keys must be strings")
                return None

            return dict(transform_dict)
        except json.JSONDecodeError as e:
            logger.warning("TransformAction: invalid JSON output", error=str(e))
            return None

    def run(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
    ) -> None:
        """Execute the transform action.

        Args:
            context: The hook context.
            config: The action configuration with entrypoint or command/script.
            accumulator: The output accumulator for recording modifications.
        """
        from ._automation import supports_modification  # noqa: PLC0415

        logger = context.hook_logger

        # Validate hook type
        if not supports_modification(context):
            logger.warning(
                "TransformAction: unsupported hook type for input modification",
                hook_event_type=str(context.hook_event_type),
            )
            return

        # Determine execution mode
        has_entrypoint = config.entrypoint is not None
        has_script = config.command is not None or config.script is not None

        if not has_entrypoint and not has_script:
            logger.debug("TransformAction: no entrypoint or command/script specified")
            return

        if has_entrypoint and has_script:
            logger.warning(
                "TransformAction: both entrypoint and command/script specified; "
                "using entrypoint"
            )

        if has_entrypoint:
            # Use Python execution
            self._run_python_transform(context, config, accumulator, logger)
        else:
            # Use script execution
            self._run_script_transform(context, config, accumulator, logger)

    def _run_python_transform(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
        logger: FilteringBoundLogger,
    ) -> None:
        """Execute Python transform and process output."""
        from oaps.utils import PythonConfig, PythonResult, run_python  # noqa: PLC0415

        from ._automation import DEFAULT_TIMEOUT_MS  # noqa: PLC0415

        entrypoint = config.entrypoint
        if not entrypoint:
            return

        python_config = PythonConfig(
            entrypoint=entrypoint,
            timeout_ms=config.timeout_ms or DEFAULT_TIMEOUT_MS,
        )

        # BlockHook should propagate - it's used for control flow
        result: PythonResult[dict[str, object]] = run_python(
            python_config, context, reraise=(BlockHook,)
        )

        if not result.success:
            # Map error types to appropriate log messages
            if result.error_type == "invalid_entrypoint":
                logger.warning(
                    "TransformAction: invalid entrypoint format",
                    entrypoint=entrypoint,
                )
            elif result.error_type == "import_error":
                logger.warning(
                    "TransformAction: failed to import module",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            elif result.error_type == "not_found":
                logger.warning(
                    "TransformAction: function not found in module",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            elif result.error_type == "not_callable":
                logger.warning(
                    "TransformAction: entrypoint is not callable",
                    entrypoint=entrypoint,
                )
            elif result.error_type == "timeout":
                timeout_seconds = python_config.timeout_ms / 1000.0
                logger.warning(
                    "TransformAction: function timed out",
                    entrypoint=entrypoint,
                    timeout_seconds=timeout_seconds,
                )
            elif result.error_type == "execution_error":
                logger.warning(
                    "TransformAction: execution failed",
                    entrypoint=entrypoint,
                    error=result.error,
                )
            return

        # Process return value if it's a dict
        if isinstance(result.result, dict):
            # Check for transform_input key
            transform_data: object = result.result.get("transform_input")
            if isinstance(transform_data, dict):
                transform_typed: dict[str, object] = transform_data
                accumulator.set_updated_input(dict(transform_typed))

    def _run_script_transform(
        self,
        context: HookContext,
        config: HookRuleActionConfiguration,
        accumulator: OutputAccumulator,
        logger: FilteringBoundLogger,
    ) -> None:
        """Execute script transform and process output."""
        from oaps.utils import (  # noqa: PLC0415
            ScriptConfig,
            run_script,
            truncate_output,
        )

        from ._automation import (  # noqa: PLC0415
            DEFAULT_TIMEOUT_MS,
            serialize_context,
        )

        cwd = str(config.cwd) if config.cwd else None
        if not cwd and hasattr(context.hook_input, "cwd") and context.hook_input.cwd:
            cwd = str(context.hook_input.cwd)

        # Always provide context JSON on stdin for transform
        stdin_data = serialize_context(context).encode("utf-8")

        script_config = ScriptConfig(
            command=config.command,
            script=config.script,
            shell=config.shell,
            cwd=cwd,
            env=config.env,
            stdin=stdin_data,
            timeout_ms=config.timeout_ms or DEFAULT_TIMEOUT_MS,
        )

        result = run_script(script_config)

        if result.timed_out:
            logger.warning(
                "TransformAction: command timed out",
                timeout=script_config.timeout_ms / 1000.0,
            )
            return

        if result.command_not_found:
            logger.warning("TransformAction: command not found", error=result.error)
            return

        if not result.success:
            logger.warning("TransformAction: execution failed", error=result.error)
            return

        stdout = truncate_output(result.stdout)

        # Parse and process output
        transform_data = self._parse_transform_output(stdout, logger)
        if transform_data is not None:
            accumulator.set_updated_input(transform_data)
