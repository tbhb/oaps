from pathlib import Path
from uuid import uuid4

from oaps.hooks._inputs import (
    NotificationInput,
    PermissionRequestInput,
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UserPromptSubmitInput,
    is_notification_hook,
    is_permission_request_hook,
    is_post_tool_use_hook,
    is_pre_compact_hook,
    is_pre_tool_use_hook,
    is_session_end_hook,
    is_session_start_hook,
    is_stop_hook,
    is_subagent_stop_hook,
    is_user_prompt_submit_hook,
)


class TestIsPreToolUseHook:
    def test_correct_type_returns_true(self) -> None:
        hook = PreToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_use_id="tool-123",
        )
        assert is_pre_tool_use_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = PostToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_response={"content": "test"},
            tool_use_id="tool-123",
        )
        assert is_pre_tool_use_hook(hook) is False

    def test_session_start_type_returns_false(self) -> None:
        hook = SessionStartInput(
            session_id=uuid4(),
            transcript_path=Path("/path/to/transcript"),
            hook_event_name="SessionStart",
            cwd=Path("/test"),
            source="startup",
        )
        assert is_pre_tool_use_hook(hook) is False


class TestIsPostToolUseHook:
    def test_correct_type_returns_true(self) -> None:
        hook = PostToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_response={"content": "test"},
            tool_use_id="tool-123",
        )
        assert is_post_tool_use_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = PreToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_use_id="tool-123",
        )
        assert is_post_tool_use_hook(hook) is False

    def test_user_prompt_type_returns_false(self) -> None:
        hook = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/test",
            prompt="test prompt",
        )
        assert is_post_tool_use_hook(hook) is False


class TestIsUserPromptSubmitHook:
    def test_correct_type_returns_true(self) -> None:
        hook = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/test",
            prompt="test prompt",
        )
        assert is_user_prompt_submit_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = PermissionRequestInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PermissionRequest",
            cwd="/test",
            tool_name="Write",
            tool_input={"file_path": "/test.py", "content": "test"},
            tool_use_id="tool-123",
        )
        assert is_user_prompt_submit_hook(hook) is False

    def test_pre_tool_use_type_returns_false(self) -> None:
        hook = PreToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_use_id="tool-123",
        )
        assert is_user_prompt_submit_hook(hook) is False


class TestIsPermissionRequestHook:
    def test_correct_type_returns_true(self) -> None:
        hook = PermissionRequestInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PermissionRequest",
            cwd="/test",
            tool_name="Write",
            tool_input={"file_path": "/test.py", "content": "test"},
            tool_use_id="tool-123",
        )
        assert is_permission_request_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = NotificationInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Notification",
            cwd="/test",
            message="test notification",
            notification_type="permission_prompt",
        )
        assert is_permission_request_hook(hook) is False

    def test_post_tool_use_type_returns_false(self) -> None:
        hook = PostToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PostToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_response={"content": "test"},
            tool_use_id="tool-123",
        )
        assert is_permission_request_hook(hook) is False


class TestIsNotificationHook:
    def test_correct_type_returns_true(self) -> None:
        hook = NotificationInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Notification",
            cwd="/test",
            message="test notification",
            notification_type="permission_prompt",
        )
        assert is_notification_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = SessionEndInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="SessionEnd",
            cwd="/test",
            reason="clear",
        )
        assert is_notification_hook(hook) is False

    def test_user_prompt_type_returns_false(self) -> None:
        hook = UserPromptSubmitInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="UserPromptSubmit",
            cwd="/test",
            prompt="test prompt",
        )
        assert is_notification_hook(hook) is False


class TestIsSessionStartHook:
    def test_correct_type_returns_true(self) -> None:
        hook = SessionStartInput(
            session_id=uuid4(),
            transcript_path=Path("/path/to/transcript"),
            hook_event_name="SessionStart",
            cwd=Path("/test"),
            source="startup",
        )
        assert is_session_start_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = SessionEndInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="SessionEnd",
            cwd="/test",
            reason="clear",
        )
        assert is_session_start_hook(hook) is False

    def test_notification_type_returns_false(self) -> None:
        hook = NotificationInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Notification",
            cwd="/test",
            message="test notification",
            notification_type="permission_prompt",
        )
        assert is_session_start_hook(hook) is False


class TestIsSessionEndHook:
    def test_correct_type_returns_true(self) -> None:
        hook = SessionEndInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="SessionEnd",
            cwd="/test",
            reason="clear",
        )
        assert is_session_end_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = StopInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Stop",
            cwd="/test",
            stop_hook_active=True,
        )
        assert is_session_end_hook(hook) is False

    def test_permission_request_type_returns_false(self) -> None:
        hook = PermissionRequestInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PermissionRequest",
            cwd="/test",
            tool_name="Write",
            tool_input={"file_path": "/test.py", "content": "test"},
            tool_use_id="tool-123",
        )
        assert is_session_end_hook(hook) is False


class TestIsStopHook:
    def test_correct_type_returns_true(self) -> None:
        hook = StopInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Stop",
            cwd="/test",
            stop_hook_active=True,
        )
        assert is_stop_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = SubagentStopInput(
            agent_id="test-agent",
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="SubagentStop",
            cwd="/test",
            stop_hook_active=True,
        )
        assert is_stop_hook(hook) is False

    def test_pre_compact_type_returns_false(self) -> None:
        hook = PreCompactInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreCompact",
            cwd="/test",
            trigger="manual",
            custom_instructions="",
        )
        assert is_stop_hook(hook) is False


class TestIsSubagentStopHook:
    def test_correct_type_returns_true(self) -> None:
        hook = SubagentStopInput(
            agent_id="test-agent",
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="SubagentStop",
            cwd="/test",
            stop_hook_active=True,
        )
        assert is_subagent_stop_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = PreCompactInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreCompact",
            cwd="/test",
            trigger="manual",
            custom_instructions="",
        )
        assert is_subagent_stop_hook(hook) is False

    def test_stop_type_returns_false(self) -> None:
        hook = StopInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="Stop",
            cwd="/test",
            stop_hook_active=True,
        )
        assert is_subagent_stop_hook(hook) is False


class TestIsPreCompactHook:
    def test_correct_type_returns_true(self) -> None:
        hook = PreCompactInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreCompact",
            cwd="/test",
            trigger="manual",
            custom_instructions="",
        )
        assert is_pre_compact_hook(hook) is True

    def test_wrong_type_returns_false(self) -> None:
        hook = PreToolUseInput(
            session_id="test-session",
            transcript_path="/path/to/transcript",
            permission_mode="default",
            hook_event_name="PreToolUse",
            cwd="/test",
            tool_name="Read",
            tool_input={"file_path": "/test.py"},
            tool_use_id="tool-123",
        )
        assert is_pre_compact_hook(hook) is False

    def test_session_start_type_returns_false(self) -> None:
        hook = SessionStartInput(
            session_id=uuid4(),
            transcript_path=Path("/path/to/transcript"),
            hook_event_name="SessionStart",
            cwd=Path("/test"),
            source="startup",
        )
        assert is_pre_compact_hook(hook) is False
