---
description: Add requirements to a specification
---

## Add requirements

1. **Determine requirement type** - Classify the requirement according to its category:

   - FR (Functional Requirement): What the system does - behaviors, features, capabilities
   - QR (Quality Requirement): How well it performs - speed, reliability, scalability, maintainability
   - SR (Security Requirement): Auth, authorization, data protection, secure communication
   - AR (Accessibility Requirement): WCAG compliance, assistive technology support
   - IR (Interface Requirement): External APIs, protocols, data formats, integration points
   - DR (Documentation Requirement): What must be documented, coverage, format standards
   - CR (Constraint): Non-negotiable boundaries - platform, dependencies, compliance

2. **Assign unique requirement ID** - Generate a permanent identifier:

   - Use format: `<TYPE>-<NUMBER>` (e.g., FR-0001, QR-0042)
   - Ensure ID is unique within the specification
   - IDs are permanent and never reused

3. **Write requirement using requirement-writing principles** - Draft clear, testable requirement:

   - Follow atomic requirement pattern (one testable statement)
   - Use active voice and precise language
   - Use "shall" for all requirement statements
   - Avoid ambiguous terms
   - Reference requirement-writing reference for guidance

4. **Add acceptance criteria** - Define measurable success conditions:

   - List specific, testable conditions
   - Include edge cases and error conditions
   - Ensure criteria fully cover the requirement

5. **Link to parent/child requirements if applicable** - Establish traceability:

   - Link to parent requirements (higher-level needs)
   - Link to child requirements (decomposed details)
   - Reference dependent requirements

6. **Update requirements.json** - Maintain requirement metadata:

   - Add requirement entry with ID and type
   - Update traceability links
   - Increment version if appropriate
