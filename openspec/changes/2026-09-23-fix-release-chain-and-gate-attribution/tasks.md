# Tasks: 2026-09-23-fix-release-chain-and-gate-attribution

## 1. bump-plugin fail-loud

- [x] 1.1 `bumpPlain` 替换无命中时抛错，报告 manifest 实际版本与 catalog 版本
- [x] 1.2 全部写入后回读校验 catalog + 4 manifest 版本与计划一致

## 2. git 意图归因（非 Shell 正文）

- [x] 2.1 `git_syntax` 新增调用形态检测（exec/spawn/subprocess/os.system 等 + git 参数位），返回 commit|push|add|config 与 skipGate 变更
- [x] 2.2 `git_context` resolve 路径：非 Shell 正文改走调用形态检测；Shell 正文行为不变
- [x] 2.3 `_guarded_mode`/`_command_indirect` 同步按 is_shell 分派

## 3. 回归测试

- [x] 3.1 JS 帮助文本（模板字符串 git 样例）不触发门禁
- [x] 3.2 node `execFileSync("git", ["…"])` / python `subprocess.run(["git", …])` 仍触发并 UNVERIFIED 阻断
- [x] 3.3 Shell 脚本真实 git commit 仍可建模（行为不变）
- [x] 3.4 非 Shell 帮助文本里的 `git config codeguard.skipGate` 不构成豁免变更
- [x] 3.5 bump 漂移 fixture 抛错（fail-loud）

## 4. 发版

- [x] 4.1 全量回归 + ruff 干净
- [x] 4.2 dogfood：直跑 `node scripts/bump-plugin.mjs codeguard patch`（不带包装）过门禁并发版
- [x] 4.3 市场仓同步 + PR/CI/合并 + 两仓推送
