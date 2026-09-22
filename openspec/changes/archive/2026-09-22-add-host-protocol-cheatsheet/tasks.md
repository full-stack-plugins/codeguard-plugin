## 1. Document

- [ ] 1.1 Create `hooks/__protocol__.md` with the 6 sections (protocol table / three-host compatibility / fail-open / new-hook checklist / change policy / spec mapping).
- [ ] 1.2 Verify every documented exit code / JSON schema matches the actual implementation in `hooks/*.py` (post_tool_lint.py:226 etc.) — record the matching line numbers.

## 2. tests/run_all.py annotation

- [ ] 2.1 Add a one-line reference to `hooks/__protocol__.md` in the top-of-file docstring of `tests/run_all.py`..

## 3. Validation

- [ ] 3.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — both tests pass.
- [ ] 3.2 `python3 tests/run_all.py` — full 141 / 0 / 0 must hold (hooks/manifests/vendored skills).
- [ ] 3.3 `git diff --check` — clean.
- [ ] 3.4 `openspec validate --all --strict` — pass (3 pre-existing + new `hook-protocol`).
- [ ] 3.5 `grep -c 'exit code\|additionalContext' hooks/__protocol__.md` ≥ 5 (sanity that document has substance).

## 4. Release

- [ ] 4.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.2 → 0.6.3.
- [ ] 4.2 Fix in-repo `.agents/plugins/marketplace.json` ref/icon to `v0.6.3`.
- [ ] 4.3 Open PR, wait for vendor-check, merge.
- [ ] 4.4 Push tag `v0.6.3`.
- [ ] 4.5 Sync market repo catalog + README codeguard row to `0.6.3` and push.
- [ ] 4.6 `openspec archive add-host-protocol-cheatsheet` after all tasks above are checked.