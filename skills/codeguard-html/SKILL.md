---
name: codeguard-html
license: Apache-2.0
description: |
  HTML 代码规范检查：lint 门禁（`npx htmlhint`）与格式化（`prettier --write`）。
  Use when users write or review HTML code, hit html lint failures, or ask about
  HTML style rules. Route framework/library questions to the official HTML docs.
---

# HTML 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`npx htmlhint`
2. 格式化：`prettier --write`
3. 扩展名：`.html` `.htm`

### ⚠️ Prerequisites
1. npm install -g htmlhint

### ❌ Out of Scope
1. HTML 语法/框架/库用法 → 官方 HTML 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "HTML 规范" / "html lint" / "html 格式化"

## Workflow

1. lint：`bin/codeguard check --lang html`
2. 格式化：`bin/codeguard fix --lang html`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
