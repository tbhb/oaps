# Input Modification Examples

Hook rules for modifying tool inputs before execution. These examples demonstrate the modify and transform actions for declarative and programmatic input transformation.

## Modify action examples

### Set: Override tool input to fixed value

Replace a field value entirely with a new value.

```toml
[[rules]]
id = "set-default-timeout"
description = "Set default timeout for Bash commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and tool_input.timeout == null
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "timeout"
operation = "set"
value = "120000"
```

### Set: Force dry-run mode for rm commands

Override rm commands to include --dry-run for safety.

```toml
[[rules]]
id = "set-rm-dry-run"
description = "Force dry-run mode for rm commands in non-CI"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("rm") and
not tool_input.command =~~ "--dry-run" and
$env("CI") != "true"
'''
result = "ok"

[[rules.actions]]
type = "warn"
message = "Running rm in dry-run mode for safety. Remove this hook to execute normally."

[[rules.actions]]
type = "modify"
field = "command"
operation = "set"
value = "${tool_input.command} --dry-run"
```

### Append: Add text to end of command

Append flags or arguments to existing commands.

```toml
[[rules]]
id = "append-verbose-flag"
description = "Append verbose flag to pytest for debugging"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("pytest") and
not tool_input.command =~~ "-v"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " -v"
```

### Append: Add color output to commands

Enable colored output for better readability.

```toml
[[rules]]
id = "append-color-output"
description = "Enable colored output for supported commands"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("ruff") or
 tool_input.command.starts_with("pytest") or
 tool_input.command.starts_with("git diff") or
 tool_input.command.starts_with("git log")) and
not tool_input.command =~~ "--color"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " --color=always"
```

### Append: Add coverage flags to tests

Automatically include coverage reporting.

```toml
[[rules]]
id = "append-coverage"
description = "Add coverage flags to pytest commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "pytest" and
not tool_input.command =~~ "--cov"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " --cov=src --cov-report=term-missing"
```

### Prepend: Add prefix to paths

Add directory prefix to relative paths.

```toml
[[rules]]
id = "prepend-src-path"
description = "Prepend src/ to relative Python imports"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Read" and
not tool_input.file_path.starts_with("/") and
not tool_input.file_path.starts_with("src/") and
matches_glob(tool_input.file_path, "*.py")
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "file_path"
operation = "prepend"
value = "src/"
```

### Prepend: Add uv run to Python commands

Ensure Python commands use uv run.

```toml
[[rules]]
id = "prepend-uv-run"
description = "Prepend uv run to bare Python commands"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
(tool_input.command.starts_with("python ") or
 tool_input.command.starts_with("python3 ")) and
not tool_input.command.starts_with("uv run")
'''
result = "ok"

[[rules.actions]]
type = "warn"
message = "Adding 'uv run' prefix. Always use 'uv run python' in this project."

[[rules.actions]]
type = "modify"
field = "command"
operation = "prepend"
value = "uv run "
```

### Replace: Pattern replacement in input

Replace patterns in command strings.

```toml
[[rules]]
id = "replace-force-with-lease"
description = "Replace --force with --force-with-lease for safer pushes"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "git\\s+push.*--force(?!-with-lease)"
'''
result = "ok"

[[rules.actions]]
type = "warn"
message = "Replacing --force with --force-with-lease for safety."

[[rules.actions]]
type = "modify"
field = "command"
operation = "replace"
pattern = "--force"
value = "--force-with-lease"
```

### Replace: Normalize package manager commands

Replace npm with pnpm for consistency.

```toml
[[rules]]
id = "replace-npm-with-pnpm"
description = "Replace npm commands with pnpm"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("npm ")
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "replace"
pattern = "^npm "
value = "pnpm "
```

### Replace: Fix common typos in paths

Correct common path typos.

```toml
[[rules]]
id = "replace-path-typos"
description = "Fix common path typos"
events = ["pre_tool_use"]
priority = "low"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit") and
(tool_input.file_path =~~ "/scr/" or tool_input.file_path =~~ "/tets/")
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "file_path"
operation = "replace"
pattern = "/scr/"
value = "/src/"

[[rules.actions]]
type = "modify"
field = "file_path"
operation = "replace"
pattern = "/tets/"
value = "/tests/"
```

### Replace: Environment-specific substitutions

Replace environment placeholders with actual values.

```toml
[[rules]]
id = "replace-env-placeholders"
description = "Replace $ENV_VAR placeholders with actual values"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "\\$\\{?HOME\\}?"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "replace"
pattern = "\\$\\{?HOME\\}?"
value = "${$env('HOME')}"
```

## Transform action examples

### Transform with Python: Complex command transformation

Use Python for transformations requiring logic.

```toml
[[rules]]
id = "transform-python-imports"
description = "Transform Python import paths based on project structure"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "python.*-m\\s+\\w+"
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.transforms:normalize_python_module"
timeout_ms = 5000
```

Python function:

```python
def normalize_python_module(context):
    """Normalize Python module paths for uv run."""
    command = context.hook_input.tool_input.get("command", "")

    # Ensure uv run prefix
    if not command.startswith("uv run"):
        command = "uv run " + command

    # Replace python -m with direct module execution
    import re
    command = re.sub(
        r"python\s+-m\s+(\w+)",
        r"python -m \1",
        command
    )

    return {"transform_input": {"command": command}}
```

### Transform with Python: Path normalization

Normalize file paths based on project conventions.

```toml
[[rules]]
id = "transform-normalize-paths"
description = "Normalize file paths to project conventions"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
(tool_name == "Read" or tool_name == "Write" or tool_name == "Edit")
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.transforms:normalize_file_path"
timeout_ms = 3000
```

Python function:

```python
def normalize_file_path(context):
    """Normalize file path to absolute path within project."""
    from pathlib import Path

    file_path = context.hook_input.tool_input.get("file_path", "")
    cwd = Path(context.hook_input.cwd)

    if not file_path:
        return None

    path = Path(file_path)

    # Convert relative paths to absolute
    if not path.is_absolute():
        path = cwd / path

    # Resolve .. and . components
    try:
        path = path.resolve()
    except Exception:
        return None

    return {"transform_input": {"file_path": str(path)}}
```

### Transform with Python: Command sanitization

Sanitize commands to remove dangerous patterns.

```toml
[[rules]]
id = "transform-sanitize-command"
description = "Sanitize bash commands for safety"
events = ["pre_tool_use"]
priority = "critical"
condition = '''
tool_name == "Bash"
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.security:sanitize_command"
timeout_ms = 3000
```

Python function:

```python
def sanitize_command(context):
    """Sanitize command by removing or escaping dangerous patterns."""
    command = context.hook_input.tool_input.get("command", "")

    # Remove command chaining that could bypass checks
    # This is a simple example - real implementation would be more thorough
    dangerous_patterns = [
        (r";\s*rm\s+-rf", "; echo 'Blocked rm -rf'"),
        (r"\|\s*sh\b", "| cat"),
        (r"\|\s*bash\b", "| cat"),
    ]

    import re
    for pattern, replacement in dangerous_patterns:
        command = re.sub(pattern, replacement, command)

    return {"transform_input": {"command": command}}
```

### Transform with shell: stdin/stdout transformation

Use shell scripts for command transformation.

```toml
[[rules]]
id = "transform-shell-docker"
description = "Transform Docker commands for local development"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("docker")
'''
result = "ok"

[[rules.actions]]
type = "transform"
stdin = "json"
script = """
#!/bin/bash
# Read JSON input from stdin
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# Add common development flags
if [[ "$command" == docker\ run* ]]; then
    # Add interactive and remove-on-exit flags if not present
    if [[ "$command" != *"-it"* ]] && [[ "$command" != *"--interactive"* ]]; then
        command=$(echo "$command" | sed 's/docker run/docker run -it/')
    fi
    if [[ "$command" != *"--rm"* ]]; then
        command=$(echo "$command" | sed 's/docker run/docker run --rm/')
    fi
fi

# Output JSON with transform_input
echo "{\"transform_input\": {\"command\": \"$command\"}}"
"""
timeout_ms = 5000
```

### Transform with shell: Environment injection

Inject environment variables into commands.

```toml
[[rules]]
id = "transform-inject-env"
description = "Inject environment variables into commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "\\$\\{?[A-Z_]+\\}?"
'''
result = "ok"

[[rules.actions]]
type = "transform"
stdin = "json"
script = """
#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command')

# Expand environment variables
expanded=$(eval echo "$command" 2>/dev/null || echo "$command")

echo "{\"transform_input\": {\"command\": \"$expanded\"}}"
"""
timeout_ms = 3000
```

### Transform with shell: Path expansion

Expand glob patterns and special paths.

```toml
[[rules]]
id = "transform-expand-paths"
description = "Expand ~ and glob patterns in file paths"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
(tool_name == "Read" or tool_name == "Write") and
(tool_input.file_path.starts_with("~") or tool_input.file_path =~~ "\\*")
'''
result = "ok"

[[rules.actions]]
type = "transform"
stdin = "json"
script = """
#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path')

# Expand tilde
if [[ "$file_path" == ~* ]]; then
    file_path="${file_path/#\~/$HOME}"
fi

# For globs, just expand tilde but keep the pattern
# (glob expansion would return multiple files)

echo "{\"transform_input\": {\"file_path\": \"$file_path\"}}"
"""
timeout_ms = 2000
```

## Combined modify and transform patterns

### Sequential modifications

Apply multiple modifications in sequence.

```toml
[[rules]]
id = "multi-modify-pytest"
description = "Apply multiple modifications to pytest commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("pytest")
'''
result = "ok"

# Prepend uv run if missing
[[rules.actions]]
type = "modify"
field = "command"
operation = "replace"
pattern = "^pytest"
value = "uv run pytest"

# Add verbose flag if missing
[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " -v"

# Add coverage if missing
[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " --cov=src"
```

### Conditional transformation

Transform based on complex conditions.

```toml
[[rules]]
id = "conditional-transform"
description = "Apply different transformations based on context"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command.starts_with("make")
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.transforms:conditional_make_transform"
timeout_ms = 5000
```

Python function:

```python
def conditional_make_transform(context):
    """Apply conditional transformations to make commands."""
    import os

    command = context.hook_input.tool_input.get("command", "")
    cwd = context.hook_input.cwd

    # Check if Makefile exists
    makefile_path = os.path.join(cwd, "Makefile")
    if not os.path.exists(makefile_path):
        # Check for justfile instead
        justfile_path = os.path.join(cwd, "justfile")
        if os.path.exists(justfile_path):
            # Replace make with just
            command = command.replace("make ", "just ", 1)
            return {"transform_input": {"command": command}}

    # Add parallel execution if not specified
    if "-j" not in command:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        command = command.replace("make ", f"make -j{cores} ", 1)

    return {"transform_input": {"command": command}}
```

### Transform with fallback

Use modify as fallback when transform fails.

```toml
# Primary: Python transform for complex logic
[[rules]]
id = "transform-complex-command"
description = "Complex command transformation"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "deploy"
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.deploy:transform_deploy_command"
timeout_ms = 5000

# Fallback: Simple modify if transform module not available
[[rules]]
id = "modify-deploy-fallback"
description = "Fallback modification for deploy commands"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and
tool_input.command =~~ "deploy" and
not tool_input.command =~~ "--dry-run"
'''
result = "ok"

[[rules.actions]]
type = "modify"
field = "command"
operation = "append"
value = " --dry-run"
```

### Validation before transformation

Validate inputs before applying transformations.

```toml
[[rules]]
id = "validate-and-transform"
description = "Validate and transform file operations"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Write" and
matches_glob(tool_input.file_path, "*.py")
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "project_hooks.validation:validate_and_format_python"
timeout_ms = 10000
```

Python function:

```python
def validate_and_format_python(context):
    """Validate Python content and optionally format it."""
    import ast

    file_path = context.hook_input.tool_input.get("file_path", "")
    content = context.hook_input.tool_input.get("content", "")

    if not content:
        return None

    # Validate Python syntax
    try:
        ast.parse(content)
    except SyntaxError as e:
        # Return warning but don't block
        return {"warn": f"Python syntax error in {file_path}: {e}"}

    # Check for forbidden imports
    if "from __future__ import annotations" in content:
        return {
            "deny": True,
            "deny_message": "This project cannot use 'from __future__ import annotations' due to runtime type inspection requirements."
        }

    # All validations passed
    return None
```
