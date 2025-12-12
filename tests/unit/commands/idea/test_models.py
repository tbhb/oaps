"""Unit tests for idea data models."""

from oaps.cli._commands._idea._models import (
    STATUS_EMOJI,
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaReference,
    IdeaStatus,
    IdeaType,
    IdeaWorkflowState,
)


class TestIdeaStatus:
    def test_status_values(self) -> None:
        assert IdeaStatus.SEED == "seed"
        assert IdeaStatus.EXPLORING == "exploring"
        assert IdeaStatus.REFINING == "refining"
        assert IdeaStatus.CRYSTALLIZED == "crystallized"
        assert IdeaStatus.ARCHIVED == "archived"

    def test_status_order_is_workflow_progression(self) -> None:
        members = list(IdeaStatus)
        expected_order = [
            IdeaStatus.SEED,
            IdeaStatus.EXPLORING,
            IdeaStatus.REFINING,
            IdeaStatus.CRYSTALLIZED,
            IdeaStatus.ARCHIVED,
        ]
        assert members == expected_order

    def test_all_statuses_have_emoji(self) -> None:
        for status in IdeaStatus:
            assert status in STATUS_EMOJI
            assert isinstance(STATUS_EMOJI[status], str)
            assert len(STATUS_EMOJI[status]) > 0


class TestIdeaType:
    def test_type_values(self) -> None:
        assert IdeaType.TECHNICAL == "technical"
        assert IdeaType.PRODUCT == "product"
        assert IdeaType.PROCESS == "process"
        assert IdeaType.RESEARCH == "research"

    def test_type_order(self) -> None:
        members = list(IdeaType)
        expected_order = [
            IdeaType.TECHNICAL,
            IdeaType.PRODUCT,
            IdeaType.PROCESS,
            IdeaType.RESEARCH,
        ]
        assert members == expected_order


class TestStatusEmoji:
    def test_seed_emoji(self) -> None:
        assert STATUS_EMOJI[IdeaStatus.SEED] == "\U0001f331"

    def test_exploring_emoji(self) -> None:
        assert STATUS_EMOJI[IdeaStatus.EXPLORING] == "\U0001f50d"

    def test_refining_emoji(self) -> None:
        assert STATUS_EMOJI[IdeaStatus.REFINING] == "\U0001f504"

    def test_crystallized_emoji(self) -> None:
        assert STATUS_EMOJI[IdeaStatus.CRYSTALLIZED] == "\U0001f48e"

    def test_archived_emoji(self) -> None:
        assert STATUS_EMOJI[IdeaStatus.ARCHIVED] == "\U0001f4e6"

    def test_emoji_count_matches_status_count(self) -> None:
        assert len(STATUS_EMOJI) == len(IdeaStatus)


class TestIdeaFrontmatter:
    def test_creates_with_required_fields(self) -> None:
        fm = IdeaFrontmatter(
            id="20241218-120000-test-idea",
            title="Test Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        assert fm.id == "20241218-120000-test-idea"
        assert fm.title == "Test Idea"
        assert fm.status == IdeaStatus.SEED
        assert fm.type == IdeaType.TECHNICAL
        assert fm.created == "2024-12-18T12:00:00Z"
        assert fm.updated == "2024-12-18T12:00:00Z"

    def test_optional_fields_have_defaults(self) -> None:
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        assert fm.author is None
        assert fm.tags == ()
        assert fm.related_ideas == ()
        assert fm.references == ()
        assert fm.workflow is None

    def test_creates_with_all_optional_fields(self) -> None:
        ref: IdeaReference = {"url": "https://example.com", "title": "Example"}
        workflow: IdeaWorkflowState = {"phase": "exploring", "iteration": 1}

        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.PRODUCT,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T13:00:00Z",
            author="test-user",
            tags=("python", "testing"),
            related_ideas=("other-idea-1", "other-idea-2"),
            references=(ref,),
            workflow=workflow,
        )
        assert fm.author == "test-user"
        assert fm.tags == ("python", "testing")
        assert fm.related_ideas == ("other-idea-1", "other-idea-2")
        assert fm.references == (ref,)
        assert fm.workflow == workflow

    def test_is_frozen(self) -> None:
        fm = IdeaFrontmatter(
            id="test",
            title="Test",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        raised = False
        try:
            fm.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised, "Should have raised AttributeError for frozen dataclass"

    def test_has_slots(self) -> None:
        assert hasattr(IdeaFrontmatter, "__slots__")


class TestIdeaIndexEntry:
    def test_creates_with_required_fields(self) -> None:
        entry = IdeaIndexEntry(
            id="20241218-120000-test-idea",
            title="Test Idea",
            status="seed",
            type="technical",
            tags=("python",),
            file_path="20241218-120000-test-idea.md",
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        assert entry.id == "20241218-120000-test-idea"
        assert entry.title == "Test Idea"
        assert entry.status == "seed"
        assert entry.type == "technical"
        assert entry.tags == ("python",)
        assert entry.file_path == "20241218-120000-test-idea.md"
        assert entry.created == "2024-12-18T12:00:00Z"
        assert entry.updated == "2024-12-18T12:00:00Z"

    def test_author_defaults_to_none(self) -> None:
        entry = IdeaIndexEntry(
            id="test",
            title="Test",
            status="seed",
            type="technical",
            tags=(),
            file_path="test.md",
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        assert entry.author is None

    def test_creates_with_author(self) -> None:
        entry = IdeaIndexEntry(
            id="test",
            title="Test",
            status="seed",
            type="technical",
            tags=(),
            file_path="test.md",
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
            author="test-user",
        )
        assert entry.author == "test-user"

    def test_is_frozen(self) -> None:
        entry = IdeaIndexEntry(
            id="test",
            title="Test",
            status="seed",
            type="technical",
            tags=(),
            file_path="test.md",
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        raised = False
        try:
            entry.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised, "Should have raised AttributeError for frozen dataclass"

    def test_has_slots(self) -> None:
        assert hasattr(IdeaIndexEntry, "__slots__")
