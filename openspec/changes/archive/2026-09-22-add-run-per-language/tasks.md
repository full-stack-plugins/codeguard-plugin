## 1. New file

- [ ] 1.1 Create `scripts/run_per_language.py` with `run_check` and `run_fix` per the design; export `__all__` listing them.

## 2. run_check.py slim down

- [ ] 2.1 Remove local `run` / `check_one` / `fix_one` from `scripts/run_check.py`.
- [ ] 2.2 Replace the per-language loop body in `cli_main()` with `results = run_per_language.run_check(languages, project_root, timeout=args.timeout, fix=args.fix)`.
- [ ] 2.3 Keep the argparse, the `mcp_main` placeholder, and the human-readable summary lines untouched.

## 3. fix.py slim down

- [ ] 3.1 Remove the in-line subprocess loop from `scripts/fix.py`.
- [ ] 3.2 Replace it with `results = run_per_language.run_fix(languages, project_root, dry_run=args.dry_run)` and the existing summary lines.

## 4. Validation

- [ ] 4.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — both `test_plugin_manifests.py` and `test_skill_vendor.py` must pass.
- [ ] 4.2 `python3 tests/run_all.py` — full 141 / 0 / 0 must hold (hooks/manifests/vendored skills).
- [ ] 4.3 Smoke `python3 scripts/run_check.py --help` and `python3 scripts/fix.py --help` — exit 0, argparse output unchanged from `v0.6.1`.
- [ ] 4.4 Smoke `python3 scripts/fix.py --dry-run .` on this repo — each detected language prints `would run: ...` and no subprocess is launched.
- [ ] 4.5 `ruff check scripts/run_per_language.py scripts/run_check.py scripts/fix.py` — zero new errors attributable to this change.
- [ ] 4.6 `git diff --check` — clean.
- [ ] 4.7 `openspec validate --all --strict` — pass (3 pre-existing + new `idiomatic-runner`).

## 5. Release

- [ ] 5.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.1 → 0.6.2.
- [ ] 5.2 Fix in-repo `.agents/plugins/marketplace.json` ref/icon to `v0.6.2`.
- [ ] 5.3 Open PR, wait for vendor-check, merge.
- [ ] 5.4 Push tag `v0.6.2`.
- [ ] 5.5 Sync market repo catalog + README codeguard row to `0.6.2` and push.
- [ ] 5.6 `openspec archive add-run-per-language` after all tasks above are checked.