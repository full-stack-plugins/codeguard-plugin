## 1. Test refactor

- [ ] 1.1 In `tests/test_plugin_manifests.py`, rename `test_each_released_manifest_points_to_the_68_skill_bundle` to `test_each_released_manifest_points_to_the_lock_union_plus_local_skills`.
- [ ] 1.2 Replace `self.assertEqual(68, expected)` with the three-source union assertion: `on_disk == lock_union | local`.

## 2. Validation

- [ ] 2.1 Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` — both `test_plugin_manifests.py` and `test_skill_vendor.py` pass.
- [ ] 2.2 Run `git diff --check` — must be clean.
- [ ] 2.3 Run `openspec validate --all --strict` — must pass (3 pre-existing + `language-gate-commands` + new `plugin-manifest-contracts`).

## 3. Release

- [ ] 3.1 Commit as part of the same release commit as HIGH 1 (single `release: v0.6.1` covers both changes).
- [ ] 3.2 After archive of `add-detect-lang-splits`, archive `add-manifest-bundle-dynamic` together with it (single release flow).