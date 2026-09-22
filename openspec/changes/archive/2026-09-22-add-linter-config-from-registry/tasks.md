## 1. Registry migration

- [x] 1.1 In `scripts/languages.json`, add `"linter_config_files": [".pre-commit-config.yaml", "checkstyle.xml", "pmd.xml"]` to the `java` entry.
- [x] 1.2 Same for `rust`, `typescript`, `python` (copy from current `hooks/env_check.py::LINTER_CONFIG_FILES`).
- [x] 1.3 All other language entries already default to `[]` via validation; explicitly verify no regression.

## 2. env_check refactor

- [x] 2.1 In `hooks/env_check.py`, delete the `LINTER_CONFIG_FILES` constant (lines 23-30).
- [x] 2.2 Add `REGISTRY` to the `from detect_lang import ...` block.
- [x] 2.3 Rewrite `detect_linter_config` to iterate over `REGISTRY.items()` and read each entry's `linter_config_files`.
- [x] 2.4 Verify `python3 tests/run_all.py` env_check subset passes (still 5/5 of the existing checks).

## 3. Validator rule

- [x] 3.1 Add `_check_linter_config_files` to `scripts/validate_languages_json.py` and wire it into `check()`.
- [x] 3.2 Add 2 unittest cases to `tests/test_validate_languages_json.py`:
  - `test_linter_config_files_must_be_list_of_str`
  - `test_linter_config_files_can_be_empty`

## 4. Validation

- [x] 4.1 `python3 scripts/validate_languages_json.py` — exit 0.
- [x] 4.2 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — pass.
- [x] 4.3 `python3 tests/run_all.py` — 141 / 0 / 0.
- [x] 4.4 `git diff --check` — clean.
- [x] 4.5 `openspec validate --all --strict` — pass.

## 5. Release

- [x] 5.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.4 → 0.6.5.
- [x] 5.2 Fix in-repo `.agents/plugins/marketplace.json` ref/icon to `v0.6.5`.
- [x] 5.3 Open PR, wait for vendor-check, merge.
- [x] 5.4 Tag v0.6.5 (use the `--force-with-lease` workflow if origin tag v0.6.4 is stale).
- [x] 5.5 Sync market repo catalog + README codeguard row to `0.6.5` and push.
- [x] 5.6 `openspec archive add-linter-config-from-registry`.