## ADDED Requirements

### Requirement: Prompt intent filtering SHALL not depend on a host matcher

The Claude `UserPromptSubmit` registration and its mirrored host declarations MUST NOT use a text matcher. The Hook MUST accept that the host invokes it for every prompt. For a non-triggering prompt, the handler MUST return without environment probing, repository discovery, native checker execution, or conversation context output. A triggering prompt MAY use the legacy soft reminder, but its result MUST NOT replace command-time Git verification or claim delivery approval.

#### Scenario: Ordinary prompt reaches the Hook
- **WHEN** the host delivers a prompt without a CodeGuard submission intent
- **THEN** the Hook exits 0 with no check process and no injected context

#### Scenario: Commit request reaches the Hook
- **WHEN** the host delivers a commit-intent prompt
- **THEN** the existing soft reminder may run while the later real Git command remains subject to PreToolUse verification
