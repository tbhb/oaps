# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false
"""Workflow orchestration actions for /dev command.

This module provides Python action entrypoints for hook rules that orchestrate
the multi-agent /dev workflow. Actions handle:

- Workflow initialization and configuration
- Agent completion tracking and aggregation
- User decision capture
- Phase state transitions
- Error handling and recovery

All functions follow the hook action signature:
    def action_name(context: HookContext) -> dict[str, object] | None

Return values can include:
- "deny": bool - Block the operation
- "deny_message": str - Message for deny
- "warn_message": str - Warning message to display
- "suggest_message": str - Suggestion message to display
- "inject_content": str - Content to inject into context
- "transform_input": dict - Modifications to tool input
"""

import re
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext
    from oaps.session import Session


# Constants
_ACTIVE = 1  # Store as int for session.set compatibility
_INACTIVE = 0
_MAX_RETRIES = 3


# -----------------------------------------------------------------------------
# Workflow initialization
# -----------------------------------------------------------------------------


def init_dev_workflow(context: HookContext) -> dict[str, object]:
    """Initialize /dev workflow state.

    Called on user_prompt_submit when /dev command is detected.
    Creates a unique workflow ID and initializes all phase tracking state.

    Args:
        context: Hook context with session access.

    Returns:
        Status dict with workflow_id.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Generate unique workflow ID
    workflow_id = str(uuid.uuid4())[:8]

    # Initialize workflow state
    session.set("dev.workflow_id", workflow_id)
    session.set("dev.active", _ACTIVE)
    session.set("dev.phase", "discovery")
    _ = session.set_timestamp("dev.started_at")

    # Extract feature description from prompt
    prompt = _get_prompt(context)
    feature_desc = _extract_feature_description(prompt)
    session.set("dev.feature_description", feature_desc)

    # Initialize phase tracking with defaults
    session.set("dev.expected_explorers", 3)
    session.set("dev.explorer_count", 0)
    session.set("dev.exploration_complete", _INACTIVE)

    session.set("dev.expected_architects", 3)
    session.set("dev.architect_count", 0)
    session.set("dev.architecture_complete", _INACTIVE)
    session.set("dev.architecture_approved", _INACTIVE)

    session.set("dev.implementation_complete", _INACTIVE)

    session.set("dev.expected_reviewers", 3)
    session.set("dev.reviewer_count", 0)
    session.set("dev.review_complete", _INACTIVE)

    msg = f"Workflow {workflow_id} initialized. Starting discovery phase."
    return {
        "status": "initialized",
        "workflow_id": workflow_id,
        "suggest_message": msg,
    }


def configure_simple_workflow(context: HookContext) -> dict[str, object]:
    """Configure workflow for simple tasks with reduced agent counts.

    Detects --quick, --simple, or task keywords like "typo", "rename".

    Args:
        context: Hook context with session access.

    Returns:
        Status dict indicating configuration applied.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # First initialize the workflow
    init_result = init_dev_workflow(context)

    # Override with simple configuration
    session.set("dev.expected_explorers", 1)
    session.set("dev.expected_architects", 1)
    session.set("dev.expected_reviewers", 1)
    session.set("dev.workflow_variant", "simple")

    msg = "Simple task detected. Using streamlined workflow."
    return {
        **init_result,
        "workflow_variant": "simple",
        "suggest_message": msg,
    }


def configure_complex_workflow(context: HookContext) -> dict[str, object]:
    """Configure workflow for complex tasks with maximum depth.

    Detects --full, --thorough, or keywords like "refactor", "architecture".

    Args:
        context: Hook context with session access.

    Returns:
        Status dict indicating configuration applied.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # First initialize the workflow
    init_result = init_dev_workflow(context)

    # Override with complex configuration
    session.set("dev.expected_explorers", 3)
    session.set("dev.expected_architects", 3)
    session.set("dev.expected_reviewers", 3)
    session.set("dev.requires_security_review", _ACTIVE)
    session.set("dev.workflow_variant", "complex")

    msg = "Complex task detected. Using enhanced workflow."
    return {
        **init_result,
        "workflow_variant": "complex",
        "suggest_message": msg,
    }


def skip_exploration_phase(context: HookContext) -> dict[str, object]:
    """Skip exploration phase for --skip-explore flag.

    Args:
        context: Hook context with session access.

    Returns:
        Status dict indicating exploration skipped.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Initialize workflow first
    init_result = init_dev_workflow(context)

    # Mark exploration as complete
    session.set("dev.exploration_complete", _ACTIVE)
    session.set("dev.exploration_summary", "Exploration skipped per user request.")
    session.set("dev.phase", "clarification")

    msg = "Skipping exploration phase. Proceeding to clarification."
    return {
        **init_result,
        "exploration_skipped": True,
        "warn_message": msg,
    }


# -----------------------------------------------------------------------------
# Agent completion tracking
# -----------------------------------------------------------------------------


def track_explorer_completion(context: HookContext) -> dict[str, object]:
    """Track code-explorer agent completion and aggregate findings.

    Called on post_tool_use when Task tool completes with code-explorer agent.
    Increments counter and checks if all expected explorers are done.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with completion state.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Increment explorer count
    count = session.increment("dev.explorer_count")
    expected = session.get("dev.expected_explorers") or 3

    # Get agent output and aggregate
    agent_output = _get_tool_output(context)
    existing = session.get("dev.exploration_findings_raw") or ""
    if isinstance(existing, str) and agent_output:
        updated = existing + f"\n\n### Explorer {count} Findings\n{agent_output}"
        session.set("dev.exploration_findings_raw", updated)

    # Extract key files from agent output
    key_files = _extract_file_paths(agent_output)
    existing_files = session.get("dev.key_files_raw") or ""
    if isinstance(existing_files, str):
        session.set("dev.key_files_raw", existing_files + "\n" + "\n".join(key_files))

    # Check if all explorers complete
    if isinstance(expected, int) and count >= expected:
        # Generate summary
        raw_findings = session.get("dev.exploration_findings_raw")
        if isinstance(raw_findings, str):
            summary = _summarize_exploration(raw_findings)
            session.set("dev.exploration_summary", summary)
        session.set("dev.exploration_complete", _ACTIVE)
        session.set("dev.phase", "clarification")

        msg = "Exploration complete. Proceed to clarifying questions."
        return {
            "status": "exploration_complete",
            "explorer_count": count,
            "expected": expected,
            "suggest_message": msg,
        }

    return {
        "status": "explorer_tracked",
        "explorer_count": count,
        "expected": expected,
    }


def track_architect_completion(context: HookContext) -> dict[str, object]:
    """Track code-architect agent completion and aggregate proposals.

    Called on post_tool_use when Task tool completes with code-architect agent.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with completion state.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Increment architect count
    count = session.increment("dev.architect_count")
    expected = session.get("dev.expected_architects") or 3

    # Get agent output and aggregate
    agent_output = _get_tool_output(context)
    existing = session.get("dev.architecture_proposals_raw") or ""
    if isinstance(existing, str) and agent_output:
        updated = existing + f"\n\n### Architecture Option {count}\n{agent_output}"
        session.set("dev.architecture_proposals_raw", updated)

    # Check if all architects complete
    if isinstance(expected, int) and count >= expected:
        session.set("dev.architecture_complete", _ACTIVE)
        session.set("dev.phase", "architecture_review")

        msg = "Architecture design complete. Present options to user."
        return {
            "status": "architecture_complete",
            "architect_count": count,
            "expected": expected,
            "suggest_message": msg,
        }

    return {
        "status": "architect_tracked",
        "architect_count": count,
        "expected": expected,
    }


def track_developer_completion(context: HookContext) -> dict[str, object]:
    """Track code-developer agent completion.

    Called on post_tool_use when Task tool completes with code-developer agent.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with completion state.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Get agent output
    agent_output = _get_tool_output(context)
    impl_summary = agent_output or "Implementation completed."
    session.set("dev.implementation_summary", impl_summary)
    session.set("dev.implementation_complete", _ACTIVE)
    session.set("dev.phase", "review")

    # Extract modified files from output
    modified_files = _extract_file_paths(agent_output)
    session.set("dev.modified_files", "\n".join(modified_files))

    # Check for critical files
    critical_patterns = [
        "auth",
        "security",
        "password",
        "secret",
        "credential",
        "token",
    ]
    has_critical = any(
        any(pattern in f.lower() for pattern in critical_patterns)
        for f in modified_files
    )
    if has_critical:
        session.set("dev.requires_security_review", _ACTIVE)

    msg = "Implementation complete. Proceed to code review phase."
    return {
        "status": "implementation_complete",
        "modified_files_count": len(modified_files),
        "requires_security_review": has_critical,
        "suggest_message": msg,
    }


def track_reviewer_completion(context: HookContext) -> dict[str, object]:
    """Track code-reviewer agent completion and aggregate findings.

    Called on post_tool_use when Task tool completes with code-reviewer agent.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with completion state.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Increment reviewer count
    count = session.increment("dev.reviewer_count")
    expected = session.get("dev.expected_reviewers") or 3

    # Get agent output and aggregate
    agent_output = _get_tool_output(context)
    existing = session.get("dev.review_findings_raw") or ""
    if isinstance(existing, str) and agent_output:
        updated = existing + f"\n\n### Review {count} Findings\n{agent_output}"
        session.set("dev.review_findings_raw", updated)

    # Check if all reviewers complete
    if isinstance(expected, int) and count >= expected:
        session.set("dev.review_complete", _ACTIVE)
        session.set("dev.phase", "review_decision")

        msg = "Code review complete. Present findings to user."
        return {
            "status": "review_complete",
            "reviewer_count": count,
            "expected": expected,
            "suggest_message": msg,
        }

    return {
        "status": "reviewer_tracked",
        "reviewer_count": count,
        "expected": expected,
    }


# -----------------------------------------------------------------------------
# User decision capture
# -----------------------------------------------------------------------------


def set_awaiting_architecture_decision(context: HookContext) -> dict[str, object]:
    """Flag that we're awaiting user's architecture decision.

    Called on pre_tool_use when AskUserQuestion is called during architecture phase.

    Args:
        context: Hook context.

    Returns:
        Status dict.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    session.set("dev.awaiting_architecture_decision", _ACTIVE)
    return {"status": "awaiting_architecture_decision"}


def capture_architecture_decision(context: HookContext) -> dict[str, object]:
    """Capture user's architecture choice from their response.

    Called on user_prompt_submit when awaiting_architecture_decision is True.

    Args:
        context: Hook context with user prompt.

    Returns:
        Status dict with captured decision.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Clear the waiting flag
    session.set("dev.awaiting_architecture_decision", _INACTIVE)

    # Get user's response
    prompt = _get_prompt(context)
    prompt_lower = prompt.lower() if prompt else ""

    # Try to match to an architecture option
    chosen: str | None = None
    option1_words = ["1", "first", "option 1", "minimal"]
    option2_words = ["2", "second", "option 2", "clean"]
    option3_words = ["3", "third", "option 3", "pragmatic", "balanced"]
    approve_words = ["proceed", "approve", "yes", "go ahead", "looks good"]

    if any(word in prompt_lower for word in option1_words):
        chosen = "minimal"
    elif any(word in prompt_lower for word in option2_words):
        chosen = "clean_architecture"
    elif any(word in prompt_lower for word in option3_words):
        chosen = "pragmatic"
    elif any(word in prompt_lower for word in approve_words):
        chosen = "recommended"

    if chosen:
        session.set("dev.architecture_approved", _ACTIVE)
        session.set("dev.chosen_approach", chosen)
        session.set("dev.phase", "implementation")

        # Store the full architecture details for injection
        proposals = session.get("dev.architecture_proposals_raw")
        if isinstance(proposals, str):
            session.set("dev.chosen_architecture", proposals)

        msg = f"Architecture '{chosen}' approved. Proceeding to implementation."
        return {
            "status": "architecture_approved",
            "chosen_approach": chosen,
            "suggest_message": msg,
        }

    msg = "Could not determine architecture choice. Please clarify."
    return {
        "status": "decision_unclear",
        "warn_message": msg,
    }


def set_awaiting_review_decision(context: HookContext) -> dict[str, object]:
    """Flag that we're awaiting user's review decision.

    Args:
        context: Hook context.

    Returns:
        Status dict.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    session.set("dev.awaiting_review_decision", _ACTIVE)
    return {"status": "awaiting_review_decision"}


def capture_review_decision(context: HookContext) -> dict[str, object]:
    """Capture user's review decision.

    Args:
        context: Hook context with user prompt.

    Returns:
        Status dict with captured decision.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    session.set("dev.awaiting_review_decision", _INACTIVE)

    prompt = _get_prompt(context)
    prompt_lower = prompt.lower() if prompt else ""

    fix_now_words = ["fix now", "fix", "address", "resolve"]
    defer_words = ["later", "skip", "ignore", "defer"]
    proceed_words = ["proceed", "done", "complete", "good", "ok", "approve"]

    if any(word in prompt_lower for word in fix_now_words):
        session.set("dev.review_decision", "fix_now")
        session.set("dev.implementation_complete", _INACTIVE)
        msg = "Fixing issues now. Will re-review after."
        return {"status": "fix_now", "suggest_message": msg}

    if any(word in prompt_lower for word in defer_words):
        session.set("dev.review_decision", "fix_later")
        session.set("dev.phase", "summary")
        msg = "Issues deferred. Proceeding to summary."
        return {"status": "fix_later", "suggest_message": msg}

    if any(word in prompt_lower for word in proceed_words):
        session.set("dev.review_decision", "proceed")
        session.set("dev.phase", "summary")
        msg = "Review approved. Proceeding to summary."
        return {"status": "proceed", "suggest_message": msg}

    return {"status": "decision_unclear"}


# -----------------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------------


def handle_agent_failure(context: HookContext) -> dict[str, object]:
    """Handle agent failure by recording state for potential retry.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with failure info.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    # Get agent type from tool input
    tool_input = _get_tool_input(context)
    agent_type = tool_input.get("subagent_type", "unknown") if tool_input else "unknown"

    # Record failure state
    session.set("dev.last_agent_failed", _ACTIVE)
    session.set("dev.last_failed_agent_type", str(agent_type))
    _ = session.set_timestamp("dev.last_failure_time")

    failure_count = session.increment("dev.agent_failure_count")

    msg = f"Agent {agent_type} failed. Consider retrying."
    return {
        "status": "failure_recorded",
        "agent_type": agent_type,
        "failure_count": failure_count,
        "can_retry": failure_count < _MAX_RETRIES,
        "warn_message": msg,
    }


def clear_failure_state(context: HookContext) -> dict[str, object]:
    """Clear failure state when retry begins.

    Args:
        context: Hook context.

    Returns:
        Status dict.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    session.set("dev.last_agent_failed", _INACTIVE)
    session.set("dev.last_failed_agent_type", "")

    return {"status": "failure_state_cleared"}


def reset_review_state(context: HookContext) -> dict[str, object]:
    """Reset review state when re-implementing after review.

    Args:
        context: Hook context.

    Returns:
        Status dict.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    session.set("dev.review_complete", _INACTIVE)
    session.set("dev.reviewer_count", 0)
    session.set("dev.review_findings_raw", "")

    msg = "Re-implementing after review. Review state reset."
    return {
        "status": "review_state_reset",
        "warn_message": msg,
    }


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_session(context: HookContext) -> Session | None:
    """Get Session from context, creating if needed."""
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


def _get_prompt(context: HookContext) -> str:
    """Extract prompt from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "prompt"):
        prompt = getattr(hook_input, "prompt", "")
        return str(prompt) if prompt else ""
    return ""


def _get_tool_input(context: HookContext) -> dict[str, object] | None:
    """Extract tool input from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "tool_input"):
        tool_input = getattr(hook_input, "tool_input", None)
        if isinstance(tool_input, dict):
            return dict(tool_input)
    return None


def _get_tool_output(context: HookContext) -> str:
    """Extract tool output/result from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "tool_response"):
        response = getattr(hook_input, "tool_response", {})
        if isinstance(response, dict):
            result = response.get("result", "")
            return str(result) if result else ""
    return ""


def _extract_feature_description(prompt: str) -> str:
    """Extract feature description from /dev command prompt."""
    if not prompt:
        return ""

    # Remove command prefix and flags
    text = prompt
    for prefix in ["/dev", "/oaps:dev"]:
        if text.lower().startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    # Remove flags
    return re.sub(r"--\w+", "", text).strip()


def _extract_file_paths(text: str) -> list[str]:
    """Extract file paths from text output."""
    if not text:
        return []

    paths: list[str] = []
    # Match common file path patterns
    patterns = [
        r"[\w./\-_]+\.\w+",  # path/to/file.ext
        r"`([^`]+\.\w+)`",  # `file.ext` in backticks
    ]

    extensions = (".py", ".ts", ".js", ".md", ".toml", ".yaml")
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            path = str(match)
            if "/" in path or path.endswith(extensions):
                paths.append(path)

    return list(set(paths))


def _summarize_exploration(findings: str) -> str:
    """Create a summary of exploration findings."""
    if not findings:
        return "No exploration findings available."

    # Simple summarization - just truncate if too long
    max_len = 2000
    if len(findings) > max_len:
        return findings[:max_len] + "\n\n[Truncated for brevity]"
    return findings
