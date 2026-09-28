# 旧实现增量核对（2026-09-24）

这份记录为 OpenSpec 1.1 的**进行中证据**。当前插件 HEAD 为 `9e4adb1`；原设计读取的 `03ebb24` 不是最新源码。两提交间旧运行时代码有 9 个文件变化。`scripts/languages.json` 未变，SHA-256 为 `012370f9d83a2daeb3cc87fef292a7509e85b53540ce9adf1eaf171f0910d251`，仍是 54 stable / 3 planned。逐语言差异与后续验收入口见 [语言迁移表](coverage-and-acceptance.zh-CN.md#2-全量迁移清单)；Rust 工程固定了该清单快照，并在 `codeguard-cli/crates/codeguard-cli/tests/capability_inventory.rs` 核验 57×5×5 个显式缺口，不能把旧注册状态当作新能力。

| 旧源码增量 | 新流程归类与依据 | 已有回归样本 / 后续 fixture |
|---|---|---|
| `hooks/__protocol__.md`：旧 skipGate 只豁免语言检查，入库安全仍检查 | **保留 legacy-v1**；新交付完全拒绝 skipGate 自授权。见 hook-protocol、rulepack-governance | `tests/test_skip_gate_safety_scope.py`；新入口 F13/F22 待实现 |
| `scripts/codeguard/gate.py`：采集缓存身份前补 PATH | **保留正确行为**，但新缓存必须绑定真实有效环境身份。见 execution-kernel | `tests/test_skip_gate_safety_scope.py`；新缓存 F09/F10 待实现 |
| `scripts/codeguard/git_guard_application.py`：语言豁免后仍执行安全路径检查 | **legacy-v1 兼容 + 新流程纠偏**：保留安全发现，新入口不得接受豁免。见 hook-protocol、scan-scope-policy | `tests/test_skip_gate_safety_scope.py`；新 Git F16/F18 待实现 |
| `scripts/codeguard/prompt_application.py`：软反馈同样保留安全报告 | **legacy-v1 兼容**；新软反馈不能冒充硬门禁。见 hook-protocol | `tests/test_skip_gate_safety_scope.py`；新宿主 F22 待实现 |
| `scripts/codeguard/toolchain.py`：补 PATH，缺入口时探测 Python 模块并给诊断 | **保留正确诊断**，但不得把模块探测成功当作原命令可执行。见 unified-cli-contract、native-tool-adapters | `tests/test_skip_gate_safety_scope.py`；新 doctor F03 待实现 |
| `scripts/paths.py`：补符号链接解释器真实 scripts 目录 | **保留正确路径发现**，工具仍需锁身份与实际启动证明。见 execution-kernel、rulepack-governance | `tests/test_skip_gate_safety_scope.py`；新 tools verify/doctor 待实现 |
| `scripts/codeguard/reporting.py`：说明旧豁免范围 | **legacy-v1 兼容**；新修复简报不得推荐绕过。见 hook-protocol、remediation-workflow | `tests/test_skip_gate_safety_scope.py`；新 RepairBrief 待实现 |
| `scripts/check_architecture.py`：容纳旧模块新增依赖 | **只保留旧架构校验**；新四 crate 方向由独立检查拒绝反例。见 execution-kernel | `tests/test_architecture.py`；`codeguard-cli/crates/codeguard-cli/tests/crate_boundaries.rs` |
| `scripts/bump-plugin.mjs`：Claude 版本路径写后核对 | **保留发布正确性**；新二进制与插件锁/市场仍需分层验收。见 binary-distribution | `tests/test_plugin_manifests.py`；新发布验收 13.4 待实现 |

旧源码中仍存在新规范明确纠偏的共性行为：通用 `rc=1` 推断 finding、最多 50 文件时的 delta/基线豁免、缺工具旧 Hook 放行、Java Maven verify 代替多项质量义务。它们分别由 native-tool-adapters、verdict-integrity、execution-kernel、hook-protocol 和 language-gate-commands 的新要求替换；当前仅有领域聚合测试，真实新适配器和完整对照 fixture 尚未落地，因此 OpenSpec 1.1 **仍未完成**。
