# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false
"""Repository checkpoint actions for workflow hooks.

This module provides Python action entrypoints for hook rules that create
automatic checkpoint commits at workflow phase transitions.

All functions follow the hook action signature:
    def action_name(context: HookContext) -> dict[str, object] | None

Return values include:
- "status": str - "committed", "no_changes", "skipped", or "error"
- "sha": str | None - Commit SHA when committed
- "warn_message": str - Warning message on error

Checkpoint commits use the conventional format:
- oaps(dev): <action> - for dev workflow phase transitions
- oaps(idea): <action> - for idea workflow phase transitions
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext
    from oaps.session import Session


# -----------------------------------------------------------------------------
# Dev Workflow Checkpoints
# -----------------------------------------------------------------------------


def checkpoint_dev_workflow(context: HookContext) -> dict[str, object]:
    """Create a checkpoint commit for dev workflow phase transitions.

    Determines the appropriate action string based on the current dev workflow
    phase and creates a commit with all pending changes in the OAPS repository.

    The action string is determined by checking session state flags:
    - exploration_complete -> "exploration complete"
    - architecture_approved -> "architecture approved"
    - implementation_complete -> "implementation complete"
    - review_complete -> "review complete"

    Args:
        context: Hook context with session access.

    Returns:
        Status dict with:
            - status: "committed" (with sha), "no_changes", "skipped", or "error"
            - sha: Commit SHA hex string when committed
            - warn_message: Warning message on error
    """
    session = _get_session(context)
    if session is None:
        return {"status": "skipped", "reason": "no_session"}

    # Determine the action based on which phase flag triggered this
    action = _determine_dev_action(session)
    if action is None:
        return {"status": "skipped", "reason": "no_phase_flag"}

    return _create_checkpoint(context, "dev", action)


# -----------------------------------------------------------------------------
# Idea Workflow Checkpoints
# -----------------------------------------------------------------------------


def checkpoint_idea_workflow(context: HookContext) -> dict[str, object]:
    """Create a checkpoint commit for idea workflow phase transitions.

    Determines the appropriate action string based on the idea workflow state
    and creates a commit with all pending changes in the OAPS repository.

    The action string format:
    - "create <idea_id>" - when document is first created
    - "update <idea_id>" - when document is updated

    Args:
        context: Hook context with session access.

    Returns:
        Status dict with:
            - status: "committed" (with sha), "no_changes", "skipped", or "error"
            - sha: Commit SHA hex string when committed
            - warn_message: Warning message on error
    """
    session = _get_session(context)
    if session is None:
        return {"status": "skipped", "reason": "no_session"}

    # Get idea ID from session
    idea_id = session.get("idea.idea_id")
    if not isinstance(idea_id, str) or not idea_id:
        idea_id = "unknown"

    # Determine action based on phase
    phase = session.get("idea.phase")
    document_created = session.get("idea.document_created")

    # If document was just created (phase transitioned to exploring)
    if phase == "exploring" and document_created:
        action = f"create {idea_id}"
    else:
        action = f"update {idea_id}"

    return _create_checkpoint(context, "idea", action)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_session(context: HookContext) -> Session | None:
    """Get Session from context, creating if needed.

    Args:
        context: Hook context with oaps_state_file and claude_session_id.

    Returns:
        Session instance or None if unavailable.
    """
    from oaps.session import Session  # noqa: PLC0415
    from oaps.utils import create_state_store  # noqa: PLC0415

    if not hasattr(context, "oaps_state_file"):
        return None

    try:
        store = create_state_store(
            context.oaps_state_file, session_id=context.claude_session_id
        )
        return Session(id=context.claude_session_id, store=store)
    except Exception:  # noqa: BLE001
        return None


def _determine_dev_action(session: Session) -> str | None:
    """Determine the dev workflow action based on session state.

    Checks phase completion flags in order and returns the appropriate
    action string for the most recently completed phase.

    Args:
        session: Session instance with dev workflow state.

    Returns:
        Action string or None if no phase flag is set.
    """
    # Check flags in reverse order of workflow progression
    # to find the most recently completed phase
    if session.get("dev.review_complete"):
        return "review complete"
    if session.get("dev.implementation_complete"):
        return "implementation complete"
    if session.get("dev.architecture_approved"):
        return "architecture approved"
    if session.get("dev.exploration_complete"):
        return "exploration complete"
    return None


def _create_checkpoint(
    context: HookContext, workflow: str, action: str
) -> dict[str, object]:
    """Create a checkpoint commit in the OAPS repository.

    Args:
        context: Hook context with session access.
        workflow: Workflow name for commit message scope.
        action: Action description for commit message.

    Returns:
        Status dict with commit result or error information.
    """
    from oaps.exceptions import OapsRepositoryNotInitializedError  # noqa: PLC0415
    from oaps.repository import OapsRepository  # noqa: PLC0415

    try:
        with OapsRepository() as repo:
            result = repo.checkpoint(
                workflow, action, session_id=context.claude_session_id
            )

            if result.no_changes:
                return {"status": "no_changes"}

            return {
                "status": "committed",
                "sha": result.sha,
                "files_count": len(result.files),
            }

    except OapsRepositoryNotInitializedError:
        # Repository not initialized - this is expected in some environments
        return {"status": "skipped", "reason": "repository_not_initialized"}

    except Exception as e:  # noqa: BLE001
        # Log the error but don't fail the hook
        context.hook_logger.warning(
            "Failed to create checkpoint commit",
            workflow=workflow,
            action=action,
            error=str(e),
        )
        return {"status": "error", "warn_message": f"Checkpoint failed: {e}"}
