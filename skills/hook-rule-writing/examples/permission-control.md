# Permission Control Examples

Hook rules for controlling what operations Claude can perform. These examples demonstrate deny, allow, warn, and suggest actions for security enforcement and user guidance.

## Deny action examples

### Block rm -rf targeting root directories

Prevent catastrophic deletion commands that could destroy the system.

```toml
[[rules]]
id = "block-rm-rf-root"
description = "Block rm -rf targeting root or critical system directories"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "rm\\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\\s+(~|/|/home|/etc|/var|/usr)"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "BLOCKED dangerous rm command: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = "Dangerous rm command blocked. Recursive force deletion of system directories is not permitted."
```

### Block sudo commands

Prevent privilege escalation without explicit approval.

```toml
[[rules]]
id = "block-sudo"
description = "Block all sudo commands"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and tool_input.command =~~ "^\\s*sudo\\b"
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "sudo commands are blocked. If root access is required, request explicit approval from the user."
```

### Block writes to protected directories

Prevent modifications to system directories and sensitive paths.

```toml
[[rules]]
id = "block-system-writes"
description = "Block file writes to system directories"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
(tool_input.file_path =~ "^/(etc|usr|var|bin|sbin|lib|boot)/" or
 tool_input.file_path =~ "^/System/" or
 tool_input.file_path =~ "^/Library/")
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Cannot write to system directory: ${tool_input.file_path}. These paths are protected."
```

### Block access to sensitive credential files

Prevent reading or modifying files containing secrets.

```toml
[[rules]]
id = "block-credential-access"
description = "Block access to credential and secret files"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/.env") or
 matches_glob(tool_input.file_path, "**/.env.*") or
 matches_glob(tool_input.file_path, "**/credentials.json") or
 matches_glob(tool_input.file_path, "**/secrets.yaml") or
 matches_glob(tool_input.file_path, "**/secrets.yml") or
 matches_glob(tool_input.file_path, "**/*.pem") or
 matches_glob(tool_input.file_path, "**/id_rsa*") or
 matches_glob(tool_input.file_path, "**/*_key"))
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to credential file blocked: ${tool_input.file_path}. These files contain sensitive information."
```

## Allow action examples

### Allowlist trusted read-only tools

Auto-approve read operations within the project directory.

```toml
[[rules]]
id = "allow-project-reads"
description = "Auto-approve Read tool for files within project"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Read" and $is_path_under(tool_input.file_path, cwd)
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Allow specific commands

Auto-approve known-safe development commands.

```toml
[[rules]]
id = "allow-test-commands"
description = "Auto-approve test execution commands"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("pytest") or
 tool_input.command.starts_with("uv run pytest") or
 tool_input.command.starts_with("just test") or
 tool_input.command.starts_with("npm test") or
 tool_input.command.starts_with("cargo test"))
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Auto-approve in CI environment

Allow all operations when running in continuous integration.

```toml
[[rules]]
id = "allow-ci-operations"
description = "Auto-approve operations in CI environment"
events = ["permission_request"]
priority = "high"
condition = '''
$env("CI") == "true" or $env("GITHUB_ACTIONS") == "true"
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

### Allow lint and format commands

Auto-approve code quality tools.

```toml
[[rules]]
id = "allow-lint-format"
description = "Auto-approve linting and formatting commands"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("ruff") or
 tool_input.command.starts_with("uv run ruff") or
 tool_input.command.starts_with("just lint") or
 tool_input.command.starts_with("just format") or
 tool_input.command.starts_with("eslint") or
 tool_input.command.starts_with("prettier"))
'''
result = "ok"

[[rules.actions]]
type = "allow"
```

## Warn action examples

### Warn on large file operations

Alert before processing files that might be large.

```toml
[[rules]]
id = "warn-large-file-patterns"
description = "Warn when reading potentially large files"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Read" and
(matches_glob(tool_input.file_path, "**/*.log") or
 matches_glob(tool_input.file_path, "**/node_modules/**") or
 matches_glob(tool_input.file_path, "**/*.min.js") or
 matches_glob(tool_input.file_path, "**/*.bundle.js"))
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "This file may be large: ${tool_input.file_path}. Consider using Grep or reading specific sections."
```

### Warn on git force operations

Caution before potentially destructive git commands.

```toml
[[rules]]
id = "warn-git-force"
description = "Warn on git commands that rewrite history"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command =~~ "git\\s+push.*--force-with-lease" or
 tool_input.command =~~ "git\\s+reset\\s+--hard" or
 tool_input.command =~~ "git\\s+rebase" or
 tool_input.command =~~ "git\\s+commit.*--amend")
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "This git command may rewrite history. Ensure this is intentional: ${tool_input.command}"
```

### Warn on main branch commits

Alert when committing directly to protected branches.

```toml
[[rules]]
id = "warn-main-commit"
description = "Warn when committing to main or master branch"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "git\\s+commit" and
($current_branch() == "main" or $current_branch() == "master")
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "You are committing directly to ${$current_branch()}. Consider using a feature branch instead."
```

### Warn on external network requests

Alert before making requests to external services.

```toml
[[rules]]
id = "warn-network-requests"
description = "Warn before external network operations"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "curl|wget|http|fetch"
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "External network request detected: ${tool_input.command}. Verify the URL is trusted."
```

## Suggest action examples

### Suggest running tests after code changes

Remind to test after modifying implementation files.

```toml
[[rules]]
id = "suggest-tests-after-edit"
description = "Suggest running tests after editing source files"
events = ["post_tool_use"]
priority = "medium"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "src/**/*.py") or
 matches_glob(tool_input.file_path, "lib/**/*.ts") or
 matches_glob(tool_input.file_path, "**/*.rs")) and
not matches_glob(tool_input.file_path, "**/test_*") and
not matches_glob(tool_input.file_path, "**/*.test.*")
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Source file modified. Consider running tests to verify: ${tool_input.file_path}"
```

### Suggest commit after multiple edits

Remind to commit changes periodically.

```toml
[[rules]]
id = "suggest-commit"
description = "Suggest committing after editing files"
events = ["post_tool_use"]
priority = "low"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
$is_path_under(tool_input.file_path, cwd)
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "File modified: ${tool_input.file_path}. Consider committing your changes when the task is complete."
```

### Suggest type hints for Python files

Remind about type annotations when writing Python.

```toml
[[rules]]
id = "suggest-type-hints"
description = "Suggest adding type hints to Python files"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name == "Write" and
matches_glob(tool_input.file_path, "*.py") and
not matches_glob(tool_input.file_path, "**/test_*.py")
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Remember to add type hints to functions. Run 'uv run basedpyright' to check types."
```

### Suggest documentation updates

Remind to update docs when changing public APIs.

```toml
[[rules]]
id = "suggest-docs-update"
description = "Suggest updating documentation after API changes"
events = ["post_tool_use"]
priority = "low"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/api/**") or
 matches_glob(tool_input.file_path, "**/__init__.py") or
 matches_glob(tool_input.file_path, "**/public/**"))
'''
result = "ok"

[[rules.actions]]
type = "suggest"
message = "Public API modified. Consider updating documentation if the interface changed."
```

## Combined patterns

### Deny with logging

Log before blocking for audit trail.

```toml
[[rules]]
id = "block-pipe-to-shell"
description = "Block curl/wget piping to shell (remote code execution)"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "(curl|wget).*\\|\\s*(ba)?sh"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "SECURITY: Remote code execution pattern blocked: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = """
Remote code execution pattern blocked.

Piping remote content to a shell is a security risk. Instead:
1. Download the script: curl -O <url>
2. Review the content: cat script.sh
3. Execute separately: bash script.sh
"""
```

### Conditional allow with context

Allow based on multiple conditions with context injection.

```toml
[[rules]]
id = "allow-docker-in-dev"
description = "Allow Docker commands only in development"
events = ["permission_request"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("docker") and
$env("NODE_ENV") != "production" and
$env("CI") != "true"
'''
result = "ok"

[[rules.actions]]
type = "allow"

[[rules]]
id = "warn-docker-command"
description = "Warn about Docker commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and tool_input.command.starts_with("docker")
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Docker command detected. Ensure containers are properly configured."
```

### Tiered access control

Different access levels for different file patterns.

```toml
# Block access to production configs
[[rules]]
id = "block-prod-config"
description = "Block access to production configuration"
events = ["pre_tool_use"]
priority = "critical"
terminal = true
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/prod/**") or
 matches_glob(tool_input.file_path, "**/production/**") or
 matches_glob(tool_input.file_path, "**/*.prod.*"))
'''
result = "block"

[[rules.actions]]
type = "deny"
message = "Access to production configuration is blocked: ${tool_input.file_path}"

# Warn on staging configs
[[rules]]
id = "warn-staging-config"
description = "Warn when accessing staging configuration"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/staging/**") or
 matches_glob(tool_input.file_path, "**/*.staging.*"))
'''
result = "warn"

[[rules.actions]]
type = "warn"
message = "Accessing staging configuration: ${tool_input.file_path}. Verify changes are intentional."

# Allow dev configs without prompt
[[rules]]
id = "allow-dev-config"
description = "Auto-approve development configuration access"
events = ["permission_request"]
priority = "high"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(matches_glob(tool_input.file_path, "**/dev/**") or
 matches_glob(tool_input.file_path, "**/development/**") or
 matches_glob(tool_input.file_path, "**/*.dev.*") or
 matches_glob(tool_input.file_path, "**/*.local.*"))
'''
result = "ok"

[[rules.actions]]
type = "allow"
```
