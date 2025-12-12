---
description: Add a reference to a skill
argument-hint: [skill-name] [reference-description]
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

# Add skill reference

You are helping a developer add a new reference to an existing Claude Code skill.

Arguments: $ARGUMENTS

Parse arguments as: first argument is skill name, remaining arguments describe the reference.

## Phase 1: Identify Target

**Goal**: Understand what reference to add

1. Parse the arguments to extract skill name and reference description
2. If skill name is missing, ask which skill to add the reference to
3. If reference description is missing, ask what the reference should contain
4. Locate the skill and confirm it exists
5. List existing references in the skill

---

## Phase 2: Load Context

**Goal**: Prepare for reference creation

1. Load skill context: `oaps skill context skill-development --references skill-references`

2. Read the skill's current structure:
   - skill.md
   - All existing files in references/

---

## Phase 3: Design & Implementation

**Goal**: Design and create the reference

1. Launch skill-developer agent to design AND implement the reference:

   ```
   Design and implement a new reference for the skill based on these requirements:

   Skill: [skill name]
   Reference need: [description from arguments]
   Existing references: [list from Phase 1]

   Follow this workflow:
   1. Choose an appropriate name (lowercase, hyphenated)
   2. Plan the frontmatter (name, title, description, related)
   3. Outline the content structure
   4. Identify which workflows should reference this
   5. Create the reference file at <skill-path>/references/<name>.md
   6. Update any workflows that should load this reference
   ```

2. Review the agent's implementation
3. Present design to user for approval

---

## Phase 4: Validation

**Goal**: Verify the reference works

1. Run `oaps skill validate <skill-name>` to check structure
2. Test loading the reference: `oaps skill context <skill-name> --references <reference-name>`
3. Report any issues

---

## Phase 5: Summary

**Goal**: Document what was created

1. Report the reference was created successfully
2. Show the file path
3. List workflows that now reference it
4. Suggest next steps (testing workflows that use this reference)
