---
name: codeguard-haskell
license: Apache-2.0
description: |
  Haskell 代码规范检查（Planned）：扩展名已识别（`.hs` `.lhs`），linter 集成在路线图（目标 V0.5）。
  钩子当前安全跳过。触发：用户提到 Haskell 规范或 haskell 文件检查时，说明现状与计划工具。
---

# Haskell 代码规范（Planned）

## Capability Boundaries

### ✅ Strengths
1. 扩展名识别：`.hs` `.lhs`
2. 计划 Linter：brew install hlint fourmolu

### ⚠️ Prerequisites
1. 暂无（linter 集成在路线图 V0.5）

### ❌ Out of Scope
1. 当前钩子不会对 Haskell 文件跑门禁（安全跳过）

## 计划工具

| 项 | 值 |
|---|---|
| Lint | `brew install hlint fourmolu` |
| 目标版本 | V0.5 |

## 启用路径

1. `scripts/languages.json` 该语言 status 改 beta + 填 lint/format 命令
2. `python3 scripts/gen_language_docs.py` 同步文档
3. 本 SKILL 补全强制项与 Gotchas
