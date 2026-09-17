---
name: codeguard-dart
license: Apache-2.0
description: |
  Dart / Flutter 代码规范检查：lint 门禁（`dart analyze`）与格式化（`dart format .`）。
  Use when users write or review Dart / Flutter code, hit dart lint failures, or ask about
  Dart / Flutter style rules. Route framework/library questions to the official Dart / Flutter docs.
---

# Dart / Flutter 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`dart analyze`
2. 格式化：`dart format .`
3. 扩展名：`.dart`

### ⚠️ Prerequisites
1. Dart SDK 内置

### ❌ Out of Scope
1. Dart / Flutter 语法/框架/库用法 → 官方 Dart / Flutter 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Dart / Flutter 规范" / "dart lint" / "dart 格式化"

## Workflow

1. lint：`bin/codeguard check --lang dart`
2. 格式化：`bin/codeguard fix --lang dart`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
