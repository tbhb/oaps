---
description: Review existing hook rules for quality and correctness
---

## Review hook rules

Use this workflow when auditing existing hook rules for quality, correctness, and maintainability.

### Step 1: Load current rules

Gather rules for review:

- Run `oaps hooks list` to see all active rules
- Note rule sources (project, plugin, builtin)
- Identify rules by category (guardrails, automation, etc.)
- Check for disabled rules that may need attention

### Step 2: Check condition correctness

Verify matching logic:

- Review expression syntax for errors
- Verify conditions match intended scenarios
- Check for overly broad conditions (false positives)
- Check for overly narrow conditions (missed matches)
- Test conditions against sample contexts mentally

### Step 3: Verify action appropriateness

Assess configured actions:

- Confirm action types match result values
- Check message clarity and helpfulness
- Verify log levels are appropriate
- Review inject content for accuracy
- Check for missing actions (block without deny)

### Step 4: Assess priority levels

Review rule ordering:

- Verify critical rules are safety-related
- Check for priority conflicts between related rules
- Ensure terminal flags are set appropriately
- Review evaluation order for correctness

### Step 5: Identify security concerns

Check for vulnerabilities:

- Look for path traversal risks in conditions
- Check for injection risks in template substitution
- Verify sensitive data is not logged
- Review shell/python actions for safety
- Check that allow rules don't create bypasses

### Step 6: Test edge cases

Validate boundary behavior:

- Consider empty or missing context values
- Test with unusual but valid inputs
- Check behavior when environment differs
- Verify git-dependent rules handle non-git scenarios

### Step 7: Evaluate maintainability

Assess long-term quality:

- Check for descriptive rule IDs
- Verify descriptions explain purpose
- Look for duplicated logic across rules
- Identify overly complex conditions to simplify
- Check for deprecated patterns or functions

### Step 8: Document findings

Record review results:

- Categorize issues by severity (critical, major, minor)
- Provide specific remediation recommendations
- Note rules that function correctly
- Suggest new rules for identified gaps
- Create action items for follow-up
