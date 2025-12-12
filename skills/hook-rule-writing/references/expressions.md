---
name: expressions
title: Expression syntax
description: Expression syntax for rule conditions including operators, safe navigation, data types, and comprehensions. Load when writing condition expressions.
commands: {}
principles:
  - Expressions must evaluate to boolean values
  - Use safe navigation to avoid null errors
  - Prefer explicit comparisons over truthiness
best_practices:
  - "**Use safe navigation for optional fields**: Access with &. and &[] to handle missing values"
  - "**Use regex search for partial matches**: Use =~~ for contains, =~ for full match"
  - "**Use in for membership tests**: Check if value is in array or key exists in mapping"
  - "**Leverage string attributes**: Use .starts_with, .ends_with, .as_lower for string checks"
  - "**Combine with logical operators**: Use and, or, not for complex conditions"
checklist:
  - Expression evaluates to boolean
  - Optional fields accessed with safe navigation
  - Regex patterns properly escaped
  - String comparisons account for case sensitivity
related:
  - functions
  - events
---

## Quick start

### Common patterns

Match tool by name:

```
tool_name == "Bash"
tool_name in ["Write", "Edit", "MultiEdit"]
```

Regex pattern matching:

```
tool_input.command =~ "^rm\\s+-rf"        # Match entire string
tool_input.command =~~ "dangerous"        # Search anywhere
```

Safe navigation for optional fields:

```
tool_input&.file_path&.ends_with(".py")   # Returns null if any step fails
tool_input&["optional_key"] == "value"    # Safe item access
```

Collection operations:

```
$all([f.ends_with(".py") for f in files])  # All match
$any([f.starts_with("test_") for f in files])  # Any match
files.length > 0                           # Non-empty check
```

Combining conditions:

```
tool_name == "Bash" and tool_input.command.starts_with("rm")
tool_name in ["Write", "Edit"] or permission_mode == "plan"
```

## Data types

| Type | Description | Example |
|------|-------------|---------|
| STRING | Text values | `"hello"`, `'world'` |
| FLOAT | Numbers (integers and decimals) | `42`, `3.14` |
| BOOLEAN | Logical values | `true`, `false` |
| NULL | Absence of value | `null` |
| ARRAY | Ordered collection | `[1, 2, 3]` |
| MAPPING | Key-value pairs | `tool_input` |
| SET | Unordered unique collection | `[1, 2, 2, 3].to_set` |
| DATETIME | Date and time | `d"2025-12-03"` |
| TIMEDELTA | Duration | `t"P1D"` |

## Operators

### Comparison operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal | `tool_name == "Bash"` |
| `!=` | Not equal | `tool_name != "Bash"` |
| `>` | Greater than | `count > 10` |
| `>=` | Greater or equal | `count >= 10` |
| `<` | Less than | `count < 10` |
| `<=` | Less or equal | `count <= 10` |

### Regex operators

| Operator | Description | Behavior |
|----------|-------------|----------|
| `=~` | Regex match | True if pattern matches **entire** string |
| `=~~` | Regex search | True if pattern found **anywhere** |
| `!~` | Regex match negation | True if pattern does NOT match |
| `!~~` | Regex search negation | True if pattern NOT found |

**Examples:**

```
tool_input.command =~ "^git\\s+"       # Starts with 'git '
tool_input.command =~~ "rm\\s+-rf"     # Contains 'rm -rf' anywhere
tool_input.command !~ "^safe_"         # Does NOT start with 'safe_'
```

**NULL behavior:**

- `=~` and `=~~`: Return `false` when left operand is NULL
- `!~` and `!~~`: Return `true` when left operand is NULL

### Logical operators

| Operator | Description | Example |
|----------|-------------|---------|
| `and` | Logical AND | `a and b` |
| `or` | Logical OR | `a or b` |
| `not` | Logical NOT | `not a` |

Logical operators use **short-circuit evaluation**:

- `and`: If left is falsy, right is not evaluated
- `or`: If left is truthy, right is not evaluated

```
tool_name == "Bash" and $expensive_check()  # $expensive_check() skipped if tool_name != "Bash"
```

### Membership operator

The `in` operator tests membership:

| Container | Behavior |
|-----------|----------|
| ARRAY | True if value is element |
| SET | True if value is member |
| STRING | True if substring found |
| MAPPING | True if key exists |

**Examples:**

```
tool_name in ["Bash", "Write", "Edit"]
"security" in prompt.as_lower
"file_path" in tool_input
```

### Ternary operator

```
condition ? true_value : false_value

is_admin ? "allowed" : "denied"
```

## Safe navigation

### Safe attribute access (`&.`)

Return NULL instead of error when:

- Left operand is NULL
- Attribute does not exist

```
tool_input&.file_path           # NULL if file_path doesn't exist
tool_input&.options&.verbose    # Chained safe access
```

### Safe item access (`&[]`)

Return NULL instead of error when:

- Left operand is NULL
- Index out of bounds (ARRAY)
- Key does not exist (MAPPING)

```
files&[0]                       # NULL if empty or NULL
tool_input&["optional_key"]     # NULL if key missing
```

## String attributes

| Attribute | Return | Description |
|-----------|--------|-------------|
| `.length` | FLOAT | Number of characters |
| `.is_empty` | BOOLEAN | True if length is 0 |
| `.as_lower` | STRING | Lowercase copy |
| `.as_upper` | STRING | Uppercase copy |
| `.starts_with(prefix)` | BOOLEAN | Starts with prefix |
| `.ends_with(suffix)` | BOOLEAN | Ends with suffix |

**Examples:**

```
tool_input.command.length > 100
prompt.is_empty
prompt.as_lower =~~ "delete"
tool_input.file_path.starts_with("/etc")
tool_input.file_path.ends_with(".py")
```

## Array attributes

| Attribute | Return | Description |
|-----------|--------|-------------|
| `.length` | FLOAT | Number of elements |
| `.is_empty` | BOOLEAN | True if empty |
| `.to_set` | SET | Convert to set |

**Examples:**

```
files.length > 5
files.is_empty
files.to_set
```

## Mapping attributes

| Attribute | Return | Description |
|-----------|--------|-------------|
| `.length` | FLOAT | Number of pairs |
| `.is_empty` | BOOLEAN | True if empty |
| `.keys` | ARRAY | Array of keys |
| `.values` | ARRAY | Array of values |

**Examples:**

```
tool_input.length > 0
tool_input.is_empty
"command" in tool_input.keys
```

## Array comprehensions

Syntax:

```
[ expression for variable in iterable ]
[ expression for variable in iterable if condition ]
```

**Examples:**

```
[ f.as_lower for f in files ]
[ f for f in files if f.ends_with(".py") ]
$all([ $is_path_under(f, cwd) for f in files ])
$any([ f.starts_with("test_") for f in files ])
```

## Context variables

Access context variables without prefix:

| Variable | Type | Available in | Description |
|----------|------|--------------|-------------|
| `hook_type` | STRING | All | Current hook type |
| `session_id` | STRING | All | Session identifier |
| `cwd` | STRING | All | Current working directory |
| `permission_mode` | STRING | All | Permission mode |
| `tool_name` | STRING | Tool hooks | Tool name |
| `tool_input` | MAPPING | Tool hooks | Tool input parameters |
| `tool_output` | STRING | PostToolUse | Tool response |
| `prompt` | STRING | UserPromptSubmit | User prompt |
| `timestamp` | DATETIME | All | Evaluation timestamp |

## Truthiness rules

| Type | Falsy | Truthy |
|------|-------|--------|
| NULL | Always | N/A |
| BOOLEAN | `false` | `true` |
| FLOAT | `0`, `nan` | Other values |
| STRING | `""` | Non-empty |
| ARRAY | `[]` | Non-empty |
| MAPPING | `{}` | Non-empty |

## NULL handling

| Operation | NULL behavior |
|-----------|---------------|
| `==` comparison | `null == null` is `true` |
| Logical operations | NULL is falsy |
| Arithmetic | Raises error |
| String concatenation | Raises error |
| Safe navigation | Returns NULL |
| Regex match | Returns `false` |
| Regex negation | Returns `true` |

## Operator precedence

| Precedence | Operators | Associativity |
|------------|-----------|---------------|
| 1 (highest) | `()` | N/A |
| 2 | `.`, `&.`, `[]`, `&[]` | Left-to-right |
| 3 | `**` | Right-to-left |
| 4 | `+`, `-` (unary) | Right-to-left |
| 5 | `*`, `/`, `//`, `%` | Left-to-right |
| 6 | `+`, `-` (binary) | Left-to-right |
| 7 | `<<`, `>>` | Left-to-right |
| 8 | `&` | Left-to-right |
| 9 | `^` | Left-to-right |
| 10 | `\|` | Left-to-right |
| 11 | `==`, `!=`, `>`, `>=`, `<`, `<=`, `=~`, `=~~`, `!~`, `!~~`, `in` | Left-to-right |
| 12 | `not` | Right-to-left |
| 13 | `and` | Left-to-right |
| 14 | `or` | Left-to-right |
| 15 (lowest) | `? :` (ternary) | Right-to-left |

## Case sensitivity

Expressions are case-sensitive for:

- Context variable names (`tool_name` vs `Tool_Name`)
- String comparisons (`"Bash"` vs `"bash"`)
- Attribute names (`.as_lower` vs `.AS_LOWER`)

Keywords (`and`, `or`, `not`, `in`, `true`, `false`, `null`) MUST be lowercase.

## Comments

Use `#` for comments. All text from `#` to end of line is ignored:

```
tool_name == "Bash"  # Only match Bash tool
```

## Reserved keywords

Do not use these as variable names:

`null`, `true`, `false`, `inf`, `nan`, `for`, `if`, `and`, `not`, `or`, `in`, `elif`, `else`, `while`

## Practical examples

### Block rm -rf commands

```toml
condition = '''
tool_name == "Bash" and tool_input.command =~~ "rm\\s+-rf"
'''
```

### Match Python files only

```toml
condition = '''
tool_name in ["Write", "Edit"] and tool_input&.file_path&.ends_with(".py")
'''
```

### Check environment

```toml
condition = '''
$env("CI") != null and tool_name == "Bash"
'''
```

### Match prompts mentioning deploy

```toml
condition = '''
prompt.as_lower =~~ "deploy|release|publish"
'''
```

### Check file under project root

```toml
condition = '''
tool_name == "Write" and $is_path_under(tool_input.file_path, cwd)
'''
```

### Complex condition with multiple checks

```toml
condition = '''
tool_name == "Bash"
and not tool_input.command.starts_with("echo")
and (
    tool_input.command =~~ "rm\\s+-rf"
    or tool_input.command =~~ "sudo"
    or tool_input.command =~~ "chmod\\s+777"
)
'''
```
