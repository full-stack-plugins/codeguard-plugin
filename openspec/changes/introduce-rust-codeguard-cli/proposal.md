# Proposal：统一 Rust Codeguard CLI

## Why

Codeguard 的目标是调用传统静态工具，完成多语言代码规范、注释规范、依赖漏洞、安全和构建质量检查。当前实现把工具故障、基线豁免和宿主放行混在交付路径中，智能体容易通过降低检查要求消除报错；需要统一执行与证据契约，恢复“准确检查、完整交付”的产品边界。

项目侧以**识别实际检查配置 → 调用已配置的原生工具 → 将结果反馈到智能体对话**为主流程。检测族目录只提供发现线索，不要求每个项目证明所有候选检查都执行过；未配置与运行失败分别给出配置或环境恢复建议。

## What Changes

- 建立独立 Rust workspace `codeguard-cli/`，四个 crate 分别负责入口、领域契约、执行基础设施、工具适配；发布可执行文件 `codeguard`。
- 提供 `lint/comments/dependencies/cve/security/build/check <language|all>`，CLI、MCP、Git 与宿主入口复用同一检查内核。
- 固化完整命令目录：发现准备、配置与工具管理、准确内容门禁、持久修复和协议入口；逐项定义输入输出、副作用、操作退出语义、执行预算和下一步，避免查询/安装成功被当成质量通过。
- **BREAKING**：新 CLI 协议采用 0 通过、1 违规、2 用法错误、3 未完成、4 内部故障、130 取消；旧协议通过显式兼容入口保留，禁止根据数字猜测状态。
- **BREAKING**：迁移后的交付门禁要求必需检查全部完成；工具故障不认定为代码违规，也不再允许被当作交付通过。
- **BREAKING**：新流程不接受智能体自行设置 skipGate、降低阈值、增加 suppression 或使用存量基线豁免；基线仅分类问题。
- 用版本化 rulepack、工具链锁、结构化报告、检查覆盖账本和真实样本评测降低误报；保留全部真实发现与不确定性。
- 将运行关联追踪、私有证据保留和分层评测门槛纳入正式规格；建立逐需求/命令/语言/平台/宿主的实施覆盖索引，明确尚需实测的参数及关闭任务。
- 在项目内初始化 `./codeguard/`，将脱敏问题、环境阻塞、修复任务和复检事件持久化；原始报告与缓存由目录内 .gitignore 忽略，通过 next/task verify 指导智能体闭环修复。
- init 识别项目边界、语言/版本、构建器、架构证据与模块依赖，形成结构化画像和检查准备任务，在被检查项目 AGENTS.md 安全维护受管摘要。
- 迁移当前注册表全部 57 个条目，逐项验收 54 个 stable 的实际能力，保留 3 个 planned 的真实状态；禁止用少数语言演示代替全量迁移。
- 保留项目既有点前缀忽略及入库安全、配置发现例外；各检查类别明确适用条件和能力缺口。

## Capabilities

### New Capabilities

- `unified-cli-contract`：统一命令、选择范围、版本化报告、CLI/MCP 协议。
- `native-tool-adapters`：工具适配、类别覆盖、Java 原生工具链和全语言迁移。
- `rulepack-governance`：规则版本、可信策略、禁止自动弱化、例外和基线治理。
- `binary-distribution`：二进制与插件版本绑定、兼容迁移、发布验收。
- `remediation-workflow`：持久问题和待办、修复简报、任务租约、真实复检关闭与重开。
- `project-initialization`：项目画像、架构证据与模块图、AGENTS 受管摘要、幂等刷新及准备状态。

### Modified Capabilities

- `verdict-integrity`：新增 Rust 双维结果和完整性交付门禁；明确旧入口的协议边界。
- `execution-kernel`：新增 Rust crate 边界、进程生命周期、准确缓存与快照约束；显式隔离旧实现兼容要求。
- `language-gate-commands`：区分旧流程与新 CLI 的前置条件、范围及工具故障语义。
- `hook-protocol`：限定旧 fail-open/skipGate 契约，规定迁移后交付入口的阻断和宿主映射。
- `scan-scope-policy`：为受管 Codeguard 产物添加精确自扫描边界，用户源码和入库安全不受影响。

## Impact

未来代码归属：`codeguard-cli` 持有 Rust 内核、适配器、规则和协议；本插件持有宿主入口、运行时版本绑定；`codeguard-skills` 持有技能事实源。现有 `skills.lock.json` 管理边界不变。

设计阶段仅交付规格与执行任务；后续实施已在相邻独立工作目录 `../codeguard-cli/` 建立 Rust 四 crate 工程基线，尚未建立远程源码仓、修改 Python 运行行为、升级安装或发布。正式规格以本 change 的 `specs/` 为准；实现完成前不 sync/archive。旧 OpenSpec change 的宿主副本治理另行保留，不并入或伪称已完成。

相关说明：[架构文档](../../../docs/rust-cli/architecture.zh-CN.md)、[技术方案](../../../docs/rust-cli/technical-design.zh-CN.md)、[语言迁移与验收](../../../docs/rust-cli/coverage-and-acceptance.zh-CN.md)。
