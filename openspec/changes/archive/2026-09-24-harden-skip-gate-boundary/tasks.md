## 1. 豁免语义收窄

- [x] 1.1 `git_guard_application`：暂存面计算移出 `not active` 短路，安全扫描恒执行，语言门禁按 `active` 执行。
- [x] 1.2 `prompt_application`：skipGate 下跳过 `run_gate` 但保留 `check_commit_safety`，违规注入上下文。
- [x] 1.3 `reporting.gate_directive` 豁免段写明范围（保留 `1/true/yes` 与「内联赋值不会传入」parity 字样）。

## 2. 工具链 PATH 根因修复

- [x] 2.1 `paths.ensure_user_path` 补 `Path(sys.executable).resolve().parent` 与 `sysconfig.get_path("scripts")`。
- [x] 2.2 `ToolchainProbe.probe` 与 `run_gate` 入口调用 `ensure_user_path`。
- [x] 2.3 探活 not_found 时以 `python3 -m <tool> --version` 试判，区分「未安装」与「模块在但入口缺失」。

## 3. 测试

- [x] 3.1 新增 `tests/test_skip_gate_safety_scope.py`：仓库级/内联豁免 + 敏感文件仍拦截；语言门禁仍豁免；软门禁注入安全报告；env 逃生门完整放行。
- [x] 3.2 工具链探活在剥离 PATH 后自修复（裸 `ruff` 可解析）。
- [x] 3.3 全量 pytest 通过，且**不**手工补 Framework bin 到 PATH（证明假失败根因已除）。

## 4. 文档与验证

- [x] 4.1 同步 `hooks/__protocol__.md`、`README.md`、`README.zh-CN.md`、`docs/current-architecture.md`。
- [x] 4.2 `openspec validate --all --strict` 通过；ruff 对改动文件零告警。
