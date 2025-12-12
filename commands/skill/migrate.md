---
description: Migrate an existing skill to OAPS's progressive disclosure system
argument-hint: "[source-path] [migration-description]"
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

# Migrate skill

You are helping a developer migrate an existing skill to OAPS's progressive disclosure system.

**Arguments provided**: $ARGUMENTS

Parse arguments as: first argument is path to source skill file, remaining arguments describe the migration goals.

---

## MANDATORY: Execute the migrate-skill workflow

**CRITICAL INSTRUCTION**: You MUST execute the `migrate-skill` workflow from the `skill-development` skill. Do NOT improvise or create your own workflow. The workflow is the authoritative source for this task.

### Step 1: Load the workflow

Run this command IMMEDIATELY to load the relevant references:

```bash
oaps skill context skill-development --references skill-structure skill-references skill-workflows
```

### Step 2: Follow the migration process

After loading the context, follow these steps for migrating skills:

1. Locating the source skill
2. Analyzing the source skill's structure
3. Designing the OAPS structure (SKILL.md, references, workflows)
4. Initializing the new skill
5. Creating lightweight SKILL.md
6. Extracting references
7. Creating workflows
8. Validating
9. Committing

### Step 3: Use the provided arguments

When executing the workflow:

- **Source path**: Use the first argument as the path to the source skill file
- **Migration description**: Use remaining arguments to understand the migration goals
- If arguments are missing, ask the user for them as directed by the workflow

---

## Reminders

- The `migrate-skill` workflow is the single source of truth for this operation
- All file modifications should be done through Task agents (skill-developer, etc.)
- Present the decomposition plan to the user for approval before implementation
- Validate with `oaps skill validate` before committing
