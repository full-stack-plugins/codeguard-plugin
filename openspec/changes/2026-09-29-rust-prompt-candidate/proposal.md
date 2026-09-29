## Why

The plugin candidate pins Rust CLI 0.1.1 and cannot route Claude Code `UserPromptSubmit` to the new bounded Rust guidance. Its default Python prompt hook still performs a potentially expensive soft gate from prompt text. The candidate needs an independently testable path that shows the correct next check without treating a user message as a commit event.

## What Changes

- Pin the verified `@partme.ai/codeguard@0.1.2` macOS arm64 artifact after registry publication and byte-identity checks.
- Extend the explicit Rust candidate dispatcher to accept `UserPromptSubmit`, preserving the existing incomplete feedback when the pinned runtime is missing or corrupt.
- Add host-protocol and offline/installed-runtime tests, then update bilingual plugin documentation and the plugin/marketplace versions.
- Keep the default Python hooks and the strict Git/CI delivery gate unchanged in this candidate change; record their remaining migration tasks explicitly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `hook-protocol`: The opt-in Rust candidate gains a non-blocking Claude Code prompt event with fixed, bounded guidance and an explicit incomplete fallback.

## Impact

`hooks/rust_runtime_dispatch.cjs`, `runtime/codeguard.lock.json`, `tests/test_rust_runtime.cjs`, `hooks/__protocol__.md`, README variants, OpenSpec acceptance evidence, plugin manifests, and marketplace metadata. The candidate uses the existing runtime manager and does not add an installation-time download.
