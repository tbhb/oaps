set shell := ['uv', 'run', '--frozen', 'bash', '-euxo', 'pipefail', '-c']
set unstable
set positional-arguments

pnpm := "pnpm exec"

# List available recipes
default:
  @just --list

# Clean build artifacts
clean:
  #!/usr/bin/env bash
  rm -rf build/
  rm -rf dist/
  rm -rf site/
  find . -type d -name __pycache__ -exec rm -rf {} +
  find . -type d -name .pytest_cache -exec rm -rf {} +
  find . -type d -name .ruff_cache -exec rm -rf {} +

# Install all dependencies (Python + Node.js)
install:
  #!/usr/bin/env bash
  uv sync --frozen
  pnpm install --frozen-lockfile

# Install only Node.js dependencies
install-node:
  #!/usr/bin/env bash
  pnpm install --frozen-lockfile

# Install only Python dependencies
install-python:
  #!/usr/bin/env bash
  uv sync --frozen

# Reinstall the OAPS Claude plugin
reinstall-plugin:
  #!/usr/bin/env bash
  claude plugin uninstall oaps@oaps -s project && claude plugin install oaps@oaps -s project

# Clear cached OAPS plugin from Claude plugins cache
clear-plugin-cache:
  rm -rf ~/.claude/plugins/cache/oaps*

# Run command
run *args:
  "$@"

# Run Python
run-python *args:
  python "$@"

# Format code
format:
  codespell -w
  ruff format .

# Fix code issues
fix:
  ruff format .
  ruff check --fix .

# Fix code issues including unsafe fixes
fix-unsafe:
  ruff format .
  ruff check --fix --unsafe-fixes .

# Lint code
lint:
  codespell
  yamllint --strict .
  ruff check .
  basedpyright
  {{pnpm}} markdownlint-cli2 "**/*.md"

# Lint Markdown files
lint-markdown:
  {{pnpm}} markdownlint-cli2 "**/*.md"

# Lint Python code
lint-python:
  ruff check .
  ruff format --check .
  basedpyright

# Lint documentation
lint-docs:
  uv run --frozen yamllint --strict mkdocs.yml
  pnpm exec markdownlint-cli2 "docs/**/*.md"
  uv run --frozen --group docs djlint docs/.overrides
  pnpm exec biome check docs/

# Check spelling
lint-spelling:
  codespell

# Run tests (excludes slow Claude integration tests by default)
test *args:
  pytest "$@"

# Run only Claude integration tests (requires Claude CLI)
test-claude *args:
  pytest -m claude_integration "$@"

# Run all tests including Claude integration tests
test-all *args:
  pytest -m "" "$@"

# Run only failed tests from last run
test-failed *args: (test args "--lf")

# Run tests with coverage
test-coverage *args:
  pytest --cov=oaps --cov-branch --cov-report=term-missing:skip-covered --cov-report=xml --cov-report=json "$@"

# Run benchmarks
benchmark *args:
  pytest tests/benchmarks/ --benchmark-only "$@"

# Run benchmarks and save results to JSON (local development)
benchmark-save name="results":
  mkdir -p .benchmarks
  pytest tests/benchmarks/ --benchmark-only \
    --benchmark-warmup=on \
    --benchmark-warmup-iterations=1000 \
    --benchmark-min-rounds=20 \
    --benchmark-max-time=2.0 \
    --benchmark-disable-gc \
    --benchmark-json=.benchmarks/{{name}}.json

# Run benchmarks for CI (variance-resistant settings)
benchmark-ci name:
  mkdir -p .benchmarks
  pytest tests/benchmarks/ --benchmark-only \
    --benchmark-warmup=on \
    --benchmark-warmup-iterations=1000 \
    --benchmark-min-rounds=20 \
    --benchmark-max-time=2.0 \
    --benchmark-disable-gc \
    --benchmark-timer=time.process_time \
    --benchmark-json=.benchmarks/{{name}}.json

# Compare benchmarks against a baseline
benchmark-compare baseline="baseline":
  pytest tests/benchmarks/ \
    --benchmark-compare=.benchmarks/{{baseline}}.json \
    --benchmark-columns=min,max,mean,median,stddev,iqr

# Run benchmarks with comparison and fail on regression (>15% slower median)
benchmark-check baseline="baseline":
  pytest tests/benchmarks/ \
    --benchmark-compare=.benchmarks/{{baseline}}.json \
    --benchmark-compare-fail=median:15%

# Initialize mutation testing (creates worktree if needed)
mutation-init *args:
  scripts/mutation-worktree.sh init {{args}}

# Run mutation testing in worktree
mutation-run:
  scripts/mutation-worktree.sh exec

# Resume interrupted mutation run
mutation-resume:
  scripts/mutation-worktree.sh exec --resume

# Show mutation testing results (works from main dir)
mutation-results:
  cr-report session.sqlite

# Generate HTML report for mutation testing
mutation-html:
  cr-html session.sqlite > mutation-report.html

# Show worktree and session status
mutation-status:
  scripts/mutation-worktree.sh status

# Clean worktree and artifacts
mutation-clean:
  scripts/mutation-worktree.sh clean

# List surviving mutants (tests didn't catch)
mutation-survivors:
  sqlite3 -header -column session.sqlite \
    "SELECT ms.job_id, ms.operator_name, ms.occurrence, ms.start_pos_row as line, wr.diff \
     FROM mutation_specs ms \
     JOIN work_results wr ON ms.job_id = wr.job_id \
     WHERE wr.test_outcome = 'SURVIVED' \
     ORDER BY ms.start_pos_row"

# List killed mutants (tests caught)
mutation-killed:
  sqlite3 -header -column session.sqlite \
    "SELECT ms.job_id, ms.operator_name, ms.occurrence, ms.start_pos_row as line \
     FROM mutation_specs ms \
     JOIN work_results wr ON ms.job_id = wr.job_id \
     WHERE wr.test_outcome = 'KILLED' \
     ORDER BY ms.start_pos_row"

# Show mutation summary statistics
mutation-summary:
  #!/usr/bin/env bash
  echo "=== Mutation Testing Summary ==="
  sqlite3 -header -column session.sqlite \
    "SELECT test_outcome, COUNT(*) as count FROM work_results GROUP BY test_outcome ORDER BY count DESC"
  echo ""
  echo "Total mutants: $(sqlite3 session.sqlite 'SELECT COUNT(*) FROM mutation_specs')"
  echo "Completed: $(sqlite3 session.sqlite 'SELECT COUNT(*) FROM work_results')"
  echo "Survival rate: $(sqlite3 session.sqlite 'SELECT ROUND(100.0 * SUM(CASE WHEN test_outcome = '\''SURVIVED'\'' THEN 1 ELSE 0 END) / COUNT(*), 1) FROM work_results')%"

# List pending mutants (not yet tested)
mutation-pending:
  sqlite3 -header -column session.sqlite \
    "SELECT job_id, operator_name, occurrence, start_pos_row as line \
     FROM mutation_specs \
     WHERE job_id NOT IN (SELECT job_id FROM work_results) \
     ORDER BY start_pos_row"

# Show details for a specific mutant by job_id
mutation-show job_id:
  #!/usr/bin/env bash
  sqlite3 -header -column session.sqlite \
    "SELECT * FROM mutation_specs WHERE job_id = '{{job_id}}'"
  echo ""
  sqlite3 -header -column session.sqlite \
    "SELECT * FROM work_results WHERE job_id = '{{job_id}}'"

# Count survivors by operator type
mutation-survivors-by-operator:
  sqlite3 -header -column session.sqlite \
    "SELECT ms.operator_name, COUNT(*) as count \
     FROM mutation_specs ms \
     JOIN work_results wr ON ms.job_id = wr.job_id \
     WHERE wr.test_outcome = 'SURVIVED' \
     GROUP BY ms.operator_name \
     ORDER BY count DESC"

# Run pre-commit hooks on changed files
prek:
  prek

# Run pre-commit hooks on all files
prek-all:
  prek run --all-files

# Install pre-commit hooks
prek-install:
  prek install

# Convert Mermaid diagrams
mermaid *args:
  {{pnpm}} mmdc "$@"

# Update documentation examples (refresh output blocks)
update-docs *args:
  pytest tests/docexamples/ --update-examples "$@"

# Build the latest documentation
build-docs: clean
  ZENSICAL_ENV=latest uv run zensical build
  uv pip freeze > requirements.txt

# Build the documentation for PR preview
[script]
build-docs-pr number: clean
  rm -f mkdocs.pr.yml
  cat << EOF >> mkdocs.pr.yml
  INHERIT: ./mkdocs.yml
  site_name: OAPS Documentation (PR-{{number}})
  site_url: https://{{number}}-oaps-docs-pr.tbhb.workers.dev/
  EOF
  uv run --group docs zensical build
  echo "User-Agent: *\nDisallow: /" > site/robots.txt
  uv pip freeze > requirements.txt

# Deploy latest documentation
deploy-docs: build-docs
  {{pnpm}} wrangler deploy --env latest

# Deploy documentation preview
deploy-docs-pr number: (build-docs-pr number)
  {{pnpm}} wrangler versions upload --env pr --preview-alias pr-{{number}}

# Develop the documentation site locally
dev-docs:
  zensical serve --dev-addr 127.0.0.1:8000

# Serve the OAPS API server (development mode with auto-reload)
serve *args:
  fastapi dev --entrypoint oaps.server:app --port 6277 "$@"

# Sync Vale styles and dictionaries
vale-sync:
  vale sync

# === Release Management ===

# Check release readiness (lint, test, coverage)
release-check:
  #!/usr/bin/env bash
  echo "Checking release readiness..."
  just lint
  just test
  echo ""
  echo "✓ All quality gates passed!"
  echo ""
  echo "Manual checks required:"
  echo "  - [ ] CHANGELOG.md updated"
  echo "  - [ ] Version in pyproject.toml is correct"

# Build distribution packages
build: clean
  #!/usr/bin/env bash
  uv build --no-sources
  echo ""
  echo "Built packages:"
  ls -la dist/

# Build distribution packages with SBOM
build-release: clean
  #!/usr/bin/env bash
  uv build --no-sources
  cyclonedx-py environment --of json -o dist/sbom.cdx.json
  echo ""
  echo "Built packages:"
  ls -la dist/

# Generate SBOM for current environment
sbom output="sbom.cdx.json":
  cyclonedx-py environment --of json -o {{output}}

# Publish to TestPyPI (requires OIDC token in CI or UV_PUBLISH_TOKEN)
release-publish-testpypi:
  #!/usr/bin/env bash
  uv publish --publish-url https://test.pypi.org/legacy/

# Publish to PyPI (requires OIDC token in CI or UV_PUBLISH_TOKEN)
release-publish-pypi:
  #!/usr/bin/env bash
  uv publish

# Verify PyPI installation (isolated environment)
release-verify-pypi version:
  ./scripts/verify_release.py pypi {{version}}

# Verify TestPyPI installation (isolated environment)
release-verify-testpypi version:
  ./scripts/verify_release.py testpypi {{version}}

# Create GitHub release (triggers PyPI publish)
release-create version:
  @echo "Creating GitHub release v{{version}}..."
  gh release create v{{version}} \
    --title "v{{version}}" \
    --notes "See [CHANGELOG.md](https://github.com/tbhb/oaps/blob/main/CHANGELOG.md) for details."

# Create GitHub pre-release
release-create-prerelease version:
  @echo "Creating GitHub pre-release v{{version}}..."
  gh release create v{{version}} \
    --prerelease \
    --title "v{{version}}" \
    --notes "See [CHANGELOG.md](https://github.com/tbhb/oaps/blob/main/CHANGELOG.md) for details."

# Create GitHub release with generated release notes from changelog
release-create-with-notes version:
  @echo "Generating release notes for v{{version}}..."
  ./scripts/release_notes.py {{version}} --output /tmp/release-notes-{{version}}.md
  @echo ""
  @echo "Creating GitHub release v{{version}}..."
  gh release create v{{version}} \
    --title "v{{version}}" \
    --notes-file /tmp/release-notes-{{version}}.md
  @rm -f /tmp/release-notes-{{version}}.md
  @echo ""
  @echo "Release created: https://github.com/tbhb/oaps/releases/tag/v{{version}}"

# Create draft GitHub release with generated release notes
release-create-draft version:
  @echo "Generating release notes for v{{version}}..."
  ./scripts/release_notes.py {{version}} --draft --output /tmp/release-notes-{{version}}.md
  @echo ""
  @echo "Creating draft GitHub release v{{version}}..."
  gh release create v{{version}} \
    --title "v{{version}}" \
    --draft \
    --notes-file /tmp/release-notes-{{version}}.md
  @rm -f /tmp/release-notes-{{version}}.md
  @echo ""
  @echo "Draft release created: https://github.com/tbhb/oaps/releases/tag/v{{version}}"
  @echo "Edit and publish at: https://github.com/tbhb/oaps/releases"

# Generate release notes from changelog (preview only, no release)
release-notes version:
  ./scripts/release_notes.py {{version}}

# Generate release notes and save to file
release-notes-save version output="release-notes.md":
  ./scripts/release_notes.py {{version}} --output {{output}}

# Show release status
release-status:
  #!/usr/bin/env bash
  echo "Release Status: oaps"
  echo "============================"
  echo ""
  echo "Current version: $(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)"
  echo "Latest tag: $(git describe --tags --abbrev=0 2>/dev/null || echo 'none')"
  echo ""
  echo "Commits since last tag:"
  git log $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD)..HEAD --oneline 2>/dev/null | wc -l | xargs echo "  "
  echo ""
  echo "Recent workflow runs:"
  gh run list --limit 3 2>/dev/null || echo "  (gh CLI not available)"

# === Version Management ===

# Show current version
version:
  @grep '^version' pyproject.toml | head -1 | cut -d'"' -f2

# Bump version (type: major, minor, patch, dev, alpha, beta, rc, post)
version-bump type:
  ./scripts/version_bump.py {{type}}

# Bump to next major version
version-bump-major:
  just version-bump major

# Bump to next minor version
version-bump-minor:
  just version-bump minor

# Bump to next patch version
version-bump-patch:
  just version-bump patch

# Bump to next alpha pre-release
version-bump-alpha:
  just version-bump alpha

# Bump to next beta pre-release
version-bump-beta:
  just version-bump beta

# Bump to next release candidate
version-bump-rc:
  just version-bump rc

# Bump to next dev release
version-bump-dev:
  just version-bump dev

# Bump to next post release
version-bump-post:
  just version-bump post
