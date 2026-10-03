## ADDED Requirements

### Requirement: Opt-in Rust runtime SHALL verify the complete pinned WASM package

The explicit candidate runtime MUST accept only the published platform-specific archive whose version, source commit, SHA-256, SHA-512 integrity and native binary digest match the lock. It MUST validate a bounded archive of exactly the declared regular members, including every pinned grammar license, before activation. It MUST verify the binary and license contents after extraction and when selecting an active runtime. Package or file changes MUST produce incomplete feedback without selecting a binary from `PATH` or silently falling back to Python. Expanded byte ceilings MUST remain finite and justified by the measured artifact.

#### Scenario: The complete 32-grammar package is installed
- **WHEN** the exact 0.1.3 macOS arm64 tarball is installed offline or downloaded from the pinned registry URL
- **THEN** the content-addressed candidate activates, `grammar status` reports 32 candidates and zero qualified grammars, and a real WASM probe remains incomplete rather than approving lint or delivery
- **AND** explicit `exec check all ABS_PROJECT` preserves native-first ordering and returns bounded candidate observations without converting them into a pass

#### Scenario: A package or active file is altered
- **WHEN** an archive member, binary or license differs from the locked identity, or an extra/non-regular member is present
- **THEN** installation or candidate use reports incomplete and does not activate or execute the changed package

#### Scenario: The host has no candidate package or uses another platform
- **WHEN** the pinned runtime is absent or the host is not macOS arm64
- **THEN** the opt-in Hook returns bounded incomplete feedback without running another CodeGuard implementation
