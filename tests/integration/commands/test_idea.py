# pyright: reportAny=false, reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
"""Integration tests for the idea command."""

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING
from unittest.mock import patch

import pendulum
import pytest

from oaps.cli._commands._context import CLIContext
from oaps.cli._commands._idea._models import (
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaStatus,
    IdeaType,
)
from oaps.cli._commands._idea._storage import save_idea, save_index
from oaps.config import Config

from tests.conftest import OapsProject

if TYPE_CHECKING:
    from pendulum import DateTime

FreezeTimeFunc = Callable[[int, int, int, int, int, int], "DateTime"]


@pytest.fixture
def freeze_time(monkeypatch: pytest.MonkeyPatch) -> FreezeTimeFunc:
    """Return a function to freeze pendulum.now() to a fixed time."""

    def _freeze(
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> DateTime:
        fixed = pendulum.datetime(year, month, day, hour, minute, second, tz="UTC")

        def mock_now(tz: str) -> DateTime:
            return fixed if tz == "UTC" else pendulum.now(tz)

        monkeypatch.setattr("pendulum.now", mock_now)
        return fixed

    return _freeze


@pytest.fixture(autouse=True)
def setup_cli_context(oaps_project: OapsProject) -> Generator[None]:
    """Set up CLI context with ideas config for tests."""
    config = Config.from_dict(
        {
            "ideas": {
                "tags": {
                    "productivity": "Ideas related to improving efficiency",
                    "ai": "Ideas involving artificial intelligence",
                    "automation": "Ideas for automating processes",
                }
            }
        }
    )
    ctx = CLIContext(config=config, project_root=oaps_project.root)
    CLIContext.set_current(ctx)
    yield
    CLIContext.reset()


class TestIdeaTags:
    def test_displays_all_tags(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("idea", "tags")

        captured = capsys.readouterr()
        assert "productivity" in captured.out
        assert "ai" in captured.out
        assert "automation" in captured.out

    def test_tags_include_descriptions(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("idea", "tags")

        captured = capsys.readouterr()
        assert "efficiency" in captured.out
        assert "artificial intelligence" in captured.out


class TestIdeaResume:
    def test_resume_shows_help_without_ideas(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        # Patch get_ideas_dir to use test directory
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "resume")

        captured = capsys.readouterr()
        assert "No active ideas found" in captured.out

    def test_resume_shows_most_recent_idea(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
        freeze_time,
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        # Create a test idea
        fm = IdeaFrontmatter(
            id="20241218-120000-test-idea",
            title="My Test Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "20241218-120000-test-idea.md", fm, "# Content")

        # Create index
        entries = [
            IdeaIndexEntry(
                id="20241218-120000-test-idea",
                title="My Test Idea",
                status="seed",
                type="technical",
                tags=(),
                file_path="20241218-120000-test-idea.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
        ]

        freeze_time(2024, 12, 18, 15, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

            with patch(
                "oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir
            ):
                oaps_cli("idea", "resume")

        captured = capsys.readouterr()
        assert "My Test Idea" in captured.out
        assert "Resume Context" in captured.out


class TestIdeaList:
    def test_list_shows_no_ideas_message(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "list")

        captured = capsys.readouterr()
        assert "No ideas found" in captured.out

    def test_list_shows_ideas(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
        freeze_time,
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        entries = [
            IdeaIndexEntry(
                id="idea-1",
                title="First Idea",
                status="seed",
                type="technical",
                tags=("python",),
                file_path="idea-1.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            ),
            IdeaIndexEntry(
                id="idea-2",
                title="Second Idea",
                status="exploring",
                type="product",
                tags=("design",),
                file_path="idea-2.md",
                created="2024-12-18T13:00:00Z",
                updated="2024-12-18T14:00:00Z",
            ),
        ]

        freeze_time(2024, 12, 18, 15, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

            with patch(
                "oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir
            ):
                oaps_cli("idea", "list")

        captured = capsys.readouterr()
        assert "First Idea" in captured.out
        assert "Second Idea" in captured.out


class TestIdeaShow:
    def test_show_displays_idea(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        fm = IdeaFrontmatter(
            id="show-test-idea",
            title="Show Test Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.PRODUCT,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T13:00:00Z",
            tags=("ui", "design"),
        )
        save_idea(
            ideas_dir / "show-test-idea.md", fm, "# Body Content\n\nDetails here."
        )

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "show", "show-test-idea")

        captured = capsys.readouterr()
        assert "Show Test Idea" in captured.out
        assert "exploring" in captured.out
        assert "product" in captured.out
        assert "Body Content" in captured.out

    def test_show_error_for_nonexistent_idea(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "show", "nonexistent-idea")

        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestIdeaSearch:
    def test_search_finds_matching_ideas(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        fm = IdeaFrontmatter(
            id="search-test",
            title="Searchable Test Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            tags=("unique-tag",),
        )
        save_idea(ideas_dir / "search-test.md", fm, "# Contains unique keyword")

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "search", "unique")

        captured = capsys.readouterr()
        assert "Searchable Test Idea" in captured.out

    def test_search_no_results(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "search", "nonexistent-query")

        captured = capsys.readouterr()
        assert "No ideas match" in captured.out


class TestIdeaArchive:
    def test_archive_updates_status(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
        freeze_time,
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        fm = IdeaFrontmatter(
            id="archive-test",
            title="To Be Archived",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "archive-test.md", fm, "# Content")

        entries = [
            IdeaIndexEntry(
                id="archive-test",
                title="To Be Archived",
                status="seed",
                type="technical",
                tags=(),
                file_path="archive-test.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
        ]

        freeze_time(2024, 12, 18, 15, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

            with patch(
                "oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir
            ):
                oaps_cli("idea", "archive", "archive-test")

        captured = capsys.readouterr()
        assert "Archived idea" in captured.out


class TestIdeaLink:
    def test_link_creates_bidirectional_relationship(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        fm1 = IdeaFrontmatter(
            id="idea-a",
            title="Idea A",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        fm2 = IdeaFrontmatter(
            id="idea-b",
            title="Idea B",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "idea-a.md", fm1, "# Idea A content")
        save_idea(ideas_dir / "idea-b.md", fm2, "# Idea B content")

        with (
            patch(
                "oaps.cli._commands._idea._storage.get_ideas_dir",
                return_value=ideas_dir,
            ),
            patch("oaps.cli._commands._idea.get_ideas_dir", return_value=ideas_dir),
        ):
            oaps_cli("idea", "link", "idea-a", "idea-b")

        captured = capsys.readouterr()
        assert "Linked ideas" in captured.out


class TestIdeaTagDescribe:
    def test_tag_describe_shows_tag_details(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            oaps_cli("idea", "tag-describe", "productivity")

        captured = capsys.readouterr()
        assert "#productivity" in captured.out
        assert "efficiency" in captured.out

    def test_tag_describe_error_for_unknown_tag(
        self,
        oaps_project: OapsProject,
        capsys: pytest.CaptureFixture[str],
        oaps_cli: Callable[..., None],
    ) -> None:
        oaps_cli("idea", "tag-describe", "nonexistent-tag")

        captured = capsys.readouterr()
        assert "not found" in captured.out
