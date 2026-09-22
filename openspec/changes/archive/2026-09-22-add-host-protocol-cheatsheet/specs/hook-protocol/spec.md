## ADDED Requirements

### Requirement: Hook-host contract SHALL live in hooks/__protocol__.md

The canonical description of how codeguard-plugin hooks communicate with Codex CLI, ZCode, and Kimi Code (exit codes, JSON output formats, fail-open convention, three-host compatibility) SHALL live in `hooks/__protocol__.md`. No hook script or docstring SHALL contradict it; any change to exit codes or JSON schema SHALL update the document in the same commit.

#### Scenario: A future hook author consults the single source

- **WHEN** an agent (human or AI) adds a new hook to `hooks/`
- **THEN** the README and `hooks/__protocol__.md` together are sufficient to design exit codes and JSON shape without further questions

#### Scenario: A hook script's docstring contradicts the cheat-sheet

- **WHEN** a reviewer or `git diff` notices a contradiction between a hook's docstring and `hooks/__protocol__.md`
- **THEN** the implementer updates whichever side is out of date so the document and implementation match in the merged commit

### Requirement: tests/run_all.py SHALL reference the cheat-sheet

The top-of-file docstring of `tests/run_all.py` SHALL contain a one-line reference to `hooks/__protocol__.md` describing its role as the canonical contract source for the host-protocol e2e suite.

#### Scenario: A new contributor opens run_all.py to add a hook subset

- **WHEN** the contributor reads the docstring
- **THEN** the reference to `hooks/__protocol__.md` is visible and points them at the single source for protocol questions

### Requirement: The cheat-sheet SHALL document fail-open for uncaught exceptions

`hooks/__protocol__.md` SHALL include a section explaining the fail-open convention: any uncaught exception inside a hook logs to stderr and exits 0, so a hook bug never blocks the host CLI workflow. This documents the existing behavior in `env_check.py`, `post_tool_lint.py`, `pre_tool_git_guard.py`, `user_prompt_validator.py`, and `stop_summary.py`.

#### Scenario: A hook hits an unexpected exception

- **WHEN** an uncaught `Exception` propagates to the top of a hook
- **THEN** the hook prints the traceback tail to stderr and exits 0; the host CLI receives no block signal and continues its workflow