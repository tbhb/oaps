---
name: conditions
title: Condition expression patterns
description: Context variables, tool-specific conditions, boolean logic, and common recipes for hook rule conditions. Load when writing condition expressions.
principles:
  - Use simple expressions when possible—complex logic belongs in Python actions
  - Prefer explicit tool_name checks before accessing tool_input fields
  - Combine related conditions with parentheses for clarity
  - Test conditions against real hook contexts before deploying
best_practices:
  - Check tool_name before accessing tool_input fields to avoid null access
  - Use regex patterns (=~) for flexible string matching
  - Group related conditions with and/or for readability
  - Prefer positive conditions over double negatives
  - Use $functions for complex checks (file existence, git state)
checklist:
  - Condition syntax is valid rule-engine expression
  - Tool-specific conditions check tool_name first
  - Boolean logic uses and/or/not (not &&/||/!)
  - String comparisons use == or =~ (regex)
  - Nested field access uses dot notation (tool_input.command)
related:
  - templates.md
  - priorities.md
---

# Condition expression patterns

Conditions determine when a hook rule fires. The hook system uses [rule-engine](https://github.com/zeroSteiner/rule-engine) for expression evaluation.

## Context variables

These variables are available in all condition expressions:

| Variable | Type | Description |
|:---------|:-----|:------------|
| `hook_type` | string | The event type: `pre_tool_use`, `post_tool_use`, `user_prompt_submit`, etc. |
| `session_id` | string | Claude session identifier |
| `cwd` | string | Current working directory |
| `permission_mode` | string | Permission mode: `default`, `acceptEdits`, `bypassPermissions`, `plan` |
| `tool_name` | string | Name of the tool (for tool events): `Bash`, `Read`, `Write`, `Edit`, etc. |
| `tool_input` | object | Tool input parameters (fields vary by tool) |
| `tool_output` | object | Tool response (only for `post_tool_use`) |
| `prompt` | string | User prompt text (only for `user_prompt_submit`) |
| `timestamp` | string | ISO 8601 timestamp of the event |

### Git context variables

When git context is available:

| Variable | Type | Description |
|:---------|:-----|:------------|
| `git_branch` | string | Current branch name |
| `git_is_dirty` | bool | Whether working tree has uncommitted changes |
| `git_head_commit` | string | HEAD commit SHA |
| `git_is_detached` | bool | Whether HEAD is detached |
| `git_staged_files` | list | Files in staging area |
| `git_modified_files` | list | Modified files not staged |
| `git_untracked_files` | list | Untracked files |
| `git_conflict_files` | list | Files with merge conflicts |

## Tool-specific conditions

### Check tool name first

Always check `tool_name` before accessing `tool_input` fields:

```toml
[[hooks.rules]]
id = "bash-rm-check"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash" and tool_input.command =~ "rm\\s+-rf"'
# ...
```

### Common tool_input fields

**Bash tool:**

- `tool_input.command` - The shell command

**Read tool:**

- `tool_input.file_path` - File path to read

**Write tool:**

- `tool_input.file_path` - File path to write
- `tool_input.content` - Content to write

**Edit tool:**

- `tool_input.file_path` - File path to edit
- `tool_input.old_string` - Text to find
- `tool_input.new_string` - Replacement text

**Glob tool:**

- `tool_input.pattern` - Glob pattern

**Grep tool:**

- `tool_input.pattern` - Search pattern
- `tool_input.path` - Search path

## Boolean operators

Use `and`, `or`, and `not` for boolean logic:

```toml
# Both conditions must be true
condition = 'tool_name == "Bash" and tool_input.command =~ "sudo"'

# Either condition can be true
condition = 'tool_name == "Write" or tool_name == "Edit"'

# Negation
condition = 'not (tool_name == "Read")'
```

### Combining with parentheses

Use parentheses to control evaluation order:

```toml
# File operations on sensitive paths
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
(tool_input.file_path =~ "\\.env" or tool_input.file_path =~ "secrets")
'''
```

## String matching

### Exact match

```toml
condition = 'tool_name == "Bash"'
```

### Regex match

Use `=~` for regex pattern matching:

```toml
# Match rm commands with -rf flags
condition = 'tool_input.command =~ "rm\\s+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)"'

# Match paths ending in .env
condition = 'tool_input.file_path =~ "\\.env$"'

# Match git commands
condition = 'tool_input.command =~ "^git\\s+(push|force-push)"'
```

### Escape sequences

In TOML strings, backslashes require escaping. For regex:

- `\\s` matches whitespace
- `\\d` matches digit
- `\\.` matches literal dot
- `\\w` matches word character

Use literal strings (`'''...'''`) for complex regex to reduce escaping.

## Negation patterns

### Simple negation

```toml
# Not a Read operation
condition = 'tool_name != "Read"'
```

### Negative regex

```toml
# Command does not contain sudo
condition = 'not (tool_input.command =~ "sudo")'
```

### Exclude specific paths

```toml
# Write to files not in tests/ directory
condition = '''
tool_name == "Write" and
not (tool_input.file_path =~ "^tests/")
'''
```

## Common recipes

### Block dangerous bash commands

```toml
[[hooks.rules]]
id = "block-dangerous-bash"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and (
    tool_input.command =~ "rm\\s+-rf\\s+/" or
    tool_input.command =~ "chmod\\s+-R\\s+777" or
    tool_input.command =~ ":(){ :|:& };:"
)
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Dangerous command blocked: ${tool_input.command}"
```

### Warn on env file access

```toml
[[hooks.rules]]
id = "warn-env-access"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
tool_input.file_path =~ "\\.env"
'''
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Accessing environment file: ${tool_input.file_path}"
```

### Log all file writes

```toml
[[hooks.rules]]
id = "log-file-writes"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Write"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "info"
message = "File written: ${tool_input.file_path}"
```

### Restrict to project directory

```toml
[[hooks.rules]]
id = "restrict-to-project"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Cannot write outside project directory: ${tool_input.file_path}"
```

### Check git branch

```toml
[[hooks.rules]]
id = "protect-main-branch"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command =~ "git\\s+push" and
git_branch == "main"
'''
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Pushing directly to main branch"
```

### User prompt filtering

```toml
[[hooks.rules]]
id = "flag-api-key-in-prompt"
events = ["user_prompt_submit"]
priority = "high"
condition = 'prompt =~ "(?i)(api[_-]?key|secret|password)\\s*[:=]"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Prompt may contain sensitive information"
```

## Custom functions

Use `$function()` syntax for complex checks:

| Function | Description |
|:---------|:------------|
| `$is_path_under(path, base)` | Check if path is under base directory |
| `$file_exists(path)` | Check if file exists |
| `$is_executable(path)` | Check if file is executable |
| `$matches_glob(path, pattern)` | Check if path matches glob pattern |
| `$env(name)` | Get environment variable value |
| `$is_git_repo()` | Check if in a git repository |
| `$is_staged(path)` | Check if file is staged |
| `$is_modified(path)` | Check if file is modified |
| `$has_conflicts(path)` | Check if file has conflicts |
| `$current_branch()` | Get current branch name |
| `$git_has_staged(pattern)` | Check if any staged file matches pattern |
| `$git_has_modified(pattern)` | Check if any modified file matches pattern |
| `$session_get(key)` | Get session state value |
| `$project_get(key)` | Get project configuration value |

### Function examples

```toml
# Block if writing to file that exists and is staged
condition = '''
tool_name == "Write" and
$file_exists(tool_input.file_path) and
$is_staged(tool_input.file_path)
'''

# Warn if there are uncommitted changes to Python files
condition = '$git_has_modified("*.py")'

# Check environment-based behavior
condition = '$env("CI") == "true"'
```
