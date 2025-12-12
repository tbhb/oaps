"""The OAPS hook runner CLI tool.

This module provides an isolated CLI for running Claude Code hooks.
It uses minimal imports at module level to handle catastrophic failures
(ImportError, SyntaxError) gracefully during development.

Exit codes follow Claude Code hook semantics:
- 0: Success, continue normally
- 1: Non-blocking error (stderr shown to user in verbose mode)
- 2: Blocking error (stderr fed back to Claude, action blocked)
"""

# ruff: noqa: PLC0415 - Deferred imports required for catastrophic error handling

import argparse
import sys
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import structlog

    from oaps.config import HooksConfiguration
    from oaps.enums import HookEventType
    from oaps.hooks._context import HookContext
    from oaps.hooks._output_builder import HardcodedContext
    from oaps.session import Session

    from ._inputs import HookInputT


def main() -> None:
    """Entry point for oaps-hook CLI.

    Defers all heavy imports to handle ImportError gracefully.
    On catastrophic failure, prints to stderr but exits 0 to avoid
    breaking Claude Code sessions during development.
    """
    try:
        _run_hook_cli()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:  # noqa: BLE001 - Intentional catch-all for catastrophic failures
        # Catastrophic failure (ImportError, SyntaxError, etc.)
        # Write to stderr for visibility in verbose mode
        # but exit 128 to allow the hook to succeed
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(128)


def _run_hook_cli() -> None:
    """Internal CLI implementation with all imports deferred."""
    from oaps.config import load_hooks_configuration, load_storage_configuration
    from oaps.enums import HookEventType
    from oaps.exceptions import BlockHook
    from oaps.hooks import (
        HOOK_EVENT_TYPE_TO_MODEL,
    )
    from oaps.utils import create_hooks_logger, create_session_logger

    class Args(argparse.Namespace):
        event: HookEventType  # pyright: ignore[reportUninitializedInstanceVariable]

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="oaps-hook",
        description="Run OAPS hooks for Claude Code events",
    )
    _ = parser.add_argument(
        "event",
        type=HookEventType,
        choices=HookEventType,
        help="The hook event type to handle",
    )
    args = parser.parse_args(namespace=Args())
    event = args.event

    # Read and validate input from stdin
    input_json = sys.stdin.read()
    model_class: type[HookInputT] = HOOK_EVENT_TYPE_TO_MODEL[event]
    hook_input = model_class.model_validate_json(input_json)

    # Load hooks configuration to get log_level, rotation settings, and rules
    hooks_config = load_hooks_configuration()
    hook_logger = create_hooks_logger(
        level=hooks_config.log_level,
        max_bytes=hooks_config.log_max_bytes,
        backup_count=hooks_config.log_backup_count,
    )
    session_logger = create_session_logger(hook_input.session_id)

    # Load storage configuration to get log_level for state stores
    storage_config = load_storage_configuration()
    storage_logger = create_session_logger(
        hook_input.session_id, level=storage_config.log_level
    )

    hook_logger.info(
        "hook_started",
        hook_event=event.value,
        session_id=hook_input.session_id,
    )
    # Debug-level: full hook input JSON
    hook_logger.debug(
        "hook_input_full",
        input_json=input_json,
    )
    hook_logger.info("hook_input", input=hook_input.model_dump())

    try:
        _execute_hook(
            event,
            hook_input,
            hooks_config,
            hook_logger,
            session_logger,
            storage_logger,
        )
        hook_logger.info(
            "hook_completed",
            hook_event=event.value,
            session_id=hook_input.session_id,
        )
        sys.exit(0)
    except BlockHook as e:
        # Intentional block - feed back to Claude
        hook_logger.warning(
            "hook_blocked",
            hook_event=event.value,
            session_id=hook_input.session_id,
            reason=str(e),
        )
        print(str(e), file=sys.stderr)  # noqa: T201
        sys.exit(2)
    except Exception:
        # Log error to file but exit 0 to not break Claude Code session
        # structlog's dict_tracebacks processor will add structured exception info
        hook_logger.exception(
            "hook_failed",
            hook_event=event.value,
            session_id=hook_input.session_id,
        )
        sys.exit(0)


def _run_builtin_logic(
    event: HookEventType,
    hook_input: HookInputT,
    context: HookContext,
    session: Session,
    hook_logger: structlog.typing.FilteringBoundLogger,
) -> HardcodedContext:
    """Execute built-in hook logic and return hardcoded context.

    Handles SessionStart environment file creation and PreCompact statistics
    gathering. These are built-in behaviors that run before custom rules.

    Args:
        event: The hook event type.
        hook_input: The validated input data for this hook.
        context: The hook context.
        session: The session object.
        hook_logger: The structlog logger instance.

    Returns:
        HardcodedContext with any additional context from built-in logic.
    """
    from oaps.enums import HookEventType
    from oaps.hooks._inputs import is_session_start_hook
    from oaps.hooks._output_builder import HardcodedContext
    from oaps.project import Project
    from oaps.utils import create_project_store

    hardcoded = HardcodedContext()

    # Normalize types early - SessionStartInput uses UUID/Path, others use str
    claude_session_id = str(hook_input.session_id)
    transcript_path = str(hook_input.transcript_path)

    claude_home = getenv("CLAUDE_HOME")
    claude_home_path = Path(claude_home) if claude_home else Path.home() / ".claude"

    env_vars = {
        "CLAUDE_SESSION_ID": claude_session_id,
        "CLAUDE_TRANSCRIPT_DIR": str(Path(transcript_path).parent),
        "CLAUDE_TRANSCRIPT_PATH": transcript_path,
        "OAPS_DIR": str(context.oaps_dir),
    }

    # SessionStart: write environment file
    if is_session_start_hook(hook_input):
        env_file = getenv("CLAUDE_ENV_FILE")
        env_file_path = Path(env_file) if env_file else None

        # TEMPORARY: See https://github.com/anthropics/claude-code/issues/11649#issuecomment-3556712799
        if not env_file_path:
            env_file_path = (
                claude_home_path / f"session-env/{claude_session_id}/hook-1.sh"
            )

        env_file_path.parent.mkdir(parents=True, exist_ok=True)

        _ = env_file_path.write_text(
            "\n".join(f"export {key}={value}" for key, value in env_vars.items())
        )
        env_file_path.chmod(0o755)

        hook_logger.debug(
            "session_env_written",
            env_file=str(env_file_path),
            session_id=claude_session_id,
        )

        # Set hardcoded context for SessionStart
        hardcoded.additional_context = (
            f"Claude Code environment file: {env_file_path}\n"
            f"Claude Code session ID: {claude_session_id}\n"
            f"Claude Code transcript path: {transcript_path}"
        )

        # Store transcript directory in project state
        transcript_dir = str(Path(transcript_path).parent)
        project_store = create_project_store()
        project = Project(store=project_store)
        project.set("oaps.claude.transcript_dir", transcript_dir)
        hook_logger.debug(
            "transcript_dir_stored",
            transcript_dir=transcript_dir,
        )

    # PreCompact: gather session statistics
    if event == HookEventType.PRE_COMPACTION:
        from oaps.hooks._statistics import (
            format_statistics_context,
            gather_session_statistics,
        )

        stats = gather_session_statistics(session)
        hardcoded.additional_context = format_statistics_context(stats)

    return hardcoded


def _execute_hook(  # noqa: PLR0913
    event: HookEventType,
    hook_input: HookInputT,
    hooks_config: HooksConfiguration,
    hook_logger: structlog.typing.FilteringBoundLogger,
    session_logger: structlog.typing.FilteringBoundLogger,
    storage_logger: structlog.typing.FilteringBoundLogger,
) -> None:
    """Execute the hook logic for the given event.

    Args:
        event: The hook event type.
        hook_input: The validated input data for this hook.
        hooks_config: The hooks configuration including rules.
        hook_logger: The structlog logger instance.
        session_logger: The structlog logger instance for the session.
        storage_logger: Logger for state store operations (respects [storage] config).

    Raises:
        BlockHook: To block the action and feed message to Claude.
    """
    from oaps.exceptions import BlockHook
    from oaps.hooks._action import OutputAccumulator
    from oaps.hooks._context import HookContext
    from oaps.hooks._executor import execute_rules
    from oaps.hooks._matcher import match_rules
    from oaps.hooks._output_builder import build_hook_output
    from oaps.hooks._state import update_hook_state
    from oaps.session import Session
    from oaps.utils import (
        SQLiteStateStore,
        get_git_context,
        get_oaps_dir,
        get_oaps_state_file,
    )

    # Normalize types early - SessionStartInput uses UUID/Path, others use str
    claude_session_id = str(hook_input.session_id)

    oaps_dir = get_oaps_dir()
    oaps_state_file = get_oaps_state_file()

    # Collect git context if available
    cwd_attr: object = getattr(hook_input, "cwd", None)
    cwd_path: Path | None = Path(str(cwd_attr)) if cwd_attr is not None else None
    git_context = get_git_context(cwd_path)

    # Create HookContext early for rule matching and execution
    context = HookContext(
        hook_event_type=event,
        hook_input=hook_input,
        claude_session_id=claude_session_id,
        oaps_dir=oaps_dir,
        oaps_state_file=oaps_state_file,
        hook_logger=hook_logger,
        session_logger=session_logger,
        git=git_context,
    )

    # Initialize Session and update built-in state
    # Ensure the state directory exists
    oaps_state_file.parent.mkdir(parents=True, exist_ok=True)
    session = Session(
        id=claude_session_id,
        store=SQLiteStateStore(
            oaps_state_file, session_id=claude_session_id, logger=storage_logger
        ),
    )
    update_hook_state(session, event, hook_input)

    # Run built-in logic (SessionStart env file, PreCompact statistics)
    hardcoded = _run_builtin_logic(
        event=event,
        hook_input=hook_input,
        context=context,
        session=session,
        hook_logger=hook_logger,
    )

    # Match and execute rules
    accumulator = OutputAccumulator()
    matched_rules = match_rules(hooks_config.rules, context, session)
    hook_logger.info(
        "rules_matched",
        count=len(matched_rules),
        rule_ids=[m.rule.id for m in matched_rules],
    )

    execution_result = execute_rules(matched_rules, context, accumulator)
    if execution_result.should_block:
        raise BlockHook(execution_result.block_reason or "Blocked by hook rule")

    # Build and output final hook response
    output_json = build_hook_output(event, accumulator, hardcoded)
    if output_json is not None:
        hook_logger.debug(
            "hook_output_full",
            output_json=output_json,
        )
        print(output_json)  # noqa: T201


if __name__ == "__main__":
    main()
