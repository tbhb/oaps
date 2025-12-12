# pyright: reportAny=false, reportCallIssue=false
import json

from oaps.hooks._outputs import (
    NotificationOutput,
    PermissionRequestDecision,
    PermissionRequestHookSpecificOutput,
    PermissionRequestOutput,
    PostToolUseHookSpecificOutput,
    PostToolUseOutput,
    PreCompactHookSpecificOutput,
    PreCompactOutput,
    PreToolUseHookSpecificOutput,
    PreToolUseOutput,
    SessionEndOutput,
    SessionStartHookSpecificOutput,
    SessionStartOutput,
    StopOutput,
    SubagentStopOutput,
    UserPromptSubmitHookSpecificOutput,
    UserPromptSubmitOutput,
)


class TestPreToolUseHookSpecificOutput:
    def test_minimal_output_returns_valid_json(self) -> None:
        output = PreToolUseHookSpecificOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"hookEventName": "PreToolUse"}

    def test_with_permission_decision_returns_camel_case_keys(self) -> None:
        output = PreToolUseHookSpecificOutput(
            permission_decision="deny",
            permission_decision_reason="Not allowed",
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Not allowed",
        }

    def test_with_updated_input_returns_nested_dict(self) -> None:
        output = PreToolUseHookSpecificOutput(
            updated_input={"file_path": "/new/path.py", "limit": 100}
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PreToolUse",
            "updatedInput": {"file_path": "/new/path.py", "limit": 100},
        }

    def test_excludes_none_values(self) -> None:
        output = PreToolUseHookSpecificOutput(
            permission_decision="allow", permission_decision_reason=None
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "permissionDecisionReason" not in parsed


class TestPostToolUseHookSpecificOutput:
    def test_minimal_output_returns_valid_json(self) -> None:
        output = PostToolUseHookSpecificOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"hookEventName": "PostToolUse"}

    def test_with_additional_context_returns_camel_case_keys(self) -> None:
        output = PostToolUseHookSpecificOutput(
            additional_context="Context after tool use"
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PostToolUse",
            "additionalContext": "Context after tool use",
        }

    def test_excludes_none_values(self) -> None:
        output = PostToolUseHookSpecificOutput(additional_context=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "additionalContext" not in parsed


class TestUserPromptSubmitHookSpecificOutput:
    def test_minimal_output_returns_valid_json(self) -> None:
        output = UserPromptSubmitHookSpecificOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"hookEventName": "UserPromptSubmit"}

    def test_with_additional_context_returns_camel_case_keys(self) -> None:
        output = UserPromptSubmitHookSpecificOutput(
            additional_context="Context before processing"
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "Context before processing",
        }

    def test_excludes_none_values(self) -> None:
        output = UserPromptSubmitHookSpecificOutput(additional_context=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "additionalContext" not in parsed


class TestPermissionRequestDecision:
    def test_allow_decision_returns_valid_json(self) -> None:
        decision = PermissionRequestDecision(behavior="allow")
        result = decision.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"behavior": "allow"}

    def test_deny_decision_with_message_returns_camel_case_keys(self) -> None:
        decision = PermissionRequestDecision(
            behavior="deny",
            message="Permission denied",
            interrupt=True,
        )
        result = decision.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "behavior": "deny",
            "message": "Permission denied",
            "interrupt": True,
        }

    def test_allow_with_updated_input_returns_nested_dict(self) -> None:
        decision = PermissionRequestDecision(
            behavior="allow", updated_input={"key": "value"}
        )
        result = decision.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "behavior": "allow",
            "updatedInput": {"key": "value"},
        }

    def test_excludes_none_values(self) -> None:
        decision = PermissionRequestDecision(behavior="allow", message=None)
        result = decision.to_output_json()
        parsed = json.loads(result)
        assert "message" not in parsed


class TestPermissionRequestHookSpecificOutput:
    def test_with_allow_decision_returns_valid_json(self) -> None:
        decision = PermissionRequestDecision(behavior="allow")
        output = PermissionRequestHookSpecificOutput(decision=decision)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }

    def test_with_deny_decision_returns_nested_structure(self) -> None:
        decision = PermissionRequestDecision(
            behavior="deny", message="Not allowed", interrupt=True
        )
        output = PermissionRequestHookSpecificOutput(decision=decision)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "deny",
                "message": "Not allowed",
                "interrupt": True,
            },
        }


class TestSessionStartHookSpecificOutput:
    def test_minimal_output_returns_valid_json(self) -> None:
        output = SessionStartHookSpecificOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"hookEventName": "SessionStart"}

    def test_with_additional_context_returns_camel_case_keys(self) -> None:
        output = SessionStartHookSpecificOutput(
            additional_context="Session start context"
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "SessionStart",
            "additionalContext": "Session start context",
        }

    def test_excludes_none_values(self) -> None:
        output = SessionStartHookSpecificOutput(additional_context=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "additionalContext" not in parsed


class TestPreCompactHookSpecificOutput:
    def test_minimal_output_returns_valid_json(self) -> None:
        output = PreCompactHookSpecificOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"hookEventName": "PreCompact"}

    def test_with_additional_context_returns_camel_case_keys(self) -> None:
        output = PreCompactHookSpecificOutput(additional_context="Preserve this info")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "hookEventName": "PreCompact",
            "additionalContext": "Preserve this info",
        }

    def test_excludes_none_values(self) -> None:
        output = PreCompactHookSpecificOutput(additional_context=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "additionalContext" not in parsed


class TestPreToolUseOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = PreToolUseOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_continue_false_returns_camel_case_keys(self) -> None:
        output = PreToolUseOutput(continue_=False, stop_reason="Stopping execution")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": False,
            "stopReason": "Stopping execution",
        }

    def test_with_all_fields_returns_complete_structure(self) -> None:
        output = PreToolUseOutput(
            continue_=True,
            stop_reason=None,
            suppress_output=True,
            system_message="Warning",
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": True,
            "suppressOutput": True,
            "systemMessage": "Warning",
        }

    def test_excludes_none_values(self) -> None:
        output = PreToolUseOutput(
            continue_=False, stop_reason=None, suppress_output=None
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "stopReason" not in parsed
        assert "suppressOutput" not in parsed


class TestPostToolUseOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = PostToolUseOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_block_decision_returns_camel_case_keys(self) -> None:
        output = PostToolUseOutput(decision="block", reason="Blocked for safety")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Blocked for safety",
        }

    def test_with_hook_specific_output_returns_nested_structure(self) -> None:
        hook_specific = PostToolUseHookSpecificOutput(
            additional_context="Extra context"
        )
        output = PostToolUseOutput(
            continue_=True,
            suppress_output=False,
            system_message="Info message",
            hook_specific_output=hook_specific,
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": True,
            "suppressOutput": False,
            "systemMessage": "Info message",
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Extra context",
            },
        }

    def test_excludes_none_values(self) -> None:
        output = PostToolUseOutput(decision="block", reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "reason" not in parsed


class TestUserPromptSubmitOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = UserPromptSubmitOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_block_decision_returns_camel_case_keys(self) -> None:
        output = UserPromptSubmitOutput(decision="block", reason="Prompt blocked")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Prompt blocked",
        }

    def test_with_hook_specific_output_returns_nested_structure(self) -> None:
        hook_specific = UserPromptSubmitHookSpecificOutput(
            additional_context="Injected context"
        )
        output = UserPromptSubmitOutput(
            continue_=False,
            stop_reason="Stopping",
            hook_specific_output=hook_specific,
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": False,
            "stopReason": "Stopping",
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "Injected context",
            },
        }

    def test_excludes_none_values(self) -> None:
        output = UserPromptSubmitOutput(decision=None, reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}


class TestPermissionRequestOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = PermissionRequestOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_hook_specific_output_returns_nested_structure(self) -> None:
        decision = PermissionRequestDecision(behavior="deny", message="Denied")
        hook_specific = PermissionRequestHookSpecificOutput(decision=decision)
        output = PermissionRequestOutput(
            continue_=True,
            suppress_output=False,
            hook_specific_output=hook_specific,
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": True,
            "suppressOutput": False,
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "deny",
                    "message": "Denied",
                },
            },
        }

    def test_excludes_none_values(self) -> None:
        output = PermissionRequestOutput(
            continue_=None, stop_reason=None, suppress_output=None
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}


class TestNotificationOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = NotificationOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_suppress_output_returns_camel_case_keys(self) -> None:
        output = NotificationOutput(suppress_output=True)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {"suppressOutput": True}

    def test_with_continue_false_returns_complete_structure(self) -> None:
        output = NotificationOutput(
            continue_=False,
            stop_reason="Stopped",
            system_message="Warning message",
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": False,
            "stopReason": "Stopped",
            "systemMessage": "Warning message",
        }

    def test_excludes_none_values(self) -> None:
        output = NotificationOutput(continue_=True, stop_reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "stopReason" not in parsed


class TestSessionStartOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = SessionStartOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_hook_specific_output_returns_nested_structure(self) -> None:
        hook_specific = SessionStartHookSpecificOutput(
            additional_context="Start context"
        )
        output = SessionStartOutput(
            continue_=True,
            system_message="Session starting",
            hook_specific_output=hook_specific,
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": True,
            "systemMessage": "Session starting",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "Start context",
            },
        }

    def test_excludes_none_values(self) -> None:
        output = SessionStartOutput(continue_=None, stop_reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}


class TestSessionEndOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = SessionEndOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}


class TestStopOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = StopOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_block_decision_returns_camel_case_keys(self) -> None:
        output = StopOutput(decision="block", reason="Cannot stop now")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Cannot stop now",
        }

    def test_with_system_message_returns_complete_structure(self) -> None:
        output = StopOutput(
            decision="block",
            reason="Stop blocked",
            system_message="Warning",
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Stop blocked",
            "systemMessage": "Warning",
        }

    def test_excludes_none_values(self) -> None:
        output = StopOutput(decision="block", reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert "reason" not in parsed


class TestSubagentStopOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = SubagentStopOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_block_decision_returns_camel_case_keys(self) -> None:
        output = SubagentStopOutput(decision="block", reason="Subagent must continue")
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Subagent must continue",
        }

    def test_with_system_message_returns_complete_structure(self) -> None:
        output = SubagentStopOutput(
            decision="block",
            reason="Blocked",
            system_message="Subagent stop prevented",
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "decision": "block",
            "reason": "Blocked",
            "systemMessage": "Subagent stop prevented",
        }

    def test_excludes_none_values(self) -> None:
        output = SubagentStopOutput(decision=None, reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}


class TestPreCompactOutput:
    def test_empty_output_returns_empty_json(self) -> None:
        output = PreCompactOutput()
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}

    def test_with_hook_specific_output_returns_nested_structure(self) -> None:
        hook_specific = PreCompactHookSpecificOutput(
            additional_context="Compaction context"
        )
        output = PreCompactOutput(
            continue_=True,
            suppress_output=True,
            hook_specific_output=hook_specific,
        )
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {
            "continue": True,
            "suppressOutput": True,
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": "Compaction context",
            },
        }

    def test_excludes_none_values(self) -> None:
        output = PreCompactOutput(continue_=None, stop_reason=None)
        result = output.to_output_json()
        parsed = json.loads(result)
        assert parsed == {}
