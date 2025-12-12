"""Unit tests for logging utilities."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestCreateLogger:
    def test_creates_log_directory_if_missing(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        log_path = Path("/logs/test.log")
        assert not log_path.parent.exists()

        _ = _create_logger(str(log_path))

        assert log_path.parent.exists()

    def test_default_format_is_json(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        logger = _create_logger("/logs/test.log")

        # Log something and check it's JSON formatted
        logger.info("test_event", key="value")

        log_content = Path("/logs/test.log").read_text()
        assert '"event": "test_event"' in log_content
        assert '"key": "value"' in log_content

    def test_text_format(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        logger = _create_logger("/logs/test.log", log_format="text")

        logger.info("test_event", key="value")

        log_content = Path("/logs/test.log").read_text()
        # Text format uses ConsoleRenderer style
        assert "test_event" in log_content
        assert "key=value" in log_content

    def test_without_rotation_uses_simple_file(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        # Without rotation params, should use simple file append
        logger = _create_logger("/logs/test.log")

        logger.info("test_message")

        assert Path("/logs/test.log").exists()

    def test_rotation_requires_both_params(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        # Only max_bytes - should not rotate
        logger1 = _create_logger("/logs/test1.log", max_bytes=1000)
        logger1.info("test")
        # Should work but no rotation

        # Only backup_count - should not rotate
        logger2 = _create_logger("/logs/test2.log", backup_count=3)
        logger2.info("test")
        # Should work but no rotation


class TestCreateLoggerRotation:
    def test_with_rotation_uses_stdlib_logger(self, fs: FakeFilesystem) -> None:
        from oaps.utils._logging import _create_logger

        _ = _create_logger(
            "/logs/test.log",
            max_bytes=1000,
            backup_count=3,
        )

        # Check a logger with rotation was configured
        # We verify by checking the handlers
        for name in logging.root.manager.loggerDict:
            if name.startswith("oaps.test."):
                stdlib_logger = logging.getLogger(name)
                assert len(stdlib_logger.handlers) == 1
                handler = stdlib_logger.handlers[0]
                assert isinstance(handler, RotatingFileHandler)
                assert handler.maxBytes == 1000
                assert handler.backupCount == 3
                break


class TestCreateHooksLogger:
    def test_creates_hooks_log_file(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project")

        with patch(
            "oaps.utils._paths.get_worktree_root",
            return_value=Path("/project"),
        ):
            from oaps.utils._logging import create_hooks_logger
            from oaps.utils._paths import get_oaps_hooks_log_file

            hooks_log = get_oaps_hooks_log_file()
            assert not hooks_log.exists()

            logger = create_hooks_logger()
            logger.info("test")

            assert hooks_log.exists()

    def test_respects_log_level(
        self, fs: FakeFilesystem, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Clear OAPS_DEBUG to ensure log level is respected
        monkeypatch.delenv("OAPS_DEBUG", raising=False)

        fs.create_dir("/project2")

        with patch(
            "oaps.utils._paths.get_worktree_root",
            return_value=Path("/project2"),
        ):
            from oaps.utils._logging import create_hooks_logger
            from oaps.utils._paths import get_oaps_hooks_log_file

            logger = create_hooks_logger(level="error")

            # Debug should not be logged (filtered by wrapper_class)
            logger.debug("debug_level_message")

            # Error should be logged
            logger.error("error_level_message")

            hooks_log = get_oaps_hooks_log_file()
            content = hooks_log.read_text()
            assert "debug_level_message" not in content
            assert "error_level_message" in content

    def test_passes_rotation_params(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project")

        with patch(
            "oaps.utils._paths.get_worktree_root",
            return_value=Path("/project"),
        ):
            from oaps.utils._logging import create_hooks_logger

            _ = create_hooks_logger(
                max_bytes=5_000_000,
                backup_count=3,
            )

            # Find the rotating handler
            found = False
            for name in logging.root.manager.loggerDict:
                if name.startswith("oaps.hooks."):
                    stdlib_logger = logging.getLogger(name)
                    for handler in stdlib_logger.handlers:
                        if isinstance(handler, RotatingFileHandler):
                            assert handler.maxBytes == 5_000_000
                            assert handler.backupCount == 3
                            found = True
                            break
                    if found:
                        break

            assert found, "RotatingFileHandler not found"


class TestHooksConfigurationRotation:
    def test_default_rotation_disabled(self) -> None:
        from oaps.config import HooksConfiguration

        config = HooksConfiguration()

        assert config.log_max_bytes is None
        assert config.log_backup_count is None

    def test_rotation_config_fields(self) -> None:
        from oaps.config import HooksConfiguration

        config = HooksConfiguration(
            log_max_bytes=10_000_000,
            log_backup_count=5,
        )

        assert config.log_max_bytes == 10_000_000
        assert config.log_backup_count == 5

    def test_partial_rotation_config(self) -> None:
        from oaps.config import HooksConfiguration

        # Only max_bytes - rotation should not activate
        config1 = HooksConfiguration(log_max_bytes=10_000_000)
        assert config1.log_max_bytes == 10_000_000
        assert config1.log_backup_count is None

        # Only backup_count - rotation should not activate
        config2 = HooksConfiguration(log_backup_count=5)
        assert config2.log_max_bytes is None
        assert config2.log_backup_count == 5
