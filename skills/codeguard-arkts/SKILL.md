---
name: codeguard-arkts
license: Apache-2.0
description: |
  ArkTS (HarmonyOS) 代码规范检查（Planned）：扩展名已识别（`.ets`），linter 集成在路线图（目标 V0.5）。
  钩子当前安全跳过。触发：用户提到 ArkTS (HarmonyOS) 规范或 arkts 文件检查时，说明现状与计划工具。
---

# ArkTS (HarmonyOS) 代码规范（Planned）

## Capability Boundaries

### ✅ Strengths
1. 扩展名识别：`.ets`
2. 计划 Linter：DevEco Studio ArkTS Linter

### ⚠️ Prerequisites
1. 暂无（linter 集成在路线图 V0.5）

### ❌ Out of Scope
1. 当前钩子不会对 ArkTS (HarmonyOS) 文件跑门禁（安全跳过）

## 计划工具

| 项 | 值 |
|---|---|
| Lint | `DevEco Studio ArkTS Linter` |
| 目标版本 | V0.5 |

## 启用路径

1. `scripts/languages.json` 该语言 status 改 beta + 填 lint/format 命令
2. `python3 scripts/gen_language_docs.py` 同步文档
3. 本 SKILL 补全强制项与 Gotchas
