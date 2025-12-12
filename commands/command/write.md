---
description: Write a new slash command with guided workflow
argument-hint: [command-description]
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

# Write slash command

You are helping a developer create a new slash command using a structured workflow. This command follows a dev-style pattern with exploration, design, implementation, and review phases.

Initial request: $ARGUMENTS

## Phase 1: Discovery

**Goal**: Understand what command needs to be created

1. Create todo list with all phases
2. If command description is unclear, ask user for:
   - What workflow are they automating?
   - What arguments does it need?
   - What tools should it use?
   - Should it be project-specific or plugin-distributed?
3. Summarize understanding and confirm with user

---

## Phase 2: Exploration

**Goal**: Understand existing commands and patterns

1. Load skill context: `oaps skill context command-development --references structure frontmatter dynamic-features`

2. Launch command-explorer agent to analyze current state:

   ```
   Analyze the command system to inform creating a new command for: [command description]

   1. List existing commands in .oaps/claude/commands/ and commands/
   2. Find similar commands that could serve as templates
   3. Identify patterns for frontmatter, arguments, and tool restrictions
   4. Note any namespace organization this new command should follow
   5. Check for related commands this might interact with
   ```

3. Read key files the explorer identified

4. Present summary of relevant patterns and similar commands

---

## Phase 3: Clarifying Questions

**Goal**: Fill in gaps before designing

**CRITICAL**: Do not skip this phase.

1. Review exploration findings and original request
2. Identify underspecified aspects:
   - Exact command location (project vs plugin, namespace)
   - Argument structure ($ARGUMENTS vs positional)
   - Tool restrictions needed
   - Model selection (haiku/sonnet/opus)
   - Whether to use file references or bash execution
3. Present questions to user in organized list
4. Wait for answers before proceeding

---

## Phase 4: Design & Implementation

**Goal**: Design and implement the slash command

1. Launch command-developer agent with full context:

   ```
   Design and implement a slash command based on these requirements:

   [Include: original request, exploration findings, user answers to questions]

   Follow the workflow:
   1. Choose appropriate location and filename
   2. Write frontmatter with description, tools, model
   3. Create prompt as instructions FOR Claude
   4. Add dynamic features (arguments, file refs, bash)
   5. Validate frontmatter syntax
   6. Create the command file
   ```

2. Review the implementation
3. Present the command to user with explanation:
   - What the command does
   - How to invoke it
   - What arguments it accepts
   - What tools it can use
   - How it fits with existing commands

4. Ask user for approval before finalizing

---

## Phase 5: Review

**Goal**: Ensure command quality and correctness

1. Launch command-reviewer agent:

   ```
   Review the newly created slash command: [command name]

   Check for:
   - Frontmatter correctness (valid YAML, appropriate values)
   - Prompt quality (instructions FOR Claude, clear directives)
   - Dynamic features (correct argument/file/bash usage)
   - Tool restrictions (least privilege, correct patterns)
   - Organization (naming, namespace fit)
   - Usability (documentation, discoverability)
   ```

2. Present review findings to user
3. If issues need fixing, launch another command-developer agent to address them

---

## Phase 6: Summary

**Goal**: Document what was created

1. Mark all todos complete
2. Summarize:
   - Command created with name and purpose
   - File location
   - Key design decisions
   - How to invoke: `/command-name [args]`
   - Suggested next steps (testing, documentation)
