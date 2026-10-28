# Isolated source-built runtime candidate

This is the executable refinement of lifecycle tasks 4.2 and 4.5. The source pin is CodeGuard `cc7b907f6ba22b61bc19e5371df31d03ee72f452`, version `0.1.4`. The candidate workflow builds that exact public commit independently on Ubuntu 22.04 x64, Windows 2022 x64 and macOS 14 arm64. It does not fetch inaccessible Actions artifacts, publish packages or select a new default runtime.

The engine's existing `npm_candidate_install.mjs` first requires all 32 pinned grammar assets/licenses and a real Zig worker, then exercises temporary offline npm installation. Its receipt records the actual binary identity, archive SHA-256 and native SHA-256. The plugin harness consumes that explicit receipt and the pinned source grammar manifest. It verifies exact archive members, regular-file types, bounds, package/version/platform, native and license hashes, and the native version's source commit/protocol before execution. The test-only archive bounds are 64 MiB compressed and 256 MiB native, separate from the unchanged published manager's 16/128 MiB limits.

`hooks/rust_runtime_adapter.cjs` contains the existing bounded native invocation and response validation extracted from the canonical dispatcher. The canonical dispatcher still resolves **only** `activeBinary()` using `runtime/codeguard.lock.json`; no CLI flag or environment variable can supply a candidate binary. After separate authentication, the test harness calls this same internal transport with a temporary candidate, project and fixed example events. This is a real plugin-adapter → native-engine call, **not** a default-runtime installation or automatic Codex/Claude Hook trigger. It grants no Hook trust.

The test proves the default dispatcher remains incomplete against an empty runtime cache even while the candidate exists elsewhere, and that the production lock bytes remain unchanged. Archive corruption, unexpected/link members, changed binary/license bytes and wrong source/version/platform/protocol are rejected by the candidate contracts. The 57-language Python compatibility implementation and MCP/CLI dispatch remain unchanged; these tests do not certify all languages.

Run contracts:

```sh
python -m unittest discover -s tests -p test_candidate_runtime.py -v
node --test tests/test_rust_adapter.cjs tests/test_rust_runtime.cjs tests/test_rust_lifecycle.cjs
```

Run full assembly after checking out the exact engine pin and obtaining its real package receipt:

```sh
python tests/acceptance_candidate_runtime.py --engine-source /absolute/codeguard --package-receipt /absolute/package-receipt.json --output /absolute/plugin-candidate.json
```

For CI, `python tests/run_candidate_pipeline.py ../engine` runs the locked build, engine package acceptance, then plugin assembly. The workflow stores bounded error annotations and local evidence files; unavailable artifact downloads remain unavailable. Receipts distinguish plugin HEAD from uncommitted changes using source status and hashes, and explicitly report `default_runtime_chain_verified=false` and `actual_host_hook_triggered=false`.

Native three-platform results must be recorded after the candidate workflow reaches a terminal state. A configured matrix or local Linux pass is not Windows/macOS acceptance. The default public macOS lock and production distribution, real installed-host Hook activation and permission/trust acceptance remain separate unfinished work.
