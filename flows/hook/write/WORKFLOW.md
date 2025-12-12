---
description: Write new hook rules from requirements
default: true
---

## Write hook rules

Use this workflow when creating new hook rules from requirements.

### Step 1: Create rule skeleton

Initialize the rule structure:

- Generate unique rule ID (kebab-case, descriptive)
- Add description explaining the rule's purpose
- Set initial enabled state (true for immediate use)
- Choose target configuration file location

### Step 2: Define events array

Specify trigger points:

- Select appropriate event types from available options
- Use specific events rather than `all` when possible
- Consider whether multiple events need the same logic
- Document why each event was chosen

### Step 3: Write condition expression

Define matching criteria:

- Start with the primary check (tool_name, path, etc.)
- Add qualifying conditions with `and` operators
- Use `or` for alternative matches
- Apply expression functions for complex checks:
  - `$matches_glob()` for path patterns
  - `$is_path_under()` for directory containment
  - `$env()` for environment checks
  - Git functions for repository context

### Step 4: Configure actions

Define rule behavior:

- Select action type matching the result:
  - `deny` with `message` for block results
  - `warn` or `suggest` with `message` for warn results
  - `log` with `level` and `message` for observability
  - `inject` with `content` for context augmentation
- Use template substitution for dynamic values: `${variable}`
- Chain multiple actions when needed

### Step 5: Set priority and flags

Position the rule:

- Assign priority level:
  - `critical` for safety-critical blocking rules
  - `high` for important enforcement
  - `medium` for standard automation (default)
  - `low` for optional suggestions
- Set `terminal = true` for definitive decisions
- Keep `enabled = true` unless staging

### Step 6: Choose result type

Define outcome:

- `block` for rules that prevent operations
- `warn` for advisory rules that allow continuation
- `ok` for rules that explicitly permit or augment

### Step 7: Validate syntax

Check rule correctness:

- Run `oaps hooks validate` to verify TOML syntax
- Check expression parsing succeeds
- Verify action configuration is complete
- Review any validation warnings

### Step 8: Add to configuration

Integrate the rule:

- Append to `.oaps/hooks.toml` or appropriate file
- Maintain logical grouping with related rules
- Add comments for complex conditions
- Commit with descriptive message
