## Purpose

定义 Rust Codeguard 的统一请求、语言选择、报告、退出码及多入口转换协议，使局部检查成功与完整交付认证具有明确边界，调用方无需猜测原生工具状态。

## ADDED Requirements

### Requirement: check all SHALL orchestrate npm roots through the shared native runtime
check all SHALL 将发现的npm构建根接入共享任务图、截止时间与并发预算，在显式原生上下文下调用同一审计服务；执行后串行同步稳定任务并反馈next，不继承宿主凭据或安装工具。

#### Scenario: Multiple npm roots are checked within one workspace
- **WHEN** 已初始化工作区有多个package.json根，调用者提供显式Node/npm/版本/原配置上下文
- **THEN** 各根原生cwd、结果及稳定任务独立，重复检查不重复生成任务；统一human/JSON展示原生诊断、锁版本线索、同步结果及下一步，局部零漏洞不证明完整覆盖

#### Scenario: One npm root fails or the shared budget expires
- **WHEN** 一个根的原生审计失败，或共享截止时间耗尽
- **THEN** 保留兄弟根已经取得的结果，不把环境失败记为源码违规；预算耗尽后不启动余下任务或签发完整检查通过，取消/超时与未同步状态明确展示

#### Scenario: npm context is absent or scoped to a Java-only check
- **WHEN** check all未提供显式npm上下文，或check java接收npm参数
- **THEN** 前者在支持的平台自动将已发现npm根加入共享准备任务，已初始化且输入可绑定时同步稳定环境/配置任务并反馈next；不得启动缺上下文的原生命令，不自行安装/继承凭据。后者在原生执行前拒绝参数；可信上下文自动解析须独立实现和验收

### Requirement: Install previews SHALL distinguish bound layout declarations from verified package contents

安装预览反馈 0.3 MUST 区分完整布局路径声明已绑定但来源未核验、缺少完整树声明及 raw 不适用目录树布局。已绑定完整布局 MUST 展示安装树声明摘要、内容寻址目录名和入口/可选 bundle 定位摘要；包内私有路径及原下载地址 MUST NOT 回显。预览 MUST 明示包/布局内容尚未验证，不得调用下载、展开或发布服务来隐式补齐。完整声明或局部制品身份匹配 MUST NOT 推导来源批准、准备完成、实际写入或门禁通过；未获批准的 apply 保持写入前阻塞。JSON/human MUST 表达相同阶段与下一步，旧版本 schema MUST 保留且不得将新反馈解释为旧普通成功。

#### Scenario: A complete layout is declared but no package is read
- **WHEN** 1.2 清单与原锁路径精确绑定，用户请求 dry-run 或未批准的 apply
- **THEN** 布局标记 declared_paths_bound_untrusted，内容核验 not_run，准备 unknown、来源 unverified、未写入；apply 不安装

#### Scenario: A legacy manifest lacks full layout or a raw package is declared
- **WHEN** 清单缺完整树声明，或工具包格式为 raw
- **THEN** 分别显示缺少声明或 raw 不适用；不猜完整安装目录，不把阶段标签当作内容核验

### Requirement: Unified commands SHALL select explicit check obligations

Rust CLI MUST 提供 `lint/comments/dependencies/cve/security/build/check <language|all> [path]`；`check` 包含项目实际已配置且可适配的检查器，以及批准策略明确要求的检查义务。候选检测族目录本身不产生项目义务；未配置的候选项应说明状态与建议，不能因为没有运行就产生代码违规。语言别名 MUST 来源于统一注册表，未知语言在执行前拒绝。部分命令 MUST 明示 selection，不得据局部通过声明项目全部通过。`plan` MUST 仅规划，不执行构建、扫描、下载、安装或修改源码。

交付聚合 MUST 对照由可信策略与完整发现独立冻结的应有义务 ID 清单和实际计划的义务清单；任一清单漏项、重复或额外项均不能签发 allow。计划和冻结清单若都来自同一未经核验的项目可写输入，数量一致仍不构成可信来源证明。无适用义务的完整空项目仍按 not_applicable 处理。

#### Scenario: Java lint succeeds in a mixed project
- **WHEN** Java lint 完成，但项目仍有 Python、安全或 CVE 义务未在该请求执行
- **THEN** 请求可成功，交付状态为 not_evaluated，不能宣称全项目通过

#### Scenario: Planned obligations omit a frozen requirement
- **WHEN** 可信冻结契约含 Java CVE 义务，但执行计划只保留已经完成的 Python lint
- **THEN** 即使 Python 结果干净，交付和请求都保持 incomplete，并列出遗漏的 Java CVE 义务

#### Scenario: User requests a plan
- **WHEN** 调用 `codeguard plan check all .`
- **THEN** 返回义务与待解析前置条件，不执行外部构建或扫描

#### Scenario: A language identifier is unknown
- **WHEN** 用户输入未注册的语言 ID
- **THEN** 执行前返回用法错误，列出规范 ID/别名，不启动检查器

#### Scenario: A candidate checker is not configured
- **WHEN** 项目未配置候选的 Javadoc 检查器，批准策略也未要求它
- **THEN** 报告说明 `missing` 和可执行的配置建议，不产生 Javadoc 代码违规或未执行义务；其他已配置检查器继续运行

#### Scenario: Policy requires an unconfigured checker
- **WHEN** 批准策略明确要求 Javadoc 检查，但项目没有有效配置
- **THEN** 报告说明配置缺口并将交付标为 incomplete，不伪造 Javadoc 源码违规或干净通过

### Requirement: Rust CLI SHALL expose a versioned exit contract

Rust CLI MUST 使用 0 请求通过、1 违规、2 用法错误、3 必需义务未完成、4 内部故障、130 取消。执行后的聚合优先级 MUST 为取消、内部故障、未完成、违规、通过；已有发现 MUST 保留。原生退出码 MUST 独立记录，不直接透传作为 CLI 结论。

#### Scenario: Findings coexist with an unavailable scanner
- **WHEN** lint 有已确认违规且必需 CVE 工具不可用
- **THEN** 返回 3，报告同时包含违规和未完成项

#### Scenario: Native tool exits with code two
- **WHEN** 工具原生退出 2
- **THEN** 依据该工具契约生成结果，不将其直接解释成 Codeguard 用法错误

#### Scenario: One task fails internally after another finds a violation
- **WHEN** `check all` 的一个任务内部故障，而另一任务已经取得原生 finding
- **THEN** CLI 返回 4 和结构化内部故障报告，列出失败任务及各任务状态，并保留已取得的原生 finding；交付保持 incomplete，不能把该 finding 或故障解释成白名单放行

#### Scenario: Cancellation follows a completed native finding
- **WHEN** `check all` 并行运行期间，一项原生检查已取得 finding，另一项收到 SIGINT 并完成取消清理
- **THEN** CLI 返回 130、`command_status=cancelled`，保留已取得的 finding 与取消任务状态；不返回普通未完成退出码 3 或交付 allow

### Requirement: Reports SHALL preserve semantics across public formats

报告 MUST 带 schema_version、请求选择、项目检查器配置状态、本次原生结果、发现及交付判定。human/JSON/SARIF/MCP MUST 来源于同一语义报告；宿主对话反馈 MUST 区分 `configured/missing/invalid/unknown` 与 `passed/finding/tool_error`，不把“已配置”说成“已通过”。结构化 stdout MUST 不混入进度或原始日志；公开结果 MUST 脱敏，私有原始证据单独存储。未知协议 major MUST 拒绝消费。检查请求与 RunReport 的原始 JSON 在全部嵌套层级 MUST 拒绝重复对象键，并设输入字节预算；不能先把重复键覆盖成普通对象再校验交付判定或预算。

#### Scenario: Duplicate protocol fields conceal a gate or execution option
- **WHEN** 原始 RunReport 同时含两个 `delivery_gate`/`decision` 键，或内嵌检查请求的 `jobs` 键重复且后值看似合法
- **THEN** 消费入口拒绝整份原始 JSON，不选取前值或后值，也不生成交付通过或对话摘要

新增误报白名单报告字段时 MUST 提升协议版本并迁移所有消费者：报告分别保留原始 finding、有效处置、活跃阻断和未完成义务，交付决策增加 `allow_with_exceptions`。CLI 请求成功可退出 0，但 human/JSON/SARIF/MCP MUST 明示“带批准例外交付”及决策 ID、可信修订、期限与本次匹配范围，不能渲染成普通 PASS；局部检查仍为 not_evaluated。旧消费者不认识新决策时 MUST 拒绝将它映射为普通 allow。

#### Scenario: Approved false positive survives every public format
- **WHEN** 有效误报白名单是唯一原始阻断，完整交付检查得到 allow_with_exceptions
- **THEN** 协议版本、CLI/MCP/Hook/SARIF 均保留原始 finding、可信批准引用、期限和带例外语义，不能渲染普通 PASS

#### Scenario: SARIF contains no findings but a required task timed out
- **WHEN** 一个必需检查超时且没有有效 finding
- **THEN** SARIF 仍表达未完成，标准报告不得变成干净通过

#### Scenario: SARIF consumes an unverified allowlist claim
- **WHEN** 结构有效的报告声明一个 finding 已被误报白名单处置，但报告来源和批准权威尚未独立核验
- **THEN** SARIF 保留该 finding 为结果、显示处置声明及来源未核验状态，不创建会使查看器隐藏结果的 suppression；只有完成可信绑定后才可声明批准有效

#### Scenario: A new run report claims a stale false-positive disposition
- **WHEN** 新版 RunReport 声明误报处置，但本轮 finding 的完整原生身份缺失，或其文件/依赖图/advisory、指纹、工具/适配器/rulepack 摘要与决策身份不同
- **THEN** 严格消费者拒绝该报告的处置声明，不把它投影为已批准例外；原生规则、工具制品、检查器类别及主目标也须与本轮 finding 和报告身份一致。旧版可作为历史未核验声明读取，未知未来版本不得按现有语义猜测；即使新版结构匹配，来源与独立批准仍须由宿主核验

#### Scenario: A source claim sits outside the native coverage or no longer matches the workspace
- **WHEN** 新版报告的源码 finding 主目标不在对应义务的预期及实际覆盖集合内，或宿主从独立指定的工作区安全读取当前文件后发现 SHA-256 不同、文件缺失或路径经过符号链接
- **THEN** 不得将该 finding 的白名单处置解释为本轮有效；覆盖结构校验直接拒绝报告，内容复核失败时宿主保持未完成。内容摘要匹配本身也不证明原生工具确实运行或批准来源可信，终局门禁仍须复核

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

### Requirement: Public commands SHALL have distinct operation contracts

CLI MUST 提供帮助/版本、detect、capabilities、init、plan、doctor、rules list、config validate/explain、tools list/verify/install、六类检查、三个 gate、work sync、status、next、task 协作、fix/verify、mcp serve 与显式 compat。每个命令 MUST 定义参数、默认值、输入/结果类型、允许副作用、错误与下一步；CLI/MCP 接入 MUST 复用核心服务，不另建检查或门禁逻辑。完整目录和 C01–C36 追踪见设计文档，命令 schema、help、映射和验收 MUST 保持一致。

#### Scenario: Help is requested outside a project
- **WHEN** 用户在无项目或无扫描工具的目录请求 help 或 version
- **THEN** 从发行元数据返回信息，不初始化、不扫描、不联网更新

#### Scenario: A capability exists but its tool is not installed
- **WHEN** capabilities 返回实现能力，而 tools list 显示必需工具缺失
- **THEN** 两者分别说明发行能力和本地库存，不将能力声明当作环境或质量通过

### Requirement: Operation success SHALL remain separate from quality certification

`rules whitelist list/explain/propose` MUST 复用规则与策略服务。list/explain 为只读；propose 仅产生候选及依据，不批准、不修改有效政策、不签发质量结论。`config validate` MUST 校验白名单 schema、精确范围、批准身份、期限和策略差异；静态无法验证可信批准时 MUST 报未完成，不能按本地声明通过。
propose 缺少本轮完整原生 finding 或工具/适配器/rulepack 身份时 MUST 返回未完成和缺证据项，不能以占位摘要生成形式上有效的候选。

命令结果 MUST 有版本及 report_type/operation/request_id/command_status/exit_code/warnings/next_actions，并保留类型特有的完整payload。RunReport MUST 继续包含逐项完整性、身份、finding和gate。信息/计划/管理操作的 exit 0 只表示该操作完成；doctor/config validate/tools verify 对所选必需条件不能验证满足时 MUST 返回3。非交付操作 MUST NOT 据操作成功签发allow，status 展示历史决策时 MUST 附来源身份与freshness。MCP 服务生命周期与单请求结果 MUST 分开。

#### Scenario: Plan contains a missing prerequisite
- **WHEN** plan 完整返回了含缺JDK条件的计划
- **THEN** 可exit 0但不声称就绪，doctor对同一必需缺失返回3且不虚构源码违规

#### Scenario: MCP request times out while the server remains available
- **WHEN** 一个MCP检查请求超时
- **THEN** 该请求返回未完成语义，服务器存活不作为检查成功证据

### Requirement: Preparation commands SHALL preserve observation and mutation boundaries

detect/capabilities/rules/config/tools list和verify MUST 静态观察，不执行项目脚本或安装工具。config validate MUST 核验配置与批准策略引用；explain MUST 解释来源而不自动选择较松要求；tools verify MUST 区分制品身份与运行能力。doctor MAY 执行适配器声明、身份已解析且有界的诊断，不隐式构建、安装、启动服务或读取凭据值。doctor 的 PrerequisiteReport MUST 带run_id、报告类型、工作区/内容/政策/工具身份、范围与freshness，可被同步为准备证据，不能作为源码质量通过。

tools list 的本地候选库存 MUST 明示仅覆盖声明锁，完整必需集合未经核验；MUST 区分声明版本、当前平台制品观察和跨平台未检查条目。运行时/发行包须分别显示缺口，字节相符不能称已批准、可启动或 ready。缺锁、空当前平台或未获可信策略绑定不能将空库存解释为无必需工具；普通候选不得自写 required_by_policy。MUST 复用制品核验服务，不启动 wrapper、联网、安装或写工作区。

#### Scenario: Inventory contains a tool for another platform
- **WHEN** tools list 读取结构有效但未经批准的跨平台锁候选
- **THEN** 保留该声明并标记 other_platform/not_inspected，不访问其制品、不虚构本机缺失或准备通过；当前平台条目按同一制品核验契约展示

#### Scenario: Tool bytes match but its runtime cannot start
- **WHEN** tools verify确认制品身份而doctor发现运行时不能启动
- **THEN** tools verify不被撤写为源码违规，doctor报告必需准备未完成，后续检查不能假通过

#### Scenario: Existing suppression conflicts with approved policy
- **WHEN** 配置包含未批准的规则弱化
- **THEN** validate报告未完成，explain展示来源与拒绝原因，不自动修正阈值或签发批准

#### Scenario: Detection is complete but a dynamic condition is unknown
- **WHEN** detect完整读取允许范围但构建条件不能静态解析
- **THEN** 返回含unknown的DiscoveryReport及exit0，不执行脚本、不写画像或任务

#### Scenario: Required discovery inputs cannot be read
- **WHEN** 必要目录因权限错误无法观察
- **THEN** detect保留部分观察并返回3，不能按空项目或完整发现解释

#### Scenario: Capabilities are planned unknown or corrupt
- **WHEN** 查询已登记planned语言、未知语言ID，或发行注册表损坏
- **THEN** 三者分别为显式planned/gap的查询成功、用法错误2、内部故障4；均不隐式探测或安装工具

### Requirement: Tool installation SHALL use a bounded explicit plan and apply

`tools install --lock PATH [--distribution-manifest FILE] [--dry-run|--apply]` 默认 MUST dry-run，返回精确来源、摘要、安装范围和限制。apply MUST 只安装可信锁与授权范围内制品，验证后逐制品原子发布；部分失败返回未完成且可恢复。扫描/诊断 MUST NOT 隐式调用安装，不自动升级到latest、修改全局PATH或提权。工具存在/安装成功 MUST NOT 直接证明项目检查通过。

#### Scenario: Tool installation has no mode flag
- **WHEN** 调用 tools install仅给出lock路径
- **THEN** 只输出安装计划，不下载或更改工具库存

#### Scenario: Apply is requested with only an untrusted local lock candidate
- **WHEN** 安装候选只通过本地结构及制品核验，可信锁或发行授权尚未绑定
- **THEN** 返回明确缺口及 blocked_before_mutation，不调用发布服务、不联网/安装/写工作区；条目可解释原有制品与恢复动作，但不得宣布已安装或 ready

#### Scenario: One of several locked artifacts fails verification
- **WHEN** apply中某个制品校验失败
- **THEN** 不发布该制品，保留其它已验证结果并返回3，后续恢复不消费半成品

发行清单 MUST 使用版本化、拒绝未知和重复字段的有界协议；制品 MUST 绑定工具锁原始字节 SHA-256、精确工具 ID/版本/平台、二进制及来源引用摘要和 bundle 身份。清单声明的子集 MUST NOT 证明必需库存或运行时闭包完整。下载地址 MUST 使用 HTTPS 且不得携带用户凭据、查询参数或片段；包摘要、传输大小和展开上限 MUST 明确且有界。原始二进制包的包摘要/大小 MUST 与入口摘要/展开大小一致，不得声明归档入口或 bundle；归档入口 MUST 是无空段、点段、回退段或平台绝对路径的相对路径。结构/引用匹配 MUST NOT 自授可信来源或安装批准，绑定入口 MUST 重新验证传入对象。

#### Scenario: Explicit manifest is inspected during install preview
- **WHEN** tools install 显式提供 --distribution-manifest FILE
- **THEN** 有界只读读取并展示未提供/不可读/无效/锁不可用/未绑定/绑定未批准状态；逐工具只展示精确绑定的脱敏包声明，原始下载地址不进入公开反馈；不执行、下载或写入，缺其它工具及运行时覆盖仍保持未完成

#### Scenario: Manifest attempts to bind changed lock bytes or another artifact
- **WHEN** 清单绑定的锁原始字节变化，或工具/版本/平台/来源/bundle/二进制身份与锁不一致
- **THEN** 拒绝绑定，不下载或发布；不得以 JSON 语义相似、版本字符串相同或文件已存在代替摘要核验

#### Scenario: Manifest is locally valid but not independently authorized
- **WHEN** 本地清单及其声明子集通过结构与精确锁绑定
- **THEN** 仅产生声明绑定，不推导覆盖完整、可信来源、批准、ready 或门禁通过；正式 apply 仍须独立发行授权

#### Scenario: Manifest includes unsafe package metadata
- **WHEN** 清单包含重复字段/工具平台条目、未知批准字段、凭据地址、零摘要、超限大小或非法归档入口
- **THEN** 拒绝清单并返回固定脱敏诊断；不把准备输入错误当成源码违规

### Requirement: Gate commands SHALL receive explicit delivery content

pre-commit MUST 使用Git传入环境的index；pre-push MUST 接受remote-name/remote-url和完整stdin ref/OID元组，不回退HEAD；ci MUST 通过版本化input请求明确仓库及不可变OID集合与预期来源。CI输入文件 MUST NOT 自授策略权威。删除ref或无适用源码不得签发代码质量allow；不同内容来源的结果不可互相替代。

#### Scenario: CI checks a merge result rather than the branch head
- **WHEN** CI请求指明merge结果OID
- **THEN** 仅按指定不可变内容建立认证，不使用当前checkout或分支头的通过代替

#### Scenario: Pre push input is absent
- **WHEN** pre-push没有获得要求的ref输入
- **THEN** 明确失败而不检查默认HEAD冒充本次推送；合法全删除集合独立记录不适用

### Requirement: Execution budgets SHALL have explicit defaults and a shared deadline

有执行行为的命令 MUST 在版本化命令schema中固化timeout/jobs的支持范围、默认值和来源优先级，报告有效值。初版检查/gate/fix/verify默认总预算30分钟，doctor 2分钟且单探测不超过10秒，tools install 10分钟；检查默认并行度为min(4,max(1,可用CPU并行度))。CLI优先于已登记环境变量、项目运行默认及发行内置值；这些值 MUST 不改变质量义务。子任务和重试 MUST 继承剩余deadline，包含排队、快照、执行、解析、存储及清理，不重置预算。无法及时回收进程 MUST 明示cleanup_pending而不声称完成。

项目检查/复检的可选运行默认值 MUST 从版本化 `codeguard/runtime.json` 读取；该文件只能声明运行预算，不能承载或覆盖必需规则、扫描排除、白名单及批准身份。CLI/已登记环境变量优先于它；当项目默认值成为候选来源时，未知字段、坏版本、非普通文件、符号链接或无效预算 MUST 在执行原生工具及取得任务租约前拒绝，不回退内置默认值来掩盖配置错误。报告 MUST 保留最终值与 `project_default` 来源，项目默认值不能把不完整检查改成通过。

`check all` 的并行上限 MUST 支持 `--jobs`、登记的 `CODEGUARD_JOBS`、同一 `codeguard/runtime.json` 中可选的 `jobs` 和内置默认值，按上述来源优先级逐字段选择；显式值限定为 1–64 的十进制整数。项目文件一旦为任一字段的候选来源，MUST 对整个版本化文档做一次严格读取和校验，防止超时与并行度从同一文件的不同版本混用。报告 MUST 分别说明并行上限、来源、本轮可执行任务数及实际启动数；并行上限不是实际并发证明，不能因只接入一个适配器就声称多语言并发已验收。

#### Scenario: Check parallelism source and actual work differ
- **WHEN** `check all` 在有多个可用 CPU 的机器上只接入一个原生任务，且调用方设置 `--jobs 4`
- **THEN** 调度器以上限 4 运行，反馈分别报告上限 4、一个可执行任务和实际启动任务数，不声称四项检查已完成

#### Scenario: Invalid selected jobs budget
- **WHEN** 选中的 `--jobs`、登记环境或项目默认值为零、负数、超过 64 或非十进制整数
- **THEN** 启动原生工具前返回 2；较高优先级的有效值覆盖较低优先级的无效环境值，项目文件被选中时仍须整体严格校验

#### Scenario: Project runtime default is selected
- **WHEN** `codeguard/runtime.json` 有效且未设置显式 CLI 或已登记环境预算
- **THEN** 本次检查使用项目默认值，报告来源为 `project_default`；之后仍须执行全部适用质量义务

#### Scenario: Project runtime default is malformed
- **WHEN** 没有更高优先级的预算来源，且项目运行默认值版本错误、预算非法、文件为链接或含质量排除字段
- **THEN** 启动原生工具和取得任务租约前拒绝，不静默回退或采纳其中的质量豁免

#### Scenario: A retry starts after most of the request budget is consumed
- **WHEN** 某任务在整次请求接近deadline时满足瞬时重试条件
- **THEN** 重试只能使用剩余预算，不能重新获得完整timeout或降低检查覆盖

#### Scenario: Timeout is zero or unsupported for the selected command
- **WHEN** 调用方提供零预算或某命令不支持的执行选项
- **THEN** 执行前返回2，不将零解释为无限等待或静默忽略参数

### Requirement: Report export SHALL preserve identity and persistence failures

标准报告 MUST 保留可逆的路径身份、展示位置和多位置/包级证据，不以有损字符串或行号单独识别问题。`--output` MUST 原子写入与所选格式一致的报告；写入失败 MUST 保留已取得的检查证据并报告操作未完成，不能把质量结论改成另一项源码违规。JSON未知major或非法枚举 MUST 拒绝，兼容minor扩展不得覆盖必需字段。跨工具归并 MUST 有明确规则映射并保留原始来源。

#### Scenario: Report destination cannot be written
- **WHEN** 检查已取得有效发现但指定output不可写
- **THEN** 保留检查结果并返回操作未完成及恢复位置，不丢弃finding或假称报告已保存

#### Scenario: Non UTF8 paths and equivalent tool findings are exported
- **WHEN** 路径含非UTF8字节且多个工具报告近似文案
- **THEN** 保留可逆路径身份，仅按批准等价映射归并，不能按展示字符串抵消发现

### Requirement: npm public CVE feedback SHALL preserve local observation boundaries

`cve typescript PATH` SHALL 支持显式Node/npm入口、具体版本、原用户/全局配置、可选审计源及共同预算；不执行package脚本、fix或安装。缺上下文提供结构化准备原因，重复/未知参数为使用错误。human/JSON MUST 反馈配置声明、原生依赖数量和脱敏组件/advisory/锁版本观察；零发现不得成为库覆盖或交付通过。当前局部协议固定advisory_coverage和delivery_decision为not_evaluated、工具unverified；工作台反馈必须反映未连接、准备失败或实际同步结果，不能固定声称已连接。取消退出130，其余局部反馈退出3，不能假称完整CVE检查。

#### Scenario: Explicit npm invocation returns coherent empty audit
- **WHEN** 公开命令获得本轮稳定输入和一致原生空报告
- **THEN** 保留依赖数量、声明状态与具体下一步，库覆盖/交付仍未判定，不能手动关闭修复任务

#### Scenario: npm context missing or interrupted
- **WHEN** 未提供工具/配置上下文或执行被取消
- **THEN** 输出准备/取消原因，不生成源码违规、不安装工具、不批准白名单；取消不要求修改源码

### Requirement: npm public audit SHALL consume shared runtime timeout defaults

npm公开CVE入口 MUST 按CLI、登记环境变量、项目runtime.json、内置默认值顺序选择超时预算。只在项目配置成为候选时读取并严格校验，不以无效文件回退掩盖错误。参数及环境值错误为使用错误；项目默认值无效为准备未完成，并在原生工具启动之前停止。反馈0.2 MUST 记录最终预算与来源，未取得有效预算时为null；不能声明可中断文件I/O的硬预算。历史0.1反馈仍按原严格结构消费，不补造预算。

#### Scenario: npm timeout precedence and malformed project defaults
- **WHEN** 原项目预算、登记环境值与CLI值同时存在或低优先级文件格式无效
- **THEN** 只使用最高优先级合法来源，显式CLI值不因低优先级坏文件失败；项目文件为候选且含未知字段、坏协议或符号链接时返回未完成，原生审计不启动
