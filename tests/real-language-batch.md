# Real checker and formatter batch

This extends the existing configuration-error, language-check and CLI fix contracts. It preserves the 57-entry registry and all existing command definitions. Historical native evidence remains valid within its recorded tool/version/platform scope; current candidate tests do not erase it or automatically revalidate it.

`acceptance_language_batch.py` uses preinstalled Ruff 0.16.8 and `cargo fmt`/rustfmt in dependency-free temporary Git projects. It installs no tools, invokes no simulated checker and performs no network fetch. Run with the plugin's Python environment and the real tools on PATH:

```sh
python tests/acceptance_language_batch.py --plugin . --output /absolute/path/language-batch.json
```

The receipt records the checked-out commit, dirty source status, relevant source hashes, exact tool versions, command results and before/after source hashes. A dirty-tree receipt is not an immutable-commit result.

- Python: valid and invalid lint input, read-only checking, dry-run, real configured autofix, second-run byte idempotence, invalid checker configuration, recovery and an expired execution budget. The timeout uses a real Ruff process and fresh temporary source files with a deliberately zero budget; it is not a throughput benchmark or proof of ordinary project latency.
- Rust: real formatting violation, configured `cargo fmt` changes, a read-only format recheck, second-run byte idempotence, invalid Cargo configuration, invalid source syntax and recovery. This is not a Clippy lint result.
- Python's registered `format` command is `ruff check --fix`, a lint autofix operation. It is not the independent `ruff format` style formatter. No such command is silently substituted.

The existing CLI candidate workflow adds Linux x64 Python 3.10/3.12 jobs using the existing requirements and pinned Ruff baseline. The job verifies actual tool availability, runs real Ruff configuration regressions and this batch, and saves bounded diagnostics plus the receipt. Windows/macOS launcher checks remain separate; their success does not imply language-tool acceptance on those platforms.

## Configuration defect found by the batch

Matching only the literal text `[tool.ruff]` ignored valid nested/inline/quoted TOML declarations, treated commented declarations as real configuration, and could mask malformed or unreadable project configuration with the plugin defaults. The corrected discovery uses TOML structure. Native Ruff handles malformed/invalid project files and returns an error instead of a fabricated PASS.

Python 3.11+ uses `tomllib`; Python 3.10 uses the conditional `tomli==2.2.1` requirement. When neither parser is available, configuration is explicitly UNVERIFIED at check, fix, gate and save boundaries. The plugin does not silently switch to a weaker rule set, execute an unverified formatter or record completed work. Existing non-blocking Hook semantics are retained; this is not remote merge enforcement.

`test_ruff_project_config.py` separates real Ruff cases from parser-unavailability fault injection. Dependency architecture checks retain their original layer restrictions: invalid execution-plan values are handled at the existing plan boundary, and the earlier thin CLI dispatcher is explicitly classified as an entry point. No general dependency allowlist or unknown-script rejection rule is weakened.

The complete cloud audit (`language-audit-57-20261028.json` and `.md`) records 12 registry entries with historical native partial evidence, including lint, compiler syntax and read-only formatter probes. These categories are not equivalent to full registered lint/format acceptance. The remaining entries retain their registered, candidate-WASM, controlled-test, missing-tool or planned distinctions.
