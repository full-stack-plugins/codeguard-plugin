## Why

`assets/` 目录里有 6 个文件：1 个 banner.svg（README 用）、1 个 composer-icon.png（codex manifest 用）、1 个 logo.png（**零引用**）、1 个 official-logo.png（marketplace + codex + zcode 用）、1 个 official-logo.svg（**零引用**）。MEDIUM #9 评审指出：双形态（png/svg）+ 重复 logo 名带来三问题——

1. SVG 文件从未被引用，但留在仓内误导「也许应该用 SVG」。
2. `logo.png` 与 `official-logo.png` 名称几乎重复，下载/分发时易混淆。
3. CDN 钉的是 `@v0.6.5/assets/official-logo.png`，删错文件会爆图标 404。

## What Changes

- 删除 `assets/logo.png`（零引用）。
- 删除 `assets/official-logo.svg`（零引用）。
- 保留 `assets/banner.svg`（README 用）、`assets/composer-icon.png`（codex manifest 用）、`assets/official-logo.png`（CDN/marketplace 钉的）。
- 不修改任何 manifest、不修改 README、不修改 docs。
- 在 `assets/README.md`（新建）记录每个文件的用途，便于未来维护。

## Capabilities

### New Capabilities

- `asset-canonicalization`: Defines which `assets/*` files are load-bearing for marketplace / manifests / README and which may be deleted without breaking any consumer.

### Modified Capabilities

None.

## Impact

删除 2 个零引用资产，零行为变化。新增 ~20 行 `assets/README.md`。