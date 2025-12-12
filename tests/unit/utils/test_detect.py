import subprocess
import sys
from typing import TYPE_CHECKING

from oaps.utils._detect import detect_tooling

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class TestDetectTooling:
    def test_includes_python_version(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.run")
        result = detect_tooling()
        expected_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert result["python"] == expected_version

    def test_successful_tool_detection(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "basedpyright 1.10.3\n"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()

        assert result["basedpyright"] == "1.10.3"
        assert mock_run.call_count == 4  # basedpyright, codespell, ruff, pytest

    def test_extracts_version_from_multiline_output(
        self, mocker: MockerFixture
    ) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "pytest 8.0.0\nsome other line\n"

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert result["pytest"] == "8.0.0"

    def test_extracts_version_from_single_word_output(
        self, mocker: MockerFixture
    ) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1.2.3\n"

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert result["basedpyright"] == "1.2.3"

    def test_handles_empty_stdout(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert result["basedpyright"] == "installed"

    def test_handles_whitespace_only_stdout(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n  "

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert result["basedpyright"] == "installed"

    def test_failed_tool_detection_nonzero_return(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error: command not found"

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert result["basedpyright"] is None
        assert result["codespell"] is None
        assert result["ruff"] is None
        assert result["pytest"] is None

    def test_handles_timeout_expired(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="test", timeout=5),
        )
        result = detect_tooling()
        assert result["basedpyright"] is None
        assert result["codespell"] is None
        assert result["ruff"] is None
        assert result["pytest"] is None

    def test_handles_file_not_found(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.run", side_effect=FileNotFoundError)
        result = detect_tooling()
        assert result["basedpyright"] is None
        assert result["codespell"] is None
        assert result["ruff"] is None
        assert result["pytest"] is None

    def test_handles_blocking_io_error(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.run", side_effect=BlockingIOError)
        mocker.patch("time.sleep")  # Speed up retries
        result = detect_tooling()
        assert result["basedpyright"] is None
        assert result["codespell"] is None
        assert result["ruff"] is None
        assert result["pytest"] is None

    def test_subprocess_run_called_with_correct_params(
        self, mocker: MockerFixture
    ) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "basedpyright 1.10.3"

        mock_run = mocker.patch("subprocess.run", return_value=mock_result)
        detect_tooling()

        # Check first call (basedpyright)
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == ["uv", "run", "basedpyright", "--version"]
        assert first_call[1]["capture_output"] is True
        assert first_call[1]["text"] is True
        assert first_call[1]["timeout"] == 5
        assert first_call[1]["check"] is False

    def test_all_tools_in_result(self, mocker: MockerFixture) -> None:
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "tool 1.0.0"

        mocker.patch("subprocess.run", return_value=mock_result)
        result = detect_tooling()
        assert "python" in result
        assert "basedpyright" in result
        assert "codespell" in result
        assert "ruff" in result
        assert "pytest" in result

    def test_mixed_success_and_failure(self, mocker: MockerFixture) -> None:
        def mock_run_side_effect(
            cmd: list[str], *args: object, **kwargs: object
        ) -> MagicMock:
            mock_result = mocker.MagicMock()
            if "basedpyright" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "basedpyright 1.10.3"
            elif "ruff" in cmd:
                mock_result.returncode = 1
                mock_result.stdout = ""
            elif "pytest" in cmd:
                mock_result.returncode = 0
                mock_result.stdout = "pytest 8.0.0"
            return mock_result

        mocker.patch("subprocess.run", side_effect=mock_run_side_effect)
        result = detect_tooling()
        assert result["basedpyright"] == "1.10.3"
        assert result["ruff"] is None
        assert result["pytest"] == "8.0.0"
