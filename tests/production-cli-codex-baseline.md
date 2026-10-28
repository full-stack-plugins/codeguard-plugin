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

## Native Windows launcher candidate (not yet Windows-accepted)

The compatibility launcher now shares `scripts/cli_entry.py` across the existing Bash entry and the Windows installation path. The command modules, default `check`, `detect` empty-path behavior, aliases, argument ordering and exit statuses remain unchanged. This is routing only; it does not replace the 57-language implementation or select a Rust runtime.

Bootstrap on Windows with `python scripts/cli_entry.py install --bin-dir C:\\path\\to\\bin`. The installer creates a regular `codeguard.cmd` file with the current absolute Python interpreter and plugin entry, so developer mode/admin symlink privileges are not required. It does not change the global PATH. Repeated installation accepts only the exact managed content; foreign, modified or linked launchers are preserved and rejected. Uninstall and dry-run retain the same ownership and no-write boundaries.

The candidate deliberately rejects non-ASCII launcher/interpreter/plugin paths and batch metacharacters (`% ! & ^`, CR/LF, quotes, redirection, pipes and parentheses), with an explicit structured error before writing. Ordinary ASCII paths with spaces are supported by the file contract. This limits exposure while Windows codepage behavior is unverified; it is not a claim of full Windows path support.

The `.cmd` launcher is for trusted interactive commands with normal shell quoting. Batch files can be parsed by Windows shells even with subprocess `shell=False`; arbitrary untrusted argument strings such as `%VARIABLE%` are not promised literal preservation through that shell. Automation needing literal arguments must launch `python scripts/cli_entry.py ...` with an argument array, not the batch file. No unchecked `%~dp0` bootstrap batch file is shipped. See Python's [subprocess security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations).

`tests/test_windows_cli_install.py` separates platform-independent file-safety simulation and real Python dispatcher routing from a Windows-only `cmd.exe` execution case (including installed paths with spaces and representative argument characters). Linux results must report the real Windows case as skipped. `.github/workflows/cli-install-candidate.yml` provides explicit branch/PR/manual Linux, Windows 2022 and macOS runner validation; it installs no engine, performs no release and does not certify every language or target architecture. Record the runner's actual machine identity and final job results before making platform claims.

## Explicit candidate assembly after the Windows engine port

The isolated candidate workflow pins engine `cc7b907f6ba22b61bc19e5371df31d03ee72f452` and exercises a source-built private package through the same internal lifecycle transport. See [the assembly contract](isolated-runtime-candidate.md). The published runtime manager/lock retain their existing platform and archive constraints. This candidate does not fix or claim the default Linux/Windows runtime distribution path, and it cannot be activated through a new environment override. Its receipt separately identifies source/bytes, direct adapter calls and unverified real-host triggering.
