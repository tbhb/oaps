---
name: review-checklist
title: Review checklist
description: Specification completeness, clarity criteria, consistency checks, testability assessment. Load when reviewing or improving existing specifications.
commands: {}
principles:
  - '**Complete**: All necessary information is present'
  - '**Clear**: Unambiguous language, no interpretation required'
  - '**Consistent**: No contradictions within or across specs'
  - '**Testable**: Every requirement can be verified'
best_practices:
  - '**Read as an implementer**: Could you build this without questions?'
  - '**Check cross-references**: Verify linked specs are consistent'
  - '**Challenge assumptions**: Are implicit assumptions documented?'
  - '**Verify examples**: Do examples match the requirements?'
  - '**Consider edge cases**: Are boundary conditions addressed?'
checklist:
  - Overview clearly explains purpose
  - Scope defines boundaries
  - Requirements are testable
  - No ambiguous terms
  - Examples match requirements
  - Edge cases documented
  - Error handling specified
references: {}
---

## Quick review checklist

Use this for rapid spec reviews:

- [ ] **Purpose clear**: Can explain in one sentence what this spec defines
- [ ] **Scope bounded**: In-scope and out-of-scope explicitly listed
- [ ] **Requirements testable**: Each requirement has verifiable criteria
- [ ] **No ambiguity**: No vague terms (fast, easy, user-friendly)
- [ ] **Examples present**: At least one example per complex concept
- [ ] **Errors handled**: Error conditions and messages defined
- [ ] **Dependencies listed**: External dependencies documented

## Comprehensive review guide

### 1. Completeness check

#### Structure completeness

| Section                     | Present | Complete | Notes |
| --------------------------- | ------- | -------- | ----- |
| Overview/Purpose            | [ ]     | [ ]      |       |
| Scope definition            | [ ]     | [ ]      |       |
| Functional requirements     | [ ]     | [ ]      |       |
| Non-functional requirements | [ ]     | [ ]      |       |
| Constraints                 | [ ]     | [ ]      |       |
| Acceptance criteria         | [ ]     | [ ]      |       |
| Examples                    | [ ]     | [ ]      |       |

#### Content completeness

- [ ] All user personas are addressed
- [ ] All use cases have requirements
- [ ] All requirements have acceptance criteria
- [ ] All error conditions are specified
- [ ] All external interfaces are documented
- [ ] All assumptions are stated

### 2. Clarity assessment

#### Ambiguous terms to flag

| Ambiguous       | Ask for clarification                 |
| --------------- | ------------------------------------- |
| "fast"          | How fast? Specify milliseconds.       |
| "easy"          | What defines easy? Clicks? Time?      |
| "secure"        | Which security measures specifically? |
| "reliable"      | What uptime percentage?               |
| "user-friendly" | What makes it user-friendly?          |
| "etc."          | List all items explicitly.            |
| "and/or"        | Which one? Or both? Be explicit.      |
| "if possible"   | Is it required or optional?           |
| "should"        | Convert to "shall" - all requirements are mandatory |

#### Language quality

- [ ] Active voice used ("The system displays..." not "It is displayed...")
- [ ] One requirement per statement
- [ ] "shall" used consistently for all requirements
- [ ] Technical terms defined in glossary
- [ ] Acronyms expanded on first use

### 3. Consistency verification

#### Internal consistency

- [ ] No contradictory requirements
- [ ] Terminology used consistently
- [ ] Examples match requirements
- [ ] Acceptance criteria align with requirements
- [ ] Non-functional requirements don't conflict

#### External consistency

- [ ] Aligns with related specifications
- [ ] Consistent with existing system behavior
- [ ] Matches API documentation
- [ ] Compatible with stated constraints

### 4. Testability assessment

For each requirement, verify:

| Requirement | Testable | Criteria defined | Test exists |
| ----------- | -------- | ---------------- | ----------- |
| REQ-001     | [ ]      | [ ]              | [ ]         |
| REQ-002     | [ ]      | [ ]              | [ ]         |

#### Testability criteria

A requirement is testable if:

- [ ] Success criteria are measurable
- [ ] Failure conditions are defined
- [ ] Input/output examples exist
- [ ] No subjective judgments required
- [ ] Can be verified in isolation

### 5. Risk identification

#### Missing information

| Gap            | Impact                | Severity     |
| -------------- | --------------------- | ------------ |
| [Missing item] | [What could go wrong] | High/Med/Low |

#### Ambiguity risks

| Ambiguous area | Possible interpretations | Risk     |
| -------------- | ------------------------ | -------- |
| [Area]         | [Interpretation A vs B]  | [Impact] |

### 6. Stakeholder readiness

- [ ] Target audience can understand the spec
- [ ] Technical depth appropriate for implementers
- [ ] Business context clear for stakeholders
- [ ] Test criteria clear for QA

## Review feedback template

See the **Review feedback template** for the complete structure including reviewer, date, verdict, summary, strengths, issues by severity, questions, and suggestions.

## Common review findings

### Frequent issues

1. **Vague requirements**: "The system should be responsive"

   - Fix: "Page load time shall be under 2 seconds on 3G connection"

1. **Missing error handling**: No specification of what happens on failure

   - Fix: Add error states section for each feature

1. **Incomplete scope**: Unclear what's in/out

   - Fix: Explicitly list what's excluded

1. **Untestable criteria**: "User experience should be good"

   - Fix: Define measurable UX metrics (task completion time, error rate)

1. **Implicit assumptions**: Dependencies not stated

   - Fix: Add assumptions section

### Review anti-patterns

Avoid these reviewer behaviors:

- Nitpicking formatting over content
- Suggesting features beyond scope
- Reviewing without reading fully
- Providing criticism without solutions
- Blocking on subjective preferences
