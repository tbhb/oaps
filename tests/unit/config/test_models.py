# pyright: reportAny=false
"""Unit tests for configuration data models.

These tests focus on our design decisions (default values, enum ordering)
rather than Python built-in behaviors (frozen dataclasses, StrEnum).
"""

from oaps.config import ConfigSourceName


class TestConfigSourceName:
    def test_precedence_order_highest_to_lowest(self) -> None:
        # This ordering is a critical design decision - CLI overrides ENV,
        # ENV overrides WORKTREE, etc. The enum definition order matters.
        members = list(ConfigSourceName)
        expected_order = [
            ConfigSourceName.CLI,
            ConfigSourceName.ENV,
            ConfigSourceName.WORKTREE,
            ConfigSourceName.LOCAL,
            ConfigSourceName.PROJECT,
            ConfigSourceName.USER,
            ConfigSourceName.DEFAULT,
        ]
        assert members == expected_order
