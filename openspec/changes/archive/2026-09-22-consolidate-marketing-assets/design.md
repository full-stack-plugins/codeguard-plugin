## Context

实测 grep 证据（2026-09-22 v0.6.5）：

| 资产 | 引用源 | 角色 |
|---|---|---|
| `assets/banner.svg` | `README.md:4` / `README.zh-CN.md:4` | README 顶部 hero 图 |
| `assets/composer-icon.png` | `.codex-plugin/plugin.json:44` (composerIcon) | Codex CLI Composer 区入口图标 |
| `assets/official-logo.png` | `.codex-plugin/plugin.json:45,46` / `.agents/plugins/marketplace.json:21,25`（CDN @v0.6.5） | Codex manifest logo + marketplace icon + marketplace logo |
| `assets/logo.png` | **零引用** | 命名重复，且与 `official-logo.png` 视觉上无差异 |
| `assets/official-logo.svg` | **零引用** | 双形态中的「vector 版本」——但所有 manifest 与 marketplace 都钉 png |
| `assets/79a62959-…png` | （UUID 命名的） | 历史资产，零引用 |

## Decisions

### 删除策略

只删**已验证零引用**的两个：`logo.png` 与 `official-logo.svg`。

- **不删 `logo.png` 的旧引用**：仓库从 `chore/release-v0.6.0` 起引用就是 `official-logo.png`，旧 `logo.png` 是历史残留。
- **不删 `79a62959-…png`**：UUID 命名通常为外部系统上传的截图，可能是旧 marketplace cache。删它需要先在 archive 仓或文档仓库验证零价值——超出本 change 范围。
- **不删 `banner.svg`**：README 直接 `<img src>` 引用。
- **不删 `composer-icon.png`**：codex manifest 的 `composerIcon` 字段钉死它。

### assets/README.md 内容

清单 + 每项用途 + 未来添加新资产应更新本文件 + 与 marketplace icon 同步更新流程。

### 风险

- `git log --follow` 还能找回删除的文件——若有用户用旧 release 引到 `logo.png`，他们只能去 archive 仓。已实测该文件 v0.6.0 前未被 manifest 引用。
- CDN 旧 version 引用的 `official-logo.png` 不受影响——只删仓内未发布版本。
- **绝对不在 marketplace CDN URL 里使用 SVG**——`.agents/plugins/marketplace.json` 的 `icon` 与 `logo` 都是 png，删除 SVG 不影响 CDN 行为。

## Risks / Trade-offs

- 删除是单向操作。仓库大小 -2 文件，可忽略。
- assets/README.md 变成 load-bearing 文档——必须与 README 的 `<img>` 同步更新（已在 spec 里作为 Requirement 2）。