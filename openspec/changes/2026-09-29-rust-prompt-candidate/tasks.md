## 1. Runtime identity

- [x] 1.1 Verify Rust 0.1.2 source commit, remote CI, npm registry tarball, package and binary SHA-256, integrity, and fresh-cache npx behavior on macOS arm64. Evidence: [candidate record](../../../tests/rust-runtime-candidate.md).
- [x] 1.2 Update the candidate runtime lock only after 1.1 and prove offline installation rejects a wrong archive or binary. Evidence: 5/5 locked runtime tests and [candidate record](../../../tests/rust-runtime-candidate.md).

## 2. Prompt event binding

- [x] 2.1 Add a failing test that the candidate dispatcher accepts Claude `UserPromptSubmit`, returns the same bounded guidance for adversarial and ordinary prompts, and never starts a checker. Evidence: TDD failure and installed-runtime comparisons in [candidate record](../../../tests/rust-runtime-candidate.md); Rust CLI fake-checker test remains the checker-execution proof.
- [x] 2.2 Route the event through the pinned Rust binary; missing runtime must report incomplete without PATH or Python fallback. Evidence: runtime tests and registry-installed candidate invocation.
- [x] 2.3 Update the canonical host protocol and bilingual README to distinguish opt-in candidate feedback from the default Python Hook and strict delivery gates.

## 3. Verification and release

- [x] 3.1 Run candidate offline and registry tests, plugin protocol tests, vendor checks, OpenSpec strict validation, and any affected regression suite; record pass, ignored, and unverified cases. Evidence: 5/5 real-tarball Node tests, 144/144 protocol tests, 653 Python unittests, offline/online vendor checks, strict validation, Node syntax and diff checks; [candidate record](../../../tests/rust-runtime-candidate.md). Actual installed Claude host and strict Git/CI gate remain unverified.
- [ ] 3.2 Bump the plugin version through the generator, publish its GitHub release, and synchronize separate marketplace metadata without overwriting unrelated user changes.
- [ ] 3.3 Verify release tag, remote CI, marketplace version, installed candidate runtime, and actual Claude event output; retain default Hook and strict-gate gaps as incomplete.
