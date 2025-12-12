---
description: Test skills for correct behavior
argument-hint: [skill-name]
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

# Test skill

You are helping a developer test a Claude Code skill to ensure it works correctly.

Target: $ARGUMENTS

## Phase 1: Identify Target

**Goal**: Determine what to test

1. If no target specified, ask user what skill to test
2. Locate the skill and confirm it exists
3. List what will be tested

---

## Phase 2: Structure Validation

**Goal**: Verify skill structure is valid

1. Run `oaps skill validate <skill-name>` to check structure
2. Report any validation errors
3. If errors exist, stop and report - structure must be valid first

---

## Phase 3: Loading Tests

**Goal**: Test skill loading mechanisms

1. Test orientation: `oaps skill orient <skill-name>`
   - Verify references are listed correctly
   - Verify workflows are listed correctly
   - Check for any loading errors

2. Test default workflow context: `oaps skill context <skill-name>`
   - Verify default workflow loads
   - Verify referenced references are included
   - Check output format is correct

3. Test loading references explicitly:
   - `oaps skill context <skill-name> --references <names...>`
   - Verify references load without errors
   - Check output format is correct

---

## Phase 4: Reference Tests

**Goal**: Test reference content

1. For each reference, verify:
   - Frontmatter is valid YAML
   - Required fields are present (name, title, description)
   - Related references exist if listed
   - Content is well-formed markdown

---

## Phase 5: Template Tests (if applicable)

**Goal**: Test template rendering

1. If skill has templates:
   - Test each template renders without errors
   - `oaps skill render <skill-name> --template <name> --var key=value`
   - Verify output format is correct

---

## Phase 6: Summary

**Goal**: Test results summary

1. Report all tests run with pass/fail status
2. List any errors or warnings encountered
3. Provide fix suggestions for failures
4. Confirm overall skill health
