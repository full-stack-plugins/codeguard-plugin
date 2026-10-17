## 1. Runtime identity and safety

- [x] 1.1 Record the published 0.1.3 archive, source, binary, manifest license identities and platform in the candidate lock; confirm registry and local hashes match.
- [x] 1.2 Write failing tests for the 0.1.3 archive rejection and license mutation, then extend exact members, measured size limits and active-file verification without weakening digest checks.

## 2. Candidate execution

- [x] 2.1 From the installed candidate run `grammar status` and a real Zig WASM probe; verify 32 candidates, zero qualified grammars, exit 3 and non-blocking feedback.
- [ ] 2.2 Verify offline and registry installation, wrong archive/binary/license rejection, platform fallback and the existing Claude candidate event behavior.

## 3. Documentation and release

- [x] 3.1 Update bilingual README and acceptance evidence; distinguish callable candidate assets from default Hook and automatic conversation integration.
- [ ] 3.2 Run OpenSpec strict validation, Node/Python regressions, vendor checks, manifest/parity checks and remote CI.
- [ ] 3.3 Bump/publish the plugin version through the generator, synchronize marketplace metadata, and verify GitHub release/tag plus clean local/remote heads.
