# Git-aware hook rules

Hook rules can leverage Git status information to enforce repository policies, prevent common mistakes, and automate workflows based on version control state. This document provides examples using the built-in Git functions available in hook conditions.

## Git function reference

**File-level status functions:**

- `$is_staged(path)` - Check if specific file is staged for commit
- `$is_modified(path)` - Check if specific file has unstaged modifications
- `$git_file_in(path, set)` - Check if file is in a specific status set ("staged", "modified", "untracked", "conflict")

**Repository status functions:**

- `$has_conflicts()` - Check if repository has any merge conflicts
- `$current_branch()` - Get current branch name (returns null if HEAD is detached)
- `$is_git_repo()` - Check if working directory is inside a git repository

**Pattern-based functions (all accept optional glob pattern):**

- `$git_has_staged(pattern?)` - Any staged files match the glob pattern
- `$git_has_modified(pattern?)` - Any modified files match the glob pattern
- `$git_has_untracked(pattern?)` - Any untracked files match the glob pattern
- `$git_has_conflicts(pattern?)` - Any conflicted files match the glob pattern

---

## Example 1: Block commits with unresolved conflicts

Prevent committing when the repository has unresolved merge conflicts.

```toml
[[rules]]
id = "block-commit-with-conflicts"
description = "Prevent commits when merge conflicts exist"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
$has_conflicts()
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot commit with unresolved merge conflicts. Resolve conflicts first, then stage the resolved files."
```

---

## Example 2: Block commits with conflicted Python files

More targeted version that only blocks when Python files have conflicts.

```toml
[[rules]]
id = "block-python-conflicts"
description = "Prevent commits when Python files have conflicts"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
$git_has_conflicts("*.py")
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Python files have unresolved merge conflicts. Run 'git status' to see affected files."
```

---

## Example 3: Warn when modifying staged files

Alert when editing a file that is already staged, which could lead to partial commits.

```toml
[[rules]]
id = "warn-staged-file-modification"
description = "Warn when editing files already staged for commit"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Edit"
and $is_staged(tool_input.file_path)
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "File '${tool_input.file_path}' is staged for commit. Editing may result in a partial commit. Run 'git diff --cached' to review staged changes."
```

---

## Example 4: Warn when writing to staged files

Similar protection for the Write tool which overwrites entire files.

```toml
[[rules]]
id = "warn-staged-file-write"
description = "Warn when writing to files already staged for commit"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write"
and $is_staged(tool_input.file_path)
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "File '${tool_input.file_path}' is staged for commit. Writing will replace its contents. Consider unstaging first with 'git reset ${tool_input.file_path}'."
```

---

## Example 5: Require tests when source files are staged

Ensure test coverage by warning when Python source files are staged but no test files are staged.

```toml
[[rules]]
id = "require-tests-with-source"
description = "Suggest adding tests when staging source files"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash"
and tool_input.command.starts_with("git commit")
and $git_has_staged("src/**/*.py")
and not $git_has_staged("tests/**/*.py")
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "Source files are staged but no test files. Consider adding or updating tests before committing."
```

---

## Example 6: Block direct commits to main branch

Prevent direct commits to protected branches, requiring feature branches instead.

```toml
[[rules]]
id = "block-main-commits"
description = "Prevent direct commits to main branch"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
$is_git_repo()
and $current_branch() in ["main", "master"]
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot commit directly to '${$current_branch()}'. Create a feature branch first: git checkout -b feat/your-feature"
```

---

## Example 7: Warn about force pushes on protected branches

Allow force push but warn when targeting protected branches.

```toml
[[rules]]
id = "warn-force-push-protected"
description = "Warn about force pushes to protected branches"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
$current_branch() in ["main", "master", "develop"]
and tool_name == "Bash"
and tool_input.command =~~ "git\\s+push.*--force"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Force pushing to '${$current_branch()}' is dangerous. Consider using --force-with-lease instead."
```

---

## Example 8: Block force push without lease

Completely block force push without the safer --force-with-lease option.

```toml
[[rules]]
id = "block-force-push"
description = "Block force push without --force-with-lease"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "git\\s+push.*--force(?!-with-lease)"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Plain --force push is blocked. Use --force-with-lease for safer force pushing."
```

---

## Example 9: Branch naming convention enforcement

Suggest proper branch naming when creating branches.

```toml
[[rules]]
id = "branch-naming-convention"
description = "Enforce branch naming conventions"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "git\\s+(checkout|switch)\\s+-b\\s+"
and not tool_input.command =~~ "(feat|fix|docs|refactor|test|chore)/"
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "Consider using conventional branch names: feat/*, fix/*, docs/*, refactor/*, test/*, chore/*"
```

---

## Example 10: Pre-commit style checks reminder

Remind to run linting before committing when Python files are staged.

```toml
[[rules]]
id = "lint-before-commit"
description = "Remind to lint before committing Python files"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
$git_has_staged("*.py")
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "Python files are staged. Consider running 'just lint' or 'ruff check' before committing."
```

---

## Example 11: Warn about unstaged changes during commit

Alert when committing with unstaged changes to tracked files.

```toml
[[rules]]
id = "warn-unstaged-changes"
description = "Warn about unstaged changes when committing"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
$git_has_modified()
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
and not tool_input.command =~~ "-a|--all"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "You have unstaged changes that will not be included in this commit. Run 'git status' to review."
```

---

## Example 12: Block editing conflicted files

Prevent editing files that have unresolved conflicts until they are resolved.

```toml
[[rules]]
id = "block-edit-conflicted"
description = "Block editing files with unresolved conflicts"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Edit"
and $git_file_in(tool_input.file_path, "conflict")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "File '${tool_input.file_path}' has unresolved conflicts. Resolve conflicts manually before editing."
```

---

## Example 13: Feature branch workflow enforcement

Ensure developers work on feature branches, not directly on develop.

```toml
[[rules]]
id = "feature-branch-workflow"
description = "Enforce feature branch workflow"
events = ["pre_tool_use"]
priority = "high"
condition = '''
$current_branch() == "develop"
and tool_name in ["Edit", "Write"]
and $matches_glob(tool_input.file_path, "src/**")
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "You are on 'develop' branch. Consider creating a feature branch: git checkout -b feat/your-feature"
```

---

## Example 14: Require branch tracking before push

Warn when pushing without setting upstream tracking.

```toml
[[rules]]
id = "require-tracking-branch"
description = "Suggest setting upstream when pushing new branches"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "^git\\s+push(?!.*-u|--set-upstream)"
and not tool_input.command =~~ "origin\\s+(main|master|develop)"
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "Consider using 'git push -u origin ${$current_branch()}' to set up tracking."
```

---

## Example 15: Log all git operations for audit

Log git commands for session audit trail.

```toml
[[rules]]
id = "log-git-operations"
description = "Log all git operations for audit"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash"
and tool_input.command.starts_with("git ")
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Git operation: ${tool_input.command}"
```

---

## Combining Git conditions

Git functions can be combined for sophisticated policies:

```toml
# Block commit when:
# - On main branch AND
# - Python files are staged AND
# - No corresponding test files are staged AND
# - Repository has unstaged changes
condition = '''
$current_branch() == "main"
and $git_has_staged("src/**/*.py")
and not $git_has_staged("tests/**/*.py")
and $git_has_modified()
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
```

```toml
# Warn about file state before editing:
# - File is either staged or modified
# - Not a new file (untracked)
condition = '''
tool_name == "Edit"
and ($is_staged(tool_input.file_path) or $is_modified(tool_input.file_path))
and not $git_file_in(tool_input.file_path, "untracked")
'''
```

---

## Best practices for git-aware rules

1. **Check repository context first**: Use `$is_git_repo()` as a guard when rules only apply inside repositories.

2. **Use pattern functions for bulk checks**: Prefer `$git_has_staged("*.py")` over iterating individual files.

3. **Combine with `$current_branch()`**: Many policies vary by branch (main vs feature branches).

4. **Consider partial commits**: The distinction between staged and modified states is important for avoiding partial commits.

5. **Handle detached HEAD**: `$current_branch()` returns null for detached HEAD; use null-safe comparisons.

6. **Log for audit**: Use `post_tool_use` events to maintain an audit trail of git operations.
