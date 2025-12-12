---
description: Test slash commands for correct behavior
argument-hint: [command-name]
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

# Test slash commands

You are helping a developer validate slash command behavior through systematic testing.

Test scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context command-development --references dynamic-features frontmatter` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If command name provided: test that specific command
   - If empty: list commands and offer to test specific ones

3. **Read command definition** - Read the command file to understand:
   - Frontmatter configuration
   - Expected arguments
   - Dynamic features used
   - Tool restrictions

4. **Test frontmatter** - Verify configuration:
   - YAML syntax is valid
   - Description is appropriate
   - allowed-tools format is correct
   - Model selection is valid
   - argument-hint matches usage

5. **Test basic invocation** - Verify the command can be invoked:
   - With no arguments (if optional)
   - With expected arguments
   - Note any errors or unexpected behavior

6. **Test argument handling** - For commands with arguments:
   - Test $ARGUMENTS substitution
   - Test positional arguments ($1, $2, etc.)
   - Test edge cases (empty, spaces, special characters)

7. **Test file references** - For commands using @file:
   - Test with existing files
   - Test with non-existent files
   - Test with argument-based paths (@$1)

8. **Test bash execution** - For commands using !`command`:
   - Verify Bash is in allowed-tools
   - Test command execution
   - Verify output is captured correctly

9. **Test tool restrictions** - Verify allowed-tools:
   - Command can use permitted tools
   - Appropriate restrictions are enforced
   - No over-permissive access

10. **Test model selection** - If model is specified:
    - Verify appropriate model is used
    - Consider if selection matches complexity

11. **Present results** - Summarize test outcomes:
    - Passing tests
    - Failing tests with details
    - Edge cases that need attention
    - Recommendations for improvements

12. **Document findings** - If issues found, offer to:
    - Launch command-developer agent to fix issues
    - Create todo items for tracking
    - Suggest using `/oaps:command:write` for rewrites
