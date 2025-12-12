---
name: configuration
title: TOML configuration format
description: File structure, locations, loading precedence, drop-in directories, and enabling/disabling rules. Load when setting up hook configuration.
principles:
  - Configuration uses fail-open semantics—errors do not block operations
  - Later sources override earlier sources with the same rule ID
  - Drop-in files provide modular, composable configuration
  - Local and worktree configs are for machine-specific overrides
best_practices:
  - Commit project rules to .oaps/oaps.toml for team sharing
  - Use .oaps/oaps.local.toml for personal overrides (gitignored)
  - Number drop-in files for explicit ordering (00-base.toml, 50-project.toml)
  - Use descriptive rule IDs that indicate purpose
  - Set enabled = false to disable inherited rules without removing them
checklist:
  - TOML syntax is valid (test with toml validator)
  - Required fields present (id, events, condition, result)
  - Rule IDs follow naming pattern (lowercase, hyphens, 2+ chars)
  - File locations match intended precedence
  - Drop-in files contain only rules (no global settings)
related:
  - conditions.md
  - priorities.md
  - templates.md
---

# TOML configuration format

Hook rules are configured in TOML format across multiple file locations with precedence-based merging.

## File structure

### Basic rule structure

```toml
[[hooks.rules]]
id = "rule-identifier"
events = ["pre_tool_use"]
priority = "medium"
condition = 'tool_name == "Bash"'
result = "warn"
enabled = true
terminal = false
description = "Optional description of what this rule does"

[[hooks.rules.actions]]
type = "warn"
message = "Warning message"
```

### Required fields

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | Unique rule identifier |
| `events` | array | Hook event types to handle |
| `condition` | string | Expression that triggers the rule |
| `result` | string | Result type: `block`, `warn`, or `ok` |

### Optional fields

| Field | Type | Default | Description |
|:------|:-----|:--------|:------------|
| `priority` | string | `"medium"` | Evaluation priority |
| `enabled` | bool | `true` | Whether rule is active |
| `terminal` | bool | `false` | Stop evaluation after match |
| `description` | string | none | Human-readable description |
| `actions` | array | `[]` | Actions to execute on match |

### Rule ID constraints

The `id` field must match the pattern `^[a-z][a-z0-9-]*[a-z0-9]$`:

- Start with a lowercase letter
- Contain only lowercase letters, digits, and hyphens
- End with a lowercase letter or digit
- Minimum length of 2 characters

```toml
# Valid IDs
id = "block-sudo"
id = "warn-env-access"
id = "log-writes-2024"

# Invalid IDs
id = "Block-Sudo"      # No uppercase
id = "1-block"         # Must start with letter
id = "block-"          # Must end with letter or digit
id = "x"               # Too short (minimum 2 chars)
```

### Event types

Valid values for the `events` field:

| Event | Category | Description |
|:------|:---------|:------------|
| `pre_tool_use` | Tool lifecycle | Before tool execution |
| `post_tool_use` | Tool lifecycle | After tool execution |
| `user_prompt_submit` | User interaction | When user submits prompt |
| `permission_request` | User interaction | When permission is requested |
| `notification` | User interaction | When notification is sent |
| `session_start` | Session lifecycle | When session begins |
| `session_end` | Session lifecycle | When session ends |
| `stop` | Session lifecycle | When stopped by user |
| `subagent_stop` | Session lifecycle | When subagent stopped |
| `pre_compact` | Memory management | Before memory compaction |
| `all` | Special | Match all event types |

```toml
# Single event
events = ["pre_tool_use"]

# Multiple events
events = ["pre_tool_use", "post_tool_use"]

# All events
events = ["all"]
```

### Result types

| Result | Description |
|:-------|:------------|
| `block` | Block the operation |
| `warn` | Show warning, allow operation |
| `ok` | Allow operation silently |

## Configuration file locations

Configuration loads from multiple sources with precedence:

| Priority | Location | Description |
|:---------|:---------|:------------|
| 1 (lowest) | Built-in | `<oaps_package>/hooks/builtin/*.toml` |
| 2 | User | `~/.config/oaps/config.toml` |
| 3 | Project hooks | `.oaps/hooks.toml` |
| 4 | Project drop-in | `.oaps/hooks.d/*.toml` |
| 5 | Project inline | `.oaps/oaps.toml` |
| 6 | Local | `.oaps/oaps.local.toml` |
| 7 (highest) | Worktree | `.git/oaps.toml` |

### User configuration

User-level defaults apply to all projects:

```
~/.config/oaps/config.toml
```

```toml
# User-wide hook rules
[[hooks.rules]]
id = "user-log-all"
events = ["post_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "debug"
message = "Tool: ${tool_name}"
```

### Project configuration

Project rules committed to version control:

```
.oaps/oaps.toml
```

```toml
[hooks]
log_level = "info"

[[hooks.rules]]
id = "project-restrict-writes"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write" and
not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[hooks.rules.actions]]
type = "deny"
message = "Cannot write outside project"
```

### Local overrides

Machine-specific overrides (gitignored):

```
.oaps/oaps.local.toml
```

```toml
# Disable a project rule locally
[[hooks.rules]]
id = "project-restrict-writes"
enabled = false
events = ["pre_tool_use"]
condition = "false"
result = "ok"
```

### Worktree configuration

Worktree-specific configuration:

```
.git/oaps.toml
```

```toml
# Worktree-specific rules (e.g., for feature branches)
[[hooks.rules]]
id = "worktree-verbose-logging"
events = ["post_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[hooks.rules.actions]]
type = "log"
level = "debug"
message = "Worktree debug: ${tool_name}"
```

## Drop-in directory

The drop-in directory (`.oaps/hooks.d/`) provides modular configuration.

### Drop-in file rules

Drop-in files must:

- Have `.toml` extension
- Be valid TOML
- Contain only `[[rules]]` sections (no global settings)

```
.oaps/hooks.d/
├── 00-security.toml      # Loaded first
├── 50-project.toml       # Loaded second
└── 90-local.toml         # Loaded last
```

### Drop-in file format

Drop-in files use `[[rules]]` instead of `[[hooks.rules]]`:

```toml
# .oaps/hooks.d/00-security.toml

[[rules]]
id = "security-block-rm-rf"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = 'tool_name == "Bash" and tool_input.command =~ "rm\\s+-rf\\s+/"'
result = "block"

[[rules.actions]]
type = "deny"
message = "Dangerous rm command blocked"

[[rules]]
id = "security-warn-sudo"
events = ["pre_tool_use"]
priority = "high"
condition = 'tool_name == "Bash" and tool_input.command =~ "sudo"'
result = "warn"

[[rules.actions]]
type = "warn"
message = "sudo command detected"
```

### Lexicographic ordering

Files load in lexicographic (alphabetical) order by filename:

```
00-base.toml      # First
01-security.toml  # Second
50-project.toml   # Third
99-local.toml     # Last
```

Use numeric prefixes to control ordering explicitly.

### Environment variable override

Override the drop-in directory path:

```bash
export OAPS_HOOKS__DROPIN_DIR="/custom/hooks.d"
```

## Loading precedence

### Merge behavior

Rules from all sources merge into a single list. When multiple rules share the same `id`, the rule from the highest-precedence source wins.

```toml
# .oaps/oaps.toml (precedence 5)
[[hooks.rules]]
id = "my-rule"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Original warning"
```

```toml
# .oaps/oaps.local.toml (precedence 6, wins)
[[hooks.rules]]
id = "my-rule"
events = ["pre_tool_use"]
condition = 'tool_name == "Bash"'
result = "ok"

[[hooks.rules.actions]]
type = "log"
message = "Overridden to log only"
```

The local version completely replaces the project version.

### Full precedence chain

1. **Built-in hooks** (`<oaps>/hooks/builtin/*.toml`): Default rules shipped with OAPS
2. **User config** (`~/.config/oaps/config.toml`): User preferences
3. **Project hooks.toml** (`.oaps/hooks.toml`): External hooks file
4. **Project drop-in** (`.oaps/hooks.d/*.toml`): Modular rules
5. **Project inline** (`.oaps/oaps.toml`): Main project config
6. **Local overrides** (`.oaps/oaps.local.toml`): Machine-specific
7. **Worktree config** (`.git/oaps.toml`): Worktree-specific

## Enabling and disabling rules

### Disable a rule

Set `enabled = false` to disable a rule:

```toml
[[hooks.rules]]
id = "some-rule"
enabled = false
events = ["pre_tool_use"]
condition = "false"
result = "ok"
```

### Override inherited rules

To disable a rule from a lower-precedence source, redefine it with `enabled = false`:

```toml
# In .oaps/oaps.local.toml
# Disables the built-in rule with this ID
[[hooks.rules]]
id = "builtin-security-check"
enabled = false
events = ["pre_tool_use"]
condition = "false"
result = "ok"
```

### Conditional enabling

Rules cannot be conditionally enabled at load time. Use condition expressions for runtime conditional behavior:

```toml
[[hooks.rules]]
id = "ci-only-rule"
events = ["pre_tool_use"]
condition = '$env("CI") == "true" and tool_name == "Bash"'
result = "warn"

[[hooks.rules.actions]]
type = "warn"
message = "Running in CI environment"
```

## Action configuration

### Action types

| Type | Description | Required Fields |
|:-----|:------------|:----------------|
| `deny` | Block operation | `message` |
| `allow` | Explicitly allow | none |
| `warn` | Show warning | `message` |
| `log` | Log to file | `message`, optionally `level` |
| `suggest` | Show suggestion | `message` |
| `script` | Run shell command | `command` or `script` |
| `python` | Run Python code | `entrypoint` or `script` |
| `transform` | Modify tool input | `field`, `value` |
| `modify` | Modify hook output | `field`, `value`, `operation` |
| `inject` | Inject context | `content` |

### Deny action

```toml
[[hooks.rules.actions]]
type = "deny"
message = "Operation blocked: ${tool_name}"
interrupt = true  # Stop agent loop (default: true)
```

### Log action

```toml
[[hooks.rules.actions]]
type = "log"
level = "info"  # debug, info, warning, error
message = "Tool used: ${tool_name} on ${tool_input.file_path}"
```

### Script action

```toml
[[hooks.rules.actions]]
type = "script"
command = "notify-send 'Hook triggered'"
timeout_ms = 5000
shell = "/bin/bash"
```

### Python action

```toml
[[hooks.rules.actions]]
type = "python"
entrypoint = "myproject.hooks:on_tool_use"
```

## Validation and errors

### Validation at load time

Configuration validates at load time:

- TOML syntax
- Required fields
- Field types
- Rule ID format
- Expression syntax

### Error handling

| Error Type | Behavior |
|:-----------|:---------|
| TOML parse error | Reject file, continue with others |
| Missing required field | Reject rule, continue with others |
| Invalid expression | Reject rule, continue with others |
| Unknown field | Log warning, ignore field |
| Duplicate rule ID | Later rule overrides earlier |

### Fail-open semantics

The hook system uses fail-open semantics:

- Configuration errors do not block Claude Code
- Individual rule failures do not affect other rules
- Hook execution failures allow operations to proceed
