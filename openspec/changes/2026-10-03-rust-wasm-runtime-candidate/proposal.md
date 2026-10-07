## Why

The explicit Rust candidate runtime still pins npm 0.1.2, which has no bundled WASM. The published 0.1.3 package contains all 32 pinned grammar candidates, but the plugin rejects its 38 archive members, 12.1 MB tarball and 100.1 MB binary. Merely changing the lock would leave the candidate unusable.

## What Changes

- Pin the registry-verified 0.1.3 macOS arm64 package, source commit, integrity and binary digest.
- Accept exactly the pinned package members and verify every bundled upstream license digest before activation and on candidate use. Raise bounded package and binary limits to accommodate this measured artifact without accepting arbitrary archive members.
- Exercise offline and registry installation, candidate `grammar status` and a real WASM probe from the installed binary, plus archive/license mutation failures.
- Update bilingual candidate documentation, then bump and publish the plugin and marketplace versions under this repository's release rules.

## Capabilities

### Modified Capabilities

- `hook-protocol`: the opt-in Rust candidate can install the published 32-grammar package while preserving exact artifact verification and incomplete semantics.

## Impact

`runtime/codeguard_runtime.cjs`, its lock and tests, bilingual README, candidate acceptance evidence, OpenSpec, plugin manifests and marketplace metadata. The default Python Hook, strict delivery gate and automatic WASM conversation feedback are separate work.
