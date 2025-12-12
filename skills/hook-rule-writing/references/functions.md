---
name: functions
title: Built-in functions
description: All 18 built-in expression functions for path checking, git status, state access, and environment variables. Load when writing conditions that need functions.
commands: {}
principles:
  - Functions use the $ prefix to distinguish from context variables
  - Functions return safe defaults for invalid inputs
  - Git functions require a git repository context
best_practices:
  - "**Use $is_path_under for security**: Validate paths are within expected directories"
  - "**Use $env for environment checks**: Detect CI, production, or feature flags"
  - "**Use $session_get for state**: Access cross-rule session state"
  - "**Use git functions for workflow rules**: Enforce commit hygiene and branch policies"
  - "**Chain with safe navigation**: Combine with &. when function input may be null"
checklist:
  - Function name spelled correctly with $ prefix
  - Correct number and types of arguments
  - Return value used appropriately in boolean context
  - Git functions used only when repository is available
related:
  - expressions
  - events
---

## Function categories

| Category | Functions | Purpose |
|----------|-----------|---------|
| Path | `$is_path_under`, `$file_exists`, `$is_executable`, `$matches_glob` | File system checks |
| Git repo | `$is_git_repo` | Repository detection |
| Git file status | `$is_staged`, `$is_modified`, `$has_conflicts`, `$current_branch` | Single file checks |
| Git pattern | `$git_has_staged`, `$git_has_modified`, `$git_has_untracked`, `$git_has_conflicts`, `$git_file_in` | Pattern-based status |
| State | `$session_get`, `$project_get` | State store access |
| Environment | `$env` | Environment variables |

## Path functions

### $is_path_under

Check if a path is safely under a base directory.

**Signature:** `$is_path_under(path, base) -> BOOLEAN`

**Description:** Use `Path.resolve()` and `is_relative_to()` for secure path checking. Prevents path traversal attacks by resolving symlinks and normalizing paths.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Path to check |
| `base` | STRING | Base directory path |

**Returns:** `true` if path is under base, `false` otherwise or on invalid input.

**Example:**

```toml
condition = '''
tool_name == "Write" and $is_path_under(tool_input.file_path, cwd)
'''
```

```toml
# Block writes outside project
condition = '''
tool_name == "Write" and not $is_path_under(tool_input.file_path, cwd)
'''
```

### $file_exists

Check if a file exists.

**Signature:** `$file_exists(path) -> BOOLEAN`

**Description:** Check if a file or directory exists at the given path.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Path to check |

**Returns:** `true` if file exists, `false` otherwise or on invalid input.

**Example:**

```toml
condition = '''
tool_name == "Write"
and tool_input.file_path.ends_with(".py")
and not $file_exists(tool_input.file_path)
'''
```

### $is_executable

Check if a file is executable.

**Signature:** `$is_executable(path) -> BOOLEAN`

**Description:** Check if a file exists and has executable permission.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Path to check |

**Returns:** `true` if file exists and is executable, `false` otherwise.

**Example:**

```toml
condition = '''
tool_name == "Bash"
and $is_executable(tool_input.command.split(" ")[0])
'''
```

### $matches_glob

Check if a path matches a glob pattern.

**Signature:** `$matches_glob(path, pattern) -> BOOLEAN`

**Description:** Match a path against a glob pattern using `fnmatch`.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Path to check |
| `pattern` | STRING | Glob pattern (e.g., `*.py`, `**/*.md`) |

**Returns:** `true` if path matches pattern, `false` otherwise.

**Example:**

```toml
condition = '''
tool_name == "Write" and $matches_glob(tool_input.file_path, "**/*.py")
'''
```

```toml
# Block writes to test files
condition = '''
tool_name == "Write" and $matches_glob(tool_input.file_path, "**/test_*.py")
'''
```

## Git repository function

### $is_git_repo

Check if the current working directory is inside a git repository.

**Signature:** `$is_git_repo() -> BOOLEAN`

**Description:** Walk up the directory tree from cwd looking for a `.git` directory.

**Arguments:** None

**Returns:** `true` if inside a git repository, `false` otherwise.

**Example:**

```toml
condition = '''
$is_git_repo() and tool_name == "Bash" and tool_input.command.starts_with("git")
'''
```

## Git file status functions

### $is_staged

Check if a file is staged for commit.

**Signature:** `$is_staged(path) -> BOOLEAN`

**Description:** Check if the given repository-relative file path is in the git staging area.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Repository-relative file path |

**Returns:** `true` if file is staged, `false` otherwise.

**Example:**

```toml
condition = '''
tool_name == "Write" and $is_staged(tool_input.file_path)
'''
```

### $is_modified

Check if a file is modified but not staged.

**Signature:** `$is_modified(path) -> BOOLEAN`

**Description:** Check if the given repository-relative file path has unstaged modifications.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Repository-relative file path |

**Returns:** `true` if file is modified (unstaged), `false` otherwise.

**Example:**

```toml
condition = '''
tool_name == "Edit" and $is_modified(tool_input.file_path)
'''
```

### $has_conflicts

Check if the repository has merge conflicts.

**Signature:** `$has_conflicts() -> BOOLEAN`

**Description:** Check if there are any files with merge conflicts in the repository.

**Arguments:** None

**Returns:** `true` if there are conflict files, `false` otherwise.

**Example:**

```toml
condition = '''
$has_conflicts() and tool_name == "Bash" and tool_input.command.starts_with("git commit")
'''
```

### $current_branch

Get the current branch name.

**Signature:** `$current_branch() -> STRING | NULL`

**Description:** Get the name of the current branch.

**Arguments:** None

**Returns:** Branch name as STRING, or `null` if HEAD is detached.

**Example:**

```toml
condition = '''
$current_branch() == "main" and tool_name == "Bash" and tool_input.command =~~ "push"
'''
```

```toml
# Warn when committing to main
condition = '''
$current_branch() in ["main", "master"]
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
```

## Git pattern functions

### $git_has_staged

Check if staged files exist, optionally matching a pattern.

**Signature:** `$git_has_staged([pattern]) -> BOOLEAN`

**Description:** Check if there are any staged files. If a pattern is provided, check if any staged files match the glob pattern.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `pattern` | STRING (optional) | Glob pattern to match against staged files |

**Returns:** `true` if staged files exist (matching pattern if provided), `false` otherwise.

**Example:**

```toml
# Any staged files
condition = '$git_has_staged()'

# Staged Python files
condition = '$git_has_staged("*.py")'

# Staged test files
condition = '$git_has_staged("test_*.py")'
```

### $git_has_modified

Check if modified (unstaged) files exist, optionally matching a pattern.

**Signature:** `$git_has_modified([pattern]) -> BOOLEAN`

**Description:** Check if there are any modified but unstaged files. If a pattern is provided, check if any modified files match the glob pattern.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `pattern` | STRING (optional) | Glob pattern to match against modified files |

**Returns:** `true` if modified files exist (matching pattern if provided), `false` otherwise.

**Example:**

```toml
# Any modified files
condition = '$git_has_modified()'

# Modified Python files
condition = '$git_has_modified("*.py")'
```

### $git_has_untracked

Check if untracked files exist, optionally matching a pattern.

**Signature:** `$git_has_untracked([pattern]) -> BOOLEAN`

**Description:** Check if there are any untracked files. If a pattern is provided, check if any untracked files match the glob pattern.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `pattern` | STRING (optional) | Glob pattern to match against untracked files |

**Returns:** `true` if untracked files exist (matching pattern if provided), `false` otherwise.

**Example:**

```toml
# Any untracked files
condition = '$git_has_untracked()'

# Untracked Python files
condition = '$git_has_untracked("*.py")'
```

### $git_has_conflicts

Check if conflict files exist, optionally matching a pattern.

**Signature:** `$git_has_conflicts([pattern]) -> BOOLEAN`

**Description:** Check if there are any files with merge conflicts. If a pattern is provided, check if any conflict files match the glob pattern.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `pattern` | STRING (optional) | Glob pattern to match against conflict files |

**Returns:** `true` if conflict files exist (matching pattern if provided), `false` otherwise.

**Example:**

```toml
# Any conflicts
condition = '$git_has_conflicts()'

# Conflicts in Python files
condition = '$git_has_conflicts("*.py")'
```

### $git_file_in

Check if a file is in a specific git status set.

**Signature:** `$git_file_in(path, set_name) -> BOOLEAN`

**Description:** Check if a file is in one of the git status sets: staged, modified, untracked, or conflict.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `path` | STRING | Repository-relative file path |
| `set_name` | STRING | Set name: "staged", "modified", "untracked", or "conflict" |

**Returns:** `true` if file is in the specified set, `false` otherwise.

**Example:**

```toml
condition = '''
tool_name == "Write"
and $git_file_in(tool_input.file_path, "staged")
'''
```

```toml
# Warn if editing a file with conflicts
condition = '''
tool_name == "Edit"
and $git_file_in(tool_input.file_path, "conflict")
'''
```

## State functions

### $session_get

Get a value from the session state store.

**Signature:** `$session_get(key) -> STRING | FLOAT | NULL`

**Description:** Retrieve a value from the session-scoped state store. Values are scoped to the current session and lost when the session ends.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `key` | STRING | Key to look up |

**Returns:** The stored value, or `null` if not found.

**Example:**

```toml
condition = '''
$session_get("oaps.prompts.count") > 5
'''
```

```toml
# Check custom flag
condition = '''
$session_get("custom.flag") == "enabled"
'''
```

### $project_get

Get a value from the project state store.

**Signature:** `$project_get(key) -> STRING | FLOAT | NULL`

**Description:** Retrieve a value from the project-scoped state store. Values persist across sessions within the same project.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `key` | STRING | Key to look up |

**Returns:** The stored value, or `null` if not found or on error.

**Example:**

```toml
condition = '''
$project_get("deploy.approved") == "true"
'''
```

## Environment function

### $env

Get an environment variable value.

**Signature:** `$env(name) -> STRING | NULL`

**Description:** Retrieve the value of an environment variable.

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `name` | STRING | Environment variable name |

**Returns:** The environment variable value, or `null` if not set.

**Example:**

```toml
# Check if running in CI
condition = '$env("CI") != null'
```

```toml
# Check specific environment
condition = '$env("OAPS_ENV") == "production"'
```

```toml
# Skip hook in CI
condition = '''
$env("CI") == null
and tool_name == "Bash"
and tool_input.command =~~ "deploy"
'''
```

## Built-in collection functions

These functions are from the underlying rule-engine library:

### $all

Check if all elements in an array are truthy.

**Signature:** `$all(array) -> BOOLEAN`

**Example:**

```toml
condition = '''
$all([f.ends_with(".py") for f in files])
'''
```

### $any

Check if any element in an array is truthy.

**Signature:** `$any(array) -> BOOLEAN`

**Example:**

```toml
condition = '''
$any([f.starts_with("test_") for f in files])
'''
```

### $abs

Get the absolute value of a number.

**Signature:** `$abs(number) -> FLOAT`

### $max

Get the maximum value from an array.

**Signature:** `$max(array) -> FLOAT`

### $min

Get the minimum value from an array.

**Signature:** `$min(array) -> FLOAT`

### $sum

Get the sum of values in an array.

**Signature:** `$sum(array) -> FLOAT`

### $split

Split a string by a separator.

**Signature:** `$split(string, separator) -> ARRAY`

**Example:**

```toml
condition = '''
$split(tool_input.command, " ")[0] == "npm"
'''
```

## Practical examples

### Enforce project boundaries

```toml
[[rules]]
id = "enforce-project-boundary"
events = ["pre_tool_use"]
condition = '''
tool_name in ["Write", "Edit"]
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write files outside project directory"
```

### Block commits on main branch

```toml
[[rules]]
id = "block-main-commits"
events = ["pre_tool_use"]
condition = '''
$is_git_repo()
and $current_branch() in ["main", "master"]
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot commit directly to ${$current_branch()}. Create a feature branch first."
```

### Warn about unstaged changes

```toml
[[rules]]
id = "warn-unstaged-changes"
events = ["pre_tool_use"]
condition = '''
$is_git_repo()
and $git_has_modified()
and tool_name == "Bash"
and tool_input.command.starts_with("git commit")
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "You have unstaged changes. Run 'git status' to review."
```

### Detect CI environment

```toml
[[rules]]
id = "ci-mode"
events = ["session_start"]
condition = '$env("CI") != null'
result = "ok"

[[rules.actions]]
type = "inject"
content = "Running in CI environment. Auto-approval enabled for safe operations."
```

### Check session prompt count

```toml
[[rules]]
id = "long-session-reminder"
events = ["user_prompt_submit"]
condition = '''
$session_get("oaps.prompts.count") > 20
'''
result = "warn"

[[rules.actions]]
type = "suggest"
message = "This is a long session. Consider starting a new session to reset context."
```
