## MODIFIED Requirements

### Requirement: Languages may declare a configuration prerequisite

注册表 MUST 允许声明配置前置条件，避免采用不适合项目的默认规则。legacy-v1 缺配置时维持未接入/未验证且旧 Hook 放行语义。Rust 新入口 MUST 使用已批准 rulepack 或已接入的项目配置；如果不能可靠满足前置条件，必需义务为 incomplete，不能通过“未接入”自动免除。

#### Scenario: 已声明前置条件且项目未接入
- **WHEN** legacy-v1 项目缺少声明配置
- **THEN** 按旧协议说明未验证并兼容放行，不签发新认证

#### Scenario: Rust required configuration is missing
- **WHEN** 新入口没有项目配置且无法使用批准规则包建立可靠计划
- **THEN** 返回 configuration_required 和未完成，不报代码违规、不满足交付门禁

#### Scenario: 已声明前置条件且项目已接入
- **WHEN** 原生配置存在且满足批准策略
- **THEN** 按有效配置执行，保留配置来源和覆盖证据

#### Scenario: 未声明前置条件的语言不受影响
- **WHEN** 工具契约不要求额外配置
- **THEN** 正常按已批准规则和工具锁执行，不凭空新增项目配置障碍

### Requirement: Gates in git repositories SHALL default to changed-file scope

本条标题描述 legacy-v1：旧门禁 MUST 保留 delta 默认、gate_scope=repo、FULL_SCAN_EXCLUDES、index/预测暂存/HEAD 的历史输入规则与完整诊断；准确快照不复用旧软缓存。Rust 新门禁 MUST 建立全部适用必需义务，增量仅作为等价执行优化，不能默认豁免未修改文件中的问题。新真实 Git 入口 MUST 使用 execution-kernel 的实际 index/ref 契约。

#### Scenario: A committed legacy issue is untouched by a clean change
- **WHEN** legacy-v1 改动仅文档且项目检查确实不适用
- **THEN** 明示无须执行，不伪称完成项目验证

#### Scenario: A new staged file introduces a problem
- **WHEN** index 内容违规但工作树已修好
- **THEN** 检出 index 违规，不借用工作树通过

#### Scenario: A bad commit made outside the gate must not slip through the push
- **WHEN** 实际待推送内容违规但工作树已修好
- **THEN** 检查待推送内容并保留违规

#### Scenario: Push with no resolvable upstream does not crash
- **WHEN** 旧入口没有可解析上游
- **THEN** 保留 HEAD 全树回退，不因空基线跳过

#### Scenario: A chained commit-and-push takes the wider face
- **WHEN** 宿主可可靠建模同仓 commit→push
- **THEN** 覆盖拟提交内容和已有待推送内容；不可建模时明示未完成

#### Scenario: Rust optimization leaves an obligation unproven
- **WHEN** 增量计划没有执行某必需任务且无等价缓存证明
- **THEN** 不能据 delta 干净签发交付 allow

### Requirement: A toolchain crash SHALL be recorded as unverified, not as a lint failure

检查器退出码 MUST 结合工具契约判定，工具故障 MUST 不认作代码违规。legacy-v1 保留 UNVERIFIED、CLI 1、Hook 可见放行。Rust MUST 将该义务标 incomplete、CLI 3，必需检查不满足交付；混合有效发现仍保留。不能统一把所有工具 exit 2 当配置错误，也不能把所有 exit 1 当违规。

#### Scenario: An npx tool crashes with exit 2
- **WHEN** ESLint 因配置问题以 exit 2 退出
- **THEN** 旧接口为 UNVERIFIED；新接口为 incomplete，均不能称为 lint 违规或通过

## ADDED Requirements

### Requirement: Rust command plans SHALL preserve explicit build levels

Rust build MUST 记录编译、静态检查和测试执行的区别。Java 默认静态构建保留不运行测试的等级；批准策略要求测试时 MUST 执行，智能体不得自行追加 skip。自定义命令 MUST 通过义务覆盖核对，不能只凭 exit 0 替代质量证据。

#### Scenario: Policy requires tests
- **WHEN** 项目批准策略要求构建时运行测试
- **THEN** 新计划包含测试执行，运行参数不能静默排除 test

#### Scenario: Default static build completes
- **WHEN** 默认静态构建成功但未运行测试
- **THEN** 报告 test_execution=false，不声称测试通过

#### Scenario: Native Cargo check reports an attributed compiler error
- **WHEN** Rust 静态构建调用原生 Cargo check，机器流包含完整 package/manifest/target 身份、可归属的编译诊断及失败结束记录
- **THEN** 保留原生编译诊断与目标身份，明确 build_level=type_check、test_execution=false；不将它改称 Clippy、文档或安全违规，不从局部目标结果推导完整项目或交付结论

#### Scenario: Native Cargo build report lacks a valid completion contract
- **WHEN** Cargo 静态构建机器流损坏、重复语义键、无结束记录、结束后仍有事件、成功结束却含 error，或进程失败而无可归属编译诊断
- **THEN** 构建结果保持未完成；有效已观察诊断可保留为调查证据，但不能把裸退出码、空输出或环境故障认作源码违规或通过

#### Scenario: Public Cargo type-check probe encounters changed inputs or cancellation
- **WHEN** build rust的显式原生类型检查执行时源码、根清单、锁或工具身份变化，或用户取消同轮执行
- **THEN** 报告绑定本轮原生状态和输入摘要，保留调查证据且移除源码修复许可；取消优先返回130；完整且目标归属唯一的局部诊断才提供限定目标修复指引，仍明确test_execution=false、coverage_proven=false和交付not_evaluated，不将局部成功当作完整策略或任务关闭

#### Scenario: Cargo build observations synchronize without closing old tasks
- **WHEN** 已初始化工作区重复扫描同一编译错误，或未消费报告的源码/原生目标/清单/锁字节已经变化
- **THEN** 当前有效观察只更新同一稳定问题和修复任务，next指向原生构建检查；陈旧证据保留为历史并生成重扫准备任务，坏身份拒绝导入；环境失败生成准备任务，不生成源码违规，同步或任务勾选不得关闭问题

#### Scenario: Cargo build task rechecks through the original checker
- **WHEN** 智能体对稳定的 Rust 编译任务执行 task verify，并显式提供同一原生 Cargo 工具
- **THEN** 在任务租约和统一截止时间内重新执行 Cargo check，绑定源码、清单、锁与工具身份，保存关联任务和尝试的复检事件；原错误仍在时返回 still_present，工具或输入异常返回 incomplete

#### Scenario: Cargo build task has no diagnostic in a local recheck
- **WHEN** 原生 Cargo check 本轮无错误，而完整项目策略、目标组合或规则覆盖尚未核验
- **THEN** 仅返回 candidate_absent_unverified_policy 或环境恢复候选，保留原任务 open，next 指引核查原生配置和完整交付；不得凭零诊断、白名单候选或任务勾选自动关闭

#### Scenario: Unified check schedules native Rust type checking
- **WHEN** `check all` 发现 Rust 源码，调用方提供绝对 Cargo 工具，并有可读取的根 Cargo 清单与锁
- **THEN** 在同一任务图、共享截止时间和 Cargo 构建资源约束下调用原生 Cargo check；反馈独立保留编译 finding、构建等级和是否执行测试，已初始化工作区同步稳定任务并在对话中给出下一步；局部构建成功仍不授予完整覆盖或交付通过

#### Scenario: Unified Rust build check cannot complete
- **WHEN** Cargo 缺失、原生机器流损坏、目标归属不明、输入或工具变化、执行超时或取消
- **THEN** `check all` 保留本轮原生诊断和具体未完成原因，生成可恢复的环境/完整性任务；不得将故障算源码编译违规、白名单命中或空结果通过
