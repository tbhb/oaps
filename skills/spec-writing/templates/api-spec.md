# API: [Service Name]

## Overview
[Brief description of the API's purpose]

## Base URL
- Production: `https://api.example.com/v1`
- Staging: `https://api-staging.example.com/v1`

## Authentication
[Auth method: API key, OAuth 2.0, JWT, etc.]

## Versioning
[Strategy: URL path, header, query parameter]

## Endpoints

### [Resource name]

#### GET /resources
[Description]

**Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | integer | No | Max results (default: 20, max: 100) |
| offset | integer | No | Pagination offset |

**Response**
```json
{
  "data": [...],
  "meta": { "total": 100, "limit": 20, "offset": 0 }
}
```

**Errors**

| Code | Description         |
| ---- | ------------------- |
| 401  | Unauthorized        |
| 429  | Rate limit exceeded |

## Data schemas

### [Schema name]

[JSON Schema or example with field descriptions]
