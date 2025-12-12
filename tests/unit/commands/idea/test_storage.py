# pyright: reportAny=false, reportUnknownVariableType=false
# pyright: reportTypedDictNotRequiredAccess=false, reportExplicitAny=false
"""Unit tests for idea storage functions."""

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from oaps.cli._commands._idea._models import (
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaReference,
    IdeaStatus,
    IdeaType,
    IdeaWorkflowState,
)
from oaps.cli._commands._idea._storage import (
    find_idea_by_id,
    frontmatter_to_dict,
    generate_idea_id,
    idea_filename,
    load_idea,
    load_index,
    parse_idea_frontmatter,
    rebuild_index,
    save_idea,
    save_index,
    slugify,
)
from oaps.exceptions import SpecIOError

from tests.conftest import OapsProject

if TYPE_CHECKING:
    from tests.unit.conftest import FreezeTimeFunc


class TestSlugify:
    def test_converts_to_lowercase(self) -> None:
        assert slugify("HELLO WORLD") == "hello-world"

    def test_replaces_spaces_with_hyphens(self) -> None:
        assert slugify("hello world") == "hello-world"

    def test_removes_special_characters(self) -> None:
        assert slugify("hello! @world#") == "hello-world"

    def test_collapses_multiple_hyphens(self) -> None:
        assert slugify("hello   world") == "hello-world"
        assert slugify("hello---world") == "hello-world"

    def test_removes_leading_trailing_hyphens(self) -> None:
        assert slugify("  hello world  ") == "hello-world"
        assert slugify("--hello--") == "hello"

    def test_limits_length_to_50(self) -> None:
        long_text = "a" * 100
        result = slugify(long_text)
        assert len(result) <= 50

    def test_handles_empty_string(self) -> None:
        assert slugify("") == ""

    def test_handles_only_special_characters(self) -> None:
        assert slugify("!@#$%") == ""

    def test_preserves_numbers(self) -> None:
        assert slugify("test123") == "test123"


class TestGenerateIdeaId:
    def test_creates_id_with_timestamp_and_slug(
        self, freeze_time: FreezeTimeFunc
    ) -> None:
        freeze_time(2024, 12, 18, 15, 30, 45)
        idea_id = generate_idea_id("My Test Idea")

        assert idea_id == "20241218-153045-my-test-idea"

    def test_uses_utc_timezone(self, freeze_time: FreezeTimeFunc) -> None:
        freeze_time(2024, 12, 18, 23, 59, 59)
        idea_id = generate_idea_id("Test")

        assert idea_id.startswith("20241218-235959-")

    def test_slugifies_title(self, freeze_time: FreezeTimeFunc) -> None:
        freeze_time(2024, 1, 1, 0, 0, 0)
        idea_id = generate_idea_id("HELLO World!!")

        assert idea_id == "20240101-000000-hello-world"


class TestIdeaFilename:
    def test_appends_md_extension(self) -> None:
        assert idea_filename("20241218-120000-test") == "20241218-120000-test.md"

    def test_works_with_complex_ids(self) -> None:
        idea_id = "20241218-153045-my-complex-idea-name"
        assert idea_filename(idea_id) == f"{idea_id}.md"


class TestParseIdeaFrontmatter:
    def test_parses_minimal_frontmatter(self) -> None:
        data: dict[str, Any] = {
            "id": "test-id",
            "title": "Test Title",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
        }
        fm = parse_idea_frontmatter(data)

        assert fm.id == "test-id"
        assert fm.title == "Test Title"
        assert fm.status == IdeaStatus.SEED
        assert fm.type == IdeaType.TECHNICAL
        assert fm.created == "2024-12-18T12:00:00Z"
        assert fm.updated == "2024-12-18T12:00:00Z"

    def test_parses_optional_author(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
            "author": "test-user",
        }
        fm = parse_idea_frontmatter(data)
        assert fm.author == "test-user"

    def test_parses_tags_as_tuple(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
            "tags": ["python", "testing"],
        }
        fm = parse_idea_frontmatter(data)
        assert fm.tags == ("python", "testing")

    def test_parses_related_ideas(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
            "related_ideas": ["idea-1", "idea-2"],
        }
        fm = parse_idea_frontmatter(data)
        assert fm.related_ideas == ("idea-1", "idea-2")

    def test_parses_references(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
            "references": [
                {"url": "https://example.com", "title": "Example"},
                {"url": "https://test.com", "title": "Test"},
            ],
        }
        fm = parse_idea_frontmatter(data)
        assert len(fm.references) == 2
        assert fm.references[0]["url"] == "https://example.com"
        assert fm.references[0]["title"] == "Example"

    def test_parses_workflow_state(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
            "workflow": {"phase": "exploring", "iteration": 2},
        }
        fm = parse_idea_frontmatter(data)
        assert fm.workflow is not None
        assert fm.workflow["phase"] == "exploring"
        assert fm.workflow["iteration"] == 2

    def test_defaults_status_to_seed(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "type": "technical",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
        }
        fm = parse_idea_frontmatter(data)
        assert fm.status == IdeaStatus.SEED

    def test_defaults_type_to_technical(self) -> None:
        data: dict[str, Any] = {
            "id": "test",
            "title": "Test",
            "status": "seed",
            "created": "2024-12-18T12:00:00Z",
            "updated": "2024-12-18T12:00:00Z",
        }
        fm = parse_idea_frontmatter(data)
        assert fm.type == IdeaType.TECHNICAL


class TestFrontmatterToDict:
    def test_converts_minimal_frontmatter(self) -> None:
        fm = IdeaFrontmatter(
            id="test-id",
            title="Test Title",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        result = frontmatter_to_dict(fm)

        assert result["id"] == "test-id"
        assert result["title"] == "Test Title"
        assert result["status"] == "seed"
        assert result["type"] == "technical"
        assert result["created"] == "2024-12-18T12:00:00Z"
        assert result["updated"] == "2024-12-18T12:00:00Z"
        assert result["tags"] == []
        assert result["related_ideas"] == []
        assert result["references"] == []
        assert "author" not in result
        assert "workflow" not in result

    def test_includes_author_when_present(self) -> None:
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            author="test-user",
        )
        result = frontmatter_to_dict(fm)
        assert result["author"] == "test-user"

    def test_converts_tags_to_list(self) -> None:
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            tags=("python", "testing"),
        )
        result = frontmatter_to_dict(fm)
        assert result["tags"] == ["python", "testing"]

    def test_converts_references_to_list_of_dicts(self) -> None:
        ref: IdeaReference = {"url": "https://example.com", "title": "Example"}
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            references=(ref,),
        )
        result = frontmatter_to_dict(fm)
        assert result["references"] == [
            {"url": "https://example.com", "title": "Example"}
        ]

    def test_includes_workflow_when_present(self) -> None:
        workflow: IdeaWorkflowState = {"phase": "exploring", "iteration": 1}
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            workflow=workflow,
        )
        result = frontmatter_to_dict(fm)
        assert result["workflow"] == {"phase": "exploring", "iteration": 1}


class TestLoadAndSaveIdea:
    def test_saves_and_loads_idea(self, oaps_project: OapsProject) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)
        path = ideas_dir / "test-idea.md"

        fm = IdeaFrontmatter(
            id="test-idea",
            title="Test Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        body = "# Test\n\nBody content here."

        save_idea(path, fm, body)
        loaded_fm, loaded_body = load_idea(path)

        assert loaded_fm.id == fm.id
        assert loaded_fm.title == fm.title
        assert loaded_fm.status == fm.status
        assert "Body content here" in loaded_body

    def test_load_raises_on_missing_file(self, oaps_project: OapsProject) -> None:
        path = oaps_project.oaps_dir / "nonexistent.md"

        with pytest.raises(SpecIOError):
            load_idea(path)

    def test_load_raises_on_no_frontmatter(self, oaps_project: OapsProject) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)
        path = ideas_dir / "no-frontmatter.md"
        path.write_text("# Just content\n\nNo frontmatter here.")

        with pytest.raises(ValueError, match="No frontmatter"):
            load_idea(path)


class TestLoadAndSaveIndex:
    def test_returns_empty_list_for_missing_index(
        self, oaps_project: OapsProject
    ) -> None:
        # Patch get_ideas_dir to use test directory
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            result = load_index()
        assert result == []

    def test_saves_and_loads_index(
        self, oaps_project: OapsProject, freeze_time: FreezeTimeFunc
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        entries = [
            IdeaIndexEntry(
                id="idea-1",
                title="Idea One",
                status="seed",
                type="technical",
                tags=("python",),
                file_path="idea-1.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            ),
            IdeaIndexEntry(
                id="idea-2",
                title="Idea Two",
                status="exploring",
                type="product",
                tags=("design", "ui"),
                file_path="idea-2.md",
                created="2024-12-18T13:00:00Z",
                updated="2024-12-18T14:00:00Z",
                author="test-user",
            ),
        ]

        freeze_time(2024, 12, 18, 15, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)
            loaded = load_index()

        assert len(loaded) == 2
        assert loaded[0].id == "idea-1"
        assert loaded[0].title == "Idea One"
        assert loaded[0].tags == ("python",)
        assert loaded[1].id == "idea-2"
        assert loaded[1].author == "test-user"

    def test_index_file_contains_updated_timestamp(
        self, oaps_project: OapsProject, freeze_time: FreezeTimeFunc
    ) -> None:
        import orjson

        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        entries = [
            IdeaIndexEntry(
                id="test",
                title="Test",
                status="seed",
                type="technical",
                tags=(),
                file_path="test.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
        ]

        freeze_time(2024, 12, 18, 16, 30, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

        index_path = ideas_dir / "index.json"
        data = orjson.loads(index_path.read_bytes())
        assert "updated" in data
        assert "2024-12-18" in data["updated"]


class TestRebuildIndex:
    def test_returns_empty_list_for_missing_directory(
        self, oaps_project: OapsProject
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            result = rebuild_index()
        assert result == []

    def test_scans_markdown_files(
        self, oaps_project: OapsProject, freeze_time: FreezeTimeFunc
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        # Create test idea files
        for i in range(2):
            fm = IdeaFrontmatter(
                id=f"idea-{i}",
                title=f"Idea {i}",
                status=IdeaStatus.SEED,
                type=IdeaType.TECHNICAL,
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
            save_idea(ideas_dir / f"idea-{i}.md", fm, "# Content")

        freeze_time(2024, 12, 18, 17, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            entries = rebuild_index()

        assert len(entries) == 2
        ids = {e.id for e in entries}
        assert "idea-0" in ids
        assert "idea-1" in ids

    def test_skips_invalid_files(
        self, oaps_project: OapsProject, freeze_time: FreezeTimeFunc
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        # Create a valid idea
        fm = IdeaFrontmatter(
            id="valid-idea",
            title="Valid",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "valid-idea.md", fm, "# Content")

        # Create an invalid file (no frontmatter)
        (ideas_dir / "invalid.md").write_text("No frontmatter here")

        freeze_time(2024, 12, 18, 17, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            entries = rebuild_index()

        assert len(entries) == 1
        assert entries[0].id == "valid-idea"


class TestFindIdeaById:
    def test_finds_idea_by_exact_filename(self, oaps_project: OapsProject) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        fm = IdeaFrontmatter(
            id="20241218-120000-test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "20241218-120000-test.md", fm, "# Content")

        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            result = find_idea_by_id("20241218-120000-test")

        assert result is not None
        assert result.name == "20241218-120000-test.md"

    def test_returns_none_for_nonexistent_idea(self, oaps_project: OapsProject) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            result = find_idea_by_id("nonexistent")

        assert result is None

    def test_finds_idea_through_index(
        self, oaps_project: OapsProject, freeze_time: FreezeTimeFunc
    ) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        # Create idea with filename different from ID
        fm = IdeaFrontmatter(
            id="special-idea-id",
            title="Special",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "different-filename.md", fm, "# Content")

        # Save index with correct mapping
        entries = [
            IdeaIndexEntry(
                id="special-idea-id",
                title="Special",
                status="seed",
                type="technical",
                tags=(),
                file_path="different-filename.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
        ]
        freeze_time(2024, 12, 18, 17, 0, 0)
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

            result = find_idea_by_id("special-idea-id")

        assert result is not None
        assert result.name == "different-filename.md"

    def test_finds_idea_by_scanning_files(self, oaps_project: OapsProject) -> None:
        ideas_dir = oaps_project.oaps_dir / "docs" / "ideas"
        ideas_dir.mkdir(parents=True)

        # Create idea with filename different from ID
        fm = IdeaFrontmatter(
            id="hidden-id",
            title="Hidden",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / "some-file.md", fm, "# Content")

        # No index file, so it must scan
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            result = find_idea_by_id("hidden-id")

        assert result is not None
        assert result.name == "some-file.md"
