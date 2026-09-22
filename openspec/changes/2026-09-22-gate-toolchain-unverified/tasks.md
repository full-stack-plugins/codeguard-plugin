# Tasks: 2026-09-22-gate-toolchain-unverified

## 1. 判定语义（工具链不兼容 ≠ 代码违规）

- [x] 1.1 `verdict.py`：`_ENV_ERROR` 追加 Maven POM 版本不匹配 / release version 不支持 / invalid target release / UnsupportedClassVersionError 特征
- [x] 1.2 `verdict.py`：SC1071 归 UNVERIFIED（ShellCheck 不支持 zsh 方言）

## 2. zsh 目标面剔除

- [x] 2.1 `languages.json`：shell 全量 gate 的 find 剔除 `*.zsh`
- [x] 2.2 `gate_lib._run_gate_uncached`：delta 面过滤 `.zsh`，明示「N 个 zsh 文件未验证」，不静默丢弃

## 3. 缓存键与逃生门

- [x] 3.1 `gate_lib._gate_cache_key`：增加 `scope` 维度并传入调用点
- [x] 3.2 `gate_lib.skip_gate_via_git_config`：读取失败记 `skipGate-read-error` 审计事件 + detail
- [x] 3.3 `pre_tool_git_guard.inline_skip_gate`：识别 `-c codeguard.skipGate=` 内联豁免，只认 `-c` 后紧跟赋值 token
- [x] 3.4 `main()` 接入内联豁免 + `record_skip_event("inline-skipGate")`
- [x] 3.5 `gate_directive` 逃生门文档增补单次内联豁免用法
- [x] 3.6 `pre_tool_git_guard.chain_skip_gate`：链内 `git config codeguard.skipGate <真值>` 设置段=显式豁免，记 `chain-skipGate` 审计（set→提交→unset 同链不再"首用必败"）
- [x] 3.7 `_git_seg_parts` 子命令边界收紧：`commit -m` 消息文本里的豁免短语不再被误判为豁免（inline/chain 双收口）

## 4. Agent 工作目录排除

- [x] 4.1 `scope.FULL_SCAN_EXCLUDES` 增加 `.mimosa`/`.worktrees`/`.code-review-graph`/`.kimi-code`/`.zcode`/`.codex-plugin`/`.agents`

## 5. 测试与验证

- [x] 5.1 `tests/test_gate_hardening_usage.py`：19 用例（6 判定语义 + 2 zsh + 1 缓存键 + 8 逃生门/审计（含链式豁免、消息文本防误判）+ 2 排除面）
- [x] 5.2 `python3 -m unittest discover -s tests` 221 通过——无 ruff 环境 3 skipped（CLI/auto_fix 用例补 `skipUnless(ruff)` 工具缺失守卫：无法验证 ≠ 验证失败）；ruff==0.16.8 shim 下 221 全过 0 skipped（守卫不掩盖坏测试）
- [x] 5.3 `python3 tests/run_all.py` 141 通过 / 0 失败
- [x] 5.4 端到端 4 场景实证（hook stdin JSON 驱动）：内联豁免留痕、.zsh 放行+明示未验证、敏感文件仍 exit 2、Maven POM 4.1.0 归 UNVERIFIED 放行
- [x] 5.5 `ruff check hooks/ scripts/ tests/` 全绿；`validate_languages_json` 11 规则通过
