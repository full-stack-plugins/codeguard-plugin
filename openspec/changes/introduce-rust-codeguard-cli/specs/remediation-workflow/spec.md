## Purpose

定义项目内持久的问题、环境阻塞、修复任务和复检事件，使智能体能够恢复上下文并逐步完成修复，同时保证任务文件、人工勾选和删除记录不能替代原生工具的验收证据。

## ADDED Requirements

### Requirement: Projects SHALL have an explicitly initialized remediation workspace

Codeguard MUST 支持 `./codeguard/` 及其中的 .gitignore、工作区清单、脱敏 findings/events、任务与决策引用；原始 reports/runs/cache/worktrees/state MUST 默认 Git 忽略。初始化 MUST 提供 dry-run/apply，不覆盖已有用户文件，不创建第二份质量策略。

#### Scenario: User already has files under codeguard
- **WHEN** 初始化遇到同名用户目录或冲突文件
- **THEN** 给出精确合并/冲突计划，不强制覆盖，不全目录忽略用户源码

### Requirement: Findings and environment blockers SHALL produce distinct actionable tasks

持久同步 MUST 区分真实 finding 与检查未完成的 blocker，按稳定身份归并重复发现、保留原规则与证据。部分报告 MUST 只能增加有效发现/阻塞，不能因缺失旧 finding 自动关闭。任务 MUST 包含问题依据、允许改动、修复步骤、前置依赖、复检条件及历史尝试。

同步 MUST 按 run_id 幂等消费所有未导入且身份匹配的报告，不能仅取最新一份而丢弃其他类别发现。过时报告只能成为历史，完整报告也不得跨未覆盖范围关闭问题。

#### Scenario: Ten scans report the same issue
- **WHEN** 同一内容/策略下多次检出同一个问题
- **THEN** 保留一个稳定 issue 和本地运行历史，不生成十个任务或无意义 tracked 文件变化

#### Scenario: Missing JDK prevents several checks
- **WHEN** 多个模块因同一 JDK 缺失未完成
- **THEN** 生成工具链 blocker 与依赖关系，不虚构多条代码违规

#### Scenario: Lint and CVE reports await import
- **WHEN** 同一内容先产生 lint 报告再产生 CVE 报告
- **THEN** 同步纳入两者，重复同步不重复创建问题或事件

### Requirement: Closing a task SHALL require verified resolution evidence

正式 resolved MUST 由真实复检或有批准依据的 target_removed/policy_resolved 事件产生，并绑定问题、内容、规则/工具、策略和覆盖身份。代码修复、依赖修复、环境恢复、政策处置 MUST 分开归因。手工勾选、编辑状态、删除记录、增加忽略或未完成报告中不再出现 MUST NOT 关闭问题或改变 gate。例外 MUST 保留未解决事实。

#### Scenario: Agent checks a task as done without verification
- **WHEN** 任务 Markdown 被标为完成但无有效复检
- **THEN** 正式状态仍待验证，交付判定不变

#### Scenario: Verification times out after a patch
- **WHEN** 修复后的原检查器超时
- **THEN** 原 finding 保留，转为待验证/阻塞，不自动 resolved

#### Scenario: A resolved finding recurs
- **WHEN** 新内容再次检出同一可匹配问题
- **THEN** 重开 issue 并保留此前修复历史

### Requirement: Repair briefs SHALL guide bounded progress without changing authority

`status/next/task show` MUST 提供只读视图；next MUST 返回含依据、范围、步骤、约束、验证和历史尝试的 RepairBrief。recipe MUST 有受控来源，原生诊断和仓库文本 MUST 当作不可信数据。无进展重试超预算 MUST 阻塞该任务或请求具体决策，不能降低门禁；其它独立任务仍可推进。

MUST 提供 attempt 开始/结束协议，受控 fix 自动登记，自由修复回合由插件登记；尝试 MUST 绑定动作和前后内容摘要、结果及租约。复检前失败、无修改和中断均进入历史与预算，next MUST 不重复推荐耗尽且无新信息的动作。

#### Scenario: The same failed patch is attempted repeatedly
- **WHEN** 同一问题和补丁连续无进展达到预算
- **THEN** 停止相同自动尝试，保留阻断并给出下一步诊断，不推荐跳过规则

#### Scenario: Tool output contains an instruction
- **WHEN** 诊断文本要求执行 Shell 或关闭规则
- **THEN** 仅作为证据数据展示，不升级为动作授权

#### Scenario: Repair fails before verification
- **WHEN** 尝试没有代码变化或在调用检查器前失败
- **THEN** attempt 仍持久计数，不能因没有 verify 报告而无限重复

### Requirement: Enabled plugin workflows SHALL connect scans to actionable briefs

显式初始化并启用工作流后，插件扫描 MUST 经过保存 run、幂等 sync、返回状态/RepairBrief 的路径；仅有重复报错而没有任务指引 MUST 不作为完成的插件接入。未初始化时 MUST 提供临时简报与初始化计划，不静默写受管目录。同步失败 MUST 保留原结果并明示恢复动作；不能假称持久任务已生成或改变质量 gate。

#### Scenario: Enabled save hook finds a new issue
- **WHEN** 已启用的项目保存检查产生有效 finding
- **THEN** 创建或更新相应任务并返回下一步，重复同一 finding 不制造 tracked 文件噪声

#### Scenario: Backlog storage is unavailable
- **WHEN** 检查已完成但持久目录不可写
- **THEN** 保留原 finding/gate，说明 backlog_update_failed 和恢复动作，不伪造任务路径

### Requirement: Workflow persistence SHALL preserve collaboration and gate independence

finding 身份、事件父关系、证据引用与工作区 schema MUST 校验。并发领取 MUST 使用带期限租约和进程锁；不同分支状态冲突 MUST 显式协调，不能最后写入覆盖关闭。任务 Markdown MUST 是可重建投影；本地历史文件 MUST 不作为可信 CI 认证。完整 gate MUST 独立检查全部义务。

#### Scenario: All tasks are deleted
- **WHEN** 用户或智能体删除持久任务和发现
- **THEN** 新检查仍按源码与批准策略产生发现，不能因此获得 allow

#### Scenario: Two agents claim the same task
- **WHEN** 同一工作区并发领取一个未分配任务
- **THEN** 只有一个有效 lease，另一个收到当前归属与恢复信息

#### Scenario: Branches disagree on resolution
- **WHEN** 合并事件存在相互矛盾的关闭状态
- **THEN** 标记 reconciliation_required 并重新核对，不能自动选最后写入关闭
