## Purpose

定义项目内持久的问题、环境阻塞、修复任务和复检事件，使智能体能够恢复上下文并逐步完成修复，同时保证任务文件、人工勾选和删除记录不能替代原生工具的验收证据。

## ADDED Requirements

### Requirement: npm remediation tasks SHALL recheck through their original native audit service
npm持久任务 SHALL 支持 task verify，结构化任务根决定原生cwd，显式原工具上下文、共享预算与任务租约保护复检和持久化。结果 SHALL 反馈原生诊断及下一步，不从零漏洞推导完整覆盖或关闭。

#### Scenario: npm native audit is coherent but coverage remains unverified
- **WHEN** 原生版本、输入摘要与锁节点关联一致，本轮没有advisory但可信漏洞覆盖尚未核验
- **THEN** 记录局部复检并保持同一任务open，返回still_blocked；next说明需核验漏洞源覆盖及时效，不标记代码修复或白名单通过

#### Scenario: npm recheck fails after a repair attempt
- **WHEN** 持有有效租约的执行者结束修复尝试后，原生审计返回错误
- **THEN** 记录关联该尝试的incomplete复检及诊断，任务仍open；next提供具体检查指引，不继续声称尚未运行复检或创建源码违规

#### Scenario: npm inputs change after a recorded recheck
- **WHEN** 清单或锁文件改变，旧复检结果与当前输入不再一致
- **THEN** 历史记录保留但不作为当前结果，next与尝试历史要求原工具重新复检，不能沿用旧的零发现或恢复结论

#### Scenario: npm verification receipts are rewritten or assigned to another root
- **WHEN** 本地报告、验证事件和消费收据一并改写摘要，但报告包含重复字段、无效结构、虚构覆盖/权威，或对应另一工作区/构建根
- **THEN** next和尝试历史拒绝该复检证据，返回具体证据异常而非输入过期；incomplete失败结果也不得用于确认另一任务的修复尝试已经复检。合法旧输入变化须单独给原工具重检指引

### Requirement: npm child projects SHALL preserve explicit workspace ownership
公开 npm 审计 SHALL 支持显式父工作区参数，原工具在子项目执行，报告与任务归属所选已初始化工作区；未指定参数不得自动寻找父工作区。

#### Scenario: Two npm children share one initialized workspace
- **WHEN** 两个子项目分别指定同一父工作区并重复审计
- **THEN** 每个构建根保留一张稳定完整性任务，原生 cwd 保持对应子项目，预算默认来自所选工作区，next 复检命令保留显式工作区

#### Scenario: npm workspace is an alias or excludes the project
- **WHEN** 显式工作区是符号链接别名或不包含项目的物理目录
- **THEN** 在原生执行前返回准备未完成，不把外部项目记录为工作区任务；路径组件 a 不包含兄弟 ab

### Requirement: Local doctor observations SHALL enter the remediation queue without granting readiness

已初始化工作区的 doctor 局部报告 MUST 绑定当前工作区身份并以 run_id/摘要幂等同步；未初始化或无效工作区不得自动初始化或写入其它路径。显式版本诊断失败可生成稳定的环境调查任务，诊断原因变化或重复运行不得创建同一前置的重复任务；未选工具不得伪造工具缺失或必需检查。任务 MUST 引用报告、具体诊断、允许环境范围、原生 doctor 复检及历史/关闭条件；原生版本恢复不自动关闭原问题、授予准备 ready 或质量通过。工作区不符、被改报告或伪造完成/批准字段 MUST 拒绝导入；持久化/同步失败须如实反馈，保留原生观察而非改写为已修复。

#### Scenario: A selected version probe fails twice
- **WHEN** 同一工作区显式选中的 Ruff 版本探测重复失败
- **THEN** 每次报告保留自己的 run_id，关联同一环境调查任务；再次同步同一报告不重复写任务，next 给 doctor 复检和环境恢复指引，不修改无关源码

#### Scenario: A later version probe succeeds
- **WHEN** 原环境调查仍待处理，本次局部原生版本恢复正常
- **THEN** 保留成功观察及未关闭任务，要求核验前置要求/可信来源；不得把局部版本成功写成质量修复或允许交付

#### Scenario: An agent verifies a doctor investigation task
- **WHEN** 智能体对 doctor 环境任务执行 task verify 并显式选择原生工具
- **THEN** 复用同一版本诊断契约、预算和任务租约，以报告摘要保存复检事件；失败保留具体原因，成功标记环境恢复但策略未核验，任务保持 open。未选择工具为 incomplete，不隐式发现随机 PATH 工具或扫描源码

### Requirement: Projects SHALL have an explicitly initialized remediation workspace

Codeguard MUST 支持 `./.codeguard/` 及其中的 .gitignore、工作区清单、脱敏 findings/events、任务与决策引用；原始 reports/runs/cache/worktrees/state MUST 默认 Git 忽略。初始化 MUST 提供 dry-run/apply，不覆盖已有用户文件，不创建第二份质量策略。

#### Scenario: User files and legacy workspace coexist
- **WHEN** 初始化遇到 `.codeguard/` 中的冲突文件，或在 `codeguard/workspace.json` 发现旧版受管工作区
- **THEN** 给出精确冲突与迁移诊断，不覆盖文件、不静默创建第二份工作区；既有 `codeguard/src/` 用户源码仍参加普通检查，不能整体搬入点目录

### Requirement: Findings and environment blockers SHALL produce distinct actionable tasks

持久同步 MUST 区分真实 finding 与检查未完成的 blocker，按稳定身份归并重复发现、保留原规则与证据。部分报告 MUST 只能增加有效发现/阻塞，不能因缺失旧 finding 自动关闭。任务 MUST 包含问题依据、允许改动、修复步骤、前置依赖、复检条件及历史尝试。

同步 MUST 按 run_id 幂等消费所有未导入且身份匹配的报告，不能仅取最新一份而丢弃其他类别发现。过时报告只能成为历史，完整报告也不得跨未覆盖范围关闭问题。

RunReport 与准备诊断 PrerequisiteReport MUST 使用 workspace_id + run_id 作为导入幂等键并验证报告摘要；同键不同摘要 MUST 拒绝而不是覆盖。每份报告的事件提交与消费标记 MUST 可恢复，失败不得先推进游标；准备诊断只能形成对应blocker/恢复证据，不伪装源码检查结果。

#### Scenario: Ten scans report the same issue
- **WHEN** 同一内容/策略下多次检出同一个问题
- **THEN** 保留一个稳定 issue 和本地运行历史，不生成十个任务或无意义 tracked 文件变化

#### Scenario: Missing JDK prevents several checks
- **WHEN** 多个模块因同一 JDK 缺失未完成
- **THEN** 生成工具链 blocker 与依赖关系，不虚构多条代码违规

#### Scenario: Lint and CVE reports await import
- **WHEN** 同一内容先产生 lint 报告再产生 CVE 报告
- **THEN** 同步纳入两者，重复同步不重复创建问题或事件

#### Scenario: CVE advisory is observed without a qualified vulnerability database
- **WHEN** 原生 OWASP 报告包含 advisory，但数据库时效或依赖归属尚未核验，且工作区已启用持久同步
- **THEN** 保留脱敏报告并生成稳定的环境/证据阻塞任务，列明原工具复检与库核验步骤；重复扫描不制造多张同身份任务，不将 advisory 直接写成已确认源码 finding、误报白名单或交付通过

#### Scenario: Rust CVE observation is rechecked before database qualification
- **WHEN** 已初始化 Rust 工作区反复执行原生 cargo-audit 检查，并对同一未核验漏洞库任务执行 `task verify`
- **THEN** 同一构建根只保留一张稳定的 CVE 覆盖阻塞任务，更新原生 advisory 观察与复检历史；`next` 继续给出原工具及漏洞库核验步骤，任务仍为 open。本地报告、任务勾选或白名单候选均不能替代受信漏洞库时效和批准身份

#### Scenario: Doctor report is imported twice or changes under the same identity
- **WHEN** 同一准备报告重复导入，或同一run_id出现不同摘要
- **THEN** 相同报告幂等，不同摘要拒绝并保留冲突，不重复任务或覆盖证据

#### Scenario: Synchronization stops between event and cursor persistence
- **WHEN** 事件已写入但消费标记尚未持久化时中断
- **THEN** 重试恢复同一事务，不漏事件、不重复计数；一份坏报告不妨碍其它有效报告持久化，整体仍明确未完成

#### Scenario: A crashed process leaves a staging file and its PID is reused
- **WHEN** `write_once` 的旧临时文件名已存在，但目标记录仍未写入
- **THEN** 重试 MUST 以有界的新独占临时文件名继续，不覆盖或删除残留文件；若名字空间耗尽则明确未完成，不伪造消费标记

#### Scenario: A malformed report remains after other reports are imported
- **WHEN** 一份坏报告重复同步失败，而同队列的有效 lint 和 CVE 报告已导入
- **THEN** 保留按报告摘要绑定的脱敏失败原因；`next` 指向修复该报告或检查器，不无限重复推荐未改变输入的 `work sync`；报告内容改变后旧失败观察不得继续适用，整体交付仍未评估

#### Scenario: Two processes import the same workspace
- **WHEN** 一个 `work sync` 已持有工作区导入锁，另一个进程尝试同步同一工作区
- **THEN** 后者在写 finding、任务、事件或消费标记前返回未完成并说明忙碌；锁释放后重试幂等恢复，不凭本地锁状态签发质量结论

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

#### Scenario: Verification resolves the original issue but finds another violation
- **WHEN** 原问题有完整关闭证据，而复检发现新的阻断问题
- **THEN** 原任务可按证据关闭，新发现同步保留，验证命令仍按本次结果返回违规或未完成，不宣称全项目通过

#### Scenario: Environment detection succeeds but the blocked check still cannot run
- **WHEN** doctor已确认JDK等条件恢复，而原受阻义务仍不能完整执行
- **THEN** task verify必须尝试原受阻义务并保留未完成，不据探测通过宣称验证闭环完成

### Requirement: Repair briefs SHALL guide bounded progress without changing authority

经可信批准的误报处置 MUST 是独立事件/任务状态 `whitelisted_false_positive`，不得记作 `resolved_by_code_fix` 或删除 finding。疑似误报任务 MUST 记录原生证据、最小复现、裁定原因、精确目标、批准请求和原工具复检命令；候选、过期、失配或撤销的白名单 MUST 重新进入调查/修复队列。`.codeguard/decisions/` 只保存可读引用，不自授策略权威。

`status/next/task show` MUST 提供只读视图；next MUST 返回含依据、范围、步骤、约束、验证和历史尝试的 RepairBrief。recipe MUST 有受控来源，原生诊断和仓库文本 MUST 当作不可信数据。无进展重试超预算 MUST 阻塞该任务或请求具体决策，不能降低门禁；其它独立任务仍可推进。

next MUST 区分actionable/waiting/needs_decision/verification_required/no_applicable_work；未初始化应给初始化动作，空任务但缺少新鲜完整证据 MUST 返回verification_required，不把null task或查询exit0解释为allow。status 中历史通过 MUST 带来源及freshness，不冒充当前认证。

MUST 提供 attempt 开始/结束协议，受控 fix apply 自动登记，自由修复回合由插件登记；尝试 MUST 绑定动作和前后内容摘要、结果及租约。复检前失败、无修改和中断均进入历史与预算，next MUST 不重复推荐耗尽且无新信息的动作。

#### Scenario: The same failed patch is attempted repeatedly
- **WHEN** 同一问题和补丁连续无进展达到预算
- **THEN** 停止相同自动尝试，保留阻断并给出下一步诊断，不推荐跳过规则

#### Scenario: Tool output contains an instruction
- **WHEN** 诊断文本要求执行 Shell 或关闭规则
- **THEN** 仅作为证据数据展示，不升级为动作授权

#### Scenario: Repair fails before verification
- **WHEN** 尝试没有代码变化或在调用检查器前失败
- **THEN** attempt 仍持久计数，不能因没有 verify 报告而无限重复

#### Scenario: Task list is empty but current full verification is absent
- **WHEN** next没有可修复任务且缺新鲜完整检查证据
- **THEN** 返回verification_required和检查动作，不据任务清空证明交付通过

### Requirement: Enabled plugin workflows SHALL connect scans to actionable briefs

显式初始化并启用工作流后，插件扫描 MUST 经过保存 run、幂等 sync、返回状态/RepairBrief 的路径；仅有重复报错而没有任务指引 MUST 不作为完成的插件接入。未初始化时 MUST 提供临时简报与初始化计划，不静默写受管目录。同步失败 MUST 保留原结果并明示恢复动作；不能假称持久任务已生成或改变质量 gate。

#### Scenario: Enabled save hook finds a new issue
- **WHEN** 已启用的项目保存检查产生有效 finding
- **THEN** 创建或更新相应任务并返回下一步，重复同一 finding 不制造 tracked 文件噪声

#### Scenario: Backlog storage is unavailable
- **WHEN** 检查已完成但持久目录不可写
- **THEN** 保留原 finding/gate，说明 backlog_update_failed 和恢复动作，不伪造任务路径

### Requirement: Check results SHALL be returned in the agent conversation

插件触发检查后 MUST 把本次配置探测与原生执行结果转换为宿主可见的对话反馈，包含已配置并运行的检查器、未配置或无效的检查器、确定性诊断、环境/工具错误、修复建议和复检命令。对话反馈以本次 CLI 结果为来源，不要求另造逐检测族执行证明；持久同步失败时也 MUST 返回已有结果与同步失败状态。CLI human/JSON、MCP 与宿主 Hook 只做展示适配，不得让智能体将原始工具文本解释为新的授权指令。

#### Scenario: Configured checker finds an issue
- **WHEN** 已配置的 Javadoc 或 CVE 原生检查器返回有效诊断
- **THEN** 智能体对话显示问题摘要、位置或组件、规则依据、建议动作及原工具复检命令

#### Scenario: Checker is not configured
- **WHEN** 项目没有配置某候选检查器
- **THEN** 对话显示 `missing` 和具体启用建议，不显示该检查器“通过”或虚构源码违规；只有批准策略要求该检查时才把缺项作为门禁未完成

### Requirement: Workflow persistence SHALL preserve collaboration and gate independence

finding 身份、事件父关系、证据引用与工作区 schema MUST 校验。并发领取 MUST 使用带期限租约和进程锁；不同分支状态冲突 MUST 显式协调，不能最后写入覆盖关闭。任务 Markdown MUST 是可重建投影；本地历史文件 MUST 不作为可信 CI 认证。完整 gate MUST 独立检查全部义务。

claim MUST 返回不可复用lease_token/generation和到期；heartbeat/release及attempt写入 MUST 核对token，而非只比较owner。租约默认5分钟，长操作MUST有界续租，失租停止应用/状态提交。正常release MUST 不遗弃未结束attempt；过期接管 MUST 先可恢复地追加abandoned与预算记录，再授予新generation，恢复失败不先取得新租约。无租约task verify使用短期验证租约，已有租约要求调用方提供匹配token，不能释放别人取得的租约。

#### Scenario: All tasks are deleted
- **WHEN** 用户或智能体删除持久任务和发现
- **THEN** 新检查仍按源码与批准策略产生发现，不能因此获得 allow

#### Scenario: Two agents claim the same task
- **WHEN** 同一工作区并发领取一个未分配任务
- **THEN** 只有一个有效 lease，另一个收到当前归属与恢复信息

#### Scenario: Branches disagree on resolution
- **WHEN** 合并事件存在相互矛盾的关闭状态
- **THEN** 标记 reconciliation_required 并重新核对，不能自动选最后写入关闭

#### Scenario: An old owner writes after the task has been reclaimed
- **WHEN** 新generation的租约已生效，旧执行者尝试heartbeat/finish/release
- **THEN** 返回未完成并拒绝旧写入，同名owner也不能复活或释放新租约

#### Scenario: Reclaim cannot persist the abandoned attempt
- **WHEN** 过期租约的abandoned事件或预算记录写入失败
- **THEN** 返回3且不授予新generation，成功重试只追加一次恢复事件并计数一次

#### Scenario: Verification owns or borrows a lease
- **WHEN** verify自行取得验证租约、携带有效调用方租约，或提供错误token
- **THEN** 自有租约收尾释放、借用租约保留；token错误时不启动检查器

### Requirement: Repair command handoffs SHALL bind attempts and leases explicitly

attempt start MUST 接受来自受控简报的action-id并由CLI计算动作指纹、观察前置内容，返回attempt_id；finish新增结束事件 MUST 明确attempt-id及当前lease-token，记录观察变化与执行者说明，冲突结束拒绝，同结果重放幂等。已落盘结束收据的原请求重放只返回该收据，即便租约过期也不得再次写入或影响新租约。每任务只允许一个未结束attempt；换action名称不重置同一无进展动作预算。finish结果仅允许ready-to-verify/no-change/failed/blocked，不直接resolved。

fix MUST 支持task及成对owner/lease-token绑定；已领取任务复用有效租约，由FixService登记自己的受控attempt，不接管已有未结束自由attempt。未领取时可自行取得并仅释放自有租约。已初始化工作区的批量apply在补丁应用前取得全部受影响任务租约，冲突不能静默跳过；未初始化时只保留私有证据，不调用持久同步/租约，不声称持久任务存在。fix dry-run MUST 不登记正式修复尝试或消耗预算；apply自动登记，插件不得重复计数。

#### Scenario: Controlled fix is invoked for an already claimed task
- **WHEN** fix接收task、owner及有效lease-token，且没有未结束attempt
- **THEN** 限定任务范围并登记受控尝试和复检，保留调用方租约，不要求插件重复start/finish

#### Scenario: The same attempt finish is retried
- **WHEN** 先前finish已持久化但响应丢失后调用方用同ID和结果重试
- **THEN** 返回已记录结果而不重复预算/事件；不同结果的重复结束返回冲突

### Requirement: Explicit Checkstyle workspace observations SHALL generate stable local repair tasks
显式提供已初始化的 --workspace 时，Checkstyle 局部检查 SHALL 绑定项目内源文件、原配置和本轮工具字节后保存观察并同步同一稳定任务。输出必须反馈同步结果和下一步；未完成检查不得生成源码修复任务，局部任务不得授予交付许可或自动关闭。

#### Scenario: Repeated native observation
- **WHEN** 同一项目内源码的相同规则和锚点在重复原生检查中仍存在
- **THEN** 更新同一稳定 finding 的观察记录，不重复创建任务；任务包含规则、证据、范围、步骤、复检、历史和关闭条件

#### Scenario: Workspace or frozen inputs mismatch
- **WHEN** 指定工作台未初始化、目标在项目外，或同步前源文件/原配置/工具字节变化
- **THEN** 不导入源码任务，并在反馈中指出具体阻塞；不能用陈旧观察要求修改源码

### Requirement: Checkstyle task verification SHALL replay the original native checker without automatic closure
Checkstyle 任务复检 SHALL 在统一预算、取消和任务租约下使用显式原工具与原配置，保存原生观察及失败尝试。零诊断不能独自证明修复；规则失配、工具身份变化或输入不稳定不能关闭任务。

#### Scenario: Original finding still exists or becomes absent
- **WHEN** 原工具完整复检仍检出同一稳定 finding，或在原规则身份仍相同且工具字节一致时未再检出
- **THEN** 分别记录 still_present 或 candidate_absent_unverified_policy，保留 open 任务和历史，对话与 next 提供下一步

#### Scenario: Rule removed or checker changed
- **WHEN** 原配置移除任务对应规则、将同一 ID 绑定到另一检查类，或显式工具字节与原观察不同
- **THEN** 返回规则覆盖待审或未完成，不把零诊断归为代码修复

#### Scenario: Native recheck cannot run
- **WHEN** 缺工具、输入不可用或原生检查未完成
- **THEN** 保存未完成复检事件与具体原因，不从可编辑 Markdown 执行指令，不关闭任务

### Requirement: Checkstyle preparation failures SHALL create stable environment tasks
已初始化且显式启用工作台时，Checkstyle 前置缺失或配置不明 SHALL 形成准备任务，保留具体诊断和当前输入范围；不能生成源码违规或建议修改无关源码。同一工作区的 Checkstyle 前置槽位重复观察更新同一任务，不因诊断变化重置历史。

#### Scenario: Native prerequisites are missing
- **WHEN** Java、Checkstyle JAR 或原配置无法确认，且目标仍在指定工作区内
- **THEN** 同步一个开放准备任务，next 给出恢复工具/配置与原工具复扫步骤，任务包含七项必需信息且不声称质量通过

#### Scenario: Repeated preparation changes diagnosis
- **WHEN** 相同前置槽位从缺参数变成缺 JAR 或未知配置，或影响另一源文件
- **THEN** 保留同一稳定任务及历史，更新当前诊断与范围；人工勾选不能关闭任务

#### Scenario: Cancelled request or outside target
- **WHEN** 用户取消检查，或目标不属于指定工作区
- **THEN** 不把取消或外部目标伪装成项目环境缺陷，不创建该准备任务

#### Scenario: Later same-scope native observation runs
- **WHEN** 准备失败后，同一源码范围存在更晚且已消费、输入仍一致的原工具局部观察
- **THEN** next 转向核对原选择及批准覆盖，不重复建议恢复工具；仍保留开放任务，后续配置或输入变化使该恢复线索失效

### Requirement: Checkstyle preparation verification SHALL preserve the original blocked obligation
准备任务复检 SHALL 在既有租约、尝试和统一预算中使用显式原工具，对当前记录的项目内受影响源码复扫。恢复后产生的原生 finding 应进入源码任务，环境恢复只作局部未验证观察，不自动关闭准备任务。

#### Scenario: Preparation remains blocked
- **WHEN** 原工具或配置仍不可用，准备任务接受一次复检
- **THEN** 保存 still_blocked 或 incomplete 观察、具体原因与尝试引用，保留 open 状态，next 不引导修改无关源码

#### Scenario: Native preparation recheck runs
- **WHEN** 同一准备任务范围的显式 Checkstyle 检查正常返回局部原生报告
- **THEN** 保存 environment_restored_unverified_policy，同步其中源码发现，并转向核验原选择、批准和完整覆盖；源码或配置再次变化不沿用恢复线索

#### Scenario: Ownership is invalid
- **WHEN** 任务有活动租约但复检者不持正确 owner/token
- **THEN** 不启动原生检查或保存恢复事件，保留原任务和租约

#### Scenario: Preparation retry remains blocked after a ready attempt
- **WHEN** 准备修复尝试已标记 ready-to-verify，原工具复检仍为 still_blocked 或 incomplete
- **THEN** 将复检绑定该尝试并累计同动作同输入的无进展次数；预算内恢复具体前置修复动作，预算耗尽后保留开放任务并要求具体诊断或决策，不能反复复检或更换动作名逃逸预算

#### Scenario: Inputs change after an attempt is finished
- **WHEN** 一次尝试已经标记 ready-to-verify，但在原工具复检前，任务绑定的源码、清单或锁文件又发生变化
- **THEN** 新输入的复检不得归因于旧尝试；旧事件保留为历史，旧尝试不再阻塞新输入的动作，且不得用新结果重置旧输入的失败次数或宣称原修复成功

#### Scenario: Checkstyle tool changes after a recovery observation
- **WHEN** 准备恢复或源码暂未检出的复检后，原 Java 或 Checkstyle JAR 字节变化、路径身份变化或文件不可用
- **THEN** next 与 task show 不沿用旧恢复或缺失结论，要求显式原工具重新复检；历史收据继续保留，不能通过旧恢复线索关闭任务

#### Scenario: Conversation consumers need a concrete invalidation reason
- **WHEN** 已有 Checkstyle 复检收据因本轮源码、配置或工具变化失效，或前置复检仍受阻
- **THEN** next/task show 将历史原工具原因与当前观察失效原因分开表达，status 任务摘要保留具体原因与失效原因；智能体无需猜测为何需要再次修复或复检，也不能把查询成功当成交付通过

#### Scenario: Present Checkstyle finding is stale after a configuration edit
- **WHEN** 原工具复检仍检出原问题，之后 Checkstyle 配置或目标源码变化
- **THEN** next/task show 显示当前输入失效原因，要求原工具重新复检；不能用旧 still_present 覆盖先前的失效判断并重新推荐旧源码修复步骤。历史原工具结果保留，任务不关闭

### Requirement: ESLint task identity SHALL bind native rule and stable source anchor

ESLint 原生发现投影 MUST 使用工作区相对路径、原生规则、源码锚点及稳定出现序号，行号与整文件摘要只作本轮证据，不因插入空行而制造新任务身份。MUST 稳定排序并去除重复原生诊断；完整输入中的任一归属或定位无效则不得发布部分源码任务。源码定位 MUST 处理 UTF-16 列及 JavaScript 原生行终止符，不把字节长度当列范围。投影只记录脱敏诊断，不证明本轮报告来源、批准策略或问题关闭。

#### Scenario: Source moves by inserted blank lines or native wording changes
- **WHEN** 同一路径与规则的原源码锚点保持，行号或原生消息文字变化
- **THEN** 稳定finding ID保持，当前行号及源码摘要更新，不把旧任务勾选当修复

#### Scenario: Native diagnostic order changes or includes duplicates
- **WHEN** 同轮报告乱序或重复同一原生诊断，或同一锚点在多个位置出现
- **THEN** 排序与去重后身份确定，不同出现序号保持不同身份，报告顺序不制造额外任务

#### Scenario: One diagnostic has invalid scope or Unicode location
- **WHEN** 任一诊断不属于冻结原生文件、相对路径跳转、行越界或列超过原行UTF-16范围
- **THEN** 拒绝整组任务投影，保持未完成并要求原工具或适配器核查，不生成部分源码修复任务

### Requirement: ESLint local observations SHALL feed stable repair records

显式 `lint typescript --workspace` MUST 将当前输入复核后的脱敏局部观察入队并通过既有同步协议生成稳定 finding 与可读任务，重复扫描更新同一问题历史，不覆盖用户任务备注。报告 MUST 固定工作区、输入、原工作目录、版本及未批准状态；坏形状、输入变化、自称门禁允许或不正确投影不得导入。已消费历史 MUST 按原字节收据确认，不用当前源码重演旧观察。公开反馈 MUST 说明同步状态和 next 查询失败，不把队列异常说成源码违规。

`next` MUST 依据摘要绑定的当前已消费报告复核输入及首次工具/配置连续性；上下文改变、抑制、原生未完成或局部零诊断均须复检/核查，不能沿用旧源码修改指引。任务勾选不改变问题状态；当前没有正式关闭入口时保持开放。此局部闭环不证明完整源集、TS插件闭包或质量门禁。

#### Scenario: Repeated ESLint scans find the same native problem
- **WHEN** 本轮输入有效，同一稳定规则/源码锚点被重复检查，用户修改了任务备注或勾选文字
- **THEN** 只保留一个稳定finding/任务，更新观察并保留用户文本，问题仍open且对话返回修复指引

#### Scenario: ESLint reports no current diagnostic after a repair
- **WHEN** 同工具/原配置复扫有效且本轮局部零诊断
- **THEN** next要求覆盖和正式复检核查，不重复旧源码修复、不自行关闭任务或签发门禁

#### Scenario: A queued ESLint report self-authorizes or current configuration changes
- **WHEN** 新报告声称delivery_decision=allow，或next查询时当前输入与记录不一致
- **THEN** 自授权报告导入失败且不增加源码任务；陈旧输入要求原工具复扫，不沿用旧修复步骤
- **AND** ESLint 上下文失效的备用复检指引仍选择 ESLint 命令并显式要求核验工具、原配置和原工作目录，不回退其它语言检查器或猜测身份

### Requirement: ESLint incomplete prerequisites SHALL create investigation tasks

显式工作区和当前有效源码目标下，缺调用上下文、工具或输入不可读、版本/报告/配置诊断等未完成结果 MUST 进入独立的环境与检查完整性任务；不得生成已确认源码违规或白名单批准。目标身份 MUST 固定工作区与具体源码范围，重复诊断更新同一稳定任务及脱敏历史。取消、外部目标、不支持范围或未初始化工作区不得伪造任务保存成功。解析或抑制诊断 MUST 指引复现根因，不默认认定环境或源码的唯一原因。

任务指引 MUST 依据最新摘要绑定的已消费报告及当前源码核验；同范围有较新的有效原工具观察时转为正式复检/覆盖核查，不继续要求修复旧环境诊断。局部恢复不得自行关闭准备任务。对话 human/JSON MUST 展示任务下一步和同步失败状态。

#### Scenario: Missing ESLint context repeats or another prerequisite fails
- **WHEN** 同一工作区源码缺Node/ESLint上下文，重复调用或后续诊断变为工具输入不可读
- **THEN** 只保留一张环境任务，记录最新具体原因；不创建源码finding，不要求修改无关源码

#### Scenario: ESLint prerequisites recover locally
- **WHEN** 同范围较新的摘要绑定原工具报告已同步且当前输入有效
- **THEN** 环境任务保持open，next转verification_required并要求核验当前结果与完整覆盖，不继续沿用旧故障诊断

#### Scenario: Native ESLint rejects an unknown configured rule
- **WHEN** 原ESLint因原配置引用不存在规则而无法完成正常报告
- **THEN** 建立检查完整性任务，反馈当前失败原因及原配置复核指引；不能推导源码违规或质量通过

#### Scenario: Preparation target is outside the workspace
- **WHEN** 未完成请求的源码属于另一个工作区
- **THEN** 返回source_outside_workspace且不创建本工作区环境任务或源码finding

### Requirement: ESLint task verification SHALL retain native observations

`task verify` MUST 支持ESLint源码任务与准备任务，复用已有租约、统一执行截止时间、同步及失败尝试预算。工具入口、具体版本、原配置和工作目录 MUST 由显式参数核验，不能执行任务Markdown或历史报告自动选择的程序。复检 MUST 固定任务目标、本轮输入及报告摘要；缺上下文也须明确未完成原因并保留开放状态，不能调用其它语言检查器。

源码任务 MUST 比较首次摘要绑定观察的Node、ESLint入口、原配置、版本和cwd连续性；变化只能要求规则/覆盖核查。原生抑制或失败不得作为修复完成。局部原问题消失只属于candidate_absent_unverified_policy；准备恢复只属于environment_restored_unverified_policy，均不自动关闭。next、status及尝试历史 MUST 能消费同一复检事件，较新复检不得被旧扫描覆盖为过期源码修复指引。

#### Scenario: ESLint task is verified without explicit native context
- **WHEN** 原任务有效但没有提供Node、ESLint入口、具体版本、原配置和cwd
- **THEN** 保存明确未完成的局部复检观察和开放事件，不执行默认工具、不签发修复完成

#### Scenario: ESLint native task remains or disappears after repair
- **WHEN** 显式原工具与原配置复扫正确完成，原稳定任务仍存在或已局部消失
- **THEN** 分别记录still_present或candidate_absent_unverified_policy，保留任务开放；事件可被next和尝试预算一致读取

#### Scenario: ESLint original context changed or a task is suppressed
- **WHEN** 工具/原配置/cwd与首次观察不同，或原生报告显示注释抑制
- **THEN** 要求规则覆盖核查或抑制复核，不能将零诊断记为resolved

### Requirement: npm local audit observations SHALL enter persistent coverage repair tasks

初始化工作区根中的显式npm公开CVE调用 MUST 保存脱敏观察，并通过现有同步器产生稳定CVE检查完整性任务。原生组件/advisory/锁版本观察 MUST 保留为未核验的报告信息，不转换成已确认源码漏洞、白名单批准或任务关闭。同一构建根的完整性义务保持单一稳定任务，具体执行诊断作为历史更新；原清单/锁摘要及节点归属须复核。重复字段、越界/未知结构、节点或版本冲突及已消费报告被篡改不得产生授权或新任务。当前局部任务可供next取得恢复环境、核对数据源与原工具复检步骤；尚未取得覆盖权威时零发现不能关闭。

#### Scenario: Repeated npm audit produces one persistent task
- **WHEN** 已初始化根重复运行同一原生npm局部审计
- **THEN** 第一次保存报告与一张稳定任务，后续更新历史；next提供原npm复检指引，清单/锁身份不符或坏报告不产生新可信事实

#### Scenario: Local npm audit cannot confirm CVE closure
- **WHEN** 原生npm报告零发现但数据库覆盖未核验
- **THEN** 稳定任务仍open、交付未判定；手动删除任务或白名单候选不能关闭CVE义务


#### Scenario: npm execution context is missing before native startup
- **WHEN** 已初始化物理工作区中的 npm 构建根具有可读取且身份可绑定的清单和锁文件，但公开 CVE 调用、显式选择 npm 的 check all 或 task verify 缺少原生调用参数
- **THEN** MUST 保存本地准备阻塞观察并关联同一稳定 npm 完整性任务；重复检查与补齐上下文后的原生报告不得产生另一张同义务任务。准备观察 MUST 标明 npm_execution_context_missing、零组件及空 advisory，不声称原生工具已启动、漏洞覆盖完整或源码存在漏洞；失败复检保留 incomplete 历史。未初始化、输入变化、路径别名、取消和预算耗尽不得制造可用证据


#### Scenario: npm lockfile is absent before tool startup
- **WHEN** 已初始化物理工作区的 npm 构建根具有可绑定清单，操作系统明确报告 package-lock.json 不存在
- **THEN** MUST 在启动原生工具前保留 npm_lock_missing 环境阻塞，使用明确 missing 状态及空锁摘要、零组件和空 advisory，不虚构锁文件内容。公开CVE、显式选择npm的check all及task verify沿用同一稳定完整性任务；补齐锁后旧缺锁观察失效，新扫描不增加同义务任务。链接、目录或不可读文件不得伪装为不存在；重放缺锁报告、未知协议或矛盾字段不得生成当前可用证据


#### Scenario: npm manifest is malformed before tool startup
- **WHEN** 初始化工作区中可绑定的package.json存在JSON语法错误、重复字段或非法scripts类型
- **THEN** 即使提供完整原生参数，MUST 在启动npm前保存配置阻塞、给出清单修复指引并沿用稳定完整性任务，不把错误改称版本失败或源码漏洞。已有可绑定锁文件时，准备观察以npm_manifest_invalid或npm_scripts_invalid表达诊断且保持零组件/空advisory；缺锁同时存在时保留明确缺锁观察及配置错误反馈。清单变化后旧收据不得解释当前输入；报告声称清单损坏时，消费者MUST 与当前绑定字节的配置解析结论核对，不能只信诊断字段


#### Scenario: Default full check discovers npm roots without explicit tools
- **WHEN** 已初始化工作区运行check all且发现可绑定的npm根，但未提供Node/npm及配置参数
- **THEN** 支持的平台MUST 自动将每根接入准备任务并串行同步，反馈稳定任务与next，重复检查不堆积任务；未启动原生命令，不继承工具环境或凭据，不安装工具。未初始化项目不得隐式创建工作区；check java不得触发npm准备。真实原生参数恢复后继续复用同一任务，仍须独立核验完整CVE覆盖


#### Scenario: npm manifest or lock becomes unavailable during remediation
- **WHEN** 已初始化物理工作区的明确npm任务或公开CVE范围中，清单/锁不存在、非普通文件、路径别名或无法有界读取
- **THEN** MUST 保存独立输入状态准备观察，缺失与不可用分开；只有可读普通文件有内容摘要，其余摘要为null，零组件/空advisory。消费方必须先严格核对结构及状态对应的原因，再核对当前物理范围、状态与可读内容；损坏字段不能被当作陈旧证据静默沿用。同一完整性义务跨状态修复复用任务，输入恢复后旧观察失效；尝试指纹可记录环境状态但不能冒充源码摘要或关闭证据，next和失败复检历史不得因目录/不可读输入而不可用


#### Scenario: npm manifest disappears from a known initialization profile
- **WHEN** 默认全项目检查不再发现初始化画像中曾记录的npm清单，但物理构建目录仍存在
- **THEN** MAY 用与该工作区受管摘要一致且严格解析的旧画像恢复准备范围；MUST 核对相对路径、画像标记、当前物理归属及输入不可用状态，只生成本轮准备观察，不用历史摘要或配置启动原工具。画像不可读、摘要不符、结构或路径无效时MUST 明示历史范围未完成并保留当前发现的其它根；恢复清单后须通过当前发现重新绑定，稳定任务不重复，历史画像不构成覆盖或批准


#### Scenario: Profile refresh cannot erase recorded npm remediation scope
- **WHEN** 当前画像刷新后不再包含清单不可用的npm根，但本工作区仍有同一稳定完整性问题的本地事实记录
- **THEN** 默认check all MUST 保留该物理构建根的准备范围；严格核验工作区、检查器、稳定身份、范围和事实结构，不能由可编辑任务附件的勾选或删除消除检查。事实只提供本地未验证范围线索，不授权原生执行、批准、关闭或覆盖；当前清单恢复后重新发现。损坏或跨工作区记录 MUST 明示范围恢复未完成，不扩展到越界路径或吞掉当前发现的其它根
