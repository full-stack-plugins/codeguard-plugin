---
name: codeguard-check
license: Apache-2.0
description: |
  codeguard check 命令：跑项目全量 lint 门禁并输出报告。检测语言 → 按语言跑 linter →
  汇总通过/失败。Use when users say "check", "跑检查", "lint 报告", or before commit.
  Route fixing to codeguard-fix; CVE scanning to codeguard-cve.
---

# codeguard check

## Capability Boundaries

### ✅ Strengths
1. 自动检测项目语言，一次跑全量 lint
2. 表格化报告：每语言通过/失败/退出码
3. `--lang` 限定范围、`--timeout` 控制单语言超时

### ⚠️ Prerequisites
1. 对应语言工具链（mvn/cargo/node/ruff）已安装

### ❌ Out of Scope
1. 自动修复 → `codeguard fix`
2. CVE 扫描 → `codeguard cve`

## 命令

```bash
bin/codeguard check                        # 全量
bin/codeguard check --lang java,python     # 限定语言
bin/codeguard check --timeout 60 path/     # 指定项目与超时
# 等价：python3 scripts/run_check.py
```

## Workflow

1. `bin/codeguard detect path` 确认语言
2. `bin/codeguard check path` 跑门禁
3. exit 0 = 全绿；exit 2 = 有失败，按语言到对应 SKILL（codeguard-java 等）修复
4. 修复后重跑至全绿，再考虑提交（提交时 commit-msg 门禁会再拦一次）
