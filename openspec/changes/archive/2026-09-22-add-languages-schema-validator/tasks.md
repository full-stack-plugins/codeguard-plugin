## 1. Validator

- [x] 1.1 Create `scripts/validate_languages_json.py` with the 11-rule set per design.md.
- [x] 1.2 `python3 scripts/validate_languages_json.py` on current registry must exit 0 (baseline).
- [x] 1.3 Document CLI flags + exit codes in the script's top docstring.

## 2. Unit tests

- [x] 2.1 Create `tests/test_validate_languages_json.py` with the 10-test matrix per design.md.
- [x] 2.2 All tests must pass with the current registry as the baseline fixture.

## 3. CI wiring

- [x] 3.1 Edit `.github/workflows/skills-check.yml` to add two new steps (validator + unit tests) after the existing unittest discovery.

## 4. Validation

- [x] 4.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — all pass (existing + new).
- [x] 4.2 `python3 tests/run_all.py` — full 141 / 0 / 0 must hold.
- [x] 4.3 `git diff --check` — clean.
- [x] 4.4 `openspec validate --all --strict` — pass (5 pre-existing + new `languages-registry-contract`).
- [x] 4.5 `ruff check scripts/validate_languages_json.py tests/test_validate_languages_json.py` — zero new errors.

## 5. Release

- [x] 5.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.3 → 0.6.4.
- [x] 5.2 Fix in-repo `.agents/plugins/marketplace.json` ref/icon to `v0.6.4`.
- [x] 5.3 Open PR, wait for vendor-check, merge.
- [x] 5.4 Push tag `v0.6.4`.
- [x] 5.5 Sync market repo catalog + README codeguard row to `0.6.4` and push.
- [x] 5.6 `openspec archive add-languages-schema-validator` after all tasks above are checked.