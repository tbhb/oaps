# Logging and audit examples

This document provides complete TOML examples for the `log` action, which writes structured log entries for telemetry, debugging, and compliance auditing without affecting hook execution.

## Log levels overview

The `log` action supports four severity levels:

| Level     | Purpose                                    |
|-----------|--------------------------------------------|
| `debug`   | Detailed diagnostic information            |
| `info`    | General informational messages             |
| `warning` | Cautionary conditions worth noting         |
| `error`   | Error conditions that may need attention   |

## Debug level examples

### Detailed debugging output

Log verbose context for troubleshooting hook behavior:

```toml
[[rules]]
id = "debug-tool-context"
description = "Log full tool context for debugging"
events = ["pre_tool_use"]
priority = "low"
condition = "$env('OAPS_DEBUG') == 'true'"
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "[DEBUG] Tool: ${tool_name} | Session: ${session_id} | CWD: ${cwd}"
```

### Debug file operations

Track file access patterns during development:

```toml
[[rules]]
id = "debug-file-reads"
description = "Debug log all file read operations"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Read" and $env("OAPS_TRACE_FILES") == "true"'
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "[FILE-TRACE] Read requested: ${tool_input.file_path}"
```

### Debug condition evaluation

Log when specific conditions are checked:

```toml
[[rules]]
id = "debug-git-branch-check"
description = "Debug log branch detection"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "git" and $env("OAPS_DEBUG") == "true"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "[DEBUG] Git command on branch ${git_branch}: ${tool_input.command}"
```

## Info level examples

### Informational messages

Log routine operations for observability:

```toml
[[rules]]
id = "info-session-activity"
description = "Log session activity for metrics"
events = ["pre_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[SESSION] ${session_id} using ${tool_name}"
```

### Track file modifications

Log all file write operations:

```toml
[[rules]]
id = "info-file-writes"
description = "Log file write operations"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Write"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[WRITE] File written: ${tool_input.file_path}"
```

### Log successful completions

Record when important operations complete:

```toml
[[rules]]
id = "info-test-completion"
description = "Log test run completions"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "pytest|npm test|cargo test"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[TEST] Test command completed: ${tool_input.command}"
```

## Warning level examples

### Cautionary messages

Warn about potentially risky operations:

```toml
[[rules]]
id = "warn-sudo-usage"
description = "Warn when sudo is used"
events = ["pre_tool_use"]
priority = "medium"
condition = 'tool_name == "Bash" and tool_input.command =~~ "sudo"'
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "[SECURITY] sudo command detected: ${tool_input.command}"
```

### Warn about external network access

Log when commands may access external resources:

```toml
[[rules]]
id = "warn-network-access"
description = "Warn about potential network access"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "curl|wget|http|ssh|scp"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "[NETWORK] External access command: ${tool_input.command}"
```

### Warn about production environment

Alert when working in production-like paths:

```toml
[[rules]]
id = "warn-production-path"
description = "Warn when modifying production paths"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
tool_input.file_path =~~ "/prod/|/production/|/live/"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "[PROD] Modifying production path: ${tool_input.file_path}"
```

## Error level examples

### Error conditions

Log when problematic patterns are detected:

```toml
[[rules]]
id = "error-dangerous-rm"
description = "Log dangerous rm commands"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "rm\\s+-rf\\s+/"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "[DANGER] Dangerous rm command attempted: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = "Dangerous rm -rf command blocked for safety"
```

### Log blocked operations

Record when operations are denied:

```toml
[[rules]]
id = "error-blocked-operation"
description = "Log when operations are blocked"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and tool_input.command =~~ ":(){ :|:& };:|fork bomb"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "[BLOCKED] Fork bomb or malicious pattern detected: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = "Malicious command pattern blocked"
```

### Log access violations

Record attempts to access restricted resources:

```toml
[[rules]]
id = "error-restricted-access"
description = "Log attempts to access restricted files"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Read" and tool_input.file_path =~~ "/etc/shadow|/etc/passwd|.ssh/id_"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "[ACCESS-VIOLATION] Attempted read of restricted file: ${tool_input.file_path}"

[[rules.actions]]
type = "deny"
message = "Access to sensitive system files is not allowed"
```

## Template variable usage

### Common template variables

```toml
[[rules]]
id = "template-demo-tool"
description = "Demonstrate tool-related variables"
events = ["pre_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = """
Tool: ${tool_name}
Input: ${tool_input}
Session: ${session_id}
Working Dir: ${cwd}
Timestamp: ${timestamp}
"""
```

### Tool input field access

Access specific fields from tool_input:

```toml
[[rules]]
id = "template-bash-command"
description = "Log Bash command details"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Bash"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[BASH] Command: ${tool_input.command} | Timeout: ${tool_input.timeout}"
```

```toml
[[rules]]
id = "template-file-operation"
description = "Log file operation details"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Write" or tool_name == "Edit" or tool_name == "Read"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[FILE] ${tool_name} on ${tool_input.file_path}"
```

```toml
[[rules]]
id = "template-edit-details"
description = "Log edit operation details"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Edit"'
result = "ok"

[[rules.actions]]
type = "log"
level = "debug"
message = "[EDIT] File: ${tool_input.file_path} | Replacing: '${tool_input.old_string}'"
```

### Git context variables

```toml
[[rules]]
id = "template-git-context"
description = "Log git context information"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Bash" and tool_input.command =~~ "git"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[GIT] Branch: ${git_branch} | Dirty: ${git_is_dirty} | Head: ${git_head_commit}"
```

## Structured audit trails

### Comprehensive audit entry

Create detailed audit records for compliance:

```toml
[[rules]]
id = "audit-all-tool-use"
description = "Create audit trail for all tool usage"
events = ["pre_tool_use"]
priority = "low"
condition = "true"
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[AUDIT] ts=${timestamp} session=${session_id} tool=${tool_name} cwd=${cwd}"
```

### Audit file modifications

Track all file changes for audit purposes:

```toml
[[rules]]
id = "audit-file-changes"
description = "Audit log for file modifications"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Write" or tool_name == "Edit"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[AUDIT-FILE] action=${tool_name} path=${tool_input.file_path} session=${session_id} ts=${timestamp}"
```

### Audit code execution

Track command execution for security auditing:

```toml
[[rules]]
id = "audit-command-execution"
description = "Audit log for command execution"
events = ["pre_tool_use"]
priority = "low"
condition = 'tool_name == "Bash"'
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[AUDIT-CMD] session=${session_id} cwd=${cwd} cmd=${tool_input.command}"
```

## Combining log with other actions

### Log and warn pattern

Log for audit while also warning the user:

```toml
[[rules]]
id = "log-and-warn-main-branch"
description = "Log and warn about main branch operations"
events = ["pre_tool_use"]
priority = "high"
condition = '''
$current_branch() == "main" and
tool_name == "Bash" and
tool_input.command =~~ "git push|git commit"
'''
result = "warn"

[[rules.actions]]
type = "log"
level = "warning"
message = "[MAIN-BRANCH] Direct operation on main: ${tool_input.command}"

[[rules.actions]]
type = "warn"
message = "You are operating directly on the main branch. Consider using a feature branch."
```

### Log and deny pattern

Log the attempt before denying:

```toml
[[rules]]
id = "log-and-deny-force-push"
description = "Log and deny force push attempts"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "push.*--force(?!-with-lease)"
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "[BLOCKED] Force push attempted: ${tool_input.command}"

[[rules.actions]]
type = "deny"
message = "Force push is not allowed. Use --force-with-lease instead."
```

### Log before and after

Track operation timing with pre and post hooks:

```toml
[[rules]]
id = "log-operation-start"
description = "Log when expensive operations start"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "npm install|pip install|cargo build"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[START] ${timestamp} Beginning: ${tool_input.command}"
```

```toml
[[rules]]
id = "log-operation-end"
description = "Log when expensive operations complete"
events = ["post_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "npm install|pip install|cargo build"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[END] ${timestamp} Completed: ${tool_input.command}"
```

## Audit patterns for compliance

### SOC 2 style audit logging

Structured logging for compliance requirements:

```toml
[[rules]]
id = "soc2-data-access"
description = "SOC 2 compliant data access logging"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Read" and (
    tool_input.file_path =~~ "customer|user|account|payment|pii"
)
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[SOC2-ACCESS] type=data_read resource=${tool_input.file_path} session=${session_id} timestamp=${timestamp}"
```

### GDPR data handling audit

Track access to personal data:

```toml
[[rules]]
id = "gdpr-personal-data"
description = "GDPR compliant personal data access logging"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
tool_input.file_path =~~ "personal|gdpr|consent|user_data"
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[GDPR] action=${tool_name} resource=${tool_input.file_path} lawful_basis=legitimate_interest session=${session_id}"
```

### Change management audit

Track all code modifications:

```toml
[[rules]]
id = "change-management-audit"
description = "Change management audit trail"
events = ["post_tool_use"]
priority = "medium"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and
$matches_glob(tool_input.file_path, "*.py") or
$matches_glob(tool_input.file_path, "*.ts") or
$matches_glob(tool_input.file_path, "*.js")
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "info"
message = "[CHANGE] type=code_modification file=${tool_input.file_path} session=${session_id} branch=${git_branch} timestamp=${timestamp}"
```

### Security event logging

Log security-relevant events:

```toml
[[rules]]
id = "security-event-log"
description = "Log security-relevant events"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and (
    tool_input.command =~~ "chmod|chown|passwd|useradd|usermod" or
    tool_input.command =~~ "iptables|firewall|ufw" or
    tool_input.command =~~ "ssh-keygen|gpg"
)
'''
result = "ok"

[[rules.actions]]
type = "log"
level = "warning"
message = "[SECURITY-EVENT] category=system_administration command=${tool_input.command} session=${session_id} timestamp=${timestamp}"
```

### Failed operation logging

Log operations that were blocked:

```toml
[[rules]]
id = "audit-denied-operations"
description = "Audit log for denied operations"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash" and (
    tool_input.command =~~ "rm\\s+-rf\\s+/" or
    tool_input.command =~~ "--force(?!-with-lease)" or
    tool_input.command =~~ ":(){ :|:& };:"
)
'''
result = "block"

[[rules.actions]]
type = "log"
level = "error"
message = "[DENIED] operation=blocked reason=dangerous_command command=${tool_input.command} session=${session_id} timestamp=${timestamp}"

[[rules.actions]]
type = "deny"
message = "Operation blocked by security policy"
```
