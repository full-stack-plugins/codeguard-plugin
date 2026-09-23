## Purpose

定义质量策略、原生配置、工具链和规则包的权威及变更流程，确保降低误报依靠准确证据而不是智能体自行关闭检查，并保留可复核的例外与历史问题记录。

## ADDED Requirements

### Requirement: Quality policy SHALL be independent from operational options

必需检查、规则、阈值、排除、测试要求及漏洞库时效 MUST 来源于批准策略。CLI/env 运行参数 MUST NOT 弱化它们；同一 PR 的策略修改 MUST NOT 在未经批准时为自身代码签发通过。config explain MUST 显示原生配置及 suppression 的有效来源和差异。

#### Scenario: Agent raises the severity threshold
- **WHEN** 智能体通过参数、环境或本地配置把批准阈值提高
- **THEN** 新交付门禁不接受该弱化，记录策略差异而非通过

#### Scenario: A checker disables all native rules
- **WHEN** 原生配置改为禁用必需规则或以自定义空命令替代
- **THEN** 覆盖校验不能满足义务，不以命令成功通过

### Requirement: Rulepacks and toolchains SHALL be versioned and locked

rulepack MUST 有版本、规则来源/许可、稳定规则映射、内容摘要及工具兼容范围。检查 MUST 验证工具/运行时/配置/规则锁；扫描 MUST NOT 隐式安装、升级或改写项目配置。安装 MUST 是单独显式动作，离线检查 MUST 不联网。

#### Scenario: Tool version differs from the lock
- **WHEN** PATH 工具与锁不匹配
- **THEN** 未完成并给出准备动作，不自动下载 latest

### Requirement: Historical findings SHALL remain findings

基线 MUST 只用于 new/existing 分类和趋势，不得默认豁免存量违规。所有阻断规则 MUST 对新旧发现一致生效。基线不可读或无法比较 MUST 不删除当前发现。

#### Scenario: A harmless edit leaves an old violation
- **WHEN** 完整检查在未修改源码中检出已有的阻断违规
- **THEN** 可标 existing，但仍阻断，不因历史身份或 diff 位置豁免

### Requirement: Exceptions SHALL require independently verifiable authority

例外 MUST 同时绑定规则、范围、内容身份、到期时间、原因和可核验的批准身份，不能采用永久无期限例外。agent 声称获批、skipGate、可写 JSON 或普通 Git config MUST NOT 本身构成授权。例外 MUST 保留原始发现及非通过检查状态；外部批准交付必须与普通 PASS 区分。文档 MUST 明示同权限本地进程不可提供不可绕过保证。

#### Scenario: Agent writes a local approval flag
- **WHEN** 智能体写 `approved=true` 或 `codeguard.skipGate=true`
- **THEN** 新交付门禁不接受为授权，不改变违规或未完成状态

#### Scenario: A real exception expires
- **WHEN** 经批准例外超过有效期或不匹配当前范围
- **THEN** 不应用该例外，保留完整门禁要求

#### Scenario: Expiry is absent or content changes
- **WHEN** 例外没有到期时间或当前内容不匹配获批身份
- **THEN** 拒绝应用例外，不能沿用此前批准关闭问题

### Requirement: Existing dot-prefix scope SHALL remain explicit

本变更 MUST 保留普通检查面点前缀默认忽略、不逐路径告警，以及入库安全和配置发现两项例外。覆盖报告 MUST 记录有效策略与汇总范围，不能宣称排除内容已检查。新增扫描或放宽禁止入库策略 MUST 经独立策略变更。

#### Scenario: Dot configuration and secret coexist
- **WHEN** 项目含点前缀 linter 配置、普通点前缀源码和拟入库 `.env`
- **THEN** 配置仍发现、普通源码按策略忽略、入库安全照常运行，三者不混为同一排除
