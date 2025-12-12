"""Tests for oaps.utils._exec module."""

from pathlib import Path

import pytest

from oaps.utils import ScriptConfig, ScriptResult, run_script, truncate_output


class TestScriptConfig:
    def test_default_values(self) -> None:
        config = ScriptConfig()
        assert config.command is None
        assert config.script is None
        assert config.shell is None
        assert config.cwd is None
        assert config.env == {}
        assert config.stdin is None
        assert config.timeout_ms == 10000

    def test_with_command(self) -> None:
        config = ScriptConfig(command="echo hello")
        assert config.command == "echo hello"

    def test_with_script(self) -> None:
        config = ScriptConfig(script="#!/bin/bash\necho hello")
        assert config.script == "#!/bin/bash\necho hello"

    def test_frozen(self) -> None:
        config = ScriptConfig(command="echo hello")
        with pytest.raises(AttributeError):
            config.command = "echo world"  # pyright: ignore[reportAttributeAccessIssue]


class TestScriptResult:
    def test_success_result(self) -> None:
        result = ScriptResult(
            success=True,
            exit_code=0,
            stdout="hello\n",
            stderr="",
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.error is None
        assert result.timed_out is False
        assert result.command_not_found is False

    def test_timeout_result(self) -> None:
        result = ScriptResult(
            success=False,
            error="Command timed out after 10s",
            timed_out=True,
        )
        assert result.success is False
        assert result.timed_out is True
        assert result.exit_code is None

    def test_command_not_found_result(self) -> None:
        result = ScriptResult(
            success=False,
            error="nonexistent: command not found",
            command_not_found=True,
        )
        assert result.success is False
        assert result.command_not_found is True


class TestTruncateOutput:
    def test_empty_string(self) -> None:
        assert truncate_output("") == ""

    def test_short_string_unchanged(self) -> None:
        text = "hello world"
        assert truncate_output(text) == text

    def test_truncates_long_string(self) -> None:
        text = "x" * 200
        result = truncate_output(text, max_bytes=100)
        # Result is 100 bytes of content + truncation message
        assert len(result) < len(text)
        assert result.endswith("... [output truncated]")

    def test_preserves_utf8(self) -> None:
        text = "こんにちは" * 50  # Japanese characters
        result = truncate_output(text, max_bytes=50)
        # Should be valid UTF-8 after truncation
        result.encode("utf-8")  # Should not raise
        assert "... [output truncated]" in result


class TestRunScript:
    def test_executes_simple_command(self) -> None:
        config = ScriptConfig(command="echo hello")
        result = run_script(config)
        assert result.success is True
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_executes_multiline_script(self) -> None:
        config = ScriptConfig(
            script="""#!/bin/sh
echo line1
echo line2
"""
        )
        result = run_script(config)
        assert result.success is True
        assert "line1" in result.stdout
        assert "line2" in result.stdout

    def test_returns_error_without_command_or_script(self) -> None:
        config = ScriptConfig()
        result = run_script(config)
        assert result.success is False
        assert result.error == "No command or script specified"

    def test_captures_exit_code(self) -> None:
        config = ScriptConfig(command="exit 42", shell="/bin/sh")  # noqa: S604
        result = run_script(config)
        assert result.success is True
        assert result.exit_code == 42

    def test_captures_stderr(self) -> None:
        config = ScriptConfig(command="echo error >&2", shell="/bin/sh")  # noqa: S604
        result = run_script(config)
        assert result.success is True
        assert "error" in result.stderr

    def test_passes_environment_variables(self) -> None:
        config = ScriptConfig(  # noqa: S604
            command="echo $TEST_VAR",
            shell="/bin/sh",
            env={"TEST_VAR": "test_value"},
        )
        result = run_script(config)
        assert result.success is True
        assert "test_value" in result.stdout

    def test_uses_custom_shell(self) -> None:
        config = ScriptConfig(command="echo hello", shell="/bin/bash")  # noqa: S604
        result = run_script(config)
        assert result.success is True
        assert "hello" in result.stdout

    def test_passes_stdin(self) -> None:
        config = ScriptConfig(
            command="cat",
            stdin=b"input data",
        )
        result = run_script(config)
        assert result.success is True
        assert "input data" in result.stdout

    def test_handles_timeout(self) -> None:
        config = ScriptConfig(
            command="sleep 10",
            timeout_ms=100,
        )
        result = run_script(config)
        assert result.success is False
        assert result.timed_out is True
        assert "timed out" in (result.error or "").lower()

    def test_handles_command_not_found(self) -> None:
        config = ScriptConfig(command="nonexistent_command_xyz")
        result = run_script(config)
        assert result.success is False
        assert result.command_not_found is True

    def test_uses_cwd(self, tmp_path: Path) -> None:
        config = ScriptConfig(command="pwd", cwd=str(tmp_path))
        result = run_script(config)
        assert result.success is True
        assert str(tmp_path) in result.stdout

    def test_cleans_up_temp_script(self, tmp_path: Path) -> None:
        import tempfile

        # Before running, count files in temp directory
        temp_dir = tempfile.gettempdir()
        initial_files = set(Path(temp_dir).iterdir())

        config = ScriptConfig(script="echo temp script")
        result = run_script(config)

        # After running, verify no new .sh files remain
        final_files = set(Path(temp_dir).iterdir())
        new_sh_files = [f for f in (final_files - initial_files) if f.suffix == ".sh"]

        assert result.success is True
        assert len(new_sh_files) == 0, (
            f"Temp script files not cleaned up: {new_sh_files}"
        )
