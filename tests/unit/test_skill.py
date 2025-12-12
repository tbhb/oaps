from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.skill import is_project_skill

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.unit
class TestIsProjectSkill:
    def test_returns_true_for_project_skill(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "oaps.skill.get_oaps_dir",
            return_value=Path("/project/.oaps"),
        )
        skill_dir = Path("/project/.oaps/claude/skills/test-skill")
        assert is_project_skill(skill_dir) is True

    def test_returns_false_for_plugin_skill(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "oaps.skill.get_oaps_dir",
            return_value=Path("/project/.oaps"),
        )
        skill_dir = Path("/home/user/.claude/plugins/oaps/skills/test-skill")
        assert is_project_skill(skill_dir) is False
