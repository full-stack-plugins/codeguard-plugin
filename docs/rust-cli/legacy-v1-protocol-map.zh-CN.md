# legacy-v1 入口协议与退出码映射

本表只描述插件旧入口的既有行为，供 Rust C35 兼容层逐项实现。旧版返回 0、MCP 工具调用成功或 Hook 放行，均**不等于**新版交付 `allow`；Rust 投影固定 `new_delivery_decision=not_evaluated`。新版 CLI 的 0/1/2/3/4/130 协议独立计算，不能直接透传旧数字。来源为当前插件旧入口和应用服务；[旧源码增量](legacy-delta-20260924.zh-CN.md)记载与早期设计快照的差异。

## CLI 入口

| 旧入口 | 旧数字和混合优先级 | 0 的实际含义及迁移边界 | 来源 | 验收入口 |
|---|---|---|---|---|
| `bin/codeguard` 默认、`check` | `FAIL→2` 优先于 `UNVERIFIED/PLANNED→1`；仅 PASS/SKIPPED→0；空语言→1；argparse 用法错→2 | 可能只有 SKIPPED，不代表完整项目质量通过；MCP 模式另列 | `bin/codeguard`、`scripts/run_check.py::cli_main`、`scripts/codeguard/verdict.py::exit_status` | Rust `legacy_v1_protocol_contract`；旧 `tests/test_verdict_integrity.py` |
| `fix` | 任一 formatter 失败、未配置而返回 PLANNED、UNVERIFIED 或无识别语言→1；全部成功/跳过/显式 dry-run、无 Git 改动或无适用文件→0；argparse 错→2 | 空 `run_fix` 结果不足以区分“无语言”和“无适用文件”，兼容层必须保留入口分支；formatter 成功不证明文件改变，仍须复检 | `scripts/fix.py::main`、`scripts/codeguard/language_check.py::run_fix` | Rust 参数表；旧 `tests/test_cli_contracts.py`、`tests/test_cli_fix_reporting.py` |
| `cve` | `FAIL→2` 优先于 `UNVERIFIED→1`；空结果→1；全 PASS→0；参数/生态/严重度错→3 | 只是旧阈值下各生态结果；不能用 2 推断新版 CLI 用法错 | `scripts/cve_check.py::main`、`scripts/codeguard/cve_policy.py::aggregate_exit` | Rust 参数表；旧 `tests/test_cve_boundaries.py` |
| `dockerfile` | 任一 UNVERIFIED 或无目标→1，即使同批有 FAIL；完整且有 FAIL→2；全 PASS→0；argparse 错→2 | 混合结果中的风险仍留在报告；退出 1 不得丢掉已确认发现 | `scripts/dockerfile_security.py::main`、`scripts/codeguard/dockerfile_reports.py::aggregate_status` | Rust 参数表；旧 `tests/test_dockerfile_boundaries.py` |
| `detect` | 有根及无根的正常查询→0（无根输出 `[]`）；配置错误→1 | 只是发现操作，`[]` 不能签发空项目质量通过 | `scripts/detect_lang.py::main` | Rust 参数表；旧 `tests/test_cli_contracts.py` |
| `init` | 总是输出人工引导并返回 0，不写项目 | 旧引导完成不等于 Rust `init --apply` 或任何检查完成 | `bin/codeguard` 的 `init` 分支 | Rust 参数表；旧 `tests/test_cli_contracts.py` |
| `java-plan` | `UNVERIFIED→1`，其余计划状态→0；argparse 错→2 | 只读计划，未执行 Java 构建或检查 | `scripts/java_project.py::main` | Rust 参数表；旧 `tests/test_java_project_impact.py` |
| 未知子命令 | wrapper→1；诊断写 stderr | 新版未知命令走自身用法协议，不能套旧 1 | `bin/codeguard` 默认分支 | Rust 参数表 |

`run_check.py --mcp` 是旧 MCP **服务器生命周期**入口：SDK 缺失时进程返回 1，启动服务后退出 0。服务退出 0 不表示任何工具调用或质量检查成功。`check_code_style` 返回逐语言数组，保留 `passed/status/reason/exit_code/log_path`；`auto_fix` 返回修复尝试与复检摘要；`list_languages` 只返回 ID/名称；`analyze_java_impact` 返回只读计划。四种工具返回的是 MCP 文本块中的 JSON payload，**没有**可直接映射的每次调用进程退出码；配置损坏可返回 `UNVERIFIED/exit_code=1` 的工具 payload，未知工具返回 `error` 对象。来源：`scripts/run_check.py::mcp_main`、`scripts/codeguard/check_application.py::mcp_tool_payload`；旧 `tests/test_mcp_server.py` 和 `tests/test_mcp_autofix_identity.py` 继续覆盖真实旧 SDK 接口。C35 的 MCP 接线与宿主验收另由 11.1/11.3 承担，本表不把服务存活变成新版认证。

## 五类 Hook

| 旧事件 | 旧退出/反馈 | 新版边界 | 来源与旧夹具 |
|---|---|---|---|
| SessionStart | 0；stdout 人类可读摘要；未捕获异常 stderr 提示并 exit 0 | 环境信息不等于检查通过 | `hooks/env_check.py`；`tests/test_startup_application.py` |
| UserPromptSubmit | 0；命中时 stdout `hookSpecificOutput.additionalContext`；内部异常 exit 0 | 观察型软反馈不阻断交付 | `hooks/user_prompt_validator.py`；`tests/test_prompt_application.py` |
| PreToolUse Bash | 0 放行或附 `additionalContext` 的未验证；2 拦截并在 stderr 给修复指令；内部异常 exit 0 | 旧 2 是宿主拦截，不是新 CLI 用法错；旧 0 包含 fail-open，不能当 `allow` | `hooks/pre_tool_git_guard.py`、`scripts/codeguard/git_guard_application.py`；`tests/test_git_guard_application.py` |
| PostToolUse Write/Edit/MultiEdit | 0；stdout 可含 JSON 反馈与 systemMessage；内部异常 exit 0 | 保存反馈不承担质量门禁 | `hooks/post_tool_lint.py`；`tests/test_save_application.py` |
| Stop | 0；stdout 会话摘要；内部异常 exit 0 | 历史计数不替代完整交付检查 | `hooks/stop_summary.py`；`tests/test_session_application.py` |

PreToolUse 当前源码还会在无法准确解析 Git 意图、没有可定位仓库等情况下返回 2；这与旧 `hooks/__protocol__.md` 中“仅已确认 lint 失败才 exit 2”的文字不完全一致。C35 必须先按真实旧源码和宿主实测固定此分支，不得以旧文档的概括删掉阻断或把不可确认意图伪称为已确认源码违规。`codeguard.skipGate`/`CODEGUARD_SKIP_GATE` 和 Hook fail-open 仅归 legacy-v1；新版交付门禁按独立完整性与受保护策略判定。

Rust `crates/codeguard-cli/src/legacy_v1_protocol.rs` 只承接**已经归类**的旧信号，拒绝不支持的入口/信号组合。它没有调用 Python、没有运行原生检查器，也不签发质量结果。C35 仍须实现旧 argv、字段、MCP/Hook 宿主接线及每种入口的真实回放；本表与纯映射测试不能替代这些运行时验收。
