# CLI / Codex production baseline — 2026-10-28

This refines `2026-10-04-rust-lifecycle-default` tasks 2.4 and 3.2–3.3. The confirmed target is Windows x64, macOS arm64 and Linux x64 with CLI and Codex. It does not reopen cross-Guard plans or replace any of the 57 registered language adapters, formatting rules or existing commands.

## Source and installed-product boundaries

- Plugin baseline: `597ae68` (including the two local launcher/argument fixes and portable manifest correction), version 0.21.2. These local fixes are not a new published release.
- The existing CLI `bin/codeguard` uses Bash and Python. Its installation contract has been exercised only on this Linux x64 host. A native Windows launcher/installation is not demonstrated by Bash tests.
- Portable MCP launches `python -X utf8 ./scripts/run_check.py --mcp`. This is the preserved Python compatibility service, not the Rust runtime manager.
- Default lifecycle Hooks use `runtime/codeguard.lock.json`, which pins published `@partme.ai/codeguard@0.1.4`, source `1cd458f6e01a44a74388243e964e3f45290ac18e`, and macOS arm64. The default lock remains unchanged.
- A Linux source build/private npm candidate is a distinct artifact. It cannot be inserted into the public macOS lock or counted as an installed default plugin merely because its CLI runs.
- Runtime distribution still hardcodes the macOS package OS/CPU, and its platform identifier for Linux is `linux_x64` whereas the engine uses `linux_x86_64`. Windows additionally needs an executable filename/archive-tool/launcher contract. These are explicit distribution gaps, not verified support.

## Available environment and evidence limits

The cloud host is Linux x86_64, with Node, Python and the MCP Python SDK. Ruff and ShellCheck are absent at baseline. Codex reports `0.159.0-alpha.3`; querying help/version succeeds with a warning that its PATH alias directory is read-only. This is not proof that the plugin is installed or that real Codex tool invocation has succeeded. Do not change global credentials or settings to manufacture host acceptance.

Existing local tests establish launcher symlink resolution, space/relative-path handling, dry-run safety and malformed-argument rejection. The compatibility manifest tests are separate from portable schema validation. The macOS runtime integration test requires `CODEGUARD_TEST_TARBALL` and a macOS arm64 host; a Linux skip is not a pass for that artifact.

Record direct CLI/MCP/Hook evidence separately from actual Codex discovery and agent execution. Missing checkers, unsupported platforms and unavailable trusted artifacts must stay UNVERIFIED/incomplete. A non-blocking Hook exit 0 is not a successful source check or delivery gate.

## Executed Linux compatibility acceptance

`tests/acceptance_cli_mcp.py` is an explicit, bounded acceptance runner, not a mock or a replacement for host acceptance. It requires the real MCP SDK plus Ruff from `requirements-dev.txt`; this run installed Ruff 0.16.8 in an isolated validation environment. Run it with `python tests/acceptance_cli_mcp.py --output /absolute/evidence.json`.

The run installed the launcher into a temporary directory, ran real Ruff through the installed CLI (unused import: exit 2; repaired file: exit 0), then used the root MCP manifest and a real stdio SDK client to discover and call the compatibility service. MCP reported all 57 registered languages, returned FAIL with an F401 log, rejected a malformed project configuration as UNVERIFIED, and recovered in the same session after the configuration/source were corrected. Source checks did not modify the source file.

Only Python was exercised with a real checker in this run. The evidence includes each of the 57 language IDs and a `current_run` field: `real_ruff_cli_and_mcp` for Python, `not_exercised` for the other 56. Registration and preservation are not full language acceptance; no existing capability is removed or downgraded by this evidence matrix.

The same runner invoked the default SessionStart Hook on Linux. It returned non-blocking exit 0 with `platform_unsupported` and explicitly stated that no source check ran. No runtime cache was created. The macOS public runtime lock was not changed and no executable was substituted through PATH.

Cloud evidence is stored separately at `/workspace/guard-update-20261028/codeguard-production-cli-mcp.json` and the matching `.log`; these are run artifacts, not portable repository paths. The JSON explicitly records `host_acceptance=false` and `rust_plugin_execution=false`. This establishes the Python compatibility chain and honest unsupported-platform behavior only. Windows/macOS execution, actual Codex invocation and the default plugin-to-Linux-Rust chain remain unaccepted here.
