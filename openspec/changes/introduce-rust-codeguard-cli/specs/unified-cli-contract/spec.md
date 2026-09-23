## Purpose

定义 Rust Codeguard 的统一请求、语言选择、报告、退出码及多入口转换协议，使局部检查成功与完整交付认证具有明确边界，调用方无需猜测原生工具状态。

## ADDED Requirements

### Requirement: Unified commands SHALL select explicit check obligations

Rust CLI MUST 提供 `lint/comments/cve/security/build/check <language|all> [path]`；`check` 包含全部适用类别。语言别名 MUST 来源于统一注册表，未知语言在执行前拒绝。部分命令 MUST 明示 selection，不得据局部通过声明项目全部通过。`plan` MUST 仅规划，不执行构建、扫描、下载、安装或修改源码。

#### Scenario: Java lint succeeds in a mixed project
- **WHEN** Java lint 完成，但项目仍有 Python、安全或 CVE 义务未在该请求执行
- **THEN** 请求可成功，交付状态为 not_evaluated，不能宣称全项目通过

#### Scenario: User requests a plan
- **WHEN** 调用 `codeguard plan check all .`
- **THEN** 返回义务与待解析前置条件，不执行外部构建或扫描

#### Scenario: A language identifier is unknown
- **WHEN** 用户输入未注册的语言 ID
- **THEN** 执行前返回用法错误，列出规范 ID/别名，不启动检查器

### Requirement: Rust CLI SHALL expose a versioned exit contract

Rust CLI MUST 使用 0 请求通过、1 违规、2 用法错误、3 必需义务未完成、4 内部故障、130 取消。执行后的聚合优先级 MUST 为取消、内部故障、未完成、违规、通过；已有发现 MUST 保留。原生退出码 MUST 独立记录，不直接透传作为 CLI 结论。

#### Scenario: Findings coexist with an unavailable scanner
- **WHEN** lint 有已确认违规且必需 CVE 工具不可用
- **THEN** 返回 3，报告同时包含违规和未完成项

#### Scenario: Native tool exits with code two
- **WHEN** 工具原生退出 2
- **THEN** 依据该工具契约生成结果，不将其直接解释成 Codeguard 用法错误

### Requirement: Reports SHALL preserve semantics across public formats

报告 MUST 带 schema_version、请求选择、内容/策略/工具身份、逐项完整性、发现、覆盖及交付判定。human/JSON/SARIF/MCP MUST 来源于同一语义报告。结构化 stdout MUST 不混入进度或原始日志；公开结果 MUST 脱敏，私有原始证据单独存储。未知协议 major MUST 拒绝消费。

#### Scenario: SARIF contains no findings but a required task timed out
- **WHEN** 一个必需检查超时且没有有效 finding
- **THEN** SARIF 仍表达未完成，标准报告不得变成干净通过

#### Scenario: Tool output contains a credential
- **WHEN** 工具 argv 或诊断含凭据
- **THEN** MCP 与公开报告不回显原文，保留可用的私有证据引用

### Requirement: Empty selection SHALL NOT certify delivery

显式语言请求无目标 MUST 为未完成。全部发现后证明确无适用义务时 MAY 返回请求成功，但 MUST 标明 not_applicable，MUST NOT 生成交付 allow。缺失工具或 adapter MUST NOT 被当成无适用目标。

#### Scenario: Java command runs in the wrong directory
- **WHEN** 显式 `lint java` 未发现 Java 目标
- **THEN** 返回 3 并说明无匹配目标，不能报告 Java 已通过

#### Scenario: Empty project has no applicable checks
- **WHEN** 完整发现证明项目无适用检查对象
- **THEN** 标为 not_applicable 且 eligible=false，不签发交付通过
