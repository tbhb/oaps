---
name: metadata
title: Metadata schema reference
description: JSON schemas for spec indexes, requirements, tests, and history logs. Load when creating or querying spec metadata, understanding status values, or working with requirements.json and tests.json files.
commands: {}
principles:
  - Metadata files are the source of truth, edited via CLI not manually
  - Use standardized status values for consistent lifecycle tracking
  - Maintain bidirectional links between requirements and tests
  - History logs are append-only for auditability
  - Schema versions enable future migrations without breaking existing specs
best_practices:
  - Include all required fields when creating requirements and tests
  - Link tests to requirements via tests_requirements and verified_by fields
  - Use Planguage-style fields (scale, meter, baseline, goal, stretch) for quality requirements
  - Record actors and commands in history for traceability
  - Keep spec summaries concise but descriptive for index listings
  - Use semantic versioning for specs that need version tracking
checklist:
  - All required fields present in index.json, requirements.json, tests.json
  - Status values use allowed values from schema
  - All requirements in specs are mandatory
  - Tests reference valid requirement IDs in tests_requirements
  - Requirements reference valid test IDs in verified_by
  - History entries include timestamp, event, and actor
  - Quality requirements include measurable targets (goal, baseline)
references: {}
---

# Metadata schema reference

This document defines the JSON schemas for spec indexes, requirements, and tests.

## Root index

`.oaps/docs/specs/index.json` is the manifest of all specs. Source of truth, edited via CLI.

```json
{
  "version": 1,
  "updated": "2024-01-15T10:30:00Z",
  "specs": [
    {
      "id": "0001",
      "slug": "indieauth",
      "title": "IndieAuth discovery and verification",
      "status": "approved",
      "created": "2024-01-10T09:00:00Z",
      "updated": "2024-01-15T10:30:00Z",
      "depends_on": [],
      "tags": ["auth", "indieweb"]
    },
    {
      "id": "0002",
      "slug": "micropub",
      "title": "Micropub endpoint",
      "status": "draft",
      "created": "2024-01-12T14:00:00Z",
      "updated": "2024-01-14T16:00:00Z",
      "depends_on": ["0001"],
      "tags": ["publishing", "indieweb"]
    }
  ]
}
```

### Root index fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | integer | yes | Schema version for migration support |
| updated | datetime | yes | Last modification timestamp |
| specs | array | yes | List of spec summary objects |

### Spec summary fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Four-digit spec identifier |
| slug | string | yes | URL-safe short name |
| title | string | yes | Human-readable title |
| status | string | yes | Spec status (see status values) |
| created | datetime | yes | Creation timestamp |
| updated | datetime | yes | Last modification timestamp |
| depends_on | array | no | Spec IDs this spec depends on |
| tags | array | no | Freeform tags for filtering |

## Per-spec index

`.oaps/docs/specs/NNNN-slug/index.json` contains full metadata for a single spec.

```json
{
  "id": "0001",
  "slug": "indieauth",
  "title": "IndieAuth discovery and verification",
  "status": "approved",
  "created": "2024-01-10T09:00:00Z",
  "updated": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "authors": ["developer-1"],
  "reviewers": ["reviewer-1", "reviewer-2"],
  "depends_on": [],
  "dependents": ["0002", "0003"],
  "tags": ["auth", "indieweb"],
  "summary": "Defines how the system discovers and verifies IndieAuth endpoints.",
  "documents": [
    {
      "file": "index.md",
      "title": "IndieAuth Specification",
      "type": "primary"
    },
    {
      "file": "flows.md",
      "title": "Authentication Flows",
      "type": "supplementary"
    }
  ],
  "external_refs": [
    {
      "title": "W3C IndieAuth Spec",
      "url": "https://indieauth.spec.indieweb.org/",
      "type": "normative"
    }
  ],
  "counts": {
    "requirements": 12,
    "tests": 28,
    "artifacts": 5
  }
}
```

### Per-spec index fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Four-digit spec identifier |
| slug | string | yes | URL-safe short name |
| title | string | yes | Human-readable title |
| status | string | yes | Spec status |
| created | datetime | yes | Creation timestamp |
| updated | datetime | yes | Last modification timestamp |
| version | string | no | Semantic version if versioned |
| authors | array | no | Creator identifiers |
| reviewers | array | no | Reviewer identifiers |
| depends_on | array | no | Spec IDs this depends on |
| dependents | array | no | Spec IDs that depend on this (generated) |
| tags | array | no | Freeform tags |
| summary | string | no | Brief description |
| documents | array | no | List of markdown files in this spec |
| external_refs | array | no | External references and links |
| counts | object | no | Summary counts (generated) |

### Document object fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | string | yes | Filename relative to spec directory |
| title | string | yes | Document title |
| type | string | yes | `primary`, `supplementary`, or `appendix` |

### External reference fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | yes | Reference title |
| url | string | yes | URL to external resource |
| type | string | yes | `normative` or `informative` |

## Spec status values

| Status | Description |
|--------|-------------|
| draft | Initial development, not yet reviewed |
| review | Under review, accepting feedback |
| approved | Accepted, ready for implementation |
| implementing | Active implementation in progress |
| implemented | Implementation complete, pending verification |
| verified | All requirements verified |
| deprecated | No longer recommended, kept for reference |
| superseded | Replaced by another spec |

## Requirements

`.oaps/docs/specs/NNNN-slug/requirements.json` contains all requirements for a spec. Source of truth, edited via CLI.

```json
{
  "spec_id": "0001",
  "updated": "2024-01-15T10:30:00Z",
  "requirements": [
    {
      "id": "FR-0001",
      "title": "IndieAuth discovery links",
      "type": "functional",
      "status": "approved",
      "created": "2024-01-10T09:00:00Z",
      "updated": "2024-01-12T11:00:00Z",
      "author": "developer-1",
      "description": "The site shall include link relations for IndieAuth discovery.",
      "rationale": "Required for IndieAuth clients to discover authorization endpoints.",
      "acceptance_criteria": [
        "Homepage contains rel=authorization_endpoint link",
        "Homepage contains rel=token_endpoint link"
      ],
      "verified_by": ["UT-0001", "NT-0001"],
      "depends_on": [],
      "tags": ["discovery", "indieauth"],
      "source_section": "index.md#discovery"
    },
    {
      "id": "FR-0001.0001",
      "title": "Authorization endpoint link",
      "type": "functional",
      "status": "approved",
      "created": "2024-01-10T09:00:00Z",
      "updated": "2024-01-12T11:00:00Z",
      "author": "developer-1",
      "parent": "FR-0001",
      "description": "The site shall include a rel=authorization_endpoint link element.",
      "rationale": "Clients use this to initiate authorization flow.",
      "acceptance_criteria": [
        "Link element present in HTML head",
        "href points to valid authorization endpoint"
      ],
      "verified_by": ["UT-0002"],
      "depends_on": [],
      "tags": ["discovery"],
      "source_section": "index.md#discovery"
    },
    {
      "id": "QR-0001",
      "title": "Build performance",
      "type": "quality",
      "subtype": "performance",
      "status": "approved",
      "created": "2024-01-11T10:00:00Z",
      "updated": "2024-01-11T10:00:00Z",
      "author": "developer-1",
      "description": "Full site build shall complete within target time.",
      "rationale": "Fast builds enable rapid iteration during development.",
      "scale": "seconds",
      "meter": "time per build on reference corpus (500 posts)",
      "baseline": 60,
      "goal": 30,
      "stretch": 10,
      "verified_by": ["PT-0001"],
      "depends_on": [],
      "tags": ["performance", "build"],
      "source_section": "index.md#quality"
    }
  ]
}
```

### Requirement fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Requirement identifier (e.g., `FR-0001`) |
| title | string | yes | Short descriptive title |
| type | string | yes | `functional`, `quality`, `security`, `accessibility`, `interface`, `documentation`, `constraint` |
| status | string | yes | Requirement status |
| created | datetime | yes | Creation timestamp |
| updated | datetime | yes | Last modification timestamp |
| author | string | yes | Creator identifier |
| description | string | yes | Full requirement statement |
| rationale | string | no | Why this requirement exists |
| acceptance_criteria | array | no | List of criteria for verification |
| verified_by | array | no | Test IDs that verify this requirement |
| depends_on | array | no | Requirement IDs this depends on |
| tags | array | no | Freeform tags |
| source_section | string | no | Reference to section in spec markdown |
| parent | string | no | Parent requirement ID for sub-requirements |
| subtype | string | no | Further categorization within type |

### Quality requirement fields (Planguage-style)

| Field | Type | Description |
|-------|------|-------------|
| scale | string | Unit of measurement |
| meter | string | How to measure |
| baseline | number | Current/past value |
| goal | number | Minimum acceptable target |
| stretch | number | Desired target |
| fail | number | Unacceptable threshold |

## Requirement status values

| Status | Description |
|--------|-------------|
| proposed | Under consideration, not yet approved |
| approved | Accepted, ready for implementation |
| implementing | Active implementation in progress |
| implemented | Implementation complete, pending verification |
| verified | All tests passing |
| deferred | Postponed to future work |
| rejected | Considered and declined |
| deprecated | No longer applicable |

## Tests

`.oaps/docs/specs/NNNN-slug/tests.json` contains all tests for a spec. Source of truth, edited via CLI.

```json
{
  "spec_id": "0001",
  "updated": "2024-01-15T10:30:00Z",
  "tests": [
    {
      "id": "UT-0001",
      "title": "Discovery links present in output",
      "method": "unit",
      "status": "passing",
      "created": "2024-01-11T09:00:00Z",
      "updated": "2024-01-14T16:00:00Z",
      "author": "developer-1",
      "tests_requirements": ["FR-0001"],
      "description": "Verify that built HTML contains IndieAuth discovery links.",
      "file": "tests/unit/test_discovery.py",
      "function": "test_discovery_links_present",
      "last_run": "2024-01-14T16:00:00Z",
      "last_result": "pass",
      "tags": ["discovery", "html"]
    },
    {
      "id": "PT-0001",
      "title": "Build time benchmark",
      "method": "performance",
      "status": "passing",
      "created": "2024-01-12T10:00:00Z",
      "updated": "2024-01-14T16:00:00Z",
      "author": "developer-1",
      "tests_requirements": ["QR-0001"],
      "description": "Measure build time against performance targets.",
      "file": "tests/performance/test_build_time.py",
      "function": "test_build_time_benchmark",
      "last_run": "2024-01-14T16:00:00Z",
      "last_result": "pass",
      "last_value": 24.5,
      "threshold": 30,
      "tags": ["performance", "build"]
    },
    {
      "id": "MT-0001",
      "title": "Visual review of error states",
      "method": "manual",
      "status": "pending",
      "created": "2024-01-13T11:00:00Z",
      "updated": "2024-01-13T11:00:00Z",
      "author": "developer-1",
      "tests_requirements": ["FR-0012"],
      "description": "Manually verify error messages display correctly.",
      "steps": [
        "Trigger token expiry error",
        "Verify error message is visible",
        "Verify error styling matches design"
      ],
      "expected_result": "Error message displays with correct styling and text",
      "tags": ["manual", "ui"]
    }
  ]
}
```

### Test fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Test identifier (e.g., `UT-0001`) |
| title | string | yes | Short descriptive title |
| method | string | yes | `unit`, `integration`, `e2e`, `performance`, `conformance`, `accessibility`, `smoke`, `manual` |
| status | string | yes | Test status |
| created | datetime | yes | Creation timestamp |
| updated | datetime | yes | Last modification timestamp |
| author | string | yes | Creator identifier |
| tests_requirements | array | yes | Requirement IDs this test verifies |
| description | string | no | What the test verifies |
| file | string | no | Path to test file (for automated tests) |
| function | string | no | Test function/method name |
| last_run | datetime | no | When test was last executed |
| last_result | string | no | `pass`, `fail`, `skip`, `error` |
| tags | array | no | Freeform tags |

### Performance test fields

| Field | Type | Description |
|-------|------|-------------|
| last_value | number | Most recent measured value |
| threshold | number | Pass/fail threshold |
| baseline | number | Historical baseline for comparison |

### Manual test fields

| Field | Type | Description |
|-------|------|-------------|
| steps | array | Step-by-step instructions |
| expected_result | string | What success looks like |
| actual_result | string | What was observed (filled on execution) |
| tested_by | string | Who performed the test |
| tested_on | datetime | When manually tested |

## Test status values

| Status | Description |
|--------|-------------|
| pending | Test defined but not yet implemented |
| implemented | Test exists but not yet run |
| passing | Last run passed |
| failing | Last run failed |
| skipped | Intentionally skipped (with reason) |
| flaky | Inconsistent results, needs attention |
| disabled | Temporarily disabled |

## History log

`.oaps/docs/specs/NNNN-slug/history.jsonl` is an append-only log of changes. One JSON object per line.

```jsonl
{"timestamp":"2024-01-10T09:00:00Z","event":"spec_created","actor":"developer-1","command":"spec create indieauth"}
{"timestamp":"2024-01-10T09:30:00Z","event":"requirement_added","id":"FR-0001","actor":"developer-1","command":"spec req add 0001 FR ..."}
{"timestamp":"2024-01-12T11:00:00Z","event":"status_changed","target":"FR-0001","from":"proposed","to":"approved","actor":"reviewer-1","command":"spec req status 0001:FR-0001 approved"}
{"timestamp":"2024-01-14T16:00:00Z","event":"test_run","id":"UT-0001","result":"pass","actor":"ci","command":"spec test run 0001"}
```

### History event types

| Event | Description |
|-------|-------------|
| spec_created | Spec was created |
| spec_status_changed | Spec status changed |
| requirement_added | Requirement added |
| requirement_updated | Requirement modified |
| requirement_removed | Requirement deleted |
| status_changed | Any status change (target field indicates what) |
| test_added | Test added |
| test_updated | Test modified |
| test_removed | Test deleted |
| test_run | Test was executed |
| artifact_added | Artifact added |
| artifact_updated | Artifact modified |
| artifact_removed | Artifact deleted |

### History entry fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | datetime | yes | When the event occurred |
| event | string | yes | Event type |
| actor | string | yes | Who/what triggered the event |
| command | string | no | CLI command that triggered the event |
| id | string | no | ID of affected item |
| target | string | no | Target of change (for status changes) |
| from | string | no | Previous value |
| to | string | no | New value |
| result | string | no | Result (for test runs) |
| reason | string | no | Explanation if relevant |
