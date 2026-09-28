## MODIFIED Requirements

### Requirement: Verdicts SHALL preserve uncertainty across interfaces

显式 legacy-v1 入口 MUST 保持 PASS、FAIL、UNVERIFIED、SKIPPED、PLANNED 及原聚合退出约定：通常 FAIL=2、无 FAIL 但有未验证/计划项=1、已验证或无须检查=0；各旧子命令的已记录差异由兼容层保持。仅真实成功检查允许 passed=true，无法验证不得触发自动修复或 all passed。

旧 `check`、CVE 与 Dockerfile MUST 分别保留其混合优先级：前两者在已确认 FAIL 与 UNVERIFIED 并存时返回旧 2，Dockerfile 在同样组合时返回旧 1 且保留已确认风险。旧 CVE 参数错误是 3，而其他使用 argparse 的旧检查/修复/规划入口参数错误为 2；旧 PreToolUse 的 2 是宿主拦截。兼容投影和 MCP/Hook 生命周期成功都 MUST 固定为新版交付 `not_evaluated`，不得按旧数字推导新版 allow。

Rust 新入口 MUST 使用 unified-cli-contract 的版本化协议，MUST 将执行完整性与 findings 分离；混合未完成和违规保留两者并退出 3。CLI/MCP/Hook 转换 MUST 根据协议和结构化语义，不能根据同一个数字猜测通过。此版本边界同样约束旧 CVE、Dockerfile 等结果在新入口的映射。

#### Scenario: Configuration error survives MCP serialization
- **WHEN** 旧入口检查器因配置错误退出且没有有效违规结论
- **THEN** 旧 CLI 退出 1，旧 MCP 返回 passed=false、UNVERIFIED 和原因

#### Scenario: Configuration error survives Rust MCP serialization
- **WHEN** 新入口同一检查因配置错误未完成
- **THEN** Rust CLI 退出 3，MCP 保留 incomplete，不能通过协议转换生成 PASS

## ADDED Requirements

### Requirement: Required completeness SHALL gate Rust delivery

Rust 交付普通 allow MUST 同时满足全部适用必需义务完成、覆盖匹配、内容与批准策略身份有效、无原始阻断违规。缺工具、无实现、坏报告、超时、缓存身份失败或输入变化 MUST NOT 成为 allow。未选择的类别与有理由不适用的类别 MUST 明确区分。

有效误报白名单命中不得抹去原始阻断发现。若全部义务完整、无未经处置的阻断 finding，且存在有效批准的精确误报处置，交付决策 MUST 为 `allow_with_exceptions`，不得显示普通 `allow`；未完成优先于违规和例外放行，未处置的阻断优先于例外放行。`allow_with_exceptions` 仅表示本次输入在带批准引用的策略下可交付，不表示原工具没有报告问题。

#### Scenario: No findings but a required tool is missing
- **WHEN** 已运行检查无违规但另一必需工具缺失
- **THEN** 交付 incomplete，不制造代码违规，也不允许交付

#### Scenario: Project scope changes while native checks run
- **WHEN** 初次发现后、原生工具运行期间，项目新增源码或改变原生规则配置
- **THEN** 检查结果保留已经取得的原生发现，并明确标记本轮范围变化、要求重新发现与复检；第二轮发现不能被自动当作批准义务账本。仅有 CodeGuard 自有受管记录变化时不得误报项目范围变化

#### Scenario: Existing source bytes change while native checks run
- **WHEN** 初次发现的源码路径不变，但原生检查器或并发编辑改变该路径的文件字节
- **THEN** 本轮检查标记输入内容变化并保持 incomplete，保留已观察到的原生诊断；无法安全捕获或复核全部目标字节时也保持 incomplete，不得把静态路径集合未变解释为内容稳定

#### Scenario: Finding remains in a historical file
- **WHEN** 必需规则检出历史文件中的违规
- **THEN** 保留 finding 并按同一策略阻断，基线分类不能改变结果

#### Scenario: Approved false positive is the only blocker
- **WHEN** 全部适用义务完整，唯一原始阻断 finding 有当前输入匹配的可信误报白名单
- **THEN** 报告保留原始 finding 和处置引用，交付决策为 allow_with_exceptions

#### Scenario: Approved false positive coexists with a real violation
- **WHEN** 同轮有有效误报白名单与未经处置的阻断 finding
- **THEN** 两者均报告，交付决策为 deny；若还有未完成义务则为 incomplete

### Requirement: Coverage SHALL not change with scheduling strategy

Rust MUST 在调度前依据项目配置、适配能力和批准策略建立完整的**实际必需义务**；候选检测族目录不自动生成义务。分批、并发、缓存和增量 MUST 保持这些必需义务的等价覆盖与判定；计划复用而未重跑的必需义务必须具有有效复用依据，否则未完成。这是交付判定的覆盖约束，不要求向智能体额外展示逐候选检测族的执行证明。文件数量阈值 MUST NOT 改变历史问题是否阻断。

#### Scenario: A clean extra file crosses a batching boundary
- **WHEN** 目标从 50 个增加至 51 个文件但已有违规未变
- **THEN** 原违规的门禁影响不变，不能因切换扫描方式而豁免或新增归因
