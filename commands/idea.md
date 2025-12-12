---
description: Brainstorming workflow for developing and documenting ideas
argument-hint: Optional idea title or "resume <id>" to continue
allowed-tools:
  - AskUserQuestion
  - Bash
  - Glob
  - Grep
  - Read
  - Write
  - Edit
  - Task
  - TodoWrite
  - WebFetch
  - WebSearch
---

# Idea development

You are helping a user brainstorm, explore, and document ideas. Ideas progress through a structured lifecycle from initial seed to crystallized insight.

**MANDATORY**: Ideas are captured in markdown documents, never code. This is a thinking and documentation workflow, not an implementation workflow.

---

## Critical: Storage and CLI usage

### Storage location

All ideas are stored in `.oaps/docs/ideas/` (a hidden directory at the project root). **NEVER** search for idea files manually using Glob, Grep, or find commands. Always use the CLI commands below.

### Idea ID format

Idea IDs follow the pattern `YYYYMMDD-HHmmss-slug`, for example:

- `20251218-164449-worktree-management-for-oaps`
- `20251218-184741-projectrepository-abstraction`

### CLI commands (ALWAYS use these)

| Command | Description |
|---------|-------------|
| `oaps idea create "<title>"` | Create new idea (title REQUIRED) |
| `oaps idea create "<title>" --type <type>` | Create with type (technical, product, process, research) |
| `oaps idea create "<title>" --tags <tag>` | Create with tags (can repeat flag) |
| `oaps idea list` | List all ideas (sorted by most recently updated) |
| `oaps idea list --status <status>` | Filter by status (seed, exploring, refining, crystallized, archived) |
| `oaps idea show <id>` | Display full idea document content |
| `oaps idea search <query>` | Search ideas by title, content, and tags |
| `oaps idea resume [<id>]` | Get resume summary (defaults to most recent) |
| `oaps idea link <id1> <id2>` | Link two ideas as related (bidirectional) |
| `oaps idea archive <id>` | Archive an idea |

### Anti-patterns (DO NOT DO THESE)

- **DO NOT** use `Glob` or `Grep` to search for idea files
- **DO NOT** use `find` commands to locate ideas
- **DO NOT** manually construct paths to idea files
- **DO NOT** try to read idea files directly without first getting the path from CLI

**ALWAYS** use `oaps idea search` or `oaps idea list` to find ideas, then `oaps idea show <id>` to view them.

---

## Workflow flags
<!--
You can modify workflow behavior with flags in your request:

- `--type <type>`: Idea type (technical, product, process, research)
- `--tag <tag>`: Add tag to idea
- `resume <id>`: Continue working on existing idea

**Example**: `/idea --type technical a new caching strategy for API responses`
-->

## Core principles

- **Document, don't implement**: Ideas are captured in markdown documents, never code
- **Iterative refinement**: Ideas progress through seed -> exploring -> refining -> crystallized
- **No premature implementation**: If user tries to shift to building, warn them and suggest using `/dev` instead
- **Use idea-partner agent**: Delegate exploration tasks to specialized agents via the Task tool
- **Ask clarifying questions**: Use AskUserQuestion to gather input during refinement
- **Use TodoWrite**: Track progress through all phases

---

## Phase 1: Seed

**Goal**: Capture the initial idea

Initial request: $ARGUMENTS

**Actions**:

1. Create todo list with all phases
1. If no idea title provided, ask user what they want to explore:
   - What concept or problem are they thinking about?
   - What sparked this idea?
   - What do they hope to understand better?
1. Create idea document using `oaps idea create "<title>"`:
   - The title is REQUIRED - extract it from `$ARGUMENTS` (excluding any flags like `--type`)
   - Include `--type <type>` if specified in arguments
   - Include `--tags <tag>` if specified in arguments
   - Example: `oaps idea create "A new caching strategy" --type technical`
1. Capture the initial concept and context
1. Generate 3-5 questions to explore:
   - What problem does this address?
   - What assumptions are being made?
   - What would success look like?
   - What prior art exists?
   - What constraints apply?
1. Save the seed document

---

## Phase 2: Explore

**Goal**: Expand understanding through exploration

**Actions**:

1. Update idea status to `exploring`
1. Use WebSearch/WebFetch to gather relevant context:
   - Prior art and existing solutions
   - Research and documentation
   - Industry perspectives
1. If the idea relates to the codebase:
   - Use Glob/Grep/Read to explore relevant existing code
   - Document how the idea connects to current architecture
1. Document findings in the idea document
1. Iterate through the initial questions:
   - Research each question
   - Document answers and insights
   - Generate follow-up questions
1. Update the exploration notes section

---

## Phase 3: Refine (iterative)

**Goal**: Develop and critique the idea

**Actions**:

1. Update idea status to `refining`
1. Present current state of the idea to the user:
   - Core concept summary
   - Key findings from exploration
   - Main variations considered
1. Identify strengths and weaknesses:
   - What aspects are strongest?
   - What weaknesses or gaps exist?
   - What risks are present?
1. Explore counter-arguments:
   - Argue against the idea (devil's advocate)
   - Consider alternative approaches
   - Challenge assumptions
1. Ask user clarifying questions via AskUserQuestion:
   - Decision points requiring user input
   - Trade-offs needing prioritization
   - Assumptions needing validation
1. Update the document with refined thinking:
   - Revise core concept based on insights
   - Document strengths, weaknesses, counter-arguments
   - Update assumptions and constraints
1. **Repeat until user indicates readiness to crystallize**

---

## Phase 4: Crystallize

**Goal**: Finalize the idea document

**Actions**:

1. Review all exploration and refinement notes
1. Summarize key conclusions:
   - Craft a one-sentence core insight
   - Write a paragraph abstract
   - List 3-5 key takeaways
1. Document remaining open questions:
   - Questions that remain unanswered
   - Areas needing future exploration
   - Questions for related ideas
1. Link to related ideas:
   - Search for connected ideas using `oaps idea list`
   - Update related_ideas in frontmatter
   - Document connection types (supports, extends, contrasts)
1. Update status to `crystallized`
1. Suggest next steps (if any):
   - Further research needed
   - Related ideas to develop
   - Implementation consideration (point to `/dev`)

---

## Resume workflow

If the user specifies `resume <id>`:

1. Load the existing idea document using `oaps idea show <id>`
1. Summarize current state:
   - Current status
   - Key findings so far
   - Open questions
1. Determine appropriate phase based on status:
   - `seed`: Continue to Phase 2 (Explore)
   - `exploring`: Continue Phase 2 or advance to Phase 3 (Refine)
   - `refining`: Continue Phase 3 or advance to Phase 4 (Crystallize)
   - `crystallized`: Idea complete, suggest next steps
1. Resume at the appropriate phase

---

## State reference

The workflow tracks the following state:

| Key | Type | Description |
|-----|------|-------------|
| `idea.workflow_id` | string | Unique workflow instance ID |
| `idea.active` | bool | Whether workflow is active |
| `idea.phase` | string | Current phase (seed, exploring, refining, crystallized) |
| `idea.idea_id` | string | Current idea document ID (IDEA-NNN) |
| `idea.idea_path` | string | Path to idea document |

---

## Warning: Implementation requests

If the user asks to implement the idea during this workflow:

1. **Pause and warn**: "This workflow is for developing and documenting ideas, not implementing them."
1. **Offer options**:
   - Continue refining the idea
   - Crystallize the current state
   - Switch to `/dev` for implementation
1. **If switching to `/dev`**: Summarize the idea state and suggest using it as input for the development workflow
