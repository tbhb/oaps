# Context Injection Examples

Hook rules for injecting additional context into Claude's conversation. These examples demonstrate the inject action across different hook events for session setup, follow-up suggestions, prompt augmentation, and memory preservation.

## SessionStart injection examples

### Inject branch name and git status

Provide git context when a session starts.

```toml
[[rules]]
id = "session-git-context"
description = "Inject git branch and status at session start"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Git Context:
- Branch: ${$current_branch()}
- Working directory: ${cwd}
- Check 'git status' for uncommitted changes
"""
```

### Inject recent commits summary

Provide context about recent work at session start.

```toml
[[rules]]
id = "session-recent-commits"
description = "Inject information about recent commits"
events = ["session_start"]
priority = "medium"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "script"
stdin = "json"
command = "git log --oneline -5 2>/dev/null || echo 'No git history available'"
stdout = "append_stop_reason"

[[rules.actions]]
type = "inject"
content = """
Session started on branch ${$current_branch()}.
Review recent commits with 'git log --oneline -10' for context on current work.
"""
```

### Inject uncommitted changes summary

Alert about pending changes when resuming work.

```toml
[[rules]]
id = "session-uncommitted-changes"
description = "Inject summary of uncommitted changes"
events = ["session_start"]
priority = "high"
condition = 'source == "startup" or source == "resume"'
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "oaps.hooks.git_context:get_uncommitted_summary"
timeout_ms = 5000

[[rules.actions]]
type = "inject"
content = """
Session Context:
- Source: ${source}
- Branch: ${$current_branch()}
- Run 'git status' to see any uncommitted changes from previous work.
"""
```

### Inject project-specific commands

Provide project command reference at startup.

```toml
[[rules]]
id = "session-project-commands"
description = "Inject project-specific command reference"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Project: ${$basename(cwd)}
Development Commands:
- just install    # Install dependencies
- just test       # Run all tests
- just lint       # Run linters
- just format     # Format code
- just clean      # Clean build artifacts

Python: Always use 'uv run' for Python commands.
"""
```

## PostToolUse injection examples

### Inject follow-up suggestions after file creation

Suggest next steps after writing new files.

```toml
[[rules]]
id = "post-write-suggestions"
description = "Suggest follow-up actions after creating files"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Write" and
matches_glob(tool_input.file_path, "src/**/*.py")
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
File created: ${tool_input.file_path}

Suggested next steps:
1. Add corresponding test file in tests/
2. Run 'uv run basedpyright ${tool_input.file_path}' to check types
3. Run 'uv run ruff check ${tool_input.file_path}' to lint
4. Update __init__.py exports if this is a public module
"""
```

### Inject test results context

Add context about test outcomes for debugging.

```toml
[[rules]]
id = "post-test-context"
description = "Inject context after test execution"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
(tool_input.command =~~ "pytest" or tool_input.command =~~ "just test")
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Test execution completed.

If tests failed:
- Check the test output for assertion errors
- Look for fixtures that may not be set up correctly
- Review recent changes that might have caused regressions

If tests passed:
- Consider running 'just lint' before committing
- Check coverage report if available
"""
```

### Inject lint fix suggestions

Provide guidance after lint errors.

```toml
[[rules]]
id = "post-lint-suggestions"
description = "Inject suggestions after linting"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
(tool_input.command =~~ "ruff check" or tool_input.command =~~ "just lint")
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Lint check completed.

Common fixes:
- 'uv run ruff check --fix .' to auto-fix safe issues
- 'uv run ruff format .' to fix formatting
- For type errors, check function signatures and return types
- Never add type ignore comments without explicit approval
"""
```

### Inject git status after commits

Provide repository state after git operations.

```toml
[[rules]]
id = "post-commit-context"
description = "Inject git status after commit operations"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "git\\s+(commit|push|merge|rebase)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Git operation completed: ${tool_input.command}

Next steps to consider:
- 'git status' to verify repository state
- 'git log --oneline -3' to review recent commits
- 'git push' if changes should be shared (if not already pushed)
"""
```

## UserPromptSubmit injection examples

### Inject project coding guidelines

Add coding standards when code-related prompts are detected.

```toml
[[rules]]
id = "inject-python-guidelines"
description = "Inject Python coding guidelines for relevant prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "(?i)(python|pytest|type.?hint|typing|def\\s|class\\s)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Python Guidelines for this project:
- Target Python 3.10+ with modern features
- NEVER use 'from __future__ import annotations' (runtime type inspection)
- Use dataclasses with slots=True where appropriate
- Add comprehensive type hints (basedpyright strict mode)
- Follow Google-style docstrings for public APIs
- Use 'uv run' for all Python execution
"""
```

### Inject relevant documentation

Provide documentation context for specific topics.

```toml
[[rules]]
id = "inject-testing-docs"
description = "Inject testing documentation for test-related prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "(?i)(test|pytest|coverage|fixture|mock|hypothesis)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Testing Guidelines:
- Tests are in tests/ directory (unit/, integration/, properties/)
- Test naming: test_<scenario>_<expected>
- No docstrings on test functions (names are self-explanatory)
- Use Hypothesis for property-based tests where appropriate
- Target >95% coverage
- Run tests: 'uv run pytest' or 'just test'
"""
```

### Inject deployment procedures

Add deployment context for deploy-related prompts.

```toml
[[rules]]
id = "inject-deploy-context"
description = "Inject deployment procedures for deploy prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "(?i)(deploy|release|publish|ship|production)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
DEPLOYMENT CHECKLIST:
1. All tests must pass: just test
2. All linting must pass: just lint
3. Update version in pyproject.toml
4. Update CHANGELOG.md
5. Create git tag for release
6. Deployments require approval - see DEPLOY.md

WARNING: Never deploy directly from main without review.
"""
```

### Inject security guidelines

Add security context for security-related prompts.

```toml
[[rules]]
id = "inject-security-context"
description = "Inject security guidelines for security prompts"
events = ["user_prompt_submit"]
priority = "critical"
condition = '''
prompt =~~ "(?i)(security|auth|password|secret|credential|token|api.?key|encrypt)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
SECURITY GUIDELINES:
- Never hardcode secrets or credentials
- Use environment variables for sensitive data
- Never commit .env files or credentials
- Validate and sanitize all user inputs
- Use parameterized queries for databases
- Follow principle of least privilege
- Log security events (but never log secrets)
"""
```

### Inject architecture context

Provide system design context for architecture prompts.

```toml
[[rules]]
id = "inject-architecture-context"
description = "Inject architecture context for design prompts"
events = ["user_prompt_submit"]
priority = "high"
condition = '''
prompt =~~ "(?i)(architect|design|structure|pattern|refactor|organize)"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Architecture Principles:
- Follow SOLID, DRY, YAGNI, KISS (KISS takes precedence)
- Private modules use leading underscore (_module.py)
- Public API exports through __init__.py
- Prefer composition over inheritance
- Prefer frozen dataclasses with slots
- Document rationale for architectural decisions
"""
```

## PreCompact injection examples

### Preserve critical project decisions

Maintain important context before memory compaction.

```toml
[[rules]]
id = "preserve-project-decisions"
description = "Preserve critical project decisions before compaction"
events = ["pre_compact"]
priority = "critical"
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = """
CRITICAL PROJECT CONTEXT - DO NOT FORGET:
- Python 3.10+ required (no 'from __future__ import annotations')
- Use 'uv run' for all Python commands
- basedpyright for type checking (zero errors AND warnings)
- ruff for linting and formatting
- Tests must maintain >95% coverage
- Never add type ignores without explicit user approval
"""
```

### Preserve current task state

Maintain information about work in progress.

```toml
[[rules]]
id = "preserve-task-state"
description = "Preserve current task context before compaction"
events = ["pre_compact"]
priority = "high"
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = """
TASK CONTEXT TO PRESERVE:
- Current branch: ${$current_branch()}
- Working directory: ${cwd}
- Check TodoWrite for active tasks
- Review git status for uncommitted work
- Review recent conversation for task context
"""
```

### Preserve debugging context

Maintain debugging state and findings.

```toml
[[rules]]
id = "preserve-debug-context"
description = "Preserve debugging context before compaction"
events = ["pre_compact"]
priority = "high"
condition = 'custom_instructions =~~ "(?i)debug"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
DEBUGGING CONTEXT:
- Review recent tool outputs for error messages
- Check test results from recent runs
- Note any hypotheses about root cause
- Preserve stack traces and error messages
- Keep track of files already examined
"""
```

### Preserve user preferences

Maintain user-specific settings and preferences.

```toml
[[rules]]
id = "preserve-user-prefs"
description = "Preserve user preferences before compaction"
events = ["pre_compact"]
priority = "medium"
condition = "true"
result = "ok"

[[rules.actions]]
type = "inject"
content = """
USER PREFERENCES:
- Check for user-specific instructions in conversation
- Preserve any established naming conventions
- Maintain agreed-upon coding style decisions
- Keep track of approval for any rule exceptions
"""
```

## Dynamic context injection

### Script-based git context

Use shell scripts to gather dynamic git information.

```toml
[[rules]]
id = "dynamic-git-context"
description = "Inject dynamic git status information"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "script"
stdin = "json"
stdout = "log"
script = """
#!/bin/bash
echo "Git Status Summary:"
git branch --show-current 2>/dev/null && echo ""
git status --short 2>/dev/null | head -20
if [ $(git status --short 2>/dev/null | wc -l) -gt 20 ]; then
    echo "... and more files"
fi
"""
timeout_ms = 5000

[[rules.actions]]
type = "inject"
content = "Git context gathered. Check logs for detailed status."
```

### Python-based context injection

Use Python for complex context gathering.

```toml
[[rules]]
id = "python-project-context"
description = "Inject project context using Python analysis"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "oaps.hooks.context:gather_project_context"
timeout_ms = 10000
```

Python function example:

```python
def gather_project_context(context):
    """Gather and return project context for injection."""
    import os
    from pathlib import Path

    cwd = Path(context.hook_input.cwd)
    project_info = []

    # Check for common project files
    if (cwd / "pyproject.toml").exists():
        project_info.append("Python project (pyproject.toml found)")
    if (cwd / "package.json").exists():
        project_info.append("Node.js project (package.json found)")
    if (cwd / "Cargo.toml").exists():
        project_info.append("Rust project (Cargo.toml found)")

    # Check for test directories
    test_dirs = ["tests", "test", "spec"]
    for td in test_dirs:
        if (cwd / td).is_dir():
            project_info.append(f"Tests in {td}/ directory")
            break

    return {
        "inject": "Project Analysis:\n" + "\n".join(f"- {info}" for info in project_info)
    }
```

### Environment-aware context

Inject different context based on environment.

```toml
[[rules]]
id = "env-aware-context"
description = "Inject environment-specific context"
events = ["session_start"]
priority = "high"
condition = 'source == "startup"'
result = "ok"

# CI Environment
[[rules]]
id = "ci-context"
description = "Inject CI-specific context"
events = ["session_start"]
priority = "high"
condition = '$env("CI") == "true"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Running in CI Environment:
- Use non-interactive commands only
- All operations are logged
- Tests must pass for pipeline success
- Avoid prompts that require user input
"""

# Development Environment
[[rules]]
id = "dev-context"
description = "Inject development context"
events = ["session_start"]
priority = "high"
condition = '$env("CI") != "true" and source == "startup"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Development Environment:
- Interactive mode available
- Use 'just' commands for common tasks
- Pre-commit hooks active
- Local testing with 'just test'
"""
```

### Branch-specific context

Inject different context based on current git branch.

```toml
[[rules]]
id = "main-branch-context"
description = "Inject caution context for main branch"
events = ["session_start"]
priority = "critical"
condition = '$current_branch() == "main" or $current_branch() == "master"'
result = "ok"

[[rules.actions]]
type = "inject"
content = """
WARNING: You are on the ${$current_branch()} branch.
- Create a feature branch before making changes
- Do not commit directly to ${$current_branch()}
- Use: git checkout -b feat/your-feature-name
"""

[[rules]]
id = "feature-branch-context"
description = "Inject feature branch workflow context"
events = ["session_start"]
priority = "medium"
condition = '''
$current_branch() =~~ "^(feat|feature|fix|bugfix|chore)/"
'''
result = "ok"

[[rules.actions]]
type = "inject"
content = """
Feature Branch: ${$current_branch()}
Workflow:
1. Make changes and commit frequently
2. Run 'just test' before pushing
3. Run 'just lint' to check code quality
4. Push and create PR when ready
"""
```
