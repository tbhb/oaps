---
description: Brainstorm new hook rules for a project
---

## Brainstorm hook rules

Use this workflow when exploring what hook rules would benefit a project.

### Step 1: Analyze current pain points

Identify workflow friction:

- Review recent incidents or mistakes that hooks could prevent
- Consider repetitive manual checks that could be automated
- Identify patterns where guidance would help Claude
- Note operations that require audit logging

### Step 2: Review existing rules

Understand current coverage:

- Run `oaps hooks list` to see active rules
- Identify gaps in event coverage
- Check for overlapping or redundant rules
- Note rules that may need refinement

### Step 3: Consider event types

Map needs to hook points:

- Pre-tool events for prevention and modification
- Post-tool events for logging and verification
- Session events for initialization and cleanup
- Prompt events for input validation

### Step 4: Categorize rule ideas by purpose

Organize by intent:

- **Guardrails**: Block dangerous operations, protect sensitive files
- **Automation**: Inject context, modify inputs, trigger scripts
- **Observability**: Log events, audit operations, track patterns
- **Guidance**: Warn about risks, suggest alternatives

### Step 5: Sketch condition requirements

Draft matching criteria:

- Identify which context variables to check
- Note patterns that need glob or regex matching
- Consider environment or branch-specific conditions
- Plan for edge cases and exceptions

### Step 6: Evaluate action options

Determine appropriate responses:

- Choose between blocking, warning, or passthrough
- Consider message content for user feedback
- Plan logging levels for observability rules
- Identify rules that need script execution

### Step 7: Prioritize rule ideas

Rank by value and effort:

- Safety-critical rules first
- High-frequency pain points next
- Nice-to-have automation last
- Consider implementation complexity

### Step 8: Document ideas for implementation

Record rule concepts:

- Write brief description of each rule idea
- Note target events and rough condition logic
- Specify intended result and action types
- Tag ideas by category and priority
