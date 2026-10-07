## ADDED Requirements

### Requirement: Canonical non-blocking lifecycle hooks SHALL use the pinned Rust runtime

Canonical `hooks/hooks.json` SHALL route SessionStart, UserPromptSubmit, successful and failed file edits, and Stop to the verified `@partme.ai/codeguard@0.1.4` binary through a thin Node host binding. Native lint SHALL precede bounded WASM where the existing adapter supports it. Ordinary events MUST NOT download tools, apply source fixes, self-approve tasks, or claim complete delivery. The existing Git PreToolUse gate SHALL remain active until its Rust replacement is accepted.

#### Scenario: Edited file produces a suspected syntax observation
- **WHEN** the locked runtime is installed, the workspace initialized and a confirmed edited file has recovery nodes
- **THEN** the default entry returns a bounded summary with a real stable native-confirmation task and recheck guidance
- **AND** repeated events update the same task and later WASM clean does not close it

#### Scenario: Runtime or platform unavailable
- **WHEN** the pinned runtime cannot be verified or the platform is unsupported
- **THEN** the ordinary Hook exits 0 with explicit incomplete and setup guidance, without executing PATH codeguard, falling back to Python or downloading a package

#### Scenario: Prompt, failed edit or Stop reentry
- **WHEN** a prompt mentions commit, an edit fails or Stop is reentered
- **THEN** it does not run project-wide lint, infer approval from prompt text, scan failed edit source or repeatedly block Stop

### Requirement: Plugin repair instructions SHALL be executable through the same pinned runtime

The runtime manager SHALL permit explicit init, next, task show and task verify requests with an absolute project root, retaining Rust argument validation and ordinary incomplete semantics. It MUST NOT add local approval flags or allow arbitrary command execution.

#### Scenario: Agent follows a native-confirmation task
- **WHEN** the agent calls task show or task verify via the manager with the reported ID and project root
- **THEN** the same locked program returns existing task evidence and native recheck feedback
- **AND** native zero diagnostics without trusted policy does not turn the task into resolved or grant delivery allow
