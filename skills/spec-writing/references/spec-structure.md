---
name: spec-structure
title: Specification structure
description: Spec file organization, section ordering, frontmatter metadata, lightweight vs formal formats. Load when creating new specs or organizing spec content.
commands:
  tree <path>: View spec directory structure
  ls <path>: List spec files
principles:
  - '**Start with context**: Overview and scope before details'
  - '**Progressive disclosure**: High-level first, details in subsections'
  - '**Testable requirements**: Every requirement should be verifiable'
  - '**Single source of truth**: Avoid duplicating information across specs'
best_practices:
  - '**Use consistent section ordering**: Overview, scope, requirements, constraints, acceptance criteria'
  - '**Include frontmatter metadata**: Title, version, status, author, reviewers'
  - '**Separate concerns**: Functional vs non-functional requirements'
  - '**Version specifications**: Track changes with semantic versioning'
  - '**Link related specs**: Cross-reference dependent specifications'
checklist:
  - Overview section explains the purpose
  - Scope clearly defines boundaries
  - Requirements are numbered for traceability
  - Acceptance criteria are testable
  - Status and version are current
references: {}
---

## Specification formats

### Lightweight format

For iterative development, small features, internal tools. See the **Lightweight specification template**.

### Formal format

For APIs, contracts, compliance, external interfaces. See the **Formal specification template**.

## Section ordering convention

1. **Metadata** (frontmatter) - Title, version, status, ownership
1. **Overview** - Purpose, scope, definitions
1. **Functional requirements** - What the system must do
1. **Non-functional requirements** - Quality attributes
1. **Constraints** - Limitations and boundaries
1. **Acceptance criteria** - How to verify requirements
1. **Appendices** - References, history, diagrams

## When to use each format

| Criterion        | Lightweight   | Formal                |
| ---------------- | ------------- | --------------------- |
| Audience         | Internal team | External stakeholders |
| Lifespan         | Short-term    | Long-term             |
| Compliance       | None          | Required              |
| Change frequency | High          | Low                   |
| Review process   | Informal      | Formal approval       |

## Requirement identifiers

Use type-prefixed identifiers for traceability. See the **identification** reference for the complete scheme.

Primary requirement prefixes:

- **FR-NNNN**: Functional requirements
- **QR-NNNN**: Quality requirements (non-functional)
- **CR-NNNN**: Constraints

This enables linking test cases back to requirements using typed test prefixes (UT, NT, ET, etc.).
