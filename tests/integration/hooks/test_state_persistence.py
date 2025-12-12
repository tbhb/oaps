"""Integration tests verifying state is persisted to SQLite after hook events."""

import json
import sqlite3
from pathlib import Path

from tests.integration.conftest import HookTestEnv, run_hook, run_session_start


def get_state_db_path(env: HookTestEnv) -> Path:
    """Get the path to the unified state database."""
    return env.tmp_path / ".oaps" / "state.db"


def query_session_store(
    db_path: Path, session_id: str, key: str
) -> str | int | float | bytes | None:
    """Query a single value from the state store for a specific session."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        'SELECT value FROM state_store WHERE "session_id" IS ? AND key = ?',
        (session_id, key),
    )
    row: tuple[str | int | float | bytes | None, ...] | None
    row = cursor.fetchone()  # pyright: ignore[reportAny]
    conn.close()
    if row is None:
        return None
    return row[0]


class TestSessionStartStatePersistence:
    def test_persists_started_at_timestamp(self, hook_test_env: HookTestEnv) -> None:
        input_data = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "source": "startup",
        }

        result = run_hook("session_start", input_data, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        value = query_session_store(
            db_path, hook_test_env.session_id, "oaps.session.started_at"
        )
        assert value is not None
        assert isinstance(value, str)
        assert "T" in value  # ISO 8601 timestamp

    def test_persists_source(self, hook_test_env: HookTestEnv) -> None:
        input_data = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "source": "resume",
        }

        result = run_hook("session_start", input_data, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        value = query_session_store(
            db_path, hook_test_env.session_id, "oaps.session.source"
        )
        assert value == "resume"


class TestSessionEndStatePersistence:
    def test_persists_ended_at_timestamp(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        end_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "SessionEnd",
            "cwd": str(hook_test_env.tmp_path),
            "reason": "clear",
        }

        result = run_hook("session_end", end_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        value = query_session_store(
            db_path, hook_test_env.session_id, "oaps.session.ended_at"
        )
        assert value is not None
        assert isinstance(value, str)
        assert "T" in value  # ISO 8601 timestamp


class TestUserPromptSubmitStatePersistence:
    def test_persists_prompt_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        prompt_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "cwd": str(hook_test_env.tmp_path),
            "prompt": "test prompt",
        }

        result = run_hook("user_prompt_submit", prompt_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.prompts.count"
        )
        assert count == 1

    def test_persists_prompt_timestamps(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        prompt_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "cwd": str(hook_test_env.tmp_path),
            "prompt": "test prompt",
        }

        run_hook("user_prompt_submit", prompt_input, hook_test_env)

        db_path = get_state_db_path(hook_test_env)
        first_at = query_session_store(
            db_path, hook_test_env.session_id, "oaps.prompts.first_at"
        )
        last_at = query_session_store(
            db_path, hook_test_env.session_id, "oaps.prompts.last_at"
        )

        assert first_at is not None
        assert last_at is not None


class TestPostToolUseStatePersistence:
    def test_persists_tool_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        tool_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PostToolUse",
            "cwd": str(hook_test_env.tmp_path),
            "tool_name": "Read",
            "tool_input": {"file_path": "/test.py"},
            "tool_response": {"content": "test content"},
            "tool_use_id": "tool-123",
        }

        result = run_hook("post_tool_use", tool_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        total_count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.tools.total_count"
        )
        read_count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.tools.Read.count"
        )
        last_tool = query_session_store(
            db_path, hook_test_env.session_id, "oaps.tools.last_tool"
        )

        assert total_count == 1
        assert read_count == 1
        assert last_tool == "Read"

    def test_persists_subagent_spawn_for_task_tool(
        self, hook_test_env: HookTestEnv
    ) -> None:
        run_session_start(hook_test_env)

        tool_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PostToolUse",
            "cwd": str(hook_test_env.tmp_path),
            "tool_name": "Task",
            "tool_input": {"prompt": "do something"},
            "tool_response": {"result": "done"},
            "tool_use_id": "tool-456",
        }

        run_hook("post_tool_use", tool_input, hook_test_env)

        db_path = get_state_db_path(hook_test_env)
        spawn_count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.subagents.spawn_count"
        )

        assert spawn_count == 1


class TestPermissionRequestStatePersistence:
    def test_persists_permission_request_count(
        self, hook_test_env: HookTestEnv
    ) -> None:
        run_session_start(hook_test_env)

        perm_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PermissionRequest",
            "cwd": str(hook_test_env.tmp_path),
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /"},
            "tool_use_id": "tool-789",
        }

        result = run_hook("permission_request", perm_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.permissions.request_count"
        )
        last_tool = query_session_store(
            db_path, hook_test_env.session_id, "oaps.permissions.last_tool"
        )

        assert count == 1
        assert last_tool == "Bash"


class TestNotificationStatePersistence:
    def test_persists_notification_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        notif_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "Notification",
            "cwd": str(hook_test_env.tmp_path),
            "message": "test notification",
            "notification_type": "permission_prompt",
        }

        result = run_hook("notification", notif_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.notifications.count"
        )
        type_count = query_session_store(
            db_path,
            hook_test_env.session_id,
            "oaps.notifications.permission_prompt.count",
        )

        assert count == 1
        assert type_count == 1


class TestStopStatePersistence:
    def test_persists_stop_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        stop_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "Stop",
            "cwd": str(hook_test_env.tmp_path),
            "stop_hook_active": True,
        }

        result = run_hook("stop", stop_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.session.stop_count"
        )

        assert count == 1


class TestSubagentStopStatePersistence:
    def test_persists_subagent_stop_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        subagent_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "SubagentStop",
            "cwd": str(hook_test_env.tmp_path),
            "stop_hook_active": True,
            "agent_id": "subagent-123",
        }

        result = run_hook("subagent_stop", subagent_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.subagents.stop_count"
        )

        assert count == 1


class TestPreCompactStatePersistence:
    def test_persists_compaction_count(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        compact_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PreCompact",
            "cwd": str(hook_test_env.tmp_path),
            "trigger": "manual",
            "custom_instructions": "",
        }

        result = run_hook("pre_compact", compact_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = get_state_db_path(hook_test_env)
        count = query_session_store(
            db_path, hook_test_env.session_id, "oaps.session.compaction_count"
        )

        assert count == 1

    def test_outputs_statistics_context(self, hook_test_env: HookTestEnv) -> None:
        run_session_start(hook_test_env)

        # Run some prompts and tools to populate statistics
        prompt_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "UserPromptSubmit",
            "cwd": str(hook_test_env.tmp_path),
            "prompt": "test prompt",
        }
        run_hook("user_prompt_submit", prompt_input, hook_test_env)

        tool_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PostToolUse",
            "cwd": str(hook_test_env.tmp_path),
            "tool_name": "Read",
            "tool_input": {"file_path": "/test.py"},
            "tool_response": {"content": "test content"},
            "tool_use_id": "tool-123",
        }
        run_hook("post_tool_use", tool_input, hook_test_env)

        # Then run pre_compact
        compact_input = {
            "session_id": hook_test_env.session_id,
            "transcript_path": str(hook_test_env.tmp_path / "transcript.json"),
            "permission_mode": "default",
            "hook_event_name": "PreCompact",
            "cwd": str(hook_test_env.tmp_path),
            "trigger": "manual",
            "custom_instructions": "",
        }

        result = run_hook("pre_compact", compact_input, hook_test_env)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        # Parse JSON output
        output: dict[str, object] = json.loads(result.stdout)  # pyright: ignore[reportAny]
        assert isinstance(output, dict)
        assert "hookSpecificOutput" in output
        hook_output: dict[str, object] = output["hookSpecificOutput"]  # pyright: ignore[reportAssignmentType]
        assert isinstance(hook_output, dict)
        assert "additionalContext" in hook_output

        context: str = hook_output["additionalContext"]  # pyright: ignore[reportAssignmentType]
        assert isinstance(context, str)
        assert "=== OAPS Session Statistics ===" in context
        assert "Prompts:" in context
        assert "Tools:" in context
        assert "Read:" in context  # Tool count should be present
