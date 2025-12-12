---
name: technical-specs
title: Technical specifications
description: API contracts, data schemas, interface specifications, protocols, versioning. Load when writing API specs, system interfaces, or data schemas.
commands: {}
principles:
  - '**Contract-first**: Define interfaces before implementation'
  - '**Explicit over implicit**: Document all assumptions'
  - '**Backward compatibility**: Consider versioning from the start'
  - '**Complete examples**: Include request/response samples'
best_practices:
  - '**Use standard formats**: OpenAPI for REST, Protocol Buffers for gRPC'
  - '**Document error responses**: All possible error codes and messages'
  - '**Include authentication**: Specify auth requirements per endpoint'
  - '**Version from day one**: Plan for evolution'
  - '**Provide examples**: Real request/response pairs'
checklist:
  - All endpoints documented with methods and paths
  - Request/response schemas defined
  - Error responses documented
  - Authentication requirements specified
  - Versioning strategy defined
  - Examples provided for each endpoint
references:
  https://swagger.io/specification/: OpenAPI Specification
  https://json-schema.org/: JSON Schema
  https://protobuf.dev/: Protocol Buffers
---

## API specification template

See the **API specification template** for the complete structure including overview, base URL, authentication, versioning, endpoints, and data schemas.

## REST API conventions

### HTTP methods

| Method | Purpose | Idempotent |
|--------|---------|------------|
| GET | Retrieve resource(s) | Yes |
| POST | Create resource | No |
| PUT | Replace resource | Yes |
| PATCH | Partial update | Yes |
| DELETE | Remove resource | Yes |

### Status codes

| Code | Meaning | Use case |
|------|---------|----------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Valid auth, insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource state conflict |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Server Error | Server-side error |

### URL design

```

# Collection

GET /users # List users
POST /users # Create user

# Resource

GET /users/{id} # Get user
PUT /users/{id} # Replace user
PATCH /users/{id} # Update user
DELETE /users/{id} # Delete user

# Nested resources

GET /users/{id}/posts # User's posts
POST /users/{id}/posts # Create post for user

# Actions (when CRUD doesn't fit)

POST /users/{id}/activate # Custom action

````

## Data schema documentation

### JSON Schema example

````json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "User",
  "required": ["id", "email", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier"
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "User's email address"
    },
    "name": {
      "type": "string",
      "maxLength": 100,
      "description": "Display name (optional)"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    }
  }
}
````

### Field documentation table

| Field      | Type     | Required | Description        | Constraints         |
| ---------- | -------- | -------- | ------------------ | ------------------- |
| id         | UUID     | Yes      | Unique identifier  | Read-only           |
| email      | string   | Yes      | Email address      | Valid email format  |
| name       | string   | No       | Display name       | Max 100 chars       |
| created_at | datetime | Yes      | Creation timestamp | ISO 8601, read-only |

## Versioning strategies

### URL versioning (recommended)

```
GET /v1/users
GET /v2/users
```

Pros: Explicit, easy to understand, cacheable
Cons: URL changes between versions

### Header versioning

```
GET /users
Accept: application/vnd.api+json;version=2
```

Pros: Clean URLs
Cons: Less visible, harder to test

### Deprecation policy

```markdown
## Deprecation policy

1. Announce deprecation 6 months before removal
2. Add `Deprecation` header with sunset date
3. Document migration path to new version
4. Remove endpoint after sunset date

Example header:
Deprecation: Sun, 01 Jan 2025 00:00:00 GMT
Sunset: Sun, 01 Jul 2025 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

## Error response format

### Standard error structure

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "code": "INVALID_FORMAT",
        "message": "Must be a valid email address"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### Error codes

Define application-specific error codes:

| Code             | HTTP Status | Description              |
| ---------------- | ----------- | ------------------------ |
| VALIDATION_ERROR | 400         | Input validation failed  |
| UNAUTHORIZED     | 401         | Authentication required  |
| FORBIDDEN        | 403         | Insufficient permissions |
| NOT_FOUND        | 404         | Resource not found       |
| CONFLICT         | 409         | Resource state conflict  |
| RATE_LIMITED     | 429         | Too many requests        |
| INTERNAL_ERROR   | 500         | Unexpected server error  |

## Rate limiting

Document rate limits and headers:

```markdown
## Rate limiting

- **Default limit**: 100 requests per minute
- **Authenticated**: 1000 requests per minute
- **Burst**: Up to 10 requests per second

### Response headers
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait (when rate limited)
```
