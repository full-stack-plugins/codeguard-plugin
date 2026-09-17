---
name: codeguard-toml
license: Apache-2.0
description: |
  TOML 代码规范检查：lint 门禁（`taplo lint`）与格式化（`taplo format`）。
  Use when users write or review TOML code, hit toml lint failures, or ask about
  TOML style rules. Route framework/library questions to the official TOML docs.
---

# TOML 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`taplo lint`
2. 格式化：`taplo format`
3. 扩展名：`.toml`

### ⚠️ Prerequisites
1. cargo install taplo-cli --locked

### ❌ Out of Scope
1. TOML 语法/框架/库用法 → 官方 TOML 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "TOML 规范" / "toml lint" / "toml 格式化"

## Workflow

1. lint：`bin/codeguard check --lang toml`
2. 格式化：`bin/codeguard fix --lang toml`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
