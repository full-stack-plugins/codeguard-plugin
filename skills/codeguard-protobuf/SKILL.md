---
name: codeguard-protobuf
license: Apache-2.0
description: |
  Protobuf 代码规范检查：lint 门禁（`buf lint`）与格式化（`buf format`）。
  Use when users write or review Protobuf code, hit protobuf lint failures, or ask about
  Protobuf style rules. Route framework/library questions to the official Protobuf docs.
---

# Protobuf 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`buf lint`
2. 格式化：`buf format`
3. 扩展名：`.proto`

### ⚠️ Prerequisites
1. brew install bufbuild/buf/buf

### ❌ Out of Scope
1. Protobuf 语法/框架/库用法 → 官方 Protobuf 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Protobuf 规范" / "protobuf lint" / "protobuf 格式化"

## Workflow

1. lint：`bin/codeguard check --lang protobuf`
2. 格式化：`bin/codeguard fix --lang protobuf`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
