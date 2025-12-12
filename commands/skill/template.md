---
description: Add a template to a skill
argument-hint: [skill-name] [template-description]
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

# Add skill template

You are helping a developer add a new template to an existing Claude Code skill.

Arguments: $ARGUMENTS

Parse arguments as: first argument is skill name, remaining arguments describe the template.

## Phase 1: Identify Target

**Goal**: Understand what template to add

1. Parse the arguments to extract skill name and template description
2. If skill name is missing, ask which skill to add the template to
3. If template description is missing, ask what the template should generate
4. Locate the skill and confirm it exists
5. List existing templates in the skill (if any)

---

## Phase 2: Load Context

**Goal**: Prepare for template creation

1. Load skill context: `oaps skill context skill-development --references templating`

2. Read the skill's current structure:
   - skill.md
   - All existing files in templates/ (if directory exists)

---

## Phase 3: Design & Implementation

**Goal**: Design and create the template

1. Launch skill-developer agent to design AND implement the template:

   ```
   Design and implement a new template for the skill based on these requirements:

   Skill: [skill name]
   Template need: [description from arguments]
   Existing templates: [list from Phase 1]

   Follow this workflow:
   1. Choose template type (Jinja2 .j2 or static)
   2. Choose an appropriate filename
   3. Identify required variables
   4. Plan the output structure
   5. Determine which workflows will use this template
   6. Create templates directory if needed: mkdir -p <skill-path>/templates/
   7. Create the template file at <skill-path>/templates/<name>
   8. Update relevant workflows or references to document the template
   ```

2. Review the agent's implementation
3. Present design to user for approval

---

## Phase 4: Validation

**Goal**: Verify the template works

1. Run `oaps skill validate <skill-name>` to check structure
2. If Jinja2 template, test rendering:

   ```
   oaps skill render <skill-name> --template <template-name> --var key=value
   ```

3. Verify output is correct
4. Report any issues

---

## Phase 5: Summary

**Goal**: Document what was created

1. Report the template was created successfully
2. Show the file path
3. List required variables (if Jinja2)
4. Explain when to use this template
5. Suggest next steps (documenting in workflows, testing with real values)
