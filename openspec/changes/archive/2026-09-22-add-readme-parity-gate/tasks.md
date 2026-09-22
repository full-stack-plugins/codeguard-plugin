## 1. Parity gate

- [x] 1.1 Create `tests/test_readme_parity.py` with three assertions (heading-level sequence / local link targets / version strings), fence-aware.
- [x] 1.2 Run it against current READMEs; record every existing mismatch.

## 2. Drift repairs (mirror both files in one commit)

- [x] 2.1 zh: insert `## 治理技能（Git 与安全）` and demote `外部技能来源` to `###` so heading sequences match.
- [x] 2.2 Both: `Current version` row `0.5.4 → 0.6.7`.
- [x] 2.3 Both: vendor snapshot `v0.1.0 → v0.1.2` (4 places; matches `skills.lock.json`).
- [x] 2.4 Both: add `bin/codeguard` dispatcher sentence in `### CLI` section (same position).
- [x] 2.5 Both: add parity note after H1 pointing at the gate test.

## 3. Docs rename (LOW #14)

- [x] 3.1 `git mv 'docs/5、partme-codeguard-plugin-技术方案与路线.md' docs/technical-roadmap.zh_CN.md`.
- [x] 3.2 Update 6 README links (en ×3, zh ×3) + document H1 (drop `5、` prefix).

## 4. Validation

- [x] 4.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — all pass (incl. new parity test).
- [x] 4.2 `python3 tests/run_all.py` — 141 / 0 / 0.
- [x] 4.3 `git diff --check` — clean.
- [x] 4.4 `openspec validate --all --strict` — pass.

## 5. Release

- [x] 5.1 bump patch → 0.6.7; fix in-repo marketplace pins; feat PR → merge; release PR → merge; tag v0.6.7; market repo catalog + README row → 0.6.7.
- [x] 5.2 `openspec archive add-readme-parity-gate`.