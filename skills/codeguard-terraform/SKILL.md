---
name: codeguard-terraform
license: Apache-2.0
description: |
  Terraform / OpenTofu 代码规范检查：lint 门禁（`tflint`）与格式化（`terraform fmt`）。
  Use when users write or review Terraform / OpenTofu code, hit terraform lint failures, or ask about
  Terraform / OpenTofu style rules. Route framework/library questions to the official Terraform / OpenTofu docs.
---

# Terraform / OpenTofu 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`tflint`
2. 格式化：`terraform fmt`
3. 扩展名：`.tf` `.tfvars` `.tofu`

### ⚠️ Prerequisites
1. brew install tflint

### ❌ Out of Scope
1. Terraform / OpenTofu 语法/框架/库用法 → 官方 Terraform / OpenTofu 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Terraform / OpenTofu 规范" / "terraform lint" / "terraform 格式化"

## Workflow

1. lint：`bin/codeguard check --lang terraform`
2. 格式化：`bin/codeguard fix --lang terraform`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
