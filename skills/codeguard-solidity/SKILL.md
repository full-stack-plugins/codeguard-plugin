---
name: codeguard-solidity
license: Apache-2.0
description: |
  Solidity 代码规范检查：lint 门禁（`solhint **/*.sol`）与格式化（`prettier --write`）。
  Use when users write or review Solidity code, hit solidity lint failures, or ask about
  Solidity style rules. Route framework/library questions to the official Solidity docs.
---

# Solidity 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`solhint **/*.sol`
2. 格式化：`prettier --write`
3. 扩展名：`.sol`

### ⚠️ Prerequisites
1. npm install -g solhint prettier prettier-plugin-solidity

### ❌ Out of Scope
1. Solidity 语法/框架/库用法 → 官方 Solidity 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Solidity 规范" / "solidity lint" / "solidity 格式化"

## Workflow

1. lint：`bin/codeguard check --lang solidity`
2. 格式化：`bin/codeguard fix --lang solidity`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
