## Correction and acceptance

- [x] 1. Add a failing test that all three `UserPromptSubmit` declarations omit matcher and a non-trigger prompt exits before environment or repository work. Red runs exposed all three matcher fields, then the premature `session_scope` call; see [acceptance](../../../tests/prompt-matcher-correction.md).
- [x] 2. Remove the unsupported matcher from the three mirrored manifests and document the actual per-prompt host invocation and in-hook filter. Ordinary prompts now exit before session/worktree scoping; legacy soft commit-intent behavior remains.
- [x] 3. Run targeted tests, the plugin protocol and unit regressions, vendor offline/online checks, OpenSpec strict validation, and source diff checks. Evidence: 144/144 protocol, 654 Python unittests, 7 README parity and 5 real-tarball Node runtime tests; Ruff, vendor, strict validation, mirrors and diff checks passed. Installed-host latency remains unverified.
- [ ] 4. Bump the plugin patch version, merge tested changes, publish the matching tag/Release, and synchronize only CodeGuard marketplace metadata while preserving unrelated user edits.
- [ ] 5. Record tag, CI, market and candidate runtime evidence; sync/archive the completed OpenSpec delta without claiming installed-host performance or a completed Rust strict gate.
