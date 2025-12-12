# pyright: reportAny=false
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.config import Config, ConfigSourceName
from oaps.exceptions import ConfigLoadError, ConfigValidationError

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


class TestConfigFromFile:
    def test_loads_valid_toml_file(self, fs: FakeFilesystem) -> None:
        content = """
[logging]
level = "debug"
format = "text"

[project]
name = "test-project"
"""
        path = Path("/test/config.toml")
        fs.create_file(path, contents=content)

        config = Config.from_file(path)

        assert config.logging.level.value == "debug"
        assert config.logging.format.value == "text"
        assert config.project.name == "test-project"

    def test_raises_file_not_found_for_missing_file(self, fs: FakeFilesystem) -> None:
        path = Path("/test/missing.toml")

        with pytest.raises(FileNotFoundError):
            Config.from_file(path)

    def test_raises_config_load_error_for_invalid_toml(
        self, fs: FakeFilesystem
    ) -> None:
        content = """
[section
key = "unclosed bracket"
"""
        path = Path("/test/invalid.toml")
        fs.create_file(path, contents=content)

        with pytest.raises(ConfigLoadError):
            Config.from_file(path)

    def test_raises_config_validation_error_for_invalid_values(
        self, fs: FakeFilesystem
    ) -> None:
        content = """
[logging]
level = "invalid_level"
"""
        path = Path("/test/invalid_value.toml")
        fs.create_file(path, contents=content)

        with pytest.raises(ConfigValidationError):
            Config.from_file(path)

    def test_skips_validation_when_validate_false(self, fs: FakeFilesystem) -> None:
        content = """
[logging]
level = "invalid_level"
"""
        path = Path("/test/invalid_value.toml")
        fs.create_file(path, contents=content)

        config = Config.from_file(path, validate=False)

        # Should load without error, parsing will fall back to defaults
        assert config.logging.level.value == "info"  # Fallback value

    def test_creates_source_tracking(self, fs: FakeFilesystem) -> None:
        content = """
[logging]
level = "debug"
"""
        path = Path("/test/config.toml")
        fs.create_file(path, contents=content)

        config = Config.from_file(path)

        assert len(config.sources) == 1
        source = config.sources[0]
        assert source.name == ConfigSourceName.PROJECT
        assert source.path == path
        assert source.exists is True
        assert source.values == {"logging": {"level": "debug"}}

    def test_merges_with_defaults(self, fs: FakeFilesystem) -> None:
        content = """
[logging]
level = "debug"
"""
        path = Path("/test/config.toml")
        fs.create_file(path, contents=content)

        config = Config.from_file(path)

        # Level is from file
        assert config.logging.level.value == "debug"
        # Format should be default (json)
        assert config.logging.format.value == "json"

    def test_loads_empty_file_with_defaults(self, fs: FakeFilesystem) -> None:
        path = Path("/test/empty.toml")
        fs.create_file(path, contents="")

        config = Config.from_file(path)

        # All values should be defaults
        assert config.logging.level.value == "info"
        assert config.logging.format.value == "json"
        assert config.project.name == ""
