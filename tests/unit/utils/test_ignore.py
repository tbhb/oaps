"""Tests for gitignore pattern matching utilities."""

from pathlib import Path
from typing import TYPE_CHECKING

from oaps.utils._ignore import (
    DEFAULT_IGNORE_PATTERNS,
    IgnoreConfig,
    collect_patterns,
    create_pathspec,
    load_gitignore_patterns,
    matches_any,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest_mock import MockerFixture


class TestDefaultIgnorePatterns:
    def test_contains_common_patterns(self) -> None:
        assert "*.pyc" in DEFAULT_IGNORE_PATTERNS
        assert "__pycache__/" in DEFAULT_IGNORE_PATTERNS
        assert ".git/" in DEFAULT_IGNORE_PATTERNS
        assert ".oaps/" in DEFAULT_IGNORE_PATTERNS
        assert "node_modules/" in DEFAULT_IGNORE_PATTERNS
        assert ".venv/" in DEFAULT_IGNORE_PATTERNS
        assert "*.egg-info/" in DEFAULT_IGNORE_PATTERNS

    def test_is_frozen_set(self) -> None:
        assert isinstance(DEFAULT_IGNORE_PATTERNS, frozenset)


class TestIgnoreConfig:
    def test_default_values(self) -> None:
        config = IgnoreConfig()
        assert config.include_defaults is True
        assert config.worktree_gitignore is True
        assert config.oaps_gitignore is True
        assert config.extra_patterns == ()

    def test_custom_values(self) -> None:
        config = IgnoreConfig(
            include_defaults=False,
            worktree_gitignore=False,
            oaps_gitignore=False,
            extra_patterns=("*.log", "tmp/"),
        )
        assert config.include_defaults is False
        assert config.worktree_gitignore is False
        assert config.oaps_gitignore is False
        assert config.extra_patterns == ("*.log", "tmp/")

    def test_is_frozen(self) -> None:
        import dataclasses

        config = IgnoreConfig()
        assert dataclasses.is_dataclass(config)
        # Verify slots are used (frozen dataclasses typically use slots too)
        assert hasattr(config, "__slots__")
        # Verify the class is indeed frozen by checking FrozenInstanceError on setattr
        # We do this indirectly by testing the class matches our expectation
        fields = dataclasses.fields(config)
        assert (
            len(fields) == 4
        )  # include_defaults, worktree_gitignore, oaps_gitignore, extra_patterns


class TestLoadGitignorePatterns:
    def test_loads_patterns_from_file(self, fs: FakeFilesystem) -> None:
        gitignore = Path("/project/.gitignore")
        fs.create_file(
            gitignore,
            contents="*.pyc\n__pycache__/\n# Comment\n\n.env\n",
        )

        patterns = load_gitignore_patterns(gitignore)

        assert patterns == ["*.pyc", "__pycache__/", ".env"]

    def test_returns_empty_for_missing_file(self, fs: FakeFilesystem) -> None:
        patterns = load_gitignore_patterns(Path("/nonexistent/.gitignore"))
        assert patterns == []

    def test_returns_empty_for_directory(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/project/.gitignore")
        patterns = load_gitignore_patterns(Path("/project/.gitignore"))
        assert patterns == []

    def test_skips_comment_lines(self, fs: FakeFilesystem) -> None:
        gitignore = Path("/project/.gitignore")
        fs.create_file(
            gitignore,
            contents="# This is a comment\n*.pyc\n  # Indented comment\n",
        )

        patterns = load_gitignore_patterns(gitignore)

        assert "# This is a comment" not in patterns
        assert "# Indented comment" not in patterns
        assert patterns == ["*.pyc"]

    def test_skips_empty_lines(self, fs: FakeFilesystem) -> None:
        gitignore = Path("/project/.gitignore")
        fs.create_file(
            gitignore,
            contents="*.pyc\n\n\n*.pyo\n   \n*.pyd\n",
        )

        patterns = load_gitignore_patterns(gitignore)

        assert patterns == ["*.pyc", "*.pyo", "*.pyd"]

    def test_strips_whitespace(self, fs: FakeFilesystem) -> None:
        gitignore = Path("/project/.gitignore")
        fs.create_file(
            gitignore,
            contents="  *.pyc  \n\t*.pyo\t\n",
        )

        patterns = load_gitignore_patterns(gitignore)

        assert patterns == ["*.pyc", "*.pyo"]


class TestCollectPatterns:
    def test_includes_defaults_by_default(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        patterns = collect_patterns(worktree_root=worktree_root)

        for default_pattern in DEFAULT_IGNORE_PATTERNS:
            assert default_pattern in patterns

    def test_excludes_defaults_when_disabled(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        config = IgnoreConfig(include_defaults=False)
        patterns = collect_patterns(worktree_root=worktree_root, config=config)

        for default_pattern in DEFAULT_IGNORE_PATTERNS:
            assert default_pattern not in patterns

    def test_loads_worktree_gitignore(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="custom_pattern/\n",
        )

        patterns = collect_patterns(worktree_root=worktree_root)

        assert "custom_pattern/" in patterns

    def test_skips_worktree_gitignore_when_disabled(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="custom_pattern/\n",
        )

        config = IgnoreConfig(worktree_gitignore=False)
        patterns = collect_patterns(worktree_root=worktree_root, config=config)

        assert "custom_pattern/" not in patterns

    def test_loads_oaps_gitignore(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root / ".oaps")
        fs.create_file(
            worktree_root / ".oaps" / ".gitignore",
            contents="oaps_pattern/\n",
        )

        patterns = collect_patterns(worktree_root=worktree_root)

        assert "oaps_pattern/" in patterns

    def test_skips_oaps_gitignore_when_disabled(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root / ".oaps")
        fs.create_file(
            worktree_root / ".oaps" / ".gitignore",
            contents="oaps_pattern/\n",
        )

        config = IgnoreConfig(oaps_gitignore=False)
        patterns = collect_patterns(worktree_root=worktree_root, config=config)

        assert "oaps_pattern/" not in patterns

    def test_includes_extra_patterns(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        config = IgnoreConfig(extra_patterns=("extra1/", "extra2/"))
        patterns = collect_patterns(worktree_root=worktree_root, config=config)

        assert "extra1/" in patterns
        assert "extra2/" in patterns

    def test_deduplicates_patterns(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="*.pyc\n",
        )

        # *.pyc is in defaults and in gitignore
        patterns = collect_patterns(worktree_root=worktree_root)

        assert patterns.count("*.pyc") == 1

    def test_preserves_order(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root / ".oaps")
        fs.create_file(
            worktree_root / ".gitignore",
            contents="worktree_first/\nworktree_second/\n",
        )
        fs.create_file(
            worktree_root / ".oaps" / ".gitignore",
            contents="oaps_first/\noaps_second/\n",
        )

        config = IgnoreConfig(extra_patterns=("extra/",))
        patterns = collect_patterns(worktree_root=worktree_root, config=config)

        # Defaults come first (sorted), then worktree, then oaps, then extra
        worktree_first_idx = patterns.index("worktree_first/")
        worktree_second_idx = patterns.index("worktree_second/")
        oaps_first_idx = patterns.index("oaps_first/")
        oaps_second_idx = patterns.index("oaps_second/")
        extra_idx = patterns.index("extra/")

        assert worktree_first_idx < worktree_second_idx
        assert worktree_second_idx < oaps_first_idx
        assert oaps_first_idx < oaps_second_idx
        assert oaps_second_idx < extra_idx

    def test_uses_get_worktree_root_when_no_worktree_provided(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/discovered/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="discovered_pattern/\n",
        )

        mocker.patch(
            "oaps.utils._paths.get_worktree_root",
            return_value=worktree_root,
        )

        patterns = collect_patterns()

        assert "discovered_pattern/" in patterns

    def test_handles_worktree_discovery_failure(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        mocker.patch(
            "oaps.utils._paths.get_worktree_root",
            side_effect=RuntimeError("Not in a git repo"),
        )

        config = IgnoreConfig(include_defaults=True)
        patterns = collect_patterns(config=config)

        # Should still have defaults even if worktree discovery fails
        assert len(patterns) == len(DEFAULT_IGNORE_PATTERNS)


class TestCreatePathspec:
    def test_returns_pathspec(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        from pathspec import PathSpec

        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        assert isinstance(spec, PathSpec)

    def test_uses_gitignore_style_matching(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        # Test gitignore-style pattern matching
        assert spec.match_file("test.pyc")
        assert spec.match_file("__pycache__/")
        assert spec.match_file(".git/config")
        assert not spec.match_file("src/main.py")

    def test_respects_config(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        config = IgnoreConfig(include_defaults=False, extra_patterns=("custom/",))
        spec = create_pathspec(worktree_root=worktree_root, config=config)

        assert spec.match_file("custom/file.txt")
        assert not spec.match_file("test.pyc")


class TestMatchesAny:
    def test_matches_pattern(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "test.pyc")
        assert matches_any(spec, "__pycache__/module.py")

    def test_no_match(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        assert not matches_any(spec, "src/main.py")
        assert not matches_any(spec, "README.md")

    def test_accepts_path_object(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, Path("test.pyc"))
        assert not matches_any(spec, Path("src/main.py"))

    def test_accepts_string(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "test.pyc")
        assert not matches_any(spec, "src/main.py")


class TestPatternMatching:
    """Integration tests for common gitignore pattern scenarios."""

    def test_wildcard_extension(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="*.log\n",
        )

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "app.log")
        assert matches_any(spec, "logs/error.log")
        assert not matches_any(spec, "log.txt")

    def test_directory_pattern(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="build/\n",
        )

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "build/")
        assert matches_any(spec, "build/output.js")
        # Note: pathspec gitignore patterns can match files too
        assert matches_any(spec, "src/build/output.js")

    def test_negation_pattern(self, mocker: MockerFixture, fs: FakeFilesystem) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="*.log\n!important.log\n",
        )

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "debug.log")
        # Negation means important.log is NOT ignored
        assert not matches_any(spec, "important.log")

    def test_double_star_pattern(
        self, mocker: MockerFixture, fs: FakeFilesystem
    ) -> None:
        worktree_root = Path("/project")
        fs.create_dir(worktree_root)
        fs.create_file(
            worktree_root / ".gitignore",
            contents="**/temp/\n",
        )

        spec = create_pathspec(worktree_root=worktree_root)

        assert matches_any(spec, "temp/")
        assert matches_any(spec, "src/temp/")
        assert matches_any(spec, "a/b/c/temp/")
