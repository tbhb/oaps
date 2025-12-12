---
name: validation
title: Agent validation rules
description: Validation requirements and rules for agent files
related:
  - anatomy
principles:
  - Validation ensures agents are well-formed and functional
  - All required fields must be present and correctly formatted
  - Descriptions must include triggering examples
best_practices:
  - Run validation before committing agents
  - Fix all validation errors before testing
  - Use validation output to guide improvements
checklist:
  - Identifier follows naming conventions
  - All required frontmatter fields present
  - Description includes example blocks
  - System prompt is within length limits
commands:
  oaps agent validate <name>: Validate agent file structure
---

# Agent validation rules

Validation ensures agents are well-formed, complete, and ready for use. Run validation before testing or committing agents.

## Running validation

```bash
oaps agent validate <agent-name>
```

The validator checks all rules below and reports errors with specific locations and fixes.

## Identifier validation

**Rules:**

| Rule | Requirement |
|------|-------------|
| Length | 3-50 characters |
| Characters | Lowercase letters, numbers, hyphens only |
| Start/End | Must start and end with alphanumeric |
| No special chars | No underscores, spaces, or special characters |

**Valid examples:**

```text
code-reviewer
test-gen
api-analyzer-v2
my-agent-123
```

**Invalid examples:**

```text
ag              # Too short (< 3 chars)
-start          # Starts with hyphen
end-            # Ends with hyphen
my_agent        # Underscore not allowed
My-Agent        # Uppercase not allowed
agent name      # Space not allowed
```

## Description validation

**Rules:**

| Rule | Requirement |
|------|-------------|
| Length | 10-5,000 characters |
| Triggering | Must include conditions for when to use |
| Examples | Must include `<example>` blocks |
| Commentary | Examples should include `<commentary>` |

**Recommended structure:**

```text
Use this agent when [conditions]. Examples:

<example>
Context: [Scenario]
user: "[Request]"
assistant: "[Response]"
<commentary>
[Explanation]
</commentary>
</example>

[More examples...]
```

**Validation warnings:**

- Missing triggering conditions ("Use this agent when...")
- No `<example>` blocks found
- Fewer than 2 examples
- Missing `<commentary>` in examples

## System prompt validation

**Rules:**

| Rule | Requirement |
|------|-------------|
| Minimum length | 20 characters |
| Maximum length | 10,000 characters |
| Recommended | 500-3,000 characters |

**Content recommendations (warnings, not errors):**

- Should include "You are" or "You will" (second person)
- Should include responsibilities or process steps
- Should include output format specification
- Should include edge case handling

## Required fields validation

All of these frontmatter fields must be present:

| Field | Type | Required |
|-------|------|----------|
| name | string | Yes |
| description | string | Yes |
| model | string | Yes |
| color | string | Yes |
| tools | array | No |

**Model values:** `inherit`, `sonnet`, `opus`, `haiku`

**Color values:** `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`

**Tools format:** Array of strings (e.g., `["Read", "Write"]`)

## Common validation errors

### Error: Invalid identifier format

```text
Error: Identifier 'my_agent' contains invalid characters
Fix: Use only lowercase letters, numbers, and hyphens
```

### Error: Missing required field

```text
Error: Missing required field 'model'
Fix: Add 'model: inherit' to frontmatter
```

### Error: Invalid model value

```text
Error: Invalid model 'gpt4' - must be inherit, sonnet, opus, or haiku
Fix: Change to one of: inherit, sonnet, opus, haiku
```

### Error: Description too short

```text
Error: Description is 5 characters, minimum is 10
Fix: Add triggering conditions and examples
```

### Error: System prompt too short

```text
Error: System prompt is 10 characters, minimum is 20
Fix: Expand system prompt with responsibilities and process
```

### Warning: No examples in description

```text
Warning: No <example> blocks found in description
Recommendation: Add 2-4 examples showing when agent triggers
```

## Validation output

Successful validation:

```text
✓ Identifier 'code-reviewer' is valid
✓ Description includes triggering conditions
✓ Found 3 example blocks
✓ All required fields present
✓ System prompt length: 1,247 characters

Agent 'code-reviewer' passed validation
```

Failed validation:

```text
✗ Identifier 'Code_Reviewer' is invalid
  - Contains uppercase characters
  - Contains underscore
✗ Missing required field: model
✗ No <example> blocks in description

Agent 'Code_Reviewer' failed validation with 3 errors
```
