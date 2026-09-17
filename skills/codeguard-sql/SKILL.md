---
name: codeguard-sql
license: Apache-2.0
description: |
  SQL 代码规范检查：lint 门禁（`sqlfluff lint`）与格式化（`sqlfluff fix`）。
  Use when users write or review SQL code, hit sql lint failures, or ask about
  SQL style rules. Route framework/library questions to the official SQL docs.
---

# SQL 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`sqlfluff lint`
2. 格式化：`sqlfluff fix`
3. 扩展名：`.sql`

### ⚠️ Prerequisites
1. pip install sqlfluff

### ❌ Out of Scope
1. SQL 语法/框架/库用法 → 官方 SQL 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "SQL 规范" / "sql lint" / "sql 格式化"

## Workflow

1. lint：`bin/codeguard check --lang sql`
2. 格式化：`bin/codeguard fix --lang sql`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
