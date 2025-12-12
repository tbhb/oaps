---
description: Add a workflow to a skill
argument-hint: [skill-name] [workflow-description]
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

# Add skill workflow

You are helping a developer add a new workflow to an existing Claude Code skill.

Arguments: $ARGUMENTS

Parse arguments as: first argument is skill name, remaining arguments describe the workflow.

## Phase 1: Identify Target

**Goal**: Understand what workflow to add

1. Parse the arguments to extract skill name and workflow description
2. If skill name is missing, ask which skill to add the workflow to
3. If workflow description is missing, ask what task the workflow should guide
4. Locate the skill and confirm it exists
5. List existing workflows in the skill

---

## Phase 2: Load Context

**Goal**: Prepare for workflow creation

1. Load skill context: `oaps skill context skill-development --references skill-workflows`

2. Read the skill's current structure:
   - skill.md
   - All existing files in workflows/
   - All existing files in references/

---

## Phase 3: Design & Implementation

**Goal**: Design and create the workflow

1. Launch skill-developer agent to design AND implement the workflow:

   ```
   Design and implement a new workflow for the skill based on these requirements:

   Skill: [skill name]
   Workflow need: [description from arguments]
   Existing workflows: [list from Phase 1]
   Available references: [list from Phase 2]

   Follow this workflow:
   1. Choose an appropriate name (verb-first, lowercase, hyphenated)
   2. Plan the frontmatter (name, description, default, references)
   3. Identify which references this workflow needs
   4. Outline the step structure
   5. Define clear completion criteria for each step
   6. Create the workflow file at <skill-path>/workflows/<name>.md
   7. Ensure steps reference loaded references appropriately
   ```

2. Review the agent's implementation
3. Present design to user for approval

---

## Phase 4: Validation

**Goal**: Verify the workflow works

1. Run `oaps skill validate <skill-name>` to check structure
2. Test loading references: `oaps skill context <skill-name> --references <reference-names...>`
3. Verify referenced references are loaded
4. Report any issues

---

## Phase 5: Summary

**Goal**: Document what was created

1. Report the workflow was created successfully
2. Show the file path
3. List references it loads
4. Explain when to use this workflow
5. Suggest next steps (testing the workflow)
