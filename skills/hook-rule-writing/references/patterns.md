---
name: patterns
title: Common rule patterns
description: Security blocking, context injection, audit logging, and automation patterns with complete TOML examples. Load when writing rules for common use cases.
commands:
  oaps hooks test <file>: Validate rule configuration
  oaps hooks run <event>: Test rule execution
principles:
  - Match action severity to rule intent - deny for blocking, warn for guidance
  - Use critical priority for security rules that must execute first
  - Apply terminal = true for blocking rules to prevent further evaluation
  - Prefer regex anchoring for security patterns to avoid bypasses
best_practices:
  - "**Anchor security patterns**: Use word boundaries or start/end anchors"
  - "**Set terminal on blocking rules**: Prevent lower-priority rules from running"
  - "**Provide actionable messages**: Explain why blocked and how to proceed"
  - "**Log before blocking**: Use multiple actions to audit blocked operations"
  - "**Test security rules thoroughly**: Verify both matches and non-matches"
checklist:
  - Security rules use critical priority
  - Blocking rules set terminal = true
  - Deny messages explain the reason
  - Regex patterns use proper escaping
  - Rules tested with both positive and negative cases
related:
  - actions
  - conditions
  - expressions
---

## Security patterns

### Block dangerous commands

Block operations that could damage the system or delete critical data.

```toml
[[rules]]
id = "block-rm-rf-root"
description = "Block rm -rf targeting root or home directories"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and tool_input.command =~~ "rm\\s+(-[a-zA-Z]*r[a-zA-Z]*f|" +
    "-[a-zA-Z]*f[a-zA-Z]*r)\\s+(~|/|/home|/etc|/var)"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "BLOCKED dangerous rm command: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = "Dangerous rm command blocked. Never delete root, home, or system directories."
```

### Block sudo and privilege escalation

Prevent privilege escalation without explicit approval.

```toml
[[rules]]
id = "block-sudo"
description = "Block sudo commands"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and tool_input.command =~~ "^\\s*sudo\\b"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "sudo commands are not permitted. Request explicit approval if root access is required."
```

### Restrict file access outside project

Prevent reading or writing files outside the project directory.

```toml
[[rules]]
id = "restrict-file-access"
description = "Block file operations outside project directory"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
not $is_path_under(tool_input.file_path, cwd)
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot access files outside project: ${tool_input.file_path}"
```

### Protect sensitive files

Block access to credentials, environment files, and secrets.

```toml
[[rules]]
id = "protect-env-files"
description = "Block access to .env files containing secrets"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
matches_glob(tool_input.file_path, "**/.env*")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to .env files is restricted. These contain sensitive credentials."

[[rules]]
id = "protect-credentials"
description = "Block access to credential files"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/credentials.json") or
 matches_glob(tool_input.file_path, "**/secrets.yaml") or
 matches_glob(tool_input.file_path, "**/*.pem") or
 matches_glob(tool_input.file_path, "**/*_key") or
 matches_glob(tool_input.file_path, "**/id_rsa*"))
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to credential files is restricted: ${tool_input.file_path}"
```

### Block force push

Prevent accidental force pushes to protected branches.

```toml
[[rules]]
id = "block-force-push"
description = "Block git force push commands"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "git\\s+push.*--force(?!-with-lease)"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Force push blocked. Use --force-with-lease for safer force pushes."
```

## Context injection patterns

### Session start environment setup

Inject project context when a session starts.

```toml
[[rules]]
id = "session-context"
description = "Inject project context at session start"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Project: ${$basename(cwd)}
Branch: ${$current_branch()}
Python: Use uv run for all commands. Never use bare python.
Testing: Run 'just test' before committing.
Linting: Run 'just lint' to check code quality.
"""
```

### User prompt guidelines

Add project-specific guidelines when processing user prompts.

```toml
[[rules]]
id = "python-guidelines"
description = "Inject Python guidelines for Python-related prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "python|pytest|type.?hint|typing"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Python Guidelines:
- Use Python 3.10+ features (pattern matching, dataclasses with slots)
- NEVER use 'from __future__ import annotations' (runtime inspection required)
- Add comprehensive type hints (basedpyright strict mode)
- Follow Google-style docstrings for public APIs
- Use 'uv run' for all Python commands
"""
```

### Pre-compact context preservation

Preserve critical context before memory compaction.

```toml
[[rules]]
id = "preserve-context"
description = "Preserve important context before compaction"
events = ["pre_compact"]
priority = "high"
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = """
CRITICAL CONTEXT TO PRESERVE:
- Current task: Check session state for active todos
- Branch: ${$current_branch()}
- Modified files: Check git status
- Test status: Last test run results
"""
```

### Deploy context injection

Add deployment procedures when deploy-related prompts are detected.

```toml
[[rules]]
id = "deploy-context"
description = "Inject deployment context for deploy prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = 'prompt =~~ "deploy|release|ship|publish"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
DEPLOYMENT CHECKLIST:
1. Ensure all tests pass: just test
2. Check linting: just lint
3. Update version in pyproject.toml
4. Create changelog entry
5. Deployments require approval - see DEPLOY.md
"""
```

## Audit and logging patterns

### Log all tool executions

Create an audit trail of all tool usage.

```toml
[[rules]]
id = "audit-all-tools"
description = "Log all tool executions for audit trail"
events = ["pre_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "TOOL: ${tool_name} | INPUT: ${tool_input}"
```

### Track file modifications

Log all file write and edit operations.

```toml
[[rules]]
id = "audit-file-writes"
description = "Log all file modifications"
events = ["post_tool_use"]
priority = "low"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
tool_response.success == true
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "FILE MODIFIED: ${tool_input.file_path}"
```

### Log dangerous command attempts

Audit potentially dangerous commands even when allowed.

```toml
[[rules]]
id = "audit-dangerous-commands"
description = "Log potentially dangerous bash commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "rm|chmod|chown|kill|pkill|shutdown|reboot"
'''
result = "warn"

[[rules.actions]]
type = "log"
level = "warning"
message = "DANGEROUS COMMAND: ${tool_input.command}"

[[rules.actions]]
type = "warn"
message = "Potentially dangerous command detected. Proceeding with caution."
```

### API call auditing

Log external API calls for security review.

```toml
[[rules]]
id = "audit-api-calls"
description = "Log web fetch operations"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "WebFetch" or tool_name == "WebSearch"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "API CALL: ${tool_name} | URL/Query: ${tool_input}"
```

## Automation patterns

### Auto-format on write

Suggest running formatters after file writes.

```toml
[[rules]]
id = "suggest-format-python"
description = "Suggest formatting after Python file changes"
events = ["post_tool_use"]
priority = "medium"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
matches_glob(tool_input.file_path, "*.py") and
tool_response.success == true
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Consider running 'uv run ruff format ${tool_input.file_path}' to format this file."
```

### Pre-commit style checks

Warn about uncommitted style issues before git operations.

```toml
[[rules]]
id = "precommit-reminder"
description = "Remind about pre-commit checks before committing"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "git\\s+commit"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Before committing, ensure 'just prek' passes to run pre-commit hooks."
```

### Notification integrations

Send notifications for significant events (using script actions).

```toml
[[rules]]
id = "notify-deploy"
description = "Send notification when deploy commands are executed"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "deploy|release" and
tool_response.exit_code == 0
'''
result = "ok"

[[rules.actions]]
type = "script"
command = "curl -X POST https://hooks.example.com/notify -d 'Deploy triggered'"
timeout_ms = 5000
```

### Auto-approve safe commands

Automatically approve known-safe commands without user confirmation.

```toml
[[rules]]
id = "auto-approve-tests"
description = "Auto-approve test execution commands"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("pytest") or
 tool_input.command.starts_with("uv run pytest") or
 tool_input.command.starts_with("just test"))
'''
result = "ok"

[[rules.actions]]
type = "allow"

[[rules]]
id = "auto-approve-lint"
description = "Auto-approve linting commands"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("ruff") or
 tool_input.command.starts_with("uv run ruff") or
 tool_input.command.starts_with("just lint"))
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

## Combining patterns

### Multi-action security rule

Combine logging, warning, and blocking in a single rule.

```toml
[[rules]]
id = "comprehensive-security"
description = "Log, warn, and optionally block dangerous patterns"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "curl.*\\|.*sh|wget.*\\|.*sh"
'''
result = "block"
terminal = true

[[rules.actions]]
type = "log"
level = "error"
message = "SECURITY: Pipe-to-shell pattern detected: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = """
Remote code execution pattern blocked.

The command attempts to pipe remote content directly to a shell, which is
a significant security risk. Download the script first, review it, then
execute it separately.
"""
```

### Conditional context injection

Inject different context based on branch or environment.

```toml
[[rules]]
id = "main-branch-context"
description = "Add extra caution context when on main branch"
events = ["session_start"]
priority = "high"
condition = '$current_branch() == "main"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
WARNING: You are on the main branch.
- Create a feature branch before making changes
- Do not commit directly to main
- Use 'git checkout -b feat/description' to create a branch
"""

[[rules]]
id = "ci-environment-context"
description = "Add CI-specific context"
events = ["session_start"]
priority = "high"
condition = '$env("CI") == "true"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Running in CI environment.
- Avoid interactive commands
- Use non-interactive flags where available
- Tests must pass for pipeline success
"""
```
