---
name: feature-specs
title: Feature specifications
description: User stories, feature templates, scope definition, edge cases, UI/UX considerations. Load when writing feature or product specifications.
commands: {}
principles:
  - "**User-centric**: Define features from the user's perspective"
  - '**Outcome-focused**: Describe the value delivered, not implementation'
  - "**Bounded scope**: Clearly define what's in and out of scope"
  - '**Complete context**: Include enough detail for implementation'
best_practices:
  - '**Start with user stories**: Capture the who, what, and why'
  - '**Define success metrics**: How will you know the feature works?'
  - '**Document edge cases**: Explicitly handle boundary conditions'
  - '**Include error states**: Specify what happens when things go wrong'
  - '**Consider accessibility**: Include a11y requirements from the start'
checklist:
  - User story defines persona, action, and benefit
  - Scope explicitly lists what's included and excluded
  - Edge cases and error states are documented
  - Success metrics are defined and measurable
  - UI/UX considerations are addressed
references: {}
---

## User story format

### Standard format

```
As a [persona],
I want [action/capability],
So that [benefit/value].
```

### Examples

```
As a new user,
I want to sign up using my Google account,
So that I can start using the app without creating a new password.

As a content creator,
I want to schedule posts for future publication,
So that I can maintain a consistent posting schedule while away.
```

### Story splitting

Large stories should be split into smaller, deliverable increments:

**Epic**: User authentication

- Story 1: User can sign up with email/password
- Story 2: User can log in with email/password
- Story 3: User can reset forgotten password
- Story 4: User can sign up/log in with Google OAuth

## Feature specification template

See the **Feature specification template** for the complete structure including user story, scope, requirements, user flow, edge cases, error states, UI/UX considerations, success metrics, and acceptance criteria.

## Scope definition

### Defining boundaries

Be explicit about what's included and excluded:

```markdown
## Scope

### In scope
- User can create, edit, and delete their own posts
- Posts support text and single image attachments
- Posts are visible to followers immediately

### Out of scope (future consideration)
- Multi-image posts (planned for v2)
- Video attachments
- Scheduled posting
- Draft saving

### Explicitly excluded
- Anonymous posting (security decision)
- Post editing after 24 hours
```

### Scope creep prevention

Document assumptions and constraints:

```markdown
## Assumptions
- Users have verified email addresses
- Images are pre-moderated by existing system
- Database can handle 1000 new posts/minute

## Constraints
- Must use existing image upload service
- Cannot modify user table schema
- Launch deadline: Q2 2025
```

## Edge cases

### Common categories

1. **Empty states**: No data, first-time user
1. **Boundary values**: Min/max limits, zero, one, many
1. **Invalid input**: Wrong format, missing required fields
1. **Concurrent access**: Multiple users, race conditions
1. **Network issues**: Offline, slow connection, timeout
1. **Permission boundaries**: Unauthorized access attempts

### Documentation format

```markdown
## Edge cases

### Empty states
- **No posts yet**: Display "No posts yet. Create your first post!"
- **No followers**: Show suggested accounts to follow

### Boundary conditions
- **Post at character limit (500)**: Allow submission, show character count
- **Post exceeds limit**: Prevent submission, highlight excess characters

### Error recovery
- **Network timeout during post**: Save draft locally, retry automatically
- **Duplicate submission**: Detect and prevent, show existing post
```

## UI/UX considerations

### Accessibility (a11y)

- All interactive elements have keyboard focus
- Images have alt text
- Color is not the only indicator of state
- Text meets WCAG 2.1 AA contrast requirements
- Screen reader announcements for dynamic content

### Responsive design

- Mobile-first layout considerations
- Touch target sizes (minimum 44x44px)
- Gesture alternatives for mouse-only interactions

### Loading states

- Skeleton screens for initial load
- Progress indicators for long operations
- Optimistic UI updates where appropriate
