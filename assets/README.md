# assets/

本目录下的每个文件都**至少被一个 tracked 消费者引用**。删除或新增资产前请同步更新本表。

| 文件 | 角色 | 消费者 |
|---|---|---|
| `banner.svg` | README 顶部 hero 图（英文 + 简体中文） | `README.md:4`, `README.zh-CN.md:4` |
| `composer-icon.png` | Codex CLI Composer 区入口图标 | `.codex-plugin/plugin.json` → `composerIcon` |
| `official-logo.png` | 插件主 logo（light/dark 共用） | `.codex-plugin/plugin.json` → `logo`/`logoDark`；市场仓 CDN URL（`@v<x.y.z>` 钉定） |
| `79a62959-c42e-42d1-9b45-a0f6b7c3f670.png` | 历史 UUID 命名资产，来源与用途不明；保留为安全网（删除前需在外部 archive 仓验证零价值） | 零当前引用 |

## 添加新资产的清单

1. 把文件放入 `assets/`。
2. **同一 commit** 更新本文件（行 + 来源 + 消费者列）。
3. 若该文件会进 marketplace icon / logo，更新 `.agents/plugins/marketplace.json` 的 `icon` 与 `logo`，并按 `bump-plugin.mjs` 流程 bump 版本号。
4. 跑 `python3 scripts/validate_languages_json.py` 与 `python3 tests/run_all.py`——确保 vendor check 不爆。

## 删除资产的清单

1. `git grep` 全仓确认零引用（含 README、docs/、manifest、市场仓镜像、CI 脚本）。
2. 确认 CDN URL 不引用（marketplace + Codex manifest + ZCode manifest + Kimi）。
3. `git rm` + 本表删除行 + 同一 commit。