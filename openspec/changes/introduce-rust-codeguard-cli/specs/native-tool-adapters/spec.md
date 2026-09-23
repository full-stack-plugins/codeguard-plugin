## Purpose

定义传统原生工具在 Codeguard 内的适用性、执行、结果解释与覆盖证明，使语言注册、工具安装、诊断能力和实际检查完成不再被混为同一种支持状态。

## ADDED Requirements

### Requirement: Adapters SHALL publish verifiable capability contracts

每个 adapter MUST 声明语言/方言、类别、工具和运行时兼容范围、配置前提、输入范围、报告格式及退出语义。语言每个类别 MUST 明确 implemented、gap 或有证据的 not_applicable。formatter 存在 MUST NOT 自动证明 lint/comments 能力。

#### Scenario: A stable legacy entry has only a formatter
- **WHEN** 迁移 Julia 或 Pascal，原 lint 命令为空
- **THEN** 补充经过真实验收的只读检查能力前保持能力缺口，不能据旧 stable 标签通过

#### Scenario: Shell dialect is unsupported
- **WHEN** 项目含 zsh，而选定 ShellCheck 不支持该方言
- **THEN** 为其保留能力缺口或选择已验证的专用适配器，不静默删除义务

### Requirement: Native evidence SHALL be interpreted per tool contract

adapter MUST 根据工具版本的报告及退出语义解析结果；MUST NOT 以通用非零、exit 1、关键词或模型主观判断替代。无效、截断、陈旧、与计划不符或内部矛盾的报告 MUST 产生未完成。有效部分发现 MUST 保留。

#### Scenario: Valid finding precedes a crash
- **WHEN** 工具先产生有效违规，随后发生配置或进程故障
- **THEN** 保存该 finding 并记录 incomplete，不覆盖为纯工具错误或完整违规结果

#### Scenario: Tool exits zero with a stale report
- **WHEN** 报告属于此前内容或当前规则未执行
- **THEN** 拒绝将其作为本次通过证据

### Requirement: Java checks SHALL prove each required native obligation

Java MUST 分别建立 P3C、通用 lint、注释、安全、依赖漏洞和构建的适用义务。官方 P3C MUST 使用经验证的 P3C PMD 实现和兼容工具链；Checkstyle 配置名 MUST NOT 充当官方 P3C 的执行证据。Maven/Gradle 生命周期成功 MUST 结合实际绑定/执行证据，不能覆盖未运行的质量任务。

#### Scenario: Verify succeeds without quality plugins
- **WHEN** `mvn verify` 成功但未运行所需 P3C/Javadoc 检查
- **THEN** 对应义务仍未完成，`check java` 不能显示全部通过

#### Scenario: JDK and PMD are incompatible
- **WHEN** P3C 规则运行因 JDK/PMD 组合失败
- **THEN** 报告具体工具链未完成，不记为代码违规，不自动换规则或跳过

### Requirement: Comment and security categories SHALL retain their own evidence

注释检查 MUST 根据语言与规则验证其确定性要求，不得以格式化代替。源代码安全、配置安全、入库策略和 CVE MUST 分开归类；仅命中禁止文件模式 MUST 报策略违规，不得无内容证据声称检测到真实私钥。未实现的语义能力 MUST 明示。

#### Scenario: Public API lacks required documentation
- **WHEN** 有效规则要求文档且源码缺少对应注释
- **THEN** 原生或经验证的确定性规则输出注释违规，普通 formatter 成功不消除该义务

#### Scenario: Public certificate matches a forbidden path rule
- **WHEN** 文件命中现行禁止入库模式但没有私钥内容证据
- **THEN** 按策略违规报告，不能将文件名命中写成已确认密钥泄露

### Requirement: CVE checks SHALL bind actual dependency and database identity

Rust CVE 检查 MUST 绑定实际解析的组件版本、依赖来源、advisory 标识和数据库身份/时效。无可靠组件匹配、数据库过期、离线无合格库、缺失必要严重度时 MUST 保留发现与不确定性，不产生无依据的安全通过或确定高危。原生工具缺失 MUST NOT 静默换覆盖不同的通用工具。共享扫描 MUST 可追溯到全部被满足的义务。

#### Scenario: Offline database is too old
- **WHEN** 离线数据库超过批准的 freshness
- **THEN** CVE 未完成，不以零匹配判安全

#### Scenario: Report has no comparable severity
- **WHEN** 已知漏洞没有策略阈值需要的严重度
- **THEN** 保留 finding；无法按策略判定时未完成，不预过滤 UNKNOWN

### Requirement: Migration SHALL account for every legacy language entry

迁移 MUST 逐项登记基线注册表全部 57 项，包括 54 stable 和 3 planned；前者完成五类别适用性和真实 adapter 验收前 MUST NOT 宣称全量迁移完成。planned MUST 保持显式状态，不能为凑数量创建空实现。注册表变化 MUST 重新做差异核对。

#### Scenario: Four major languages are implemented
- **WHEN** 仅 Java/Rust/Python/TypeScript 已可用
- **THEN** 只能声明这部分能力完成，剩余迁移任务仍未完成
