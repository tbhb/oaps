"""Unit tests for the hooks CLI."""

import json
import uuid
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from oaps.enums import HookEventType
from oaps.exceptions import BlockHook

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestMain:
    def test_keyboard_interrupt_exits_130(self) -> None:
        from oaps.hooks.cli import main

        with (
            patch("oaps.hooks.cli._run_hook_cli", side_effect=KeyboardInterrupt),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 130

    def test_import_error_exits_128_gracefully(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from oaps.hooks.cli import main

        with (
            patch(
                "oaps.hooks.cli._run_hook_cli",
                side_effect=ImportError("No module named 'broken'"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 128
        captured = capsys.readouterr()
        assert "ImportError" in captured.err
        assert "No module named 'broken'" in captured.err

    def test_syntax_error_exits_128_gracefully(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from oaps.hooks.cli import main

        with (
            patch(
                "oaps.hooks.cli._run_hook_cli",
                side_effect=SyntaxError("invalid syntax"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 128
        captured = capsys.readouterr()
        assert "SyntaxError" in captured.err

    def test_generic_exception_exits_128_gracefully(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from oaps.hooks.cli import main

        with (
            patch(
                "oaps.hooks.cli._run_hook_cli",
                side_effect=RuntimeError("unexpected error"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 128
        captured = capsys.readouterr()
        assert "RuntimeError" in captured.err
        assert "unexpected error" in captured.err


class TestBlockHookException:
    def test_raise_with_message(self) -> None:
        msg = "test message"
        with pytest.raises(BlockHook, match=msg):
            raise BlockHook(msg)

    def test_str_returns_message(self) -> None:
        error = BlockHook("blocking reason")
        assert str(error) == "blocking reason"


class TestArgParsing:
    def test_valid_event_type_parses_successfully(self, fs: FakeFilesystem) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project/.oaps/logs")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        assert exc_info.value.code == 0

    def test_invalid_event_type_exits_2(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with (
            patch("sys.argv", ["oaps-hook", "invalid_event"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        # The error message mentions "invalid" and the bad value
        assert "invalid" in captured.err.lower()
        assert "invalid_event" in captured.err

    def test_all_event_types_are_valid_choices(self) -> None:
        import argparse

        for event in HookEventType:
            parser = argparse.ArgumentParser()
            parser.add_argument(
                "event",
                choices=[e.value for e in HookEventType],
            )
            args = parser.parse_args([event.value])
            assert args.event == event.value


class TestLoggingSetup:
    def test_log_directory_created(self, fs: FakeFilesystem) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            pytest.raises(SystemExit),
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        log_dir = Path("/project/.oaps/logs")
        assert log_dir.exists()

    def test_log_file_created(self, fs: FakeFilesystem) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            pytest.raises(SystemExit),
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        log_file = Path("/project/.oaps/logs/hooks.log")
        assert log_file.exists()


class TestRunHookCLI:
    def test_block_hook_exits_2_with_message(
        self,
        fs: FakeFilesystem,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project/.oaps/logs")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.hooks.cli._execute_hook",
                side_effect=BlockHook("Operation blocked for testing"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Operation blocked for testing" in captured.err

    def test_generic_exception_in_hook_exits_0(self, fs: FakeFilesystem) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project/.oaps/logs")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.hooks.cli._execute_hook",
                side_effect=RuntimeError("Unexpected hook failure"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        # Generic exceptions in _execute_hook exit 0 to not break Claude Code
        assert exc_info.value.code == 0

    def test_successful_hook_exits_0(self, fs: FakeFilesystem) -> None:
        session_id = str(uuid.uuid4())
        transcript_path = "/project/transcript.json"
        fs.create_dir("/project/.oaps/logs")

        stdin_data = json.dumps(
            {
                "session_id": session_id,
                "transcript_path": transcript_path,
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch("oaps.hooks.cli._execute_hook"),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import _run_hook_cli

            _run_hook_cli()

        assert exc_info.value.code == 0


class TestExecuteHook:
    def _make_hooks_config(self) -> MagicMock:
        """Create a mock HooksConfiguration with empty rules."""
        config = MagicMock()
        config.rules = []
        return config

    def test_session_start_creates_env_file(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=Path("/project/transcript.json"),
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = Path(f"/claude_home/session-env/{session_id}/hook-1.sh")
            assert env_file.exists()

    def test_session_start_env_file_contains_vars(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()
            transcript_path = Path("/project/transcript.json")

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=transcript_path,
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = Path(f"/claude_home/session-env/{session_id}/hook-1.sh")
            content = env_file.read_text()

            assert f"CLAUDE_SESSION_ID={session_id}" in content
            assert f"CLAUDE_TRANSCRIPT_PATH={transcript_path}" in content
            assert "CLAUDE_TRANSCRIPT_DIR=/project" in content
            assert "OAPS_DIR=" in content

    def test_session_start_outputs_json(
        self,
        fs: FakeFilesystem,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=Path("/project/transcript.json"),
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert "hookSpecificOutput" in output
            assert "additionalContext" in output["hookSpecificOutput"]
            additional_context = output["hookSpecificOutput"]["additionalContext"]
            assert f"session ID: {session_id}" in additional_context

    def test_session_start_env_file_executable(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=Path("/project/transcript.json"),
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = Path(f"/claude_home/session-env/{session_id}/hook-1.sh")
            # Check file mode includes execute permission (0o755)
            mode = env_file.stat().st_mode
            assert mode & 0o755 == 0o755

    def test_session_start_uses_claude_env_file_when_set(
        self, fs: FakeFilesystem
    ) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/custom/env")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict(
                "os.environ",
                {
                    "CLAUDE_HOME": "/claude_home",
                    "CLAUDE_ENV_FILE": "/custom/env/session.sh",
                },
            ),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=Path("/project/transcript.json"),
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = Path("/custom/env/session.sh")
            assert env_file.exists()

    def test_session_start_fallback_to_home_dir(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        # Don't set CLAUDE_HOME - should fall back to ~/.claude
        home_dir = Path.home()
        fs.create_dir(str(home_dir / ".claude"))
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=MockStateStore(session_id=None),
            ),  # Mock project store for SessionStart
        ):
            # Ensure CLAUDE_HOME is not set
            import os

            os.environ.pop("CLAUDE_HOME", None)
            os.environ.pop("CLAUDE_ENV_FILE", None)

            session_id = uuid.uuid4()

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=Path("/project/transcript.json"),
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = home_dir / ".claude" / f"session-env/{session_id}/hook-1.sh"
            assert env_file.exists()

    def test_non_session_start_no_env_file(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
        ):
            session_id = str(uuid.uuid4())

            from oaps.hooks import SessionEndInput

            hook_input = SessionEndInput(
                session_id=session_id,
                transcript_path="/project/transcript.json",
                permission_mode="default",
                hook_event_name="SessionEnd",
                cwd="/project",
                reason="clear",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_END,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            env_file = Path(f"/claude_home/session-env/{session_id}/hook-1.sh")
            assert not env_file.exists()

    def test_creates_hook_context(self, fs: FakeFilesystem) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
        ):
            session_id = str(uuid.uuid4())

            from oaps.hooks import SessionEndInput

            hook_input = SessionEndInput(
                session_id=session_id,
                transcript_path="/project/transcript.json",
                permission_mode="default",
                hook_event_name="SessionEnd",
                cwd="/project",
                reason="clear",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            # Just verify it doesn't raise - HookContext creation is tested
            _execute_hook(
                HookEventType.SESSION_END,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

    def test_session_start_stores_transcript_dir_in_project_state(
        self, fs: FakeFilesystem
    ) -> None:
        from oaps.hooks.cli import _execute_hook
        from oaps.utils import MockStateStore

        fs.create_dir("/claude_home")
        fs.create_dir("/project/.oaps/state/sessions")

        # Track what gets stored in project state
        project_store = MockStateStore(session_id=None)

        with (
            patch.dict("os.environ", {"CLAUDE_HOME": "/claude_home"}),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            patch(
                "oaps.utils.SQLiteStateStore", MockStateStore
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_state_store",
                lambda _path, **_kwargs: MockStateStore(),
            ),  # Use MockStateStore for pyfakefs
            patch(
                "oaps.utils.create_project_store",
                return_value=project_store,
            ),  # Mock project store for SessionStart
        ):
            session_id = uuid.uuid4()
            transcript_path = Path("/Users/tony/.claude/projects/test/session.jsonl")

            from oaps.hooks import SessionStartInput

            hook_input = SessionStartInput(
                session_id=session_id,
                transcript_path=transcript_path,
                hook_event_name="SessionStart",
                cwd=None,
                source="startup",
            )

            mock_hook_logger = MagicMock()
            mock_session_logger = MagicMock()
            mock_storage_logger = MagicMock()
            hooks_config = self._make_hooks_config()

            _execute_hook(
                HookEventType.SESSION_START,
                hook_input,
                hooks_config,
                mock_hook_logger,
                mock_session_logger,
                mock_storage_logger,
            )

            # Verify transcript directory was stored in project state
            assert "oaps.claude.transcript_dir" in project_store
            stored_dir = project_store["oaps.claude.transcript_dir"]
            assert stored_dir == "/Users/tony/.claude/projects/test"


class TestInputValidation:
    def test_invalid_json_exits_128_via_main(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project/.oaps/logs")

        with (
            patch("sys.stdin", StringIO("not valid json")),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import main

            main()

        # JSON decode error is caught by main() and exits 128
        assert exc_info.value.code == 128

    def test_missing_required_field_exits_128_via_main(
        self, fs: FakeFilesystem
    ) -> None:
        fs.create_dir("/project/.oaps/logs")

        # Missing session_id
        stdin_data = json.dumps(
            {
                "transcript_path": "/project/transcript.json",
                "source": "startup",
            }
        )

        with (
            patch("sys.stdin", StringIO(stdin_data)),
            patch("sys.argv", ["oaps-hook", "session_start"]),
            patch(
                "oaps.utils._paths.get_worktree_root",
                return_value=Path("/project"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from oaps.hooks.cli import main

            main()

        # Validation error is caught by main() and exits 128
        assert exc_info.value.code == 128
