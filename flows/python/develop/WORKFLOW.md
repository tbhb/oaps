---
description: Standard Python development workflow
default: true
---

## Default Python workflow

1. **Plan implementation** - Design your approach following the patterns in the loaded references

1. **Implement incrementally** - Make small, verifiable changes

1. **Verify after each change** - Run relevant quality checks:

   - `uv run basedpyright` - Type checking (zero errors/warnings)
   - `uv run ruff format .` - Format code
   - `uv run ruff check --fix .` - Linting (zero errors/warnings)
   - `just test` - Tests (>95% coverage)

1. **Final quality gate** - Before completing, run `just lint && just test`
