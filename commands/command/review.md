---
description: Review existing slash commands for quality
argument-hint: [command-name-or-path]
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

# Review slash commands

You are helping a developer audit their slash commands for quality, usability, and correctness.

Review scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context command-development --references structure frontmatter` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If command name provided: focus on that specific command
   - If file path provided: review that command file
   - If namespace provided: review all commands in that namespace
   - If empty: review all project commands

3. **Launch review** - Use the Task tool to launch a command-reviewer agent:

   ```
   Review slash commands for quality and correctness.

   Scope: [all commands / specific command / specific namespace]

   Follow the review workflow:
   1. List commands in scope
   2. Check frontmatter correctness (YAML, description, tools, model)
   3. Verify prompt quality (instructions for Claude, clarity)
   4. Validate dynamic features ($ARGUMENTS, @file, !`bash`)
   5. Assess tool restrictions (least privilege)
   6. Evaluate organization and naming
   7. Check usability (argument-hint, discoverability)

   Report only issues with confidence >= 80.
   ```

4. **Present findings** - Summarize the review results:
   - Critical issues requiring immediate attention
   - Important issues to address
   - Minor improvements (if requested)
   - Commands that passed review

5. **Gather feedback** - Ask user what they want to do:
   - Fix issues now
   - Create tasks for later
   - Proceed without changes

6. **Address issues** - If user wants fixes, either:
   - Make simple fixes directly
   - For complex changes, suggest using `/oaps:command:write` to recreate the command
