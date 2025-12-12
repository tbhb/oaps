---
name: identification
title: Identification scheme for specifications, requirements, and tests
description: Numbering and prefix conventions for specs, requirements, and test cases.
commands: {}
required: true
---
# Specification identification scheme

## Spec numbering

Specs are numbered sequentially with four digits: `0001`, `0002`, etc.

Once assigned, a spec number is permanent. Deprecated specs keep their number to preserve cross-references.

## Requirement prefixes

| Prefix | Name                      | Description                                                            |
|--------|---------------------------|------------------------------------------------------------------------|
| FR     | Functional requirement    | What the system does: behaviors, features, capabilities                |
| QR     | Quality requirement       | How well it performs: speed, reliability, scalability, maintainability |
| SR     | Security requirement      | Auth, authorization, data protection, secure communication             |
| AR     | Accessibility requirement | WCAG compliance, assistive technology support                          |
| IR     | Interface requirement     | External APIs, protocols, data formats, integration points             |
| DR     | Documentation requirement | What must be documented, coverage, format standards                    |
| CR     | Constraint                | Non-negotiable boundaries: platform, dependencies, compliance          |

## Requirement numbering

Within a spec, requirements are numbered by prefix with optional sub-requirements:

```
FR-0001
FR-0001.0001
FR-0001.0002
FR-0002
```

Cross-spec references include the spec number:

```
0001:FR-0001
0002:IR-0003.0002
```

## Test method prefixes

| Prefix | Name               | Description                                  | Speed           |
|--------|--------------------|----------------------------------------------|-----------------|
| UT     | Unit test          | Isolated component, mocked dependencies      | Fast            |
| NT     | Integration test   | Components together, real dependencies       | Medium          |
| ET     | End-to-end test    | Full system flows, user journeys             | Slow            |
| PT     | Performance test   | Benchmarks, load tests against QR thresholds | Scheduled       |
| CT     | Conformance test   | Protocol/spec compliance validation          | On IR changes   |
| AT     | Accessibility test | Automated a11y checks against AR             | On HTML changes |
| ST     | Smoke test         | Basic system health checks                   | On deploy       |
| MT     | Manual test        | Human verification, exploratory, UX review   | Milestone gates |

## Test numbering

Tests are numbered sequentially within their method prefix using four digits:

```
UT-0001
UT-0002
NT-0001
```

Cross-spec test references (rare) would be `0001:UT-0001`.

## Typical verification patterns

| Requirement | Primary test methods          |
|-------------|-------------------------------|
| FR          | UT, NT, ET, ST                |
| QR          | PT                            |
| SR          | UT, NT, ET, MT                |
| AR          | AT, MT                        |
| IR          | NT, CT                        |
| DR          | MT (or automated doc tooling) |
| CR          | UT, ST                        |

## File structure

```
.oaps/docs/specs/
  index.json                    # Root manifest of all specs
  0001-spec-system/
    index.json                  # Spec metadata, dependencies
    index.md                    # Main spec content
    requirements.json           # All FR/QR/SR/AR/IR/DR/CR
    tests.json                  # All UT/NT/ET/PT/CT/AT/ST/MT
    history.jsonl               # Append-only change log
  0002-hook-system/
    ...
```
