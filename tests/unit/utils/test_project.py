from pathlib import Path
from typing import TYPE_CHECKING

from oaps.utils._project import is_oaps_project

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest_mock import MockerFixture


class TestIsOapsProject:
    def test_returns_true_when_oaps_dir_exists(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_dir = Path("/test/project/.oaps")
        fs.create_dir(oaps_dir)
        mocker.patch("oaps.utils._project.get_oaps_dir", return_value=oaps_dir)
        assert is_oaps_project() is True

    def test_returns_false_when_oaps_dir_not_exists(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_dir = Path("/test/project/.oaps")
        mocker.patch("oaps.utils._project.get_oaps_dir", return_value=oaps_dir)
        assert is_oaps_project() is False

    def test_returns_false_when_oaps_path_is_file(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        oaps_path = Path("/test/project/.oaps")
        fs.create_file(oaps_path)
        mocker.patch("oaps.utils._project.get_oaps_dir", return_value=oaps_path)
        assert is_oaps_project() is False
