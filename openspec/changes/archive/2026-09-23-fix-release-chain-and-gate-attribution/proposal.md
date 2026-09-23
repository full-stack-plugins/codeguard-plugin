# 2026-09-23-fix-release-chain-and-gate-attribution

## Why

v0.15.0 发版过程实测出两个缺陷（用户指令 2026-09-23：修复）：

1. **bump-plugin.mjs 的 plain manifest 替换静默 no-op**：`bumpPlain` 按 catalog 版本字符串
   精确替换，catalog 与 manifest 漂移时（实测 catalog 0.14.14 vs manifest 0.14.12）replace
   不匹配、无报错地写回原文，发版计划照常打印「-> 0.15.0」——半程假成功，版本链断裂还伴随
   后续 sync 校验崩溃（同根因）。
2. **git 意图门禁的间接正文误报**：非 Shell 解释器（node/python）脚本正文被按 shell 切段扫描，
   JS 模板字符串里的 git commit/git add/git push **样例文本**（bump-plugin.mjs:164-165 帮助文本
   `cd … && git add && git commit && git push`）被当成真实 git 副作用 →
   `node scripts/bump-plugin.mjs` 被判「间接 Git 操作不能可靠建模」**不可绕过地阻断**，
   发版工具被自家门禁锁死。

## What Changes

- bump-plugin.mjs：plain manifest 替换失败（版本漂移）改为**显式抛错**，不再静默跳过；
  全部写入后回读校验版本一致，杜绝半程假成功。
- git 意图归因：非 Shell 脚本正文不再 shell 切段，改按**subprocess/exec 调用形态**高精度识别
  git 副作用（`execFileSync("git", …)`、`os.system("…")` 等）；帮助文本/模板字符串里的
  git 字面量不再触发门禁。命中真实调用时仍按既有语义「不可建模 → UNVERIFIED 阻断」。
- Shell 脚本正文的行为完全不变（可建模，保留切段解析）。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

无（行为修复归入既有 gate-trigger-policy 语义：误报消除、触发面不变；按 fix-gate-trigger-and-mcp
先例以 proposal+design+tasks 收口）。

## Impact

- `scripts/bump-plugin.mjs`、`scripts/codeguard/git_syntax.py`、`scripts/codeguard/git_context.py`。
- 发版链路行为：漂移时 fail-loud（此前静默）；`node scripts/bump-plugin.mjs` 恢复可直跑。
- 测试：新增间接归因回归（JS 帮助文本不触发 / node、python 真实 git 调用仍触发并阻断 / Shell 行为不变）。
- 已知边界（非目标）：Bash heredoc/命令文本数据段里的 git 样例仍可能被外层切段误伤（写作侧规避）。
