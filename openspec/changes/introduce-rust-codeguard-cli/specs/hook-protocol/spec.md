## MODIFIED Requirements

### Requirement: The cheat-sheet SHALL document fail-open for uncaught exceptions

`hooks/__protocol__.md` MUST 按运行时和事件区分：legacy-v1 未捕获异常保留 stderr 诊断和 exit 0 的旧兼容行为；普通保存/提示反馈不承担交付阻断。迁移到 Rust 严格交付模式的 Git/CI/PreToolUse 入口遇到内部故障 MUST 依宿主协议阻断并说明未完成，不能 fail-open。宿主不支持可靠阻断时 MUST 明示能力边界并依赖真实 Git/CI，不得声称该宿主已提供硬门禁。

#### Scenario: A hook hits an unexpected exception
- **WHEN** 显式旧兼容 Hook 顶层异常
- **THEN** 记录诊断并按旧 exit 0，不能称为新认证成功

#### Scenario: A migrated delivery hook hits an unexpected exception
- **WHEN** 严格交付入口内部失败
- **THEN** 按宿主阻断协议拒绝交付并报告未完成

### Requirement: Soft and hard gates SHALL share the skipGate escape and neither may fall back to scanning outside a git repository

共享 `codeguard.skipGate` 的豁免 MUST 仅存在于 legacy-v1，维持旧计数和 Stop 汇总。Rust 交付 MUST 不接受此字段作为授权，例外遵循 rulepack-governance。非 Git 目录的 Git 事件 MUST 不回退扫描整个 workspace；普通显式 CLI 项目扫描不受该 Git 前提限制。

#### Scenario: SkipGate set, user asks to commit
- **WHEN** legacy-v1 设置了 skipGate 且消息触发提交意图
- **THEN** 按旧约定退出和记账，并标明不提供新认证

#### Scenario: SkipGate set with a secret on the commit face
- **WHEN** 仓库已设 skipGate 且用户消息触发提交意图，待提交面含敏感模式文件
- **THEN** 软门禁注入入库安全报告（非阻断）；硬门禁在同一提交面 exit 2

#### Scenario: Rust agent sets skipGate
- **WHEN** 新交付入口发现同名 Git config 或链式设置
- **THEN** 不作为质量豁免，仍按完整 contract 检查

#### Scenario: Prompt fires outside any git repository
- **WHEN** Git 提交提示发生于非 Git cwd
- **THEN** 说明没有目标仓，不扫描整个 workspace，也不称交付已通过

### Requirement: Fail-open uncertainty SHALL be visible

legacy-v1 的 PreToolUse 放行工具故障 MUST 继续通过 additionalContext 明示未验证。Rust 交付入口 MUST 根据报告的 gate decision 映射宿主动作，必需 incomplete 与 deny 均阻断；普通 UserPromptSubmit/PostToolUse 反馈 MUST 保持可见未完成，不得宣称 all passed 或承担未实现的阻断。新 CLI exit 2 是用法错误，MUST NOT 直接当作所有宿主的阻断语义透传。

#### Scenario: A tool cannot run at the Git gate
- **WHEN** 旧入口缺工具
- **THEN** 按旧协议 exit 0 且明确未验证

#### Scenario: Tool cannot run at a migrated gate
- **WHEN** 新严格入口缺必需工具
- **THEN** 映射为宿主阻断，说明恢复工具链所需动作，不假称代码有错

### Requirement: Skip-gate bypass values SHALL be parsed strictly

legacy-v1 的 `CODEGUARD_SKIP_GATE` MUST 只认 1/true/yes（大小写不敏感）；0/false/空串不豁免，提示词保持原值域与传递边界说明。Rust 新流程 MUST 不将任何该变量值解释为授权，不能仅因保留旧环境变量而失去严格门禁。

#### Scenario: Zero and false values do not bypass
- **WHEN** 旧入口变量为 0 或 false
- **THEN** 旧门禁照常检查

#### Scenario: Accepted values bypass consistently
- **WHEN** 显式旧入口变量为 1/true/yes
- **THEN** 按旧协议豁免并审计，不签发新认证

#### Scenario: Rust receives an accepted legacy value
- **WHEN** 新入口继承 CODEGUARD_SKIP_GATE=true
- **THEN** 仍执行完整门禁，不把变量存在当批准

## ADDED Requirements

### Requirement: Migrated host surfaces SHALL share the same report semantics

CLI、MCP、宿主 Hook、真实 Git Hook 与 CI 对相同请求和证据 MUST 得到相同核心结果；差异仅为入口展示和协议映射。绑定二进制/协议失败 MUST 未完成；核心报告 MUST 不由宿主或智能体重写。迁移 MUST 为三宿主提供真实调用证据。

#### Scenario: Mixed findings and incomplete evidence reach three hosts
- **WHEN** 同一标准报告包含违规及未完成项
- **THEN** 各宿主均保留二者，严格交付入口阻断，保存反馈不冒充交付通过
