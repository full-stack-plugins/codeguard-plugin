## ADDED Requirements

### Requirement: The UserPromptSubmit hook SHALL run the lint gate only when intent is commit-like
The `UserPromptSubmit` hook MUST evaluate the user's prompt for commit intent using word-boundary matching of trigger words (`commit|push|deploy|发布|部署`) and a separate action-verb check. The hook SHALL exit silently when either (a) no trigger word is present, (b) the only trigger occurrence is followed by `?`, or (c) a trigger word appears in an interrogative sentence identified by `QUESTION_MARKERS` (`?`, `？`, `么`, `吗`, `如何`, `怎么`, `有没有`, `是不是`, `什么是`, `哪些`).

#### Scenario: User asks a question containing a trigger word

- **WHEN** the user prompt is `使用过程中的情况` or `Should I commit this?` or `先读项目结构`
- **THEN** the hook exits 0 with empty stdout; no linter runs

#### Scenario: User issues a commit-like imperative

- **WHEN** the user prompt is `请帮我 commit` or `commit this now` or `请帮我 push`
- **THEN** the hook enters the gate path and invokes `run_gate()`

#### Scenario: Trigger word followed by question mark is exempt

- **WHEN** the user prompt is `commit?` or `要不要 push?` or `should I deploy?`
- **THEN** the hook exits silently regardless of other QUESTION_MARKERS content

### Requirement: The gate SHALL run only languages named in the user message when they can be identified
When the trigger fires, the hook MUST extract candidate language ids from the user prompt using case-insensitive token matching against `scripts/languages.json` ids. When the intersection is non-empty, the gate SHALL run only that subset. When the intersection is empty, the gate SHALL fall back to the existing `detect_languages()` behavior.

#### Scenario: User mentions one language explicitly

- **WHEN** the user prompt is `请帮我 commit 这次 ruff 改动`
- **THEN** the gate runs only Python; other detected languages are skipped for this invocation

#### Scenario: User mentions no language

- **WHEN** the user prompt is `请帮我 commit` with no language token
- **THEN** the gate runs every language detected by `detect_languages()` (current behavior preserved)

### Requirement: Question markers SHALL cover both Chinese and English
`QUESTION_MARKERS` MUST include the ASCII `?` in addition to the existing Chinese markers, so that an English prompt ending with `?` is recognized as a question even without other markers.

#### Scenario: ASCII question mark without any other marker

- **WHEN** the user prompt is `Should I push this?`
- **THEN** the hook exits silently because `?` is a recognized question marker
