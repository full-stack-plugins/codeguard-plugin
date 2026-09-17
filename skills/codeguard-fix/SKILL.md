---
name: codeguard-fix
license: Apache-2.0
description: |
  codeguard fix 命令：自动修复各语言 lint 问题（spotless:apply / cargo fmt / eslint --fix /
  ruff --fix / gofmt），修复后建议复跑 check。Use when users say "自动修复", "/fix",
  "格式化修复". Route logic-level violations (unused vars with meaning, complexity) to
  manual review; do not auto-edit business code.
---

# codeguard fix

## Capability Boundaries

### ✅ Strengths
1. 格式类问题一键修复（各语言 format 命令）
2. `--dry-run` 预览将要执行的修复
3. 只跑 format 工具，不触碰业务逻辑

### ⚠️ Prerequisites
1. 对应 format 工具已安装（同 check）

### ❌ Out of Scope
1. javadoc 缺失等需要"写内容"的修复 → 人工/AI 补写（codeguard-java）
2. 安全豁免（改阈值/删规则）→ 禁止，见 codeguard 主入口门禁规则

## 命令

```bash
bin/codeguard fix --dry-run       # 预览（不实际修改）
bin/codeguard fix                 # 执行修复
bin/codeguard fix --lang python   # 只修 Python
```

## Workflow

1. `bin/codeguard check` 确认失败项
2. `bin/codeguard fix --dry-run` 预览
3. `bin/codeguard fix` 执行
4. `bin/codeguard check` 复扫至全绿
5. `git diff` review 自动修复的改动，确认无业务逻辑变更

## Gotchas

1. `npm audit fix` 可能引入破坏性升级——fix 后必须回归测试
2. `eslint --fix` 只修可自动修复规则；复杂度/unused 需人工
