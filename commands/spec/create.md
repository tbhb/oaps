---
description: Create a new specification with guided wizard
argument-hint: Optional spec title or topic
allowed-tools:
  - AskUserQuestion
  - Bash(oaps:*)
  - Glob
  - Grep
  - Read
  - Skill
  - Task
  - TodoWrite
  - Write
  - Edit
---

# Create specification

You are helping a developer create a new OAPS specification using a guided wizard. This command coordinates spec-architect, spec-writer, and spec-reviewer agents to produce a well-structured specification.

Initial topic: $ARGUMENTS

## Phase 1: Gather information

**Goal**: Understand what specification needs to be created

1. Create todo list with all phases
2. If no topic provided or topic is unclear, ask user for:
   - What system, feature, or component is being specified?
   - What is the scope (high-level or detailed)?
   - What type of spec (feature, technical, API)?
   - Who is the intended audience?
3. Load spec-writing skill context: `oaps skill context spec-writing --references spec-structure formatting`
4. Summarize understanding and confirm with user

---

## Phase 2: Design structure

**Goal**: Design specification structure before writing content

1. Launch spec-architect agent to design structure:

   ```
   Design a specification structure for: [topic description]

   Consider:
   1. Appropriate scope and boundaries
   2. Document hierarchy (index.md + supplementary docs if needed)
   3. Requirement categories (FR, QR, SR, etc.)
   4. Test coverage strategy
   5. Dependencies on existing specs

   Based on existing patterns in .oaps/docs/specs/
   ```

2. Present proposed structure to user:
   - Spec title and slug
   - Document organization
   - Requirement categories with estimates
   - Test approach
3. Ask user for approval or refinements using AskUserQuestion

---

## Phase 3: Create specification

**Goal**: Create the specification directory and initial content

1. Determine next spec ID: Check `.oaps/docs/specs/index.json` for highest ID and increment
2. Run CLI to create spec directory structure:

   ```bash
   oaps spec create --title "Spec Title" --slug "spec-slug"
   ```

   Or manually create:
   - `.oaps/docs/specs/NNNN-slug/`
   - Required files: index.json, index.md, requirements.json, tests.json, history.jsonl

3. Launch spec-writer agent to create initial content:

   ```
   Create initial specification content based on this approved structure:

   [Include: topic, approved structure from architect, user preferences]

   Create:
   1. index.md with overview, scope, and initial sections
   2. index.json with metadata (title, status: draft, version: 0.1.0)
   3. requirements.json with initial requirements (follow RFC 2119)
   4. tests.json with placeholder tests linked to requirements
   5. history.jsonl with creation entry
   ```

4. Present created files to user

---

## Phase 4: Review

**Goal**: Validate the new specification

1. Launch spec-reviewer agent:

   ```
   Review the newly created specification: [spec ID]

   Check for:
   - Required files present
   - JSON schema compliance
   - Valid frontmatter in markdown
   - Requirement format and RFC 2119 compliance
   - Test-requirement bidirectional links
   - Cross-reference validity (if any)
   ```

2. Present review findings to user
3. If issues found, fix them directly or launch spec-writer to address

---

## Phase 5: Summary

**Goal**: Document what was created

1. Mark all todos complete
2. Summarize:
   - Spec created: ID, title, location
   - Document count and structure
   - Requirement count by category
   - Next steps for adding more requirements
3. Show commands for further work:

   ```
   /spec:info NNNN        # View spec details
   /spec:review NNNN      # Review spec quality
   oaps spec show NNNN    # CLI info
   ```
