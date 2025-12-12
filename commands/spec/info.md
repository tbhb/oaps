---
description: Show detailed information about a specification
argument-hint: Spec ID or slug
allowed-tools:
  - Bash(oaps:*)
  - Glob
  - Grep
  - Read
  - Task
---

# Specification information

You are showing detailed information about an OAPS specification.

Spec to show: $ARGUMENTS

## Phase 1: Identify specification

1. If no spec ID provided, list available specs:

   ```bash
   oaps spec list
   ```

   Then report the list and ask which spec they want information about.

2. Locate the spec by:
   - Exact numeric ID (e.g., `0001`)
   - Slug (e.g., `spec-system`)
   - Full directory name (e.g., `0001-spec-system`)

3. Verify spec exists by checking for index.json

---

## Phase 2: Gather information

1. Launch spec-explorer agent for quick analysis:

   ```
   Analyze specification: [spec ID]

   Gather:
   1. Metadata from index.json (title, status, version, dates)
   2. Requirement summary from requirements.json (counts by category, by status)
   3. Test summary from tests.json (counts by type, coverage percentage)
   4. Document structure (list of .md files)
   5. Dependencies (cross-references to other specs)
   6. Recent history (last 5 entries from history.jsonl)
   ```

2. Read the key files directly for structured data:
   - `.oaps/docs/specs/NNNN-slug/index.json`
   - `.oaps/docs/specs/NNNN-slug/requirements.json`
   - `.oaps/docs/specs/NNNN-slug/tests.json`

---

## Phase 3: Present information

Display comprehensive spec information in structured format:

```markdown
## Specification: NNNN-slug

**Title**: [Full specification title]
**Status**: [draft | review | approved | implementing | implemented | verified | deprecated | superseded]
**Version**: X.Y.Z
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD

### Requirements Summary

| Category | Count | Status Distribution |
|----------|-------|---------------------|
| FR (Functional) | N | draft: X, approved: Y |
| QR (Quality) | N | draft: X, approved: Y |
| SR (Security) | N | draft: X, approved: Y |
| CR (Conformance) | N | draft: X, approved: Y |
| **Total** | **N** | |

### Test Coverage

| Metric | Value |
|--------|-------|
| Requirements with tests | N / M (X%) |
| Total test cases | N |
| Unit tests | N |
| Integration tests | N |
| Acceptance tests | N |

### Documents

| File | Description |
|------|-------------|
| index.md | Main specification document |
| [other.md] | [Supplementary document description] |

### Dependencies

**Depends on:**
- 0002-other-spec (via FR-0001 -> 0002:FR-0005)

**Depended by:**
- 0003-another-spec (via 0003:QR-0001 -> FR-0002)

### Recent History

| Date | Action | Actor | Details |
|------|--------|-------|---------|
| YYYY-MM-DD | update_requirements | user | Added FR-0010 |
| YYYY-MM-DD | update_tests | user | Added T-0015 |
```

---

## Phase 4: Suggest next steps

Based on spec state, suggest relevant actions:

**If status is draft:**

- `/spec:review NNNN` - Review for completeness
- Add more requirements with spec-writer

**If status is review:**

- `/spec:review NNNN` - Check review feedback
- `oaps spec update NNNN --status approved` - Approve spec

**If coverage is low:**

- Add tests to cover untested requirements
- Review requirements without tests

**If there are orphaned tests/requirements:**

- Fix bidirectional links
- Remove orphaned items

---

## CLI equivalents

Show the user equivalent CLI commands for future reference:

```bash
# Quick spec info
oaps spec show NNNN

# Detailed with requirements
oaps spec show NNNN --requirements

# Detailed with tests
oaps spec show NNNN --tests

# Check dependencies
oaps spec deps NNNN

# Validate structure
oaps spec validate NNNN
```
