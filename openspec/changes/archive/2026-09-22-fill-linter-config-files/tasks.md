## 1. Data fill

- [x] 1.1 Apply the conservative per-language map from design.md to `scripts/languages.json` (~30 stable/beta entries).
- [x] 1.2 `python3 scripts/validate_languages_json.py` — exit 0 (type rule covers the new values).

## 2. Coverage guard test

- [x] 2.1 Add `test_linter_config_files_coverage` (≥25 stable/beta with non-empty list) to `tests/test_validate_languages_json.py`.

## 3. Validation

- [x] 3.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — all pass.
- [x] 3.2 `python3 tests/run_all.py` — 141 / 0 / 0.
- [x] 3.3 `git diff --check` — clean; `openspec validate --all --strict` — pass.

## 4. Release

- [x] 4.1 bump patch → 0.6.8; in-repo marketplace pins → v0.6.8; feat PR → merge; release PR → merge; tag v0.6.8; market repo catalog + README row → 0.6.8.
- [x] 4.2 `openspec archive fill-linter-config-files`.