---
name: codeguard-cobol
license: Apache-2.0
description: |
  COBOL 代码规范检查（Planned）：扩展名已识别（`.cbl` `.cob` `.cpy`），linter 集成在路线图（目标 V0.5）。
  钩子当前安全跳过。触发：用户提到 COBOL 规范或 cobol 文件检查时，说明现状与计划工具。
---

# COBOL 代码规范（Planned）

## Capability Boundaries

### ✅ Strengths
1. 扩展名识别：`.cbl` `.cob` `.cpy`
2. 计划 Linter：IBM COBOL Checker

### ⚠️ Prerequisites
1. 暂无（linter 集成在路线图 V0.5）

### ❌ Out of Scope
1. 当前钩子不会对 COBOL 文件跑门禁（安全跳过）

## 计划工具

| 项 | 值 |
|---|---|
| Lint | `IBM COBOL Checker` |
| 目标版本 | V0.5 |

## 启用路径

1. `scripts/languages.json` 该语言 status 改 beta + 填 lint/format 命令
2. `python3 scripts/gen_language_docs.py` 同步文档
3. 本 SKILL 补全强制项与 Gotchas
