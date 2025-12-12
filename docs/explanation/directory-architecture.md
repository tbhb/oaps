# OAPS directory architecture

This document describes the architecture of the `.oaps` directory system, its relationship with Claude Code, and how it integrates with git worktrees.

## Overview

OAPS (Overengineered Agentic Project System) provides project planning and execution tooling designed to integrate with Claude Code. The system centers around a `.oaps` directory at the project root that stores planning artifacts, session state, and Claude Code configuration.

Key design principles:

- **Separation of concerns**: The `.oaps` directory is its own git repository, versioned independently from the main project
- **Zero awareness**: The main project repository has no knowledge of `.oaps` (no submodules, no gitconfig references)
- **Worktree support**: Full support for git worktrees with both shared and isolated `.oaps` configurations
- **Dynamic orientation**: CLI commands and hooks can reliably find the `.oaps` directory from any context

## Directory Structure

### Main Project Layout

```text
project-root/
├── .git/                         # Main project repository
├── .gitignore                    # Includes .oaps/, .claude
├── .claude -> .oaps/claude       # Symlink (ephemeral, created at bootstrap)
├── .oaps/                        # Planning artifacts (separate git repo)
│   ├── .git/                     # .oaps is its own repository
│   ├── .gitignore                # Ignores ephemeral directories
│   ├── claude/                   # Claude Code configuration (versioned)
│   │   ├── commands/             # Slash commands
│   │   ├── settings.json         # Project settings
│   │   └── ...
│   ├── sessions/                 # Session-specific state (gitignored)
│   │   ├── .gitkeep
│   │   └── <session-id>/
│   │       ├── context.json
│   │       └── tasks.json
│   ├── logs/                     # Session logs (gitignored)
│   │   └── .gitkeep
│   └── tasks/                    # Task definitions (versioned)
├── .worktrees/                   # Git worktrees directory
│   └── <worktree-name>/
└── src/
```

**Ephemeral vs versioned content in `.oaps`:**

| Directory   | Versioned | Notes                                           |
| ----------- | --------- | ----------------------------------------------- |
| `claude/`   | Yes       | Claude Code configuration                       |
| `tasks/`    | Yes       | Task definitions                                |
| `sessions/` | No        | Session state, cleaned up via exit hooks or CLI |
| `logs/`     | No        | Session logs, cleaned up via policy             |

Gitignored directories use `.gitkeep` files to maintain structure in fresh clones.

### Worktree Layouts

Worktrees can have two configurations for `.oaps`:

**Shared (default)**: `.oaps` is symlinked to the main project's `.oaps`

```text
.worktrees/feature-a/
├── .git                          # File pointing to main .git/worktrees/...
├── .claude -> .oaps/claude       # Symlink (ephemeral)
├── .oaps -> ../../.oaps          # Symlink to shared .oaps
└── src/
```

**Isolated (opt-in)**: `.oaps` is a git worktree of the main `.oaps` repository. This is useful for testing changes to planning artifacts or Claude configuration without affecting other worktrees.

```text
.worktrees/experimental/
├── .git                          # File pointing to main .git/worktrees/...
├── .claude -> .oaps/claude       # Symlink (ephemeral)
├── .oaps/                        # Worktree of project-root/.oaps
│   ├── .git                      # File pointing to ../../.oaps/.git/worktrees/...
│   └── claude/                   # Isolated config for testing
└── src/
```

Isolated worktrees are explicitly opt-in and intended for development/testing of OAPS itself or Claude configuration changes.

## Path Resolution

All CLI commands and hooks need to reliably find the worktree root and `.oaps` directory.

### Finding the Worktree Root

Use `git rev-parse --show-toplevel` to find the current worktree root:

```python
import subprocess
from pathlib import Path


def get_worktree_root() -> Path:
    """Get the root of the current worktree (or main checkout)."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())
```

This works correctly whether you're in:

- The main project checkout
- A git worktree
- Any subdirectory of either

### Finding the .oaps Directory

Since `.oaps` is present (either directly or via symlink) in every worktree:

```python
def get_oaps_dir() -> Path:
    """Get the .oaps directory for the current worktree."""
    return get_worktree_root() / ".oaps"
```

### Shell Hooks

For shell hooks that only have `$PWD`:

```bash
WORKTREE_ROOT="$(git rev-parse --show-toplevel)"
OAPS_DIR="$WORKTREE_ROOT/.oaps"
```

### Session-Specific Paths

When `CLAUDE_SESSION_ID` is available (injected via SessionStart hook):

```python
def get_session_dir() -> Path:
    """Get the session-specific directory."""
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        raise RuntimeError("CLAUDE_SESSION_ID not set")
    return get_oaps_dir() / "sessions" / session_id
```

### Checking .oaps Mode

To determine if `.oaps` is shared or isolated:

```python
def is_oaps_shared() -> bool:
    """Check if .oaps is a symlink (shared) or directory (isolated)."""
    oaps = get_worktree_root() / ".oaps"
    return oaps.is_symlink()
```

## Claude Code Integration

### Transcript and History Files

Claude Code stores session data in two places:

| File Type             | Location                                               | Contents                                                               |
| --------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------- |
| **Transcript**        | `~/.claude/projects/<encoded-path>/<session-id>.jsonl` | Complete conversation record (messages, tool calls, results, thinking) |
| **History**           | `~/.claude/history.jsonl`                              | User prompts only (like shell history)                                 |
| **Agent transcripts** | `~/.claude/projects/<encoded-path>/agent-<id>.jsonl`   | Subagent conversations (Task tool)                                     |

### Environment Variables

Claude Code sets these environment variables:

| Variable                 | Description                              |
| ------------------------ | ---------------------------------------- |
| `CLAUDECODE`             | Set to `1` when running in Claude Code   |
| `CLAUDE_SESSION_ID`      | Unique session identifier                |
| `CLAUDE_TRANSCRIPT_PATH` | Path to the current session's transcript |

Additional variables can be injected via the SessionStart hook.

### Hook Integration

The `oaps` CLI provides hook handlers that Claude Code calls:

```python
# src/oaps/_commands/_hook/_run.py
# Handles SessionStart, UserPromptSubmit, etc.
```

Hooks can:

- Inject environment variables (like `CLAUDE_SESSION_ID` into Bash calls)
- Provide additional context to the session
- Validate or modify tool calls

## CLI Commands

### Bootstrapping

**New project initialization:**

```bash
oaps init
```

- Creates `.oaps/` as a new git repository
- Creates `.oaps/claude/` directory structure with default configuration
- Creates ephemeral directories with `.gitkeep` files
- Creates `.claude -> .oaps/claude` symlink
- Adds `.oaps/` and `.claude` to main project's `.gitignore`

**Existing project setup (after cloning):**

```bash
oaps bootstrap [<oaps-remote-url>]
```

- Clones the `.oaps` repository into place
- Creates `.claude -> .oaps/claude` symlink
- Creates ephemeral directories if missing

If `<oaps-remote-url>` is omitted, the command tries a convention-based URL: `<main-repo-url>.oaps`. For example, if the main repo is `git@github.com:org/project.git`, it tries `git@github.com:org/project.oaps.git`.

**Sharing the `.oaps` repository URL:**

The main project has zero awareness of `.oaps`, so sharing the URL is flexible:

- **Open source projects**: May choose not to publish the `.oaps` repo at all (maintainer-only)
- **Team projects**: Document the URL in the main repo's README or contributing guide
- **Convention**: Use `<main-repo>.oaps` naming for easy discovery

### Worktree Management

**Create a worktree with shared .oaps:**

```bash
oaps worktree add <name> [<branch>]
```

- Creates git worktree at `.worktrees/<name>/`
- Symlinks `.oaps -> ../../.oaps`
- Symlinks `.claude -> .oaps/claude`

**Create a worktree with isolated .oaps:**

```bash
oaps worktree add <name> --isolated [<oaps-branch>]
```

- Creates git worktree at `.worktrees/<name>/`
- Creates `.oaps` as a worktree of the main `.oaps` repository
- Symlinks `.claude -> .oaps/claude`
- Useful for testing changes to planning artifacts or Claude configuration

**Remove a worktree:**

```bash
oaps worktree remove <name>
```

- Removes the git worktree
- Cleans up `.oaps` worktree if isolated
- Removes the directory

**List worktrees:**

```bash
oaps worktree list
```

- Shows all worktrees
- Indicates `.oaps` mode (shared/isolated) for each

### Isolated Worktree Management

When working with isolated `.oaps` worktrees, additional commands help manage the lifecycle:

**Merge isolated changes back to main:**

```bash
oaps worktree merge <name>
```

- Merges the isolated `.oaps` worktree branch back into `.oaps` main
- Useful after testing configuration changes

**Convert isolated to shared:**

```bash
oaps worktree share <name>
```

- Removes the isolated `.oaps` worktree
- Replaces it with a symlink to the main `.oaps`
- Typically used after merging changes

**Convert shared to isolated:**

```bash
oaps worktree isolate <name> [<oaps-branch>]
```

- Replaces the `.oaps` symlink with a worktree
- Optionally creates a new branch in `.oaps` for the isolated work

### Cleanup

Ephemeral directories (sessions, logs) accumulate over time and need cleanup.

**Exit hooks**: CLI commands that write to ephemeral directories can register exit hooks to clean up based on policy (e.g., delete session data after N days).

**Manual cleanup:**

```bash
oaps cleanup sessions [--older-than <duration>]
oaps cleanup logs [--older-than <duration>]
oaps cleanup all [--older-than <duration>]
```

### Diagnostics

**Show current context:**

```bash
oaps status
```

- Current worktree root
- `.oaps` mode (shared/isolated)
- Active session ID (if in Claude Code)

**Verify and fix structure:**

```bash
oaps doctor
```

- Verifies symlinks are correct
- Checks `.oaps` repository health
- Offers to fix common issues

## Configuration

OAPS uses a layered configuration system with settings files at multiple levels.

### Configuration Files

| File              | Location                       | Versioned | Scope                          |
| ----------------- | ------------------------------ | --------- | ------------------------------ |
| **User**          | `~/.local/oaps/settings.json`  | No        | All projects for this user     |
| **Project**       | `.oaps/settings.json`          | Yes       | Shared project settings        |
| **Project Local** | `.oaps/settings.local.json`    | No        | Local overrides (gitignored)   |
| **Worktree**      | `.oaps/settings.worktree.json` | No        | Worktree-specific (gitignored) |

Platform-specific user config locations:

- **Linux**: `~/.local/oaps/settings.json`
- **macOS**: `~/Library/Application Support/oaps/settings.json`
- **Windows**: `%APPDATA%\oaps\settings.json`

### Configuration Hierarchy

Settings are merged in order (later overrides earlier):

```text
User → Project → Project Local → Worktree
```

### Worktree Configuration Behavior

When a worktree is created:

- **Shared worktree**: `settings.local.json` is symlinked from `<project-root>/.oaps/settings.local.json` (if it exists)
- **Isolated worktree**: No symlink — the isolated `.oaps` has its own independent `settings.local.json`
- **Worktree-specific**: Each worktree can have its own `settings.worktree.json` for worktree-only settings

```text
# Shared worktree
.worktrees/feature-a/.oaps/
├── settings.json              # Via symlink to main .oaps
├── settings.local.json -> ../../../.oaps/settings.local.json
└── settings.worktree.json     # Worktree-specific (if needed)

# Isolated worktree
.worktrees/experimental/.oaps/
├── settings.json              # From isolated .oaps branch
├── settings.local.json        # Independent (not symlinked)
└── settings.worktree.json     # Worktree-specific (if needed)
```

### Setting Scopes

Some settings only make sense at certain levels:

| Setting Type               | User | Project | Local | Worktree |
| -------------------------- | ---- | ------- | ----- | -------- |
| Default `.oaps` remote URL | ✓    |         |       |          |
| Cleanup retention policy   | ✓    | ✓       | ✓     |          |
| Task definitions           |      | ✓       |       |          |
| API keys / secrets         |      |         | ✓     | ✓        |
| Debug flags                | ✓    | ✓       | ✓     | ✓        |

### Initialization

Running `oaps init` creates:

```text
.oaps/
├── .git/
├── .gitignore           # Includes settings.local.json, settings.worktree.json
├── settings.json        # Empty/default project settings
├── claude/
│   └── ...
├── sessions/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
└── tasks/
```

## Session Management

Sessions are identified by `CLAUDE_SESSION_ID` and can store state in:

```text
.oaps/sessions/<session-id>/
├── context.json      # Session context
├── tasks.json        # Active tasks
└── ...
```

CLI commands like `oaps orient task` can read this state to provide context to agents and slash commands.

## CI Integration

OAPS works in CI environments like GitHub Actions with [Claude Code's GitHub Actions integration](https://code.claude.com/docs/en/github-actions).

**Example workflow:**

```yaml
jobs:
  claude:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main project
        uses: actions/checkout@v4

      - name: Checkout .oaps repository
        uses: actions/checkout@v4
        with:
          repository: org/project.oaps
          path: .oaps
          token: ${{ secrets.OAPS_REPO_TOKEN }}

      - name: Bootstrap OAPS
        run: oaps bootstrap --local  # Use already-cloned .oaps

      - name: Run Claude Code
        uses: anthropics/claude-code-action@v1
        with:
          # ... configuration
```

The flow mirrors local development:

1. Checkout the main project
1. Checkout the `.oaps` repository (may require separate credentials)
1. Run `oaps bootstrap --local` to set up symlinks without cloning
1. Claude Code finds `.claude/` via the symlink and operates normally

## Design Decisions

### Why a Separate Repository?

- **Independent versioning**: Planning artifacts evolve differently than code
- **Access control**: `.oaps` repo can have different permissions
- **Clean history**: Main repo history isn't polluted with planning changes
- **Flexibility**: Can be private even if main repo is public

### Why Symlink .claude?

- Claude Code expects `.claude/` at the repository root
- Keeping actual config in `.oaps/claude/` allows versioning with planning artifacts
- Symlink provides compatibility without duplication

### Why is .claude Ephemeral (Not Checked In)?

- The `.claude` symlink is created at bootstrap time, not stored in either repo
- Both `.oaps/` and `.claude` are in the main project's `.gitignore`
- This maintains the "zero awareness" principle — the main repo truly has no knowledge of OAPS
- The symlink is trivial to recreate (`ln -s .oaps/claude .claude`)

### Why Support Isolated .oaps in Worktrees?

- Testing changes to Claude configuration without affecting other worktrees
- Experimenting with new slash commands or settings
- Developing new planning workflows in isolation
- Testing OAPS CLI changes themselves

### Why Exit Hook Cleanup?

- Session data can accumulate quickly with active use
- Exit hooks allow cleanup policies to run automatically
- Projects can define their own retention policies
- Manual cleanup commands provide flexibility for different workflows
