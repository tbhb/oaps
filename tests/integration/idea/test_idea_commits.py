# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportTypedDictNotRequiredAccess=false
"""Integration tests verifying idea operations create proper git commits.

These tests verify that idea operations (create, update_status, update_content,
add_reference) result in actual git commits when used with OapsRepository.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from oaps.cli._commands._idea._models import (
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaReference,
    IdeaStatus,
    IdeaType,
)
from oaps.cli._commands._idea._storage import (
    load_idea,
    save_idea,
    save_index,
)
from oaps.repository import OapsRepository


def _run_git(cwd: Path, *args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(  # noqa: S603 - Safe: running git in tests
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr}"
        raise RuntimeError(msg)
    return result.stdout


@pytest.fixture
def oaps_git_repo(tmp_path: Path) -> Path:
    """Create a real .oaps git repository for testing."""
    oaps_dir = tmp_path / ".oaps"
    oaps_dir.mkdir()

    # Initialize git repo
    _run_git(oaps_dir, "init")
    _run_git(oaps_dir, "config", "user.name", "Test User")
    _run_git(oaps_dir, "config", "user.email", "test@example.com")
    _run_git(oaps_dir, "config", "commit.gpgsign", "false")

    # Create initial commit with README
    readme = oaps_dir / "README.md"
    readme.write_text("# OAPS Test Repository\n")
    _run_git(oaps_dir, "add", "README.md")
    _run_git(oaps_dir, "commit", "-m", "Initial commit")

    # Create ideas directory structure
    ideas_dir = oaps_dir / "docs" / "ideas"
    ideas_dir.mkdir(parents=True)

    return tmp_path


class TestIdeaCreateCommits:
    def test_idea_create_commits_file(self, oaps_git_repo: Path) -> None:
        """Verify creating an idea results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        # Create the idea file
        idea_id = "20241218-120000-test-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Test Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T12:00:00Z",
            updated="2024-12-18T12:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Initial content\n\nSome details.")

        # Create index entry
        entries = [
            IdeaIndexEntry(
                id=idea_id,
                title="Test Idea",
                status="seed",
                type="technical",
                tags=(),
                file_path=f"{idea_id}.md",
                created="2024-12-18T12:00:00Z",
                updated="2024-12-18T12:00:00Z",
            )
        ]
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

        # Commit using OapsRepository
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"create {idea_id}",
                session_id="test-session",
            )

        # Verify commit was created
        assert not result.no_changes
        assert result.sha is not None
        assert len(result.files) >= 1

        # Verify commit message format
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert f"oaps(idea): create {idea_id}" in log_output

        # Verify file exists in repository
        assert (ideas_dir / f"{idea_id}.md").exists()

    def test_idea_create_with_tags_commits(self, oaps_git_repo: Path) -> None:
        """Verify creating an idea with tags results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        idea_id = "20241218-130000-tagged-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Tagged Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.PRODUCT,
            created="2024-12-18T13:00:00Z",
            updated="2024-12-18T13:00:00Z",
            tags=("python", "testing", "automation"),
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Tagged content")

        # Commit using OapsRepository
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"create {idea_id}",
            )

        assert not result.no_changes
        assert result.sha is not None

        # Verify the idea has tags
        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert loaded_fm.tags == ("python", "testing", "automation")


class TestIdeaUpdateStatusCommits:
    def test_idea_update_status_commits(self, oaps_git_repo: Path) -> None:
        """Verify updating idea status results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        # Create initial idea
        idea_id = "20241218-140000-status-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Status Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T14:00:00Z",
            updated="2024-12-18T14:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Initial content")

        # Commit initial version
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Update status
        updated_fm = IdeaFrontmatter(
            id=idea_id,
            title="Status Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T14:00:00Z",
            updated="2024-12-18T15:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", updated_fm, "# Updated content")

        # Commit the status change
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"update status {idea_id}",
            )

        assert not result.no_changes
        assert result.sha is not None

        # Verify commit message
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "-1", "--format=%s")
        assert f"oaps(idea): update status {idea_id}" in log_output

        # Verify status was updated
        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert loaded_fm.status == IdeaStatus.EXPLORING

    def test_idea_status_progression(self, oaps_git_repo: Path) -> None:
        """Verify idea status progression through lifecycle."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        idea_id = "20241218-150000-lifecycle-idea"
        statuses = [
            IdeaStatus.SEED,
            IdeaStatus.EXPLORING,
            IdeaStatus.REFINING,
            IdeaStatus.CRYSTALLIZED,
            IdeaStatus.ARCHIVED,
        ]

        # Create initial idea
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Lifecycle Idea",
            status=statuses[0],
            type=IdeaType.RESEARCH,
            created="2024-12-18T15:00:00Z",
            updated="2024-12-18T15:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Progress through each status
        for i, status in enumerate(statuses[1:], start=1):
            updated_fm = IdeaFrontmatter(
                id=idea_id,
                title="Lifecycle Idea",
                status=status,
                type=IdeaType.RESEARCH,
                created="2024-12-18T15:00:00Z",
                updated=f"2024-12-18T{15 + i}:00:00Z",
            )
            save_idea(ideas_dir / f"{idea_id}.md", updated_fm, f"# Content v{i + 1}")

            with OapsRepository(working_dir=oaps_git_repo) as repo:
                result = repo.checkpoint(
                    workflow="idea",
                    action=f"update status {idea_id} to {status.value}",
                )
            assert not result.no_changes

        # Verify final status
        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert loaded_fm.status == IdeaStatus.ARCHIVED

        # Verify commit history
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--oneline")
        lines = log_output.strip().split("\n")
        # Should have: initial + create + 4 status updates = 6 commits
        assert len(lines) >= 5


class TestIdeaUpdateContentCommits:
    def test_idea_update_content_commits(self, oaps_git_repo: Path) -> None:
        """Verify updating idea content results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        # Create initial idea
        idea_id = "20241218-160000-content-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Content Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T16:00:00Z",
            updated="2024-12-18T16:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Initial content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Update content only (not status)
        save_idea(
            ideas_dir / f"{idea_id}.md", fm, "# Updated content\n\nWith more details."
        )

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"update content {idea_id}",
            )

        assert not result.no_changes
        assert result.sha is not None

        # Verify content was updated
        _, body = load_idea(ideas_dir / f"{idea_id}.md")
        assert "With more details" in body

    def test_idea_update_title_commits(self, oaps_git_repo: Path) -> None:
        """Verify updating idea title results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        idea_id = "20241218-170000-title-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Original Title",
            status=IdeaStatus.SEED,
            type=IdeaType.PRODUCT,
            created="2024-12-18T17:00:00Z",
            updated="2024-12-18T17:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Update title
        updated_fm = IdeaFrontmatter(
            id=idea_id,
            title="Better Title",
            status=IdeaStatus.SEED,
            type=IdeaType.PRODUCT,
            created="2024-12-18T17:00:00Z",
            updated="2024-12-18T18:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", updated_fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"update title {idea_id}",
            )

        assert not result.no_changes

        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert loaded_fm.title == "Better Title"


class TestIdeaAddReferenceCommits:
    def test_idea_add_reference_commits(self, oaps_git_repo: Path) -> None:
        """Verify adding a reference to an idea results in a git commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        # Create initial idea without references
        idea_id = "20241218-180000-reference-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Reference Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.RESEARCH,
            created="2024-12-18T18:00:00Z",
            updated="2024-12-18T18:00:00Z",
            references=(),
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Add a reference
        ref = IdeaReference(
            url="https://example.com/article",
            title="Relevant Article",
        )
        updated_fm = IdeaFrontmatter(
            id=idea_id,
            title="Reference Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.RESEARCH,
            created="2024-12-18T18:00:00Z",
            updated="2024-12-18T19:00:00Z",
            references=(ref,),
        )
        save_idea(ideas_dir / f"{idea_id}.md", updated_fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action=f"add reference {idea_id}",
            )

        assert not result.no_changes
        assert result.sha is not None

        # Verify reference was added
        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert len(loaded_fm.references) == 1
        assert loaded_fm.references[0]["url"] == "https://example.com/article"

    def test_idea_add_multiple_references_commits(self, oaps_git_repo: Path) -> None:
        """Verify adding multiple references creates proper commits."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        idea_id = "20241218-190000-multi-ref-idea"
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Multi-Reference Idea",
            status=IdeaStatus.REFINING,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T19:00:00Z",
            updated="2024-12-18T19:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Add first reference
        ref1 = IdeaReference(url="https://example.com/ref1", title="First Reference")
        updated_fm = IdeaFrontmatter(
            id=idea_id,
            title="Multi-Reference Idea",
            status=IdeaStatus.REFINING,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T19:00:00Z",
            updated="2024-12-18T20:00:00Z",
            references=(ref1,),
        )
        save_idea(ideas_dir / f"{idea_id}.md", updated_fm, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result1 = repo.checkpoint(
                workflow="idea",
                action=f"add reference 1 {idea_id}",
            )
        assert not result1.no_changes

        # Add second reference
        ref2 = IdeaReference(url="https://example.com/ref2", title="Second Reference")
        updated_fm2 = IdeaFrontmatter(
            id=idea_id,
            title="Multi-Reference Idea",
            status=IdeaStatus.REFINING,
            type=IdeaType.TECHNICAL,
            created="2024-12-18T19:00:00Z",
            updated="2024-12-18T21:00:00Z",
            references=(ref1, ref2),
        )
        save_idea(ideas_dir / f"{idea_id}.md", updated_fm2, "# Content")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result2 = repo.checkpoint(
                workflow="idea",
                action=f"add reference 2 {idea_id}",
            )
        assert not result2.no_changes

        # Verify both references are present
        loaded_fm, _ = load_idea(ideas_dir / f"{idea_id}.md")
        assert len(loaded_fm.references) == 2


class TestIdeaSequentialOperations:
    def test_multiple_idea_operations_in_sequence(self, oaps_git_repo: Path) -> None:
        """Verify multiple idea operations in sequence create proper commit history."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        idea_id = "20241218-200000-sequence-idea"

        # Create
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Sequence Idea",
            status=IdeaStatus.SEED,
            type=IdeaType.PROCESS,
            created="2024-12-18T20:00:00Z",
            updated="2024-12-18T20:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Initial")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"create {idea_id}")

        # Update status to exploring
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Sequence Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.PROCESS,
            created="2024-12-18T20:00:00Z",
            updated="2024-12-18T21:00:00Z",
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Exploring")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"update status {idea_id}")

        # Add reference
        ref = IdeaReference(url="https://example.com", title="Reference")
        fm = IdeaFrontmatter(
            id=idea_id,
            title="Sequence Idea",
            status=IdeaStatus.EXPLORING,
            type=IdeaType.PROCESS,
            created="2024-12-18T20:00:00Z",
            updated="2024-12-18T22:00:00Z",
            references=(ref,),
        )
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# With reference")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"add reference {idea_id}")

        # Update content
        save_idea(ideas_dir / f"{idea_id}.md", fm, "# Updated content\n\nMore details.")

        with OapsRepository(working_dir=oaps_git_repo) as repo:
            repo.checkpoint(workflow="idea", action=f"update content {idea_id}")

        # Verify commit history
        log_output = _run_git(oaps_git_repo / ".oaps", "log", "--oneline")
        lines = log_output.strip().split("\n")

        # Should have: initial + create + update status + add ref + update content = 5
        assert len(lines) >= 5

        # Verify all commit messages are present
        full_log = _run_git(oaps_git_repo / ".oaps", "log", "--format=%s")
        assert f"oaps(idea): create {idea_id}" in full_log
        assert f"oaps(idea): update status {idea_id}" in full_log
        assert f"oaps(idea): add reference {idea_id}" in full_log
        assert f"oaps(idea): update content {idea_id}" in full_log


class TestIdeaIndexCommits:
    def test_idea_index_update_commits(self, oaps_git_repo: Path) -> None:
        """Verify updating the idea index results in a commit."""
        ideas_dir = oaps_git_repo / ".oaps" / "docs" / "ideas"

        # Create multiple ideas and update index
        idea_ids = [f"20241218-21000{i}-index-idea-{i}" for i in range(3)]

        entries = []
        for i, idea_id in enumerate(idea_ids):
            fm = IdeaFrontmatter(
                id=idea_id,
                title=f"Index Idea {i}",
                status=IdeaStatus.SEED,
                type=IdeaType.TECHNICAL,
                created=f"2024-12-18T21:0{i}:00Z",
                updated=f"2024-12-18T21:0{i}:00Z",
            )
            save_idea(ideas_dir / f"{idea_id}.md", fm, f"# Content {i}")

            entries.append(
                IdeaIndexEntry(
                    id=idea_id,
                    title=f"Index Idea {i}",
                    status="seed",
                    type="technical",
                    tags=(),
                    file_path=f"{idea_id}.md",
                    created=f"2024-12-18T21:0{i}:00Z",
                    updated=f"2024-12-18T21:0{i}:00Z",
                )
            )

        # Save index
        with patch(
            "oaps.cli._commands._idea._storage.get_ideas_dir", return_value=ideas_dir
        ):
            save_index(entries)

        # Commit all ideas and index
        with OapsRepository(working_dir=oaps_git_repo) as repo:
            result = repo.checkpoint(
                workflow="idea",
                action="rebuild index",
            )

        assert not result.no_changes
        assert result.sha is not None

        # Verify files were committed by checking git status shows clean
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(oaps_git_repo / ".oaps"),
            capture_output=True,
            text=True,
            check=False,
        )
        # Only check docs/ideas directory for uncommitted changes
        uncommitted_idea_files = [
            line
            for line in status.stdout.strip().split("\n")
            if line and "docs/ideas" in line
        ]
        assert len(uncommitted_idea_files) == 0
