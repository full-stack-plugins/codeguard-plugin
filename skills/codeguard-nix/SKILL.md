---
name: codeguard-nix
license: Apache-2.0
description: |
  Nix 代码规范检查：lint 门禁（`deadnix`）与格式化（`nixpkgs-fmt`）。
  Use when users write or review Nix code, hit nix lint failures, or ask about
  Nix style rules. Route framework/library questions to the official Nix docs.
---

# Nix 代码规范门禁

## Capability Boundaries

### ✅ Strengths
1. lint 门禁：`deadnix`
2. 格式化：`nixpkgs-fmt`
3. 扩展名：`.nix`

### ⚠️ Prerequisites
1. nix-env -iA nixpkgs.nixpkgs-fmt nixpkgs.deadnix

### ❌ Out of Scope
1. Nix 语法/框架/库用法 → 官方 Nix 文档或对应语言技能仓
2. 依赖 CVE → codeguard-security-code

## When to Use

- "Nix 规范" / "nix lint" / "nix 格式化"

## Workflow

1. lint：`bin/codeguard check --lang nix`
2. 格式化：`bin/codeguard fix --lang nix`
3. 复扫至零失败

## Gotchas

1. 工具未装时门禁返回「无法验证」——先按 install_hint 安装
2. 规则阈值可在项目内配置文件调整（不得为过门禁而静默放宽）
