---
description: Review a specification for completeness and compliance
argument-hint: Spec ID or slug to review
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

# Review specification

You are helping a developer review an existing OAPS specification for completeness, consistency, and compliance with standards.

Spec to review: $ARGUMENTS

## Phase 1: Identify specification

**Goal**: Locate and validate the specification to review

1. If no spec ID provided, list available specs:

   ```bash
   oaps spec list
   ```

   Then ask user which spec to review.

2. Locate the spec:
   - Try exact ID match (e.g., `0001`)
   - Try slug match (e.g., `spec-system`)
   - Try full directory name (e.g., `0001-spec-system`)

3. Read spec metadata to confirm:

   ```
   .oaps/docs/specs/NNNN-slug/index.json
   ```

4. Create todo list with review phases

---

## Phase 2: Load context

**Goal**: Gather spec context and load review guidance

1. Load spec-writing skill with review checklist:

   ```bash
   oaps skill context spec-writing --references review-checklist keywords
   ```

2. Read spec files to understand current state:
   - index.json (metadata)
   - index.md (content structure)
   - requirements.json (requirement count, categories)
   - tests.json (test count, coverage)

3. Summarize spec state:
   - Title and status
   - Requirement count by category
   - Test coverage percentage
   - Last update date

---

## Phase 3: Run review

**Goal**: Comprehensive specification review

1. Launch spec-reviewer agent:

   ```
   Review specification: [spec ID and title]

   Perform comprehensive review checking:

   **Structure**
   - Required files present (index.json, index.md, requirements.json, tests.json, history.jsonl)
   - JSON files have valid syntax and schema
   - Markdown frontmatter is valid YAML

   **Requirements**
   - RFC 2119 keyword usage (MUST, SHOULD, MAY in uppercase)
   - Requirement completeness (all fields: id, page, section, title, description, priority, status)
   - Requirement testability (each can be independently verified)
   - ID format compliance (PREFIX-NNNN pattern)
   - No duplicate IDs

   **Tests**
   - Test ID format (T-NNNN pattern)
   - Bidirectional links (tests reference requirements, requirements reference tests)
   - Test completeness (type, description, expected)

   **Cross-references**
   - All cross-refs point to existing specs/items
   - Format is correct (NNNN:PREFIX-NNNN)

   **Consistency**
   - Consistent terminology
   - Status values are valid
   - Requirement priorities match RFC 2119 usage

   Rate each issue on confidence 0-100. Only report issues >= 80 confidence.
   ```

2. Wait for review results

---

## Phase 4: Present findings

**Goal**: Clearly communicate review results to user

1. Organize findings by severity:
   - **Critical**: Must fix before approval (structural issues, broken links)
   - **Important**: Should fix (RFC 2119 compliance, incomplete requirements)
   - **Suggestions**: Could improve (style, organization)

2. Show coverage metrics:
   - Requirements with tests / total requirements
   - Requirements by category breakdown
   - Status distribution

3. Ask user what to do with AskUserQuestion:
   - Fix issues now (return to spec-writer)
   - Create review artifact (document findings)
   - Proceed (mark review complete)

---

## Phase 5: Handle decision

**Goal**: Act on user's decision

### If fixing issues

1. For each critical/important issue:
   - Show current state
   - Show suggested fix
   - Apply fix or launch spec-writer

2. Re-run review to verify fixes

### If creating review artifact

1. Create artifact in spec's artifacts/ directory:

   ```
   .oaps/docs/specs/NNNN-slug/artifacts/review-YYYY-MM-DD.md
   ```

2. Include:
   - Review date and reviewer
   - Summary of findings
   - Coverage metrics
   - Recommended actions

### If proceeding

1. Optionally update spec status:

   ```bash
   oaps spec update NNNN --status review
   ```

---

## Phase 6: Summary

**Goal**: Document review outcome

1. Mark all todos complete
2. Summarize:
   - Spec reviewed: ID, title
   - Issues found: critical/important/suggestions counts
   - Issues fixed (if any)
   - Current coverage metrics
   - Recommendation for next steps

3. If status changed, note the new status
