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

## 6. 第二批：误拦治理深化 + 可审计（2026-09-22 追加）

- [x] 6.1 `verdict._strip_dialect_blocks`：SC1071 剥离后重判，不掩盖同批真问题
- [x] 6.2 `verdict.finding_signatures`：规则码优先、无码归一化描述行的可比较签名
- [x] 6.3 `gate_lib.baseline_stale_finding`：双跑基线豁免（无基线绝不豁免；commit→HEAD、push→@{upstream}——push 面拿 HEAD 当基线会把新引入坏内容误判成存量，实测踩过后收紧）
- [x] 6.4 `gate_lib.record_gate_decision`：gate-decisions.jsonl 决策日志（lang/cmd/rc/status/reason，滚动 500 条）
- [x] 6.5 `skip_gate_via_git_config`：3s 超时 ×2 次重试，两次失败才审计 skipGate-read-error（此前 timeout=10s 静默 False）
- [x] 6.6 `_openspec_validate` 及调用点 except 扩宽到 Exception（异常归未验证，不 fail-open 静默吞）
- [x] 6.7 Java install_hint 语义修正（无需安装工具；用项目自带 wrapper 与匹配 JDK）
- [x] 6.8 `scope._project_python_target` + `ruff_config_args`：按 requires-python/.python-version 自适应 `--target-version`（注入配置硬编码 py310 会把老项目按 3.10 目标刷 UP 假违规）
- [x] 6.9 `tests/test_gate_hardening_batch2.py`：18 用例（14 落地 + 4 待接线）
- [x] 6.10 全量 unittest + run_all 141 + ruff 全绿（与 3.6/3.7 链式豁免改动合并验证）

## 7. 让位项（pre_tool_git_guard.py 并行修改活跃期，避免竞争写入）

- [x] 7.1 已由架构重构接管：`git_staging.resolve_pathspecs` 成组调用只读 Git pathspec 查询，目录/glob/literal/exclude/`-u`/`-f` 与真实 Hook 敏感文件回归均已恢复为常规测试；无需另建第二份 `match_pathspec` 实现。
- [x] 7.2 已由架构重构接管：内联与链式豁免按目标仓审计并在 Hook additionalContext 明示，`test_inline_skip_emits_user_visible_notice` 与多仓豁免测试为常规回归。
- [ ] 7.3 双副本判定一致性核对（partme-ai 0.3.4 悬挂 hook 已用 fail-open 占位止血——宿主仍执行已删除的 hook 致全部 Bash 报错；根治=宿主禁用 codeguard@partme-ai 旧副本）
