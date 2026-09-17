---
name: codeguard-ansible
license: Apache-2.0
description: |
  Ansible 代码规范检查：lint 门禁（`ansible-lint`）与格式化（`ansible-lint --fix`）。
  Use when users write or review Ansible code, hit ansible lint failures, or ask about
  Ansible style rules. Route framework/library questions to the official Ansible docs.
---

# Ansible 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`ansible-lint`
2. 格式化：`ansible-lint --fix`
3. 扩展名：（文件名匹配）

### ⚠️ Prerequisites
1. pip install ansible-lint

### ❌ Out of Scope
1. Ansible 语法/框架/库用法 → 官方 Ansible 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Ansible 规范" / "ansible lint" / "ansible 格式化"

## Workflow

1. lint：`bin/codeguard check --lang ansible`
2. 格式化：`bin/codeguard fix --lang ansible`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
