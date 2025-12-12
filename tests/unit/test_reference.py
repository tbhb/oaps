from pathlib import Path
from typing import TYPE_CHECKING

from oaps.reference import (
    ReferenceFrontmatter,
    discover_references,
    find_reference_file,
    format_commands_table,
    format_consolidated_section,
    format_references_section,
    load_reference_content,
    merge_commands,
    merge_references,
    resolve_reference_dependencies,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem

    from oaps.context import SkillContext


class TestMergeReferences:
    def test_returns_builtin_when_no_overrides(self) -> None:
        builtin: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1"}
        }
        result = merge_references(builtin, {})
        assert result == builtin

    def test_overrides_take_precedence(self) -> None:
        builtin: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "original"}
        }
        overrides: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "overridden"}
        }
        result = merge_references(builtin, overrides)
        assert result["ref1"]["description"] == "overridden"

    def test_adds_new_from_overrides(self) -> None:
        builtin: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1"}
        }
        overrides: dict[str, ReferenceFrontmatter] = {
            "ref2": {"name": "ref2", "description": "desc2"}
        }
        result = merge_references(builtin, overrides)
        assert "ref1" in result
        assert "ref2" in result


class TestMergeCommands:
    def test_returns_single_commands_unchanged(self) -> None:
        commands = [{"cmd1": "desc1", "cmd2": "desc2"}]
        result = merge_commands(commands)
        assert result == {"cmd1": "desc1", "cmd2": "desc2"}

    def test_merges_same_command_descriptions(self) -> None:
        commands = [
            {"cmd1": "first desc"},
            {"cmd1": "second desc"},
        ]
        result = merge_commands(commands)
        assert result["cmd1"] == "first desc; second desc"

    def test_strips_trailing_periods_before_merging(self) -> None:
        commands = [
            {"cmd1": "first desc."},
            {"cmd1": "second desc."},
        ]
        result = merge_commands(commands)
        assert result["cmd1"] == "first desc; second desc"

    def test_deduplicates_same_descriptions(self) -> None:
        commands = [
            {"cmd1": "same desc"},
            {"cmd1": "same desc"},
        ]
        result = merge_commands(commands)
        assert result["cmd1"] == "same desc"


class TestFormatCommandsTable:
    def test_returns_empty_string_for_empty_dict(self) -> None:
        result = format_commands_table({})
        assert result == ""

    def test_formats_as_markdown_table(self) -> None:
        commands = {"cmd1": "desc1"}
        result = format_commands_table(commands)
        assert "## Allowed commands" in result
        assert "| Command | Description |" in result
        assert "`cmd1`" in result
        assert "desc1" in result

    def test_escapes_pipe_characters(self) -> None:
        commands = {"cmd|pipe": "desc|pipe"}
        result = format_commands_table(commands)
        assert "cmd\\|pipe" in result
        assert "desc\\|pipe" in result


class TestFormatConsolidatedSection:
    def test_returns_empty_string_when_all_empty(self) -> None:
        items: dict[str, list[str]] = {"ref1": [], "ref2": []}
        result = format_consolidated_section("Principles", items)
        assert result == ""

    def test_formats_with_h2_and_h3_headers(self) -> None:
        items = {"Title1": ["item1", "item2"]}
        result = format_consolidated_section("Principles", items)
        assert "## Principles" in result
        assert "### Title1 principles" in result
        assert "- item1" in result
        assert "- item2" in result

    def test_skips_empty_sections(self) -> None:
        items = {"Title1": ["item1"], "Title2": []}
        result = format_consolidated_section("Principles", items)
        assert "Title1" in result
        assert "Title2" not in result


class TestFormatReferencesSection:
    def test_returns_empty_string_when_all_empty(self) -> None:
        refs: dict[str, dict[str, str]] = {"ref1": {}, "ref2": {}}
        result = format_references_section(refs)
        assert result == ""

    def test_formats_urls_with_angle_brackets(self) -> None:
        refs = {"Title1": {"https://example.com": "Example"}}
        result = format_references_section(refs)
        assert "## References" in result
        assert "### Title1 references" in result
        assert "- <https://example.com>: Example" in result


class TestDiscoverReferences:
    def test_returns_empty_when_dir_does_not_exist(self, fs: FakeFilesystem) -> None:
        result = discover_references(Path("/nonexistent"))
        assert result == {}

    def test_discovers_valid_references(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/ref1.md",
            contents="---\nname: ref1\ndescription: First reference\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert "ref1" in result
        assert result["ref1"]["name"] == "ref1"
        assert result["ref1"]["description"] == "First reference"

    def test_skips_files_without_name(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/invalid.md",
            contents="---\ndescription: Missing name\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result == {}

    def test_skips_files_without_description(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/invalid.md",
            contents="---\nname: ref1\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result == {}

    def test_skips_files_with_non_string_name(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/invalid.md",
            contents="---\nname: 123\ndescription: desc\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result == {}

    def test_skips_files_with_non_string_description(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/invalid.md",
            contents="---\nname: ref1\ndescription: 123\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result == {}

    def test_extracts_required_field_when_true(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/ref1.md",
            contents="---\nname: ref1\ndescription: desc\nrequired: true\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result["ref1"].get("required") is True

    def test_extracts_required_field_when_false(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/ref1.md",
            contents="---\nname: ref1\ndescription: desc\nrequired: false\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert result["ref1"].get("required") is False

    def test_omits_required_field_when_not_bool(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/refs/ref1.md",
            contents="---\nname: ref1\ndescription: desc\nrequired: invalid\n---\nBody",
        )
        result = discover_references(Path("/refs"))
        assert "required" not in result["ref1"]

    def test_extracts_references_field(self, fs: FakeFilesystem) -> None:
        contents = (
            "---\nname: ref1\ndescription: desc\n"
            "references:\n  - dep1\n  - dep2\n---\nBody"
        )
        fs.create_file("/refs/ref1.md", contents=contents)
        result = discover_references(Path("/refs"))
        assert result["ref1"].get("references") == ["dep1", "dep2"]

    def test_omits_references_when_not_list(self, fs: FakeFilesystem) -> None:
        contents = (
            "---\nname: ref1\ndescription: desc\nreferences: not-a-list\n---\nBody"
        )
        fs.create_file("/refs/ref1.md", contents=contents)
        result = discover_references(Path("/refs"))
        assert "references" not in result["ref1"]

    def test_omits_references_when_list_contains_non_strings(
        self, fs: FakeFilesystem
    ) -> None:
        contents = (
            "---\nname: ref1\ndescription: desc\n"
            "references:\n  - dep1\n  - 123\n---\nBody"
        )
        fs.create_file("/refs/ref1.md", contents=contents)
        result = discover_references(Path("/refs"))
        assert "references" not in result["ref1"]


class TestFindReferenceFile:
    def test_returns_none_when_not_found(self, fs: FakeFilesystem) -> None:
        fs.create_dir("/builtin")
        result = find_reference_file("nonexistent", Path("/builtin"), None)
        assert result is None

    def test_finds_in_builtin_dir(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/builtin/ref1.md",
            contents="---\nname: ref1\ndescription: desc\n---\nBody",
        )
        result = find_reference_file("ref1", Path("/builtin"), None)
        assert result == Path("/builtin/ref1.md")

    def test_prefers_override_over_builtin(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/builtin/ref1.md",
            contents="---\nname: ref1\ndescription: builtin\n---\nBody",
        )
        fs.create_file(
            "/override/ref1.md",
            contents="---\nname: ref1\ndescription: override\n---\nBody",
        )
        result = find_reference_file("ref1", Path("/builtin"), Path("/override"))
        assert result == Path("/override/ref1.md")

    def test_fallback_to_builtin_when_not_in_override(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/builtin/ref1.md",
            contents="---\nname: ref1\ndescription: desc\n---\nBody",
        )
        fs.create_dir("/override")
        result = find_reference_file("ref1", Path("/builtin"), Path("/override"))
        assert result == Path("/builtin/ref1.md")

    def test_handles_override_dir_not_existing(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/builtin/ref1.md",
            contents="---\nname: ref1\ndescription: desc\n---\nBody",
        )
        result = find_reference_file("ref1", Path("/builtin"), Path("/nonexistent"))
        assert result == Path("/builtin/ref1.md")

    def test_skips_files_with_invalid_frontmatter_in_override(
        self, fs: FakeFilesystem
    ) -> None:
        fs.create_file("/override/invalid.md", contents="not valid frontmatter")
        fs.create_file(
            "/builtin/ref1.md",
            contents="---\nname: ref1\ndescription: desc\n---\nBody",
        )
        result = find_reference_file("ref1", Path("/builtin"), Path("/override"))
        assert result == Path("/builtin/ref1.md")

    def test_skips_files_with_invalid_frontmatter_in_builtin(
        self, fs: FakeFilesystem
    ) -> None:
        fs.create_file("/builtin/invalid.md", contents="not valid frontmatter")
        result = find_reference_file("ref1", Path("/builtin"), None)
        assert result is None

    def test_returns_none_when_builtin_dir_not_exists(self, fs: FakeFilesystem) -> None:
        result = find_reference_file("ref1", Path("/nonexistent"), None)
        assert result is None


class TestLoadReferenceContent:
    def test_loads_body_with_template_rendering(self, fs: FakeFilesystem) -> None:
        fs.create_file("/ref.md", contents="---\ntitle: Test\n---\nBody content")
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.body == "Body content"

    def test_extracts_title_from_frontmatter(self, fs: FakeFilesystem) -> None:
        fs.create_file("/ref.md", contents="---\ntitle: Test Title\n---\nBody")
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.title == "Test Title"

    def test_falls_back_to_name_when_no_title(self, fs: FakeFilesystem) -> None:
        fs.create_file("/ref.md", contents="---\nname: Test Name\n---\nBody")
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.title == "Test Name"

    def test_title_empty_when_neither_title_nor_name(self, fs: FakeFilesystem) -> None:
        fs.create_file("/ref.md", contents="---\n---\nBody")
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.title == ""

    def test_extracts_commands_dict(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/ref.md",
            contents="---\ncommands:\n  cmd1: desc1\n  cmd2: desc2\n---\nBody",
        )
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.commands == {"cmd1": "desc1", "cmd2": "desc2"}

    def test_extracts_principles_list(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/ref.md",
            contents="---\nprinciples:\n  - principle1\n  - principle2\n---\nBody",
        )
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.principles == ["principle1", "principle2"]

    def test_extracts_best_practices_list(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/ref.md",
            contents="---\nbest_practices:\n  - practice1\n  - practice2\n---\nBody",
        )
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.best_practices == ["practice1", "practice2"]

    def test_extracts_checklist_list(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/ref.md",
            contents="---\nchecklist:\n  - item1\n  - item2\n---\nBody",
        )
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.checklist == ["item1", "item2"]

    def test_extracts_references_dict(self, fs: FakeFilesystem) -> None:
        fs.create_file(
            "/ref.md",
            contents="---\nreferences:\n  https://example.com: Example\n---\nBody",
        )
        context: SkillContext = {"tool_versions": {}}
        result = load_reference_content(Path("/ref.md"), context)
        assert result.references == {"https://example.com": "Example"}


class TestResolveReferenceDependencies:
    def test_returns_requested_when_no_dependencies(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1"},
            "ref2": {"name": "ref2", "description": "desc2"},
        }
        resolved, missing = resolve_reference_dependencies(["ref1", "ref2"], refs)
        assert resolved == ["ref1", "ref2"]
        assert missing == []

    def test_resolves_single_dependency(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["dep1"]},
            "dep1": {"name": "dep1", "description": "dep desc"},
        }
        resolved, missing = resolve_reference_dependencies(["ref1"], refs)
        assert resolved == ["dep1", "ref1"]
        assert missing == []

    def test_resolves_transitive_dependencies(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["dep1"]},
            "dep1": {"name": "dep1", "description": "dep desc", "references": ["dep2"]},
            "dep2": {"name": "dep2", "description": "dep2 desc"},
        }
        resolved, missing = resolve_reference_dependencies(["ref1"], refs)
        assert resolved == ["dep2", "dep1", "ref1"]
        assert missing == []

    def test_handles_circular_dependency(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["ref2"]},
            "ref2": {"name": "ref2", "description": "desc2", "references": ["ref1"]},
        }
        resolved, missing = resolve_reference_dependencies(["ref1"], refs)
        # Should break the cycle and include both
        assert "ref1" in resolved
        assert "ref2" in resolved
        assert missing == []

    def test_reports_missing_dependencies(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["missing"]},
        }
        resolved, missing = resolve_reference_dependencies(["ref1"], refs)
        assert resolved == ["ref1"]
        assert missing == ["missing"]

    def test_deduplicates_references(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["shared"]},
            "ref2": {"name": "ref2", "description": "desc2", "references": ["shared"]},
            "shared": {"name": "shared", "description": "shared desc"},
        }
        resolved, missing = resolve_reference_dependencies(["ref1", "ref2"], refs)
        # shared should appear only once
        assert resolved.count("shared") == 1
        assert resolved.count("ref1") == 1
        assert resolved.count("ref2") == 1
        assert missing == []

    def test_handles_diamond_dependency(self) -> None:
        # A depends on B and C, both B and C depend on D
        refs: dict[str, ReferenceFrontmatter] = {
            "A": {"name": "A", "description": "desc", "references": ["B", "C"]},
            "B": {"name": "B", "description": "desc", "references": ["D"]},
            "C": {"name": "C", "description": "desc", "references": ["D"]},
            "D": {"name": "D", "description": "desc"},
        }
        resolved, missing = resolve_reference_dependencies(["A"], refs)
        # D should come first, then B and C, then A
        assert resolved.index("D") < resolved.index("B")
        assert resolved.index("D") < resolved.index("C")
        assert resolved.index("B") < resolved.index("A")
        assert resolved.index("C") < resolved.index("A")
        assert resolved.count("D") == 1
        assert missing == []

    def test_handles_self_reference(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {
            "ref1": {"name": "ref1", "description": "desc1", "references": ["ref1"]},
        }
        resolved, missing = resolve_reference_dependencies(["ref1"], refs)
        assert resolved == ["ref1"]
        assert missing == []

    def test_reports_missing_requested_reference(self) -> None:
        refs: dict[str, ReferenceFrontmatter] = {}
        resolved, missing = resolve_reference_dependencies(["nonexistent"], refs)
        assert resolved == []
        assert missing == ["nonexistent"]
