---
description: Workflow for debugging test failures
---

## Debugging test failures

Use this workflow when investigating why tests are failing.

1. **Read the failure message** - Understand what assertion failed and why

2. **Run in isolation** - `uv run pytest -x -k <test_name>` to run just the failing test

3. **Use debugger if needed** - `uv run pytest --pdb -k <test_name>` to drop into debugger on failure

4. **Check for flakiness** - Time-dependent or order-dependent tests may pass inconsistently
