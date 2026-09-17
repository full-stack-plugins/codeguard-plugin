---
name: codeguard-markdown
license: Apache-2.0
description: |
  Markdown 代码规范检查：lint 门禁（`npx markdownlint-cli2 **/*.md`）与格式化（`markdownlint-cli2 --fix`）。
  Use when users write or review Markdown code, hit markdown lint failures, or ask about
  Markdown style rules. Route framework/library questions to the official Markdown docs.
---

# Markdown 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`npx markdownlint-cli2 **/*.md`
2. 格式化：`markdownlint-cli2 --fix`
3. 扩展名：`.md` `.markdown`

### ⚠️ Prerequisites
1. npm install -g markdownlint-cli2

### ❌ Out of Scope
1. Markdown 语法/框架/库用法 → 官方 Markdown 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Markdown 规范" / "markdown lint" / "markdown 格式化"

## Workflow

1. lint：`bin/codeguard check --lang markdown`
2. 格式化：`bin/codeguard fix --lang markdown`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
