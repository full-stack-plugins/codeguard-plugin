## 1. Audit

- [x] 1.1 Run `grep -rn 'logo\.png\b\|official-logo\.svg'` (excluding `.git`) — verify zero matches for both files.
- [x] 1.2 Run `grep -rn 'official-logo\.\(png\|svg\)\|composer-icon\|banner' .agents/ .codex-plugin/ .zcode-plugin/ kimi.plugin.json README.md README.zh-CN.md` — record which consumer uses which file.

## 2. Deletion

- [x] 2.1 Delete `assets/logo.png`.
- [x] 2.2 Delete `assets/official-logo.svg`.
- [x] 2.3 Verify `git status` shows only these two deletions + new `assets/README.md` (and any spec archive files).

## 3. Documentation

- [x] 3.1 Create `assets/README.md` with a Markdown table listing the four remaining files (banner.svg, composer-icon.png, official-logo.png, 79a62959-…png — note the last as legacy/unknown provenance).

## 4. Validation

- [x] 4.1 `python3 -m unittest discover -s tests -p 'test_*.py' -v` — all pass.
- [x] 4.2 `python3 tests/run_all.py` — full 141 / 0 / 0 must hold.
- [x] 4.3 `git diff --check` — clean.
- [x] 4.4 `openspec validate --all --strict` — pass.

## 5. Release

- [x] 5.1 `node scripts/bump-plugin.mjs codeguard patch` — bump 0.6.5 → 0.6.6.
- [x] 5.2 Fix in-repo `.agents/plugins/marketplace.json` ref/icon to `v0.6.6`.
- [x] 5.3 Open PR, wait for vendor-check, merge.
- [x] 5.4 Tag v0.6.6 (force-move if origin tag v0.6.5/0.6.4 stale).
- [x] 5.5 Sync market repo catalog + README codeguard row to `0.6.6` and push.
- [x] 5.6 `openspec archive consolidate-marketing-assets`.