## 1. New files

- [x] 1.1 Create `scripts/paths.py` with `ensure_user_path(from_login_shell=False)` plus its internal static-dir and node-availability helpers, copied verbatim from `scripts/detect_lang.py`.
- [x] 1.2 Create `scripts/user_config.py` with `load_user_config`, `load_project_overrides`, `get_overrides`, copied verbatim from `scripts/detect_lang.py`.

## 2. detect_lang.py refactor

- [x] 2.1 Delete the implementation bodies of `ensure_user_path` and configuration helpers from `scripts/detect_lang.py`.
- [x] 2.2 Replace them with re-exports (`from paths import ensure_user_path`, `from user_config import load_user_config, load_project_overrides, get_overrides`) and add `__all__` enumerating all externally imported symbols (existing + new re-exports).

## 3. Hooks annotation

- [x] 3.1 In each of `hooks/env_check.py`, `hooks/pre_tool_git_guard.py`, `hooks/post_tool_lint.py`, `hooks/user_prompt_validator.py`, append an inline comment to the existing `from detect_lang import ...` line noting the source file (`paths.py` or `user_config.py`).

## 4. Validation

- [x] 4.1 Run `python3 tests/run_all.py` — all hook simulation, language-registry, unit, CVE, edges, and field-regression subsets must pass.
- [x] 4.2 Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` — `test_plugin_manifests.py` and `test_skill_vendor.py` must pass (pre-existing baseline).
- [x] 4.3 Run `git diff --check` — must be clean.
- [x] 4.4 Run `openspec validate --all --strict` — must pass (3 pre-existing specs + new `language-gate-commands`).
- [x] 4.5 Run `ruff check scripts/paths.py scripts/user_config.py scripts/detect_lang.py hooks/` — zero lint issues.

## 5. Graph evidence

- [x] 5.1 Rebuild `code-review-graph` and verify the cross-community edge count between `hooks-gate` and `scripts-scan` drops to ≤4 (was 19).

## 6. Release

- [x] 6.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.0 → 0.6.1.
- [x] 6.2 Commit plugin repo change, push `main` + tag `v0.6.1`.
- [x] 6.3 In `full-stack-plugins` market repo, sync catalog `codeguard` to `0.6.1` and regenerate three marketplace manifests; commit and push.
- [x] 6.4 `openspec archive add-detect-lang-splits` after all tasks above are checked.