"""Integration tests for the hooks CLI."""

import json
import os
import subprocess
import uuid
from pathlib import Path


def init_git_repo(path: Path) -> None:
    """Initialize a minimal git repository in the given path."""
    subprocess.run(
        ["git", "init"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    # Configure git user for the repo
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )


class TestHooksCLISessionStart:
    def test_creates_env_file(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        transcript_path = str(tmp_path / "transcript.json")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        env_file = claude_home / f"session-env/{session_id}/hook-1.sh"
        assert env_file.exists()

        env_content = env_file.read_text()
        assert f"CLAUDE_SESSION_ID={session_id}" in env_content
        assert f"CLAUDE_TRANSCRIPT_PATH={transcript_path}" in env_content

    def test_outputs_session_start_response(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        hook_output = output["hookSpecificOutput"]
        assert "additionalContext" in hook_output
        additional_context = hook_output["additionalContext"]
        assert f"Claude Code session ID: {session_id}" in additional_context

    def test_creates_log_file(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        log_file = tmp_path / ".oaps" / "logs" / "hooks.log"
        assert log_file.exists()

        log_content = log_file.read_text()
        assert "hook_started" in log_content
        assert "hook_completed" in log_content

    def test_env_file_is_executable(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        env_file = claude_home / f"session-env/{session_id}/hook-1.sh"
        mode = env_file.stat().st_mode
        assert mode & 0o755 == 0o755

    def test_uses_claude_env_file_when_set(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()
        custom_env_dir = tmp_path / "custom_env"
        custom_env_dir.mkdir()

        session_id = str(uuid.uuid4())
        custom_env_file = custom_env_dir / "session.sh"

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)
        env["CLAUDE_ENV_FILE"] = str(custom_env_file)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert custom_env_file.exists()

    def test_creates_session_store_database(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

        db_path = tmp_path / ".oaps" / "state.db"
        assert db_path.exists()

        # Verify it's a valid SQLite database with the expected schema
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='state_store'"
        )
        tables = cursor.fetchall()
        conn.close()

        assert len(tables) == 1
        assert tables[0][0] == "state_store"


class TestHooksCLISessionEnd:
    def test_session_end_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "SessionEnd",
                "cwd": str(tmp_path),
                "reason": "clear",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_end"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_session_end_no_env_file(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        session_id = str(uuid.uuid4())
        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "SessionEnd",
                "cwd": str(tmp_path),
                "reason": "clear",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_end"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0

        # No env file should be created for session_end
        env_file = claude_home / f"session-env/{session_id}/hook-1.sh"
        assert not env_file.exists()


class TestHooksCLIErrorHandling:
    def test_invalid_event_type_exits_2(self) -> None:
        result = subprocess.run(
            ["uv", "run", "oaps-hook", "invalid_event"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 2
        # The error mentions "invalid" in some form
        assert "invalid" in result.stderr.lower()

    def test_invalid_json_exits_128_gracefully(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input="not valid json",
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        # Should exit 128 (catastrophic failure that's handled gracefully)
        assert result.returncode == 128

    def test_missing_required_field_exits_128_gracefully(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        # Missing session_id
        stdin_data = json.dumps(
            {
                "transcript_path": str(tmp_path / "transcript.json"),
                "source": "startup",
            }
        )

        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home)

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "session_start"],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=str(tmp_path),
        )

        # Should exit 128 (catastrophic failure that's handled gracefully)
        assert result.returncode == 128

    def test_missing_argument_exits_2(self) -> None:
        result = subprocess.run(
            ["uv", "run", "oaps-hook"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 2
        stderr_lower = result.stderr.lower()
        assert "required" in stderr_lower or "arguments" in stderr_lower


class TestHooksCLIOtherEvents:
    def test_pre_tool_use_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "PreToolUse",
                "cwd": str(tmp_path),
                "tool_name": "Read",
                "tool_input": {"file_path": "/test.py"},
                "tool_use_id": "tool-123",
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "pre_tool_use"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_post_tool_use_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "PostToolUse",
                "cwd": str(tmp_path),
                "tool_name": "Read",
                "tool_input": {"file_path": "/test.py"},
                "tool_response": {"content": "test content"},
                "tool_use_id": "tool-123",
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "post_tool_use"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_user_prompt_submit_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(tmp_path),
                "prompt": "test prompt",
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "user_prompt_submit"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_notification_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "Notification",
                "cwd": str(tmp_path),
                "message": "test notification",
                "notification_type": "permission_prompt",
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "notification"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_stop_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "Stop",
                "cwd": str(tmp_path),
                "stop_hook_active": True,
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "stop"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_pre_compact_exits_0(
        self,
        tmp_path: Path,
    ) -> None:
        init_git_repo(tmp_path)

        stdin_data = json.dumps(
            {
                "session_id": str(uuid.uuid4()),
                "transcript_path": str(tmp_path / "transcript.json"),
                "permission_mode": "default",
                "hook_event_name": "PreCompact",
                "cwd": str(tmp_path),
                "trigger": "manual",
                "custom_instructions": "",
            }
        )

        result = subprocess.run(
            ["uv", "run", "oaps-hook", "pre_compact"],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
