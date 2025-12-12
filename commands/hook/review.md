---
description: Review existing hook rules for quality
argument-hint: [rule-id-or-file]
allowed-tools:
  - AskUserQuestion
  - Bash(oaps:*)
  - Glob
  - Grep
  - Read
  - Skill
  - Task
  - TodoWrite
---

# Review hook rules

You are helping a developer audit their hook rules for quality, correctness, and security.

Review scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context hook-rule-writing --references patterns troubleshooting` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If rule ID provided: focus on that specific rule
   - If file path provided: review rules in that file
   - If empty: review all project hook rules

3. **Launch review** - Use the Task tool to launch a hook-reviewer agent:

   ```
   Review hook rules for quality and correctness.

   Scope: [all rules / specific rule ID / specific file]

   Follow the review workflow:
   1. Load current rules with `oaps hooks list`
   2. Check condition correctness
   3. Verify action appropriateness
   4. Assess priority levels
   5. Identify security concerns
   6. Test edge cases mentally
   7. Evaluate maintainability

   Report only issues with confidence >= 80.
   ```

4. **Present findings** - Summarize the review results:
   - Critical issues requiring immediate attention
   - Important issues to address
   - Minor improvements (if requested)
   - Rules that passed review

5. **Gather feedback** - Ask user what they want to do:
   - Fix issues now
   - Create tasks for later
   - Proceed without changes

6. **Address issues** - If user wants fixes, either:
   - Make simple fixes directly
   - For complex changes, suggest using `/hook:write` to recreate the rule
