---
name: security
title: Security patterns
description: Path traversal prevention, dangerous command detection, sensitive file protection, and permission mode awareness for secure hook rules.
commands: {}
principles:
  - Use $is_path_under for all path validation
  - Block dangerous commands at the earliest opportunity
  - Protect sensitive files from modification
  - Consider permission_mode when allowing operations
  - Apply defense in depth with multiple rule layers
best_practices:
  - "**Validate paths with $is_path_under**: Always verify paths are within expected directories"
  - "**Block destructive commands**: Prevent rm -rf, force push, and similar operations"
  - "**Protect sensitive files**: Block access to .env, credentials, and config files"
  - "**Check permission_mode**: Be stricter in default mode, relaxed in bypassPermissions"
  - "**Use terminal rules**: Stop evaluation after critical security blocks"
  - "**Layer defenses**: Combine multiple rules for defense in depth"
checklist:
  - Paths validated with $is_path_under before allowing writes
  - Dangerous command patterns blocked (rm -rf, force push, etc.)
  - Sensitive files protected (.env, credentials, secrets)
  - Permission mode considered for auto-approval rules
  - Security rules use critical or high priority
  - Terminal flag set on blocking rules to prevent bypasses
related:
  - functions
  - expressions
  - priorities
---

## Path traversal prevention

Use `$is_path_under` to prevent path traversal attacks. This function resolves symlinks and normalizes paths before checking.

### Basic path validation

```toml
[[rules]]
id = "enforce-project-boundary"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit"]
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write files outside project directory"
```

### Protect specific directories

```toml
[[rules]]
id = "protect-system-files"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit", "Bash"]
and (
    $is_path_under(tool_input.file_path, "/etc")
    or $is_path_under(tool_input.file_path, "/usr")
    or $is_path_under(tool_input.file_path, "/var")
)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot modify system files"
```

### Allow specific subdirectories

```toml
[[rules]]
id = "restrict-to-src"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write"
and tool_input.file_path.ends_with(".py")
and not $is_path_under(tool_input.file_path, cwd + "/src")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Python files must be in src/ directory"
```

## Safe path checking patterns

### Combine path and file type checks

```toml
[[rules]]
id = "validate-config-writes"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write"
and $matches_glob(tool_input.file_path, "**/*.toml")
and not $is_path_under(tool_input.file_path, cwd + "/.oaps")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "TOML config files can only be created in .oaps directory"
```

### Check both absolute and relative paths

```toml
[[rules]]
id = "block-parent-traversal"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit", "Read"]
and (
    tool_input.file_path =~~ "\\.\\."
    or tool_input.file_path.starts_with("/")
)
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Path traversal detected"
```

## Permission mode awareness

The `permission_mode` context variable indicates the current Claude Code permission level.

### Permission mode values

| Mode | Description |
|------|-------------|
| `default` | Normal interactive mode, requires user approval |
| `plan` | Planning mode, more restricted |
| `acceptEdits` | Auto-accept file edits |
| `bypassPermissions` | Full automation mode (CI/scripts) |

### Stricter rules in default mode

```toml
[[rules]]
id = "strict-default-mode"
events = ["pre_tool_use"]
priority = "high"
condition = '''
permission_mode == "default"
and tool_name == "Bash"
and tool_input.command =~~ "npm publish|docker push"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Publishing commands require explicit approval. Use bypassPermissions mode for automation."
```

### Allow in automation mode

```toml
[[rules]]
id = "allow-ci-operations"
events = ["permission_request"]
priority = "medium"
condition = '''
permission_mode == "bypassPermissions"
and tool_name == "Bash"
and tool_input.command.starts_with("pytest")
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Warn in interactive mode

```toml
[[rules]]
id = "warn-interactive-deploy"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
permission_mode in ["default", "acceptEdits"]
and tool_name == "Bash"
and tool_input.command =~~ "deploy"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Running deploy in interactive mode. Consider using CI/CD for production deployments."
```

## Dangerous command detection

### Block destructive file operations

```toml
[[rules]]
id = "block-rm-rf"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "rm\\s+(-[rRf]+\\s+)+/"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Recursive delete from root blocked"
```

```toml
[[rules]]
id = "block-dangerous-rm"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "rm\\s+-[rRf]*\\s+(\\*|~|\\$HOME|/home)"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Dangerous rm command blocked: ${tool_input.command}"
```

### Block dangerous git operations

```toml
[[rules]]
id = "block-force-push"
events = ["pre_tool_use"]
priority = "high"
terminal = true
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "git\\s+push.*--force(?!-with-lease)"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Force push blocked. Use --force-with-lease for safer force pushing."
```

```toml
[[rules]]
id = "block-hard-reset"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "git\\s+reset\\s+--hard"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "git reset --hard will lose uncommitted changes. Ensure this is intentional."
```

### Block privilege escalation

```toml
[[rules]]
id = "block-sudo"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "^sudo\\s|\\s+sudo\\s"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "sudo commands are not allowed"
```

```toml
[[rules]]
id = "block-chmod-dangerous"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "chmod\\s+777|chmod\\s+-R\\s+777"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "chmod 777 creates security vulnerabilities. Use more restrictive permissions."
```

## Sensitive file protection

### Block access to secret files

```toml
[[rules]]
id = "protect-env-files"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit", "Read"]
and (
    tool_input.file_path.ends_with(".env")
    or tool_input.file_path.ends_with(".env.local")
    or $matches_glob(tool_input.file_path, "**/.env.*")
)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to .env files is blocked to protect secrets"
```

### Protect credential files

```toml
[[rules]]
id = "protect-credentials"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name in ["Write", "Edit", "Read"]
and (
    $matches_glob(tool_input.file_path, "**/credentials*")
    or $matches_glob(tool_input.file_path, "**/secrets*")
    or $matches_glob(tool_input.file_path, "**/*.pem")
    or $matches_glob(tool_input.file_path, "**/*.key")
    or $matches_glob(tool_input.file_path, "**/id_rsa*")
)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to credential files is blocked"
```

### Warn on config file access

```toml
[[rules]]
id = "warn-config-access"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name in ["Write", "Edit"]
and (
    $matches_glob(tool_input.file_path, "**/config.json")
    or $matches_glob(tool_input.file_path, "**/settings.json")
    or $matches_glob(tool_input.file_path, "**/*.config.js")
)
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Modifying config file: ${tool_input.file_path}. Ensure no secrets are exposed."
```

## Environment variable safety

### Block commands that expose secrets

```toml
[[rules]]
id = "block-env-exposure"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "env|printenv|export|echo\\s+\\$"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Command may expose environment variables. Avoid logging sensitive data."
```

### Detect hardcoded secrets in writes

```toml
[[rules]]
id = "warn-potential-secrets"
events = ["post_tool_use"]
priority = "high"
condition = '''
tool_name == "Write"
and (
    tool_input.content =~~ "password\\s*=|api_key\\s*=|secret\\s*="
    or tool_input.content =~~ "sk-[a-zA-Z0-9]{20,}"
    or tool_input.content =~~ "ghp_[a-zA-Z0-9]{36}"
)
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Potential hardcoded secret detected. Use environment variables instead."
```

## CI vs interactive mode considerations

### Auto-approve safe operations in CI

```toml
[[rules]]
id = "ci-auto-approve-tests"
events = ["permission_request"]
priority = "medium"
condition = '''
$env("CI") != null
and tool_name == "Bash"
and (
    tool_input.command.starts_with("pytest")
    or tool_input.command.starts_with("npm test")
    or tool_input.command.starts_with("cargo test")
)
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Extra caution in CI

```toml
[[rules]]
id = "ci-block-network"
events = ["pre_tool_use"]
priority = "high"
condition = '''
$env("CI") != null
and tool_name == "Bash"
and tool_input.command =~~ "curl|wget|nc|netcat"
and not tool_input.command =~~ "localhost|127\\.0\\.0\\.1"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Network commands to external hosts blocked in CI"
```

### Interactive-only warnings

```toml
[[rules]]
id = "interactive-production-warning"
events = ["pre_tool_use"]
priority = "high"
condition = '''
$env("CI") == null
and tool_name == "Bash"
and tool_input.command =~~ "production|prod\\s"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Command references production. Double-check before proceeding."
```

## Defense in depth

Layer multiple rules for comprehensive protection:

```toml
# Layer 1: Critical blocks (terminal)
[[rules]]
id = "security-critical-blocks"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash"
and (
    tool_input.command =~~ "rm\\s+-rf\\s+/"
    or tool_input.command =~~ ":[(][)][{]\\s*:[|]:[&]\\s*[}];:"
)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Dangerous command blocked"

# Layer 2: High priority warnings
[[rules]]
id = "security-high-warnings"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash"
and tool_input.command =~~ "sudo|chmod\\s+[0-7]*7|curl.*\\|.*sh"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Potentially dangerous command. Review carefully."

[[rules.actions]]
type = "log"
level = "warning"
message = "Security warning: ${tool_input.command}"

# Layer 3: Path boundary enforcement
[[rules]]
id = "security-path-boundary"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name in ["Write", "Edit"]
and not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write outside project directory"

# Layer 4: Audit logging
[[rules]]
id = "security-audit-log"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name in ["Write", "Edit", "Bash"]
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "Operation: ${tool_name}, Path: ${tool_input.file_path}, Command: ${tool_input.command}"
```
