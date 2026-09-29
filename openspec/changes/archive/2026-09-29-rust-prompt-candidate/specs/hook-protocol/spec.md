## ADDED Requirements

### Requirement: Opt-in Rust prompt feedback SHALL remain bounded and non-blocking

When the opt-in Rust candidate receives a Claude Code `UserPromptSubmit` event, it MUST return a bounded `hookSpecificOutput.additionalContext` associated with that event. The response MUST report that source checks were not run and delivery was not evaluated. It MUST NOT echo or interpret the prompt as an instruction to scan, narrow scope, bypass policy, or approve a commit. A missing, corrupt, or incompatible pinned runtime MUST return an explicit incomplete message without invoking an arbitrary executable from `PATH` or silently falling back to the legacy Python implementation.

#### Scenario: Commit wording and an ordinary question arrive
- **WHEN** valid prompt events contain either a commit request or an ordinary question
- **THEN** the candidate returns the same bounded timing guidance, does not run a checker, and exits with the soft-hook host status

#### Scenario: Pinned runtime cannot be used
- **WHEN** the exact Rust artifact is absent or fails identity verification
- **THEN** the candidate reports runtime incomplete for `UserPromptSubmit` and does not invoke another CodeGuard implementation

### Requirement: Candidate runtime pin SHALL match the published artifact

The plugin candidate MUST pin an exact published package version, source revision, package integrity, and native binary digest for the supported host. Offline installation of that package MUST verify those identities before activation. A plugin release MUST update its manifest and marketplace versions with the candidate change; this does not activate the candidate as the default Hook.

#### Scenario: Matching package is installed locally
- **WHEN** the exact package is supplied offline and all pinned identities match
- **THEN** a valid Claude prompt event reaches the bundled Rust program and returns non-blocking guidance

#### Scenario: Package or binary bytes differ
- **WHEN** the archive or active binary digest differs from the pin
- **THEN** installation or dispatch remains incomplete and no fallback checker is started
