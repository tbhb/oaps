# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnusedParameter=false
# pyright: reportExplicitAny=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportUnnecessaryComparison=false, reportUnreachable=false
# ruff: noqa: D415, A002, ARG001, BLE001, PLR0911, PLR0912, PLR0915, S108
"""Test subcommand for hooks."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.config import (
    find_project_root,
    load_all_hook_rules,
)
from oaps.enums import HookEventType
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import HOOK_EVENT_TYPE_TO_MODEL, PreToolUseInput
from oaps.hooks._matcher import match_rules
from oaps.utils import create_hooks_logger, create_session_logger, get_oaps_dir

from ._app import app
from ._exit_codes import EXIT_INPUT_ERROR, EXIT_LOAD_ERROR, EXIT_NOT_FOUND, EXIT_SUCCESS
from ._formatters import format_match_result

if TYPE_CHECKING:
    from oaps.hooks._inputs import HookInputT


def _parse_event_type(event: str) -> HookEventType | None:
    """Parse event type string to HookEventType enum.

    Args:
        event: Event type string (e.g., "pre_tool_use").

    Returns:
        HookEventType enum value, or None if invalid.
    """
    try:
        return HookEventType(event)
    except ValueError:
        return None


def _read_input(input_file: Path | None) -> str | None:
    """Read input JSON from file or stdin.

    Args:
        input_file: Path to input file, or None to read from stdin.

    Returns:
        JSON string, or None if stdin is a TTY with no input.
    """
    if input_file:
        return input_file.read_text()

    # Read from stdin if not a TTY
    if not sys.stdin.isatty():
        try:
            return sys.stdin.read()
        except OSError:
            # Handle case where stdin is captured (e.g., pytest)
            return None

    return None


def _create_minimal_input(event_type: HookEventType) -> dict[str, Any]:
    """Create minimal valid input for an event type.

    Args:
        event_type: The hook event type.

    Returns:
        A dictionary with minimal required fields for the event type.
        Uses snake_case keys to match Pydantic model field names.
    """
    base: dict[str, Any] = {
        "session_id": "test-session",
        "transcript_path": "/tmp/test-transcript.json",
        "permission_mode": "default",
        "cwd": str(Path.cwd()),
    }

    match event_type:
        case HookEventType.PRE_TOOL_USE:
            return {
                **base,
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"},
                "tool_use_id": "test-tool-use-id",
            }
        case HookEventType.POST_TOOL_USE:
            return {
                **base,
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "echo test"},
                "tool_response": {"output": "test"},
                "tool_use_id": "test-tool-use-id",
            }
        case HookEventType.USER_PROMPT_SUBMIT:
            return {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "test prompt",
            }
        case HookEventType.PERMISSION_REQUEST:
            return {
                **base,
                "hook_event_name": "PermissionRequest",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
                "tool_use_id": "test-tool-use-id",
            }
        case HookEventType.NOTIFICATION:
            return {
                **base,
                "hook_event_name": "Notification",
                "message": "Test notification",
                "notification_type": "idle_prompt",
            }
        case HookEventType.SESSION_START:
            return {
                "session_id": "00000000-0000-0000-0000-000000000000",
                "transcript_path": "/tmp/test-transcript.json",
                "hook_event_name": "SessionStart",
                "cwd": str(Path.cwd()),
                "source": "startup",
            }
        case HookEventType.SESSION_END:
            return {
                **base,
                "hook_event_name": "SessionEnd",
                "reason": "other",
            }
        case HookEventType.STOP:
            return {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
            }
        case HookEventType.SUBAGENT_STOP:
            return {
                **base,
                "hook_event_name": "SubagentStop",
                "stop_hook_active": False,
            }
        case HookEventType.PRE_COMPACTION:
            return {
                **base,
                "hook_event_name": "PreCompact",
                "trigger": "manual",
                "custom_instructions": "",
            }
        case _:
            return base


def _build_context(
    event_type: HookEventType,
    hook_input: HookInputT,
) -> HookContext:
    """Build a HookContext for testing.

    Args:
        event_type: The hook event type.
        hook_input: The validated hook input.

    Returns:
        A HookContext suitable for rule matching.
    """
    # Extract session ID (handling both str and UUID types)
    session_id = str(hook_input.session_id)

    hook_logger = create_hooks_logger()
    session_logger = create_session_logger(session_id)

    oaps_dir = get_oaps_dir()
    oaps_state_file = oaps_dir / "state.db"

    return HookContext(
        hook_event_type=event_type,
        hook_input=hook_input,
        claude_session_id=session_id,
        oaps_dir=oaps_dir,
        oaps_state_file=oaps_state_file,
        hook_logger=hook_logger,
        session_logger=session_logger,
        git=None,  # Git context not available in test mode
    )


@app.command(name="test")
def _test(
    *,
    event: Annotated[
        str,
        Parameter(
            name=["--event", "-e"],
            help="Event type to simulate (e.g., pre_tool_use, post_tool_use)",
        ),
    ] = "pre_tool_use",
    input_file: Annotated[
        Path | None,
        Parameter(
            name=["--input", "-i"],
            help="JSON file with hook input (reads from stdin if piped)",
        ),
    ] = None,
    rule_id: Annotated[
        str | None,
        Parameter(
            name=["--rule", "-r"],
            help="Test specific rule by ID only",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        Parameter(
            name="--dry-run",
            help="Show what would match without executing actions",
        ),
    ] = True,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Test which rules match a given hook input

    Simulates a hook event and shows which rules would match.
    Useful for testing rule conditions before deployment.

    Examples:
      # Test with default pre_tool_use event
      oaps hooks test

      # Test with specific event type
      oaps hooks test --event user_prompt_submit

      # Test with custom input JSON
      echo '{"sessionId": "...", ...}' | oaps hooks test --event pre_tool_use

      # Test with input file
      oaps hooks test --event pre_tool_use --input test_input.json

      # Test specific rule only
      oaps hooks test --rule my-rule-id

    Exit codes:
        0: Test completed successfully
        1: Failed to load configuration files
        3: Specified rule ID not found
        4: Invalid input JSON
    """
    logger = create_hooks_logger()

    # Parse event type
    event_type = _parse_event_type(event)
    if event_type is None:
        valid_events = ", ".join(e.value for e in HookEventType)
        print(f"Error: Invalid event type '{event}'. Valid types: {valid_events}")
        raise SystemExit(EXIT_INPUT_ERROR)

    # Resolve project root
    project_root = find_project_root()

    # Load all rules
    try:
        rules = load_all_hook_rules(project_root, logger)
    except Exception as e:
        print(f"Error loading hook rules: {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    # Filter to specific rule if requested
    if rule_id:
        rules = [r for r in rules if r.id == rule_id]
        if not rules:
            print(f"Error: Rule '{rule_id}' not found")
            raise SystemExit(EXIT_NOT_FOUND)

    # Read or create input
    input_json = _read_input(input_file)

    # Get the model class for this event type
    model_class = HOOK_EVENT_TYPE_TO_MODEL.get(event_type)
    if model_class is None:
        print(f"Error: No input model for event type '{event}'")
        raise SystemExit(EXIT_INPUT_ERROR)

    # Parse or create input
    if input_json:
        try:
            hook_input = model_class.model_validate_json(input_json)
        except Exception as e:
            print(f"Error parsing input JSON: {e}")
            raise SystemExit(EXIT_INPUT_ERROR) from None
    else:
        # Create minimal input for the event type
        minimal = _create_minimal_input(event_type)
        try:
            hook_input = model_class.model_validate(minimal)
        except Exception as e:
            print(f"Error creating minimal input: {e}")
            raise SystemExit(EXIT_INPUT_ERROR) from None

    # Build context
    context = _build_context(event_type, hook_input)

    # Match rules
    matched = match_rules(rules, context)

    # Format context description
    if isinstance(hook_input, PreToolUseInput):
        context_desc = f"event={event}, tool={hook_input.tool_name}"
    else:
        context_desc = f"event={event}"

    # Format output
    if format == OutputFormat.JSON:
        import orjson

        data = {
            "event": event,
            "context": context_desc,
            "matched_rules": [
                {
                    "order": m.match_order,
                    "rule_id": m.rule.id,
                    "priority": m.rule.priority.value,
                    "result": m.rule.result,
                }
                for m in matched
            ],
            "total_rules": len(rules),
            "matched_count": len(matched),
        }
        print(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        print(format_match_result(matched, context_desc))
        print()
        print(f"Total rules evaluated: {len(rules)}")

    raise SystemExit(EXIT_SUCCESS)
