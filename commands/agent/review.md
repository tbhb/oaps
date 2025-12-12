---
description: Review existing agents for quality
argument-hint: [agent-name-or-path]
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

# Review agents

You are helping a developer audit their agents for quality, triggering reliability, and effectiveness.

Review scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context agent-development --plugin --references structure frontmatter` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If agent name provided: focus on that specific agent
   - If file path provided: review that agent file
   - If empty: review all project agents

3. **Launch review** - Use the Task tool to launch an agent-reviewer agent:

   ```
   Review agents for quality and correctness.

   Scope: [all agents / specific agent]

   Follow the review workflow:
   1. List agents in scope
   2. Check frontmatter correctness (YAML, name, description, model, color, tools)
   3. Verify triggering quality (examples complete, cover scenarios)
   4. Assess system prompt quality (structure, clarity, completeness)
   5. Evaluate tool restrictions (least privilege)
   6. Check organization and naming

   Report only issues with confidence >= 80.
   ```

4. **Present findings** - Summarize the review results:
   - Critical issues requiring immediate attention
   - Important issues to address
   - Minor improvements (if requested)
   - Agents that passed review

5. **Gather feedback** - Ask user what they want to do:
   - Fix issues now
   - Create tasks for later
   - Proceed without changes

6. **Address issues** - If user wants fixes, either:
   - Make simple fixes directly
   - For complex changes, suggest using `/oaps:agent:write` to recreate the agent
