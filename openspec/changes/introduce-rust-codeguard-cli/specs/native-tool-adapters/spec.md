## Purpose

定义传统原生工具在 Codeguard 内的配置发现、受控调用和结果解释，使语言注册、项目配置、工具安装与本次检查结果不再被混为同一种支持状态。

## ADDED Requirements

### Requirement: Explicit Maven Javadoc selection SHALL not fall back to isolated single-file diagnostics

项目检查明确提供 Maven 执行上下文时，Javadoc MUST 选择原 POM/完整显式主源码的多文件检查，不再额外启动隔离单文件 JDK 探针。构建根不适用、配置/类路径未知、环境缺失或原生失败 MUST 保留具体未完成诊断，不得用单文件探针代替项目配置。未选择 Maven 的显式 JDK 局部模式保持可用，但 MUST 标注其单文件范围且不推导项目覆盖。报告 MUST 版本化显示探针模式及独立多文件结果；跨文件类型引用不得因为已舍弃的单文件上下文额外生成源码 finding 或环境任务。

#### Scenario: Two configured source files refer to each other
- **WHEN** 用户明确提供 Maven/JDK/离线检查上下文且静态原 POM 可重放
- **THEN** 仅运行 Maven 多文件检查，所有单文件 observation 为空并指向构建根结果；原生日志和源码位置可展示，覆盖/批准仍单独核验

#### Scenario: Maven cannot establish a valid project scope
- **WHEN** 已选择 Maven 但 POM 动态/继承或检查前置缺失
- **THEN** 返回多文件具体未完成原因，不回退单文件 JDK 以制造无关诊断或伪装完成


### Requirement: Adapters SHALL publish verifiable capability contracts

每个 adapter MUST 声明语言/方言、类别、可识别的原生配置、工具和运行时兼容范围、输入范围、报告格式及退出语义。发行能力与项目配置分开呈现；项目检查器状态 MUST 区分 `configured`、`missing`、`invalid`、`unknown`。formatter 存在 MUST NOT 自动证明 lint/comments 能力。

#### Scenario: A project has no Javadoc checker configuration
- **WHEN** Java 项目没有启用 Javadoc 检查规则或可识别的检查命令
- **THEN** 返回 `missing` 与可操作的配置建议，不报告源码缺少 Javadoc，也不声称已检查通过

#### Scenario: A stable legacy entry has only a formatter
- **WHEN** 迁移 Julia 或 Pascal，原 lint 命令为空
- **THEN** 补充经过真实验收的只读检查能力前保持能力缺口，不能据旧 stable 标签通过

#### Scenario: Shell dialect is unsupported
- **WHEN** 项目含 zsh，而选定 ShellCheck 不支持该方言
- **THEN** 为其保留能力缺口或选择已验证的专用适配器，不静默删除义务

### Requirement: Native evidence SHALL be interpreted per tool contract

adapter MUST 根据工具版本的报告及退出语义解析结果；MUST NOT 以通用非零、exit 1、关键词或模型主观判断替代。无效、截断、陈旧、与计划不符或内部矛盾的报告 MUST 产生未完成。有效部分发现 MUST 保留。

Rust 注释诊断 MUST 使用原生 Cargo/rustdoc 机器流，不能复用只接收 Clippy 规则的解析器或通过正则重写文档规则。已识别 missing_docs 与 rustdoc::broken_intra_doc_links 的观察 MUST 保留原生规则/级别、唯一主定位和原生 package/manifest/target 身份供执行层核对；不得把其它编译错误改称注释问题。重复 JSON 键、缺失/重复/失败的结束记录、结束后新事件、歧义主定位及未支持的警告 MUST 保持未完成。纯解析或显式局部库目标执行不证明项目原配置、完整工作区/features/targets、可信工具或批准规则覆盖。

公开 comments rust 的局部探针 MUST 显式选择Cargo入口、采用共享预算与受控运行时，使用锁定离线输入和私有输出目录，不隐式下载/安装工具。MUST 将当前清单/锁/已观察源码、工具字节及原生主目标核对，输入变化、目标越界或机器流异常返回未完成。显式探针规则 MUST 标明不代表项目获批准的生效文档规则；局部零诊断不得关闭任务或批准白名单，完整配置闭包与构建组合仍须独立验证。

Rustdoc发现候选身份 MUST 绑定原生主定位字节范围所对应的真实UTF8源码及精确规则/相对目标，而不是诊断列表序号；范围缺失、倒置、越界或切断UTF8时不得猜测行内容补造。相同原生记录可去重，但同一候选身份对应多个不同源码范围/诊断时 MUST 明示歧义，保留观察且不分配正式finding ID或关闭任务。文档修复/行移动不得让剩余发现借用另一问题的顺序身份；完整符号归属尚未建立时仍是候选。

Rustdoc逐问题反馈 MUST 提供问题证据、规则依据、允许修改的范围、修复步骤、原工具复检命令、尝试历史状态和关闭条件。局部完成且身份唯一时可提供限定目标源码的修复指引；输入变化、歧义、取消或其它未完成状态 MUST 保留调查指引且不给源码修改范围。尚未接入持久任务时 MUST 明示历史未接通，不得把空历史伪装为无失败尝试。简报不能授权任务关闭、白名单批准或完整交付。

#### Scenario: Rustdoc evidence becomes stale before repair guidance
- **WHEN** 原工具发现文档问题，但同轮输入变化或发现身份歧义
- **THEN** 反馈保留原生证据，指向重新检查或身份调查，允许修改的源码范围为空，不指示按旧定位修复

#### Scenario: Rustdoc observations synchronize to an initialized workbench
- **WHEN** 初始化工作区的本轮文档观察具有绑定身份和唯一原生发现，且同步时源码、清单与锁仍匹配
- **THEN** 保存本地报告并自动同步为同一稳定问题及可读任务；重复扫描更新观察而不重复建任务，未完成/歧义产生检查准备任务，陈旧发现不得驱动源码修复

#### Scenario: Full Rust check schedules independent lint and documentation observations
- **WHEN** check all发现Rust源码并取得显式Cargo上下文
- **THEN** 共享预算分别调度Clippy与rustdoc，保留各自结果、未完成原因和持久任务；库文档探针不代表项目原配置或完整构建组合，不能授予完整交付通过

#### Scenario: Rustdoc task recheck encounters native suppression
- **WHEN** 文档任务使用同一 Cargo 在稳定输入上复检，普通扫描未发现原问题而原生 force-warn 对照发现同文件同规则
- **THEN** 记录 suppression_requires_review 和原工具证据，保持任务open；两轮局部零发现仍须策略/范围核验，不自行关闭或批准白名单

#### Scenario: Rustdoc forced evidence has a forged identity
- **WHEN** 文档任务复检封套中的强制告警报告指纹、原生范围或输入身份损坏，普通报告仍合法
- **THEN** 导入必须独立核验两份原生观察，不得仅凭封套形状或普通报告有效就消费损坏对照；保持未完成并指出证据修复动作

#### Scenario: Rustdoc declarations have identical source text
- **WHEN** 同文件两个不同原生范围产生相同规则及声明字节，缺足够符号归属区分
- **THEN** 保留两项歧义观察，finding ID为空且运行未完成，不按出现顺序发放稳定任务身份或把修复一项解释为另一项关闭

#### Scenario: Public Rust comments probe observes a selected library
- **WHEN** comments rust 收到显式Cargo工具，在原生库目标上观察文档诊断或零诊断
- **THEN** 对话显示规则/位置与局部范围，整体仍未完成/not_evaluated；清单/锁/源码/工具变化或诊断目标归属失配不能作为当前完整观察，未集成的持久任务须明确说明

#### Scenario: Rust comments cancellation coincides with input changes
- **WHEN** 原生文档进程被用户取消，运行后复核同时发现源码变化
- **THEN** 保留取消状态和退出130，局部观察保持未完成；不能用输入变化将取消降级为普通退出3或解释为修复

#### Scenario: Native rustdoc reports documentation diagnostics
- **WHEN** 原生 rustdoc 机器流产生 missing_docs 或 broken_intra_doc_links 并有唯一主定位及目标身份
- **THEN** 适配器保留具体规则、位置及目标归属；不能因 Clippy 不接收这些规则而丢失注释观察，也不能据局部观察签发完整项目通过

#### Scenario: Rustdoc encounters compilation failure or ambiguous report
- **WHEN** 同轮有编译错误、未知警告、重复键、主定位歧义或异常结束记录
- **THEN** 结果标未完成，保留已观察诊断用于调查，不把环境/报告失败当注释违规或零问题通过

#### Scenario: Tool verification observes a local lock candidate
- **WHEN** `tools verify` 读取本地工具锁候选并核对当前平台的入口、可选运行时及目录包字节
- **THEN** 逐项反馈匹配、缺失、不可读、摘要失配或不可执行及恢复动作；不启动 wrapper、安装或联网，不把结构合法/字节匹配解释为可信批准、可启动或规则已执行。本地来源未获核验时整体未完成、readiness=unknown、无门禁效力；坏锁或链接锁不生成源码 finding

#### Scenario: Doctor diagnoses an explicitly selected Ruff binary
- **WHEN** doctor 观察项目配置并收到显式绝对路径的 Ruff 原生入口
- **THEN** 在私有目录以固定版本参数、清空继承环境、共同预算及单探测上限执行版本诊断；不运行源码扫描或项目 wrapper。未选择工具不冒充工具缺失，脚本入口在无法隔离时启动前未完成；原生成功仅形成未核验来源的局部版本观察，不能给 readiness 或质量门禁签发通过，必须反馈其它诊断缺口及下一步

#### Scenario: Version discovery fails before checking source
- **WHEN** 原生版本探测超时、预算在启动前耗尽、无法启动、被取消、被信号终止或输出/管道/清理失败
- **THEN** 保留执行层的具体失败类别，返回环境阻塞和对应恢复动作；不启动后续质量检查，不将失败误报为源码违规

#### Scenario: A version process exits zero with incompatible output or changed artifact
- **WHEN** 原生版本探测退出零，但 stdout 不符合适配器精确版本契约、出现未预期 stderr、工具字节改变，或本轮私有记录失败
- **THEN** 分别反馈版本不符、输出异常、制品变化或记录失败；不运行后续源码检查，不将零退出推导为可用、质量通过或批准身份。超时/取消/无法启动/信号/输出超限保留各自执行类别，共享截止时间不得因记录或工具复核重置

#### Scenario: Valid finding precedes a crash
- **WHEN** 工具先产生有效违规，随后发生配置或进程故障
- **THEN** 保存该 finding 并记录 incomplete，不覆盖为纯工具错误或完整违规结果

#### Scenario: Tool exits zero with a stale report
- **WHEN** 报告属于此前内容或当前规则未执行
- **THEN** 拒绝将其作为本次通过证据

#### Scenario: A Clippy finding disappears behind a native lint allowance
- **WHEN** Rust 任务普通 Clippy 复检不再报告原规则，但同工具、同目标字节、同 manifest 和同截止时间内的 `--force-warn <原规则>` 原生对照重新检出该稳定 finding
- **THEN** 记录原生抑制待核查并保留任务；对照失败、输入或工具身份改变时保持 incomplete，不能把零诊断当作修复或白名单批准

#### Scenario: A Go target disappears because native build selection excludes it
- **WHEN** 原 Go finding 在默认构建条件的 vet 复检中未检出，但同工具、同受控环境与同截止时间内的 go list JSON 显示目标被构建标签、平台或 CGO 排除，或未列入本轮原生源文件集合
- **THEN** 保留任务并要求核查构建范围；不得把未检查目标解释为已修复。原生清单损坏、归属未知或两轮源码/模块/工具变化时为 incomplete；局部 selected 观察不得证明所有平台与规则覆盖或白名单批准

#### Scenario: Go source inputs change after a verification observation
- **WHEN** Go 复检绑定的整组源码或模块清单与读取下一步/同步时的当前内容不一致
- **THEN** 旧观察不能指引关闭；next 要求原工具复扫，同步将旧发现计入历史而非当前活动源码任务

### Requirement: Static detection families SHALL remain explicit and extensible

Codeguard MUST 分别记录 `lint`、`comments`、`dependencies`、`cve`、`security`、`build` 六类别。`comments.api_docs` 对应 Javadoc 等 API 文档检查；`dependencies` 对应依赖图、版本治理、许可证、SBOM 和来源；`cve` 对应漏洞匹配。28 个检测族是可扩展的**候选目录**，不是每个项目都必须配置或逐项证明执行的清单。Codeguard MUST 识别项目中实际配置的检查器、规则和命令；已配置且可用的检查器由 Rust 调用原生能力，并把本次结果反馈给智能体。未配置、配置错误和工具不可用 MUST 分开说明。只有批准策略明确要求的缺失检查才影响交付门禁，不能把所有候选检测族自动升级为必需义务。

#### Scenario: Configured Javadoc checker reports a missing comment
- **WHEN** Java 项目已配置 Javadoc 检查，原生工具返回有效缺失注释诊断
- **THEN** 智能体对话显示文件、位置、规则、修复建议和复检命令；不要求额外的逐族执行证明

#### Scenario: Javadoc output cannot be attributed to the configured project checker
- **WHEN** 局部 JDK doclint 探针发现缺失注释，但尚未绑定项目生效配置、完整源集、可信工具身份或所需类路径
- **THEN** 可以显示带来源的局部诊断和复检建议；不得把它写成已批准项目 finding、完整检查通过或可关闭任务的证据。未知原生输出、缺少类路径和工具执行故障标为未完成，不转换为代码违规

#### Scenario: Javadoc plugin declaration disables missing-comment checks
- **WHEN** Maven POM 声明 Javadoc 插件，但显式 `doclint=none`、`all,-missing` 或其它不含 `missing` 的静态规则组合
- **THEN** 注释检查配置显示为无效并给出启用 `missing` 的建议；动态 doclint 或动态错误处理策略显示未知，显式 `failOnError=false` 显示无效，不能仅凭插件存在宣称注释规则已启用

#### Scenario: Maven Javadoc reports warnings with a successful build
- **WHEN** 已配置的 Maven Javadoc 插件产生有效缺注释警告，但 `failOnWarnings=false` 使原生命令返回 `BUILD SUCCESS`
- **THEN** 仍须解析并反馈原生缺注释诊断；退出码和 `BUILD SUCCESS` 不得覆盖警告。复检必须验证本轮独立执行与目标产物，不能用上轮缓存导致的零诊断关闭任务

#### Scenario: A successful Javadoc log has no diagnostic block
- **WHEN** 已完整注释的项目首次执行与同目录重跑均输出无诊断的 `BUILD SUCCESS`，且日志未提供可核验的本轮产物身份
- **THEN** 解析器只能记录无诊断日志观察，不能据此证明本轮重新检查、关闭任务或签发项目通过；须由受控执行器另行核验新鲜快照和产物归属

#### Scenario: A synthetic Maven Javadoc POM differs from project configuration
- **WHEN** 隔离探针准备用固定 POM 替代项目 POM 来扫描多份源码
- **THEN** 不得把探针诊断归为该项目已配置检查器的 finding；`check java` 不用合成 POM 遮盖真实项目配置，配置无法受控重放时保持未完成

#### Scenario: A simple project POM is replayed for Maven Javadoc
- **WHEN** 当前项目 POM 直接固定 Javadoc 3.12.0 与 `doclint=missing`，且静态验证没有父 POM、profile、依赖、模块、扩展或其它插件
- **THEN** Rust 在私有快照中复制原 POM 和显式 Java 源码，运行原生 Maven，报告原 POM 字节摘要及局部诊断；若 POM 变化或输出无法归属，结果未完成；即使日志干净，也不能据此声明完整源集或交付通过

#### Scenario: A complex project POM cannot be safely replayed
- **WHEN** Javadoc 声明依赖继承、动态属性、其它插件或未知构建内容
- **THEN** 不以固定 POM 替代项目配置生成可归因诊断；标记项目 POM 重放不适用，保留检查义务并给出解析生效模型或受控执行的下一步

#### Scenario: No SAST or IaC checker is configured
- **WHEN** 项目只配置秘密扫描，而没有 SAST 或 IaC 检查器配置
- **THEN** 如实列出已配置的秘密扫描和未配置的候选检查；不虚构 SAST/IaC 已执行，也不凭候选目录自动判代码违规

#### Scenario: Java dependency and CVE checker declarations differ by module
- **WHEN** 多模块 Java 项目的根构建文件声明 OWASP Dependency-Check，而内层构建根没有声明，且两处都有 Java 源码
- **THEN** `check java` 对已识别 CVE checker 报告构建根配置混合与逐模块核查动作，不将根声明推广为全项目已配置；已声明但未执行原工具时保持未完成，不产生“无漏洞”结论

#### Scenario: A Gradle source tree has no Maven checker identity
- **WHEN** Java 源码归属 Gradle 构建根，或 Maven 与 Gradle 构建根混合，且尚未解析 Gradle 生效模型
- **THEN** 类别反馈说明 Gradle 或混合构建模型未解析，不把 Maven checker ID 贴到这些源码，也不推断依赖治理、CVE 或安全检查已完成

#### Scenario: Python dependency inputs are not mistaken for a CVE result
- **WHEN** Python 构建根只有逐行固定版本的 requirements、含动态约束的 requirements、uv/Poetry 锁文件，或没有可识别依赖输入
- **THEN** `detect` 按构建根分别记录输入位置及相应未解析原因；`plan cve python` 与 `check all` 保留原生检查器、依赖图和漏洞数据库待核验状态。固定版本行不等于完整传递依赖图，锁文件存在不等于已解析或已完成漏洞匹配；任何一种情况都不得生成零漏洞结论或已完成门禁

#### Scenario: Python dependency input changes during discovery
- **WHEN** Python 依赖文件在首次清单观察后不可读或字节摘要变化
- **THEN** 本轮发现标记不完整，指出变化的输入和重新发现动作；不能将旧输入或相邻构建根的锁文件用作当前根的 CVE 证据

#### Scenario: A tool-specific Python lock is not a pip-audit standard lock
- **WHEN** 项目有符合 PyPA 命名的 `pylock.toml` 或 `pylock.<name>.toml`，或只有 `uv.lock`/`poetry.lock`，或同根同时存在两类锁
- **THEN** 分别记录标准锁未解析、工具专用锁未解析或锁选择歧义；不得把 `uv.lock`/`poetry.lock` 直接交给当前只支持项目 pylock 的 pip-audit `--locked` 入口。标准锁存在也不证明环境选择、完整依赖图、原生审计或数据库时效；多锁不得擅自任选一份

#### Scenario: pip-audit reports a skipped dependency or inconsistent result
- **WHEN** 受控 pip-audit 项目锁审计的 JSON 报告含跳过的包、重复字段、非预期修复结果，或漏洞数量与原生退出状态矛盾
- **THEN** 保留本次观察为未完成并给出明确原因；只有结构完整的原生组件、解析版本和 advisory 可成为后续归属候选。即使原生报告为空且退出零，也须另行核验项目锁的环境/依赖组、完整包图、工具及漏洞数据库身份和时效，不能仅凭 JSON 解析签发无漏洞结论

#### Scenario: Python native CVE probe uses a private snapshot
- **WHEN** 用户显式选择 pip-audit 可执行文件和版本，为有且仅有一份标准 pylock 的 Python 项目运行局部 `cve python`
- **THEN** Rust 先观察项目清单、锁和工具字节，在私有目录复放输入并由受控进程调用原生工具；前后任一原文件、私有副本或工具变化都使结果未完成。结构有效且整组组件名/解析版本与同轮标准锁逐项匹配的 advisory 才可反馈为局部候选；不匹配者不得成为项目 finding。零项与异常均保留 `not_evaluated` 和未核验覆盖；该局部探针不代替完整项目环境选择、漏洞库时效、稳定任务或交付门禁验收

#### Scenario: Conditional pylock packages are not flattened into one project environment
- **WHEN** 标准 pylock 含 `environments`、`requires-python`、非空 `extras`/`dependency-groups`/`default-groups`，或包级 `marker`/`requires-python`，而当前探针没有相应的目标环境与选择上下文
- **THEN** 在已配置原生工具且锁的基本结构可解析时仍调用原生 CVE 检查，把版本、退出状态和待归属 advisory 数量反馈给智能体；同时返回明确的锁选择未解析状态与环境核对动作。不得把所有 `[[packages]]` 合并为当前项目实际依赖，不得把待归属 advisory 发布为项目 finding 或零漏洞结论。显式空 extras/组可继续作为单用途锁的局部输入，但仍不证明完整覆盖

#### Scenario: check all schedules Python CVE by build root
- **WHEN** `check all` 发现一个或多个具有可识别 `pyproject.toml` 的 Python 构建根，调用方可选择显式 pip-audit 路径和版本
- **THEN** 每个构建根作为独立任务复用同一个私有快照原生探针，共享请求截止时间与取消；JSON/human 反馈必须逐根显示原生 advisory 或缺锁、缺工具、输入不一致等具体阻塞。无清单的源码根只保留配置缺口，不伪造原生扫描。即使每个局部报告有效，项目环境、依赖组、漏洞库身份及时效和可信策略未核验时，类别最多为 `observed_unverified`，全项目交付仍为 `incomplete`

#### Scenario: Python CVE observation enters the repair workbench
- **WHEN** 已初始化工作区对同一 Python 构建根重复运行 `cve python` 或 `check all`，随后对该任务执行原生复检
- **THEN** 输入清单、标准锁集合、构建根及运行报告必须在导入时重新核对；相同构建根和 CVE 完整性义务只保留一张稳定任务，后续扫描与失败尝试形成历史事件。缺工具/锁形成环境准备指引，已观察 advisory 保留为待核验局部证据；复检必须再次调用原工具并写入观察事件，不能因零 advisory、自写白名单、任务勾选或报告重放自动关闭。过期或损坏的报告必须显式阻止导入，且不吞掉其他任务的证据

#### Scenario: A similarly named security plugin dependency is not FindSecBugs
- **WHEN** SpotBugs 插件依赖中的 `artifactId` 为 `findsecbugs-plugin`，但 `groupId` 并非 FindSecBugs 制品坐标
- **THEN** 静态探测不得标记 FindSecBugs 已配置，也不得把该名称当作原生安全规则已运行

### Requirement: Java checks SHALL prove each required native obligation

Java MUST 识别 P3C、通用 lint、Javadoc/注释、安全、依赖治理、依赖漏洞和构建的项目配置状态。官方 P3C MUST 使用经验证的 P3C PMD 实现和兼容工具链；Checkstyle 配置名 MUST NOT 被标为 P3C。已配置的 Maven/Gradle 检查通过其原生命令执行，结果按该工具契约解释。`mvn verify` 成功只作为本次构建结果反馈，不能被描述成未配置的检查器也通过。

#### Scenario: Verify succeeds without quality plugins
- **WHEN** `mvn verify` 成功但未运行所需 P3C/Javadoc 检查
- **THEN** 在智能体对话中显示 P3C/Javadoc `missing` 与配置建议；`check java` 只总结实际运行的检查，批准策略要求的缺项才使门禁未完成

#### Scenario: JDK and PMD are incompatible
- **WHEN** P3C 规则运行因 JDK/PMD 组合失败
- **THEN** 报告具体工具链未完成，不记为代码违规，不自动换规则或跳过

#### Scenario: Maven PMD returns zero with default or error-skipping configuration
- **WHEN** Maven PMD 运行成功，但生效规则集并非项目声明的 P3C 规则，或处理错误被忽略
- **THEN** 报告配置错误或工具结果未完成；Rust 不得把 Maven 退出码或空 XML 转述为 P3C 检查通过

#### Scenario: Isolated P3C probe must honor the project ruleset subset
- **WHEN** 项目仅声明 `ali-naming.xml`，隔离探针内置模板还包含 `ali-comment.xml`
- **THEN** 项目检查只执行已确认的命名规则集；作者注释规则的诊断不得进入该项目 finding 或修复任务。POM 在发现、执行或同步期间变化，或生效配置无法确定时，保留配置阻塞而非借误报白名单放行

#### Scenario: Native XML claims an unselected or impossible P3C rule
- **WHEN** PMD XML 结构合法且退出码为 0，但诊断中的规则集未被本轮项目配置选择，或规则 ID 不属于该规则集
- **THEN** 不生成项目 finding 或源码修复任务；反馈报告规则归属未核验并保持 incomplete。规则目录须与固定版本 P3C 制品核对，不能只凭报告中的自由文本 ruleset 名称接受诊断

### Requirement: Comment and security categories SHALL retain their own evidence

注释检查 MUST 根据语言与规则验证其确定性要求，不得以格式化代替。源代码安全、配置安全、入库策略和 CVE MUST 分开归类；仅命中禁止文件模式 MUST 报策略违规，不得无内容证据声称检测到真实私钥。未实现的语义能力 MUST 明示。

#### Scenario: Public API lacks required documentation
- **WHEN** 有效规则要求文档且源码缺少对应注释
- **THEN** 原生或经验证的确定性规则输出注释违规，普通 formatter 成功不消除该义务

#### Scenario: Configured Ruff reports a Python module docstring rule
- **WHEN** Python 项目配置 Ruff 的 D100，原生 Ruff 对公共模块报告缺少 docstring
- **THEN** 注释类别保留该原生规则、定位与修复后原工具复检建议；局部诊断可标已观察但不得推断全部注释规则、工具/策略批准或项目交付通过。补充 docstring 后原生零诊断只撤销该局部问题观察，不自动签发完整注释检查通过

#### Scenario: Configured Ruff reports another pydocstyle rule
- **WHEN** Python 项目显式启用 Ruff D### pydocstyle 规则，例如 D101，且同轮原生设置确认该规则生效并返回诊断
- **THEN** 将该精确原生诊断归入注释候选，保留规则 ID、源码位置与原工具复检建议；仅有配置文本、非 D### 代码或没有诊断均不证明注释义务已执行或通过

#### Scenario: Ruff docstring report conflicts with effective settings
- **WHEN** 原生报告声称检出 D### pydocstyle 规则，而同轮 Ruff 生效设置并未启用该精确规则
- **THEN** 保留原生诊断供核查，但本轮源码检查标为未完成，不生成可执行的注释修复结论或项目交付通过；用于交叉核对的完整原生规则集合不自动成为公开批准规则包

#### Scenario: Public certificate matches a forbidden path rule
- **WHEN** 文件命中现行禁止入库模式但没有私钥内容证据
- **THEN** 按策略违规报告，不能将文件名命中写成已确认密钥泄露

### Requirement: CVE checks SHALL bind actual dependency and database identity

Rust CVE 检查 MUST 绑定实际解析的组件版本、依赖来源、advisory 标识和数据库身份/时效。无可靠组件匹配、数据库过期、离线无合格库、缺失必要严重度时 MUST 保留发现与不确定性，不产生无依据的安全通过或确定高危。原生工具缺失 MUST NOT 静默换覆盖不同的通用工具。共享扫描 MUST 可追溯到全部被满足的义务。

#### Scenario: Offline database is too old
- **WHEN** 离线数据库超过批准的 freshness
- **THEN** CVE 未完成，不以零匹配判安全

#### Scenario: Native cargo-audit JSON omits database provenance
- **WHEN** Rust 使用显式原生 cargo-audit 可执行文件和离线数据库扫描 Cargo.lock，报告有漏洞或零漏洞，但数据库提交/更新时间缺失或尚未由可信边界核验
- **THEN** 保留原生 advisory 与锁定组件的名称、解析版本和来源观察；公开反馈不得泄露私有来源，数据库身份/时效仍为未完成，零漏洞不得称安全通过。原生忽略列表、损坏报告、计数或退出码矛盾也不得转成误报白名单或质量通过

#### Scenario: Project check includes the Rust CVE obligation
- **WHEN** `check all` 发现 Rust 项目，不论是否提供显式 cargo-audit 工具和离线数据库
- **THEN** 在共享任务图中登记独立 `rust.cve` 节点，反馈原生漏洞或缺工具/数据库的具体阻塞；JSON/human/SARIF 均不得吞掉已观察 advisory，未核验数据库、工具和策略仍使完整交付未完成。取消或内部故障时保留已取得的其它原生结果，旧报告版本保持可辨识

#### Scenario: Report has no comparable severity
- **WHEN** 已知漏洞没有策略阈值需要的严重度
- **THEN** 保留 finding；无法按策略判定时未完成，不预过滤 UNKNOWN

#### Scenario: OWASP report and Maven graph share only a local identity candidate
- **WHEN** 同一构建根配置两个原生插件，本轮 OWASP 报告与 Maven 图的 POM、工具、JDK、离线仓库摘要一致，且某条 advisory 的精确 PURL、图节点和制品 SHA-256 一致
- **THEN** 可显示该条候选归属及原生证据引用；数据库时效、可信工具与项目覆盖未经核验时仍不得签发 CVE 通过、确定严重度门禁或误报白名单放行

#### Scenario: Advisory cannot be safely attributed to the current dependency graph
- **WHEN** 两份原生报告的构建根、输入摘要、组件坐标或制品字节摘要不一致，或 PURL 因私服限定符不能无损解释
- **THEN** 逐条显示失配或无法归属，并保留原生漏洞观察；不得按相似文件名、脱敏摘要或历史图推断组件身份

### Requirement: Migration SHALL account for every legacy language entry

迁移 MUST 逐项登记基线注册表全部 57 项，包括 54 stable 和 3 planned；前者完成六类别配置识别、原生适配器调用与结果反馈验收前 MUST NOT 宣称全量迁移完成。planned MUST 保持显式状态，不能为凑数量创建空实现。注册表变化 MUST 重新做差异核对。

#### Scenario: Four major languages are implemented
- **WHEN** 仅 Java/Rust/Python/TypeScript 已可用
- **THEN** 只能声明这部分能力完成，剩余迁移任务仍未完成

#### Scenario: A project contains a planned language
- **WHEN** 项目含 COBOL、ArkTS 或 Metal 源码并运行 `check all`
- **THEN** 六类别候选均明确保留 `planned` 的旧登记状态与 `gap` 的当前能力含义，返回未完成和具体适配步骤；不能把无原生适配器解释为 `not_applicable`、空结果或质量通过

### Requirement: Adapters SHALL separate static observation from executable resolution

adapter MUST 基于注入观察声明适用性、计划与报告解析，不自行spawn、联网或写文件。动态构建模型解析 MUST 作为有身份、预算、网络声明和证据的执行任务，由core经runtime port调用；静态detect/init/plan无法解析的条件保留unknown，不偷偷执行wrapper。模块/源集/方言与跨语言依赖映射 MUST 保留各自范围，不能用主语言覆盖其它构建根。

Codeguard 自有的新执行、解析、策略判定、门禁与验收工具 MUST 由 Rust 实现，不在新 CLI 路径中调用 Python 脚本来承担这些职责。P3C、Maven 等原生检查器仍按各自官方命令执行，由 Rust runtime 受控启动，Rust adapter 解释其原生证据；本要求不意味着用 Rust 重写它们的规则实现。旧 Python 入口只属于具名 legacy 兼容范围，不能参与新入口的通过判定。

#### Scenario: A build model requires project extensions to resolve
- **WHEN** 静态读取不足以确定effective model或条件依赖
- **THEN** plan保留待解析任务，实际解析只在明确执行阶段进行并记录证据

#### Scenario: A shared scanner serves several language obligations
- **WHEN** 多模块多语言共享一个依赖扫描器
- **THEN** 原生执行由统一runtime协调，结果映射到全部对应义务，不绕过进程控制或漏掉另一构建根

### Requirement: Checkstyle XML interpretation SHALL preserve native identity and distinguish processing failures

Checkstyle XML 解析 MUST 保留完整 source（包括自定义模块 ID）、原生严重度、文件及可选列号；文件级零行号 MUST NOT 被改成任意源码行。异常和缺文件归属的事件 MUST 保持未完成，不制造源码规则违规。解析 MUST 有界并拒绝 DTD、损坏/未知结构、版本不符、歧义重复文件和非法字段。结构有效与空诊断 MUST NOT 单独证明本轮执行、检查范围、批准规则或交付通过。

原生结果判定 MUST 使用独立冻结的完整文件列表和经版本/平台验收的退出契约；缺失、重复、遗漏或额外文件不得形成完整结果。warning/info 在退出零时 MUST 保留；操作系统退出截断 MUST NOT 抹去报告中的错误。异常、信号、取消或退出与诊断矛盾 MUST 保持未完成，不冒充源码违规或普通通过。

原配置的重复属性与无法区分的原生规则来源 MUST 保留上下文歧义，不能默认选择某个属性值、合并检查实例或扩大白名单。具有可区分模块 ID 的相同检查类 MUST 保留各自身份，不因检查类相同而自动忽略。

#### Scenario: Distinct modules share a source ID in an older native version
- **WHEN** 锁定原工具版本仅输出模块 ID，两个配置实例共用该 ID
- **THEN** 无法独立归属的局部执行保持待解析，不产生可用于扩大白名单的规则绑定；改为不同 ID 后仍按原配置执行并分别展示诊断

#### Scenario: Warning severity returns a successful native exit
- **WHEN** 原工具退出零但本轮 XML 含有效 warning/info
- **THEN** 报告保留诊断及原严重度，不将退出零投影为零诊断

#### Scenario: Native scope differs from the frozen source list
- **WHEN** XML 文件列表遗漏或增加冻结范围外的文件
- **THEN** 返回范围未完成，原始诊断仅保留为局部证据，不自动扩大活动 finding 或白名单范围

#### Scenario: Two configured modules use the same checker class
- **WHEN** 原生 source 使用相同类名但不同自定义模块 ID
- **THEN** 解析保留两个完整身份，不能合并后扩大白名单或规则归属

#### Scenario: An exception appears beside a valid diagnostic
- **WHEN** 文件 XML 内含 exception 及可解析的 error
- **THEN** 保留可解析诊断为局部证据，同时报告处理未完成；异常不成为源码违规且报告不能当作完整结果

#### Scenario: A structurally valid report contains no violations
- **WHEN** 原生报告仅列出零诊断文件或没有文件
- **THEN** 解析只返回结构观察，执行器仍须核对本轮产物、原配置、退出码与完整范围

### Requirement: Checkstyle repair feedback SHALL bind native sources to original configuration
局部 Checkstyle 反馈 SHALL 从同轮原配置精确关联原生 source 与内置检查类，保留原生 ID，并提供规则依据、修复方向和原输入复检参数。该映射不能授予工具批准、规则覆盖、白名单或项目交付权威。

#### Scenario: Custom ID has an unambiguous original module
- **WHEN** 固定版本原工具报告自定义 ID，原配置中该 ID 唯一对应已支持模块
- **THEN** 展示对应检查类、中文规则摘要、官方依据与复检步骤，不改写原生 ID，也不因有修复指引就关闭任务

#### Scenario: Native source cannot be bound
- **WHEN** 原生 source 未在原配置映射中，或配置存在重复 ID 或未知版本语义
- **THEN** 返回未完成，不按消息、短类名或顺序推测规则，不发布用于修改源码的 finding

### Requirement: Field Javadoc checking SHALL use the native configured Checkstyle rule
Rust 的 Checkstyle 注释适配 SHALL 支持原配置的 JavadocVariable，保留原生自定义规则 ID、完整检查类、严重度、范围及精确目标，不用自写字段注释规则替代原工具。

#### Scenario: Native field rule distinguishes configured scope and exceptions
- **WHEN** 固定 Checkstyle 10.21.4 对显式原配置下的字段执行 JavadocVariable
- **THEN** 只把原生报告中的问题生成稳定任务；原配置忽略名、访问范围、serialVersionUID 和局部变量等边界以原工具输出为准，不额外制造缺注释问题

#### Scenario: Field repair is verified with the same rule
- **WHEN** 原字段任务补充实际语义文档后接受 task verify
- **THEN** 使用显式同一原工具/配置，原问题未再检出只作为局部候选观察；保留任务开放，不以原生零诊断证明完整项目覆盖或批准

#### Scenario: Field and enum tokens select different native targets
- **WHEN** 原 JavadocVariable 配置选择 VARIABLE_DEF 或 ENUM_CONSTANT_DEF，或限定访问范围/excludeScope
- **THEN** Rust 保留静态合法原参数，不扩展 token 集合；保留原生默认及必需 token 语义：10.21.4 的 VARIABLE_DEF 必需，仅配置 ENUM_CONSTANT_DEF 时仍包含字段检查，不由 Rust 过滤；访问范围外的声明不产生额外 finding。未知 token 或其它模块借用该参数不能按本适配上下文执行

### Requirement: Official Checkstyle module names SHALL preserve native checker identity
已支持的静态 Checkstyle 模块 SHALL 接受官方短名和完整类名原写法，原 XML 字节照常交给工具，Rust 仅在既定版本映射中归一检查器身份，不以任意后缀、消息或类名相似度猜测归属。

#### Scenario: Official short and full names describe the same rule
- **WHEN** Checker、TreeWalker 及已支持 Javadoc 模块改用官方完整类名，原目标、规则 ID 和工具保持相同
- **THEN** 保留同一稳定 finding/task 和原生规则依据，不创建伪造配置阻塞；配置变化仍需重新原工具检查

#### Scenario: Unknown namespace or duplicated alias claims a rule
- **WHEN** 其它包的同名检查类冒用已支持类名，或短名与完整类名产生同一未区分的原生 source
- **THEN** 返回上下文未完成而非猜测身份；不能按遍历顺序把一条诊断分配给任一模块

### Requirement: Missing method Javadoc configuration SHALL remain native and context-bound
MissingJavadocMethod 的静态原配置 SHALL 支持本版范围、allowedAnnotations、allowMissingPropertyJavadoc、minLineCount 与 ignoreMethodNamesRegex 参数，原工具决定其筛选与文档语义；适配器不得移除用户原参数改用默认扫描。

#### Scenario: Original method exclusions select only real native findings
- **WHEN** 原配置按访问范围、注解、属性方法、名称或长度限制方法检查
- **THEN** 只将原工具实际诊断接入稳定修复任务；这些参数不是 CodeGuard 误报白名单批准，也不能证明受保护必需规则覆盖

#### Scenario: Method properties are borrowed by another module
- **WHEN** 非该检查器声明相同参数，或静态整数/布尔/注解名称无法解析
- **THEN** 返回配置上下文未完成而非猜测含义，不把配置故障伪装成源码缺注释

#### Scenario: Method configuration explicitly selects constructors or annotation members
- **WHEN** MissingJavadocMethod 原配置选择 METHOD_DEF、CTOR_DEF、ANNOTATION_FIELD_DEF 或 COMPACT_CTOR_DEF
- **THEN** 在该模块上下文保留原 token 集合与原生必需 token 语义；原生诊断进入稳定任务，非选中类别不被 Rust 额外补报，record 紧凑构造器可用同配置原工具复检。跨模块借用或不支持 token 返回上下文未完成

#### Scenario: Same checker class changes its target exclusions during repair
- **WHEN** 同一稳定任务复检的检查类未变，但原始配置字节已变化，原问题不再出现在诊断中
- **THEN** Codeguard SHALL 返回 rule_coverage_requires_review，不能将调整 scope、token、名称排除或其它原生参数造成的零诊断标为修复候选；缺原配置身份也须复核。后续重复复检或扫描不得用新配置覆写首次发现的配置身份。恢复原配置并修正文档后才可给出局部待策略核验候选，仍不得自动关闭事实

### Requirement: Method tag configuration SHALL preserve native option semantics

固定 Checkstyle 10.21.4 的 JavadocMethod 静态适配 MUST 保留 accessModifiers、allowMissingParamTags、allowMissingReturnTag、validateThrows、allowedAnnotations 与原生可接受 tokens，不将它们借用给缺方法文档检查器。源码是否缺参数、返回或异常标签 MUST 由原生诊断决定，参数不产生白名单批准或必需规则覆盖证明。

#### Scenario: Original method tag policy deliberately permits missing tags
- **WHEN** 原配置限定访问修饰符，并选择允许缺参数/返回标签、允许注解或启用 throws 标签校验
- **THEN** 原 XML 不改写，实际诊断进入稳定任务；不对原工具已允许的缺标签额外补报。使用原始配置修正文档后仅给局部复检候选

#### Scenario: A method tag property appears in an unrelated module
- **WHEN** 未支持检查器借用标签检查专属属性，或布尔/修饰符/token 不合法
- **THEN** 保持配置上下文未完成，不套默认值或标源码违规

### Requirement: Type documentation options SHALL retain their original checker context

固定 10.21.4 的 MissingJavadocType/JavadocType 原 scope/excludeScope 与五类类型 tokens MUST 保留原生语义。skipAnnotations MUST 只适配 MissingJavadocType；allowedAnnotations、allowMissingParamTags、allowUnknownTags、authorFormat/versionFormat MUST 只在 JavadocType 上适配。正则含义与是否缺文档/标签 MUST 由原工具判断，不由 Rust 生成替代规则或白名单批准。

#### Scenario: Type annotations or record parameter policy permit documentation exceptions
- **WHEN** 原类型检查配置限定访问范围、注解例外、类型 token 或允许缺 record 参数标签
- **THEN** 执行原 XML，仅将实际原生诊断同步到稳定任务；不额外补报被原配置允许的情况。恢复首次配置并修正文档后只形成局部复检候选

#### Scenario: A type property is borrowed by a method checker
- **WHEN** 类型专属属性跨模块声明，或非法布尔/范围/token/动态值出现
- **THEN** 保持配置上下文未完成，不猜测默认规则或将配置错误当源码违规

#### Scenario: Author and version tags violate original type format requirements
- **WHEN** JavadocType 原 authorFormat/versionFormat 检出缺标签或值格式不符
- **THEN** 保留原生诊断和稳定任务，修复指引须包含作者/版本格式并要求使用项目实际身份/版本依据，不编造事实。原格式配置不变时真实修正文档仅给局部复检候选

#### Scenario: A type format regex is rejected by the native checker
- **WHEN** 静态配置可读取，但原生工具拒绝无效格式正则
- **THEN** 反馈 incomplete 并生成稳定配置准备任务，重复失败不制造多张任务，不生成源码标签违规或假干净结论

#### Scenario: Native configuration regex failure has a recognized fixed-version signature
- **WHEN** 10.21.4 原进程正常退出 254，预算内 stderr 同时含官方配置属性非法值异常和 PatternSyntaxException，且没有相互一致的原生诊断报告
- **THEN** Codeguard SHALL 只返回脱敏 checkstyle_configuration_regex_invalid 和原配置修复/原工具复扫指引，不回显属性值或原始堆栈；未知退出/异常、取消/超时/超限及证据失败不得套用该细分，不能生成源码违规或覆盖通过

### Requirement: ESLint JSON reports SHALL separate rule findings from incomplete execution and suppression

ESLint 10 原生 JSON 适配 MUST 核对冻结的具体版本、完整显式文件集合、诊断/计数与 exit/max-warnings 契约。普通退出零的 warning MUST 保留；退出 1 MUST 根据 error 或已冻结警告阈值解释，不直接算工具故障；退出 2、未知/非正常退出、坏报告或身份/范围矛盾 MUST 未完成。fatal 或无原生 ruleId 的诊断 MUST 调查语法/parser/配置，不能伪造规则 finding；同报告合法规则诊断须保留。

#### Scenario: ESLint warning does not fail the native process
- **WHEN** 完整 JSON 报告只含 warning 且退出 0，或冻结 max-warnings 阈值导致退出 1
- **THEN** 保留原生规则、严重度和位置；解析一致性不证明项目有效配置、工具批准或交付通过

#### Scenario: A parser error or ignored-file notice lacks a native rule identity
- **WHEN** JSON 中出现 fatal/parser 诊断或无 ruleId 的文件/配置提示
- **THEN** 标为待调查的未完成，不把它当普通规则违规；有效规则发现仍可供定位

#### Scenario: ESLint reports only suppressed diagnostics
- **WHEN** suppressedMessages 非空而活动 messages 为空
- **THEN** 保留抑制数量并要求覆盖/批准核查，不标干净范围，不自动制造白名单或源码 finding

#### Scenario: A native array omits a planned file or contradicts its counts
- **WHEN** 文件集合缺失/重复/额外，版本不匹配，路径含跳转，诊断计数矛盾或 JSON 损坏
- **THEN** 返回未完成，不能签发解析一致性或复检关闭候选

### Requirement: ESLint native command planning SHALL use explicit literal inputs

Rust ESLint 命令计划 MUST 明确 Node 入口、ESLint JS 入口、原 flat config、完整显式源码列表与本轮独立 JSON 槽位，以字面 argv 构造，不借 Shell/npx 隐式安装或拼接命令。MUST 禁用配置自动查找、保留原配置/ignore 语义与显式 max-warnings；不得隐式 fix/cache/quiet 或替换规则。规划 MUST 有界，拒绝相对/跳转/控制字符、空/重复范围与输入输出冲突；物理路径别名、脚本/插件闭包、报告新鲜性和生效项目上下文仍须执行层核验。

#### Scenario: A selected project has file paths with spaces or shell metacharacters
- **WHEN** 显式原配置和源码路径合法但含空格或 Shell 元字符
- **THEN** 逐项保留字面路径，Node 与 ESLint 参数分界明确，不能执行字符串中的 Shell 片段或隐式修复源码

#### Scenario: Caller freezes a warning threshold
- **WHEN** 本轮计划明确 max-warnings
- **THEN** 使用原生整数参数，反馈解析须核对同一冻结阈值；不通过 quiet 删除 warning 来制造通过

#### Scenario: Report slot aliases a planned input or argument budget is exceeded
- **WHEN** 词法输入输出冲突、范围重复/为空、路径不安全或规划预算超限
- **THEN** 启动前拒绝计划，不写报告，不删除输入，不冒充已检查的干净范围

### Requirement: ESLint controlled execution SHALL bind version and current inputs

Rust ESLint 执行层 MUST 在统一 runtime 中运行显式 Node/ESLint 入口，版本探测和扫描共享取消、绝对截止时间及有界日志。启动前 MUST 校验 Node、入口、原配置、所有显式源码的精确物理路径与摘要集合，使用私有的新鲜报告槽位；版本必须与冻结预期一致。版本探测后和扫描后 MUST 复核输入，输入改变或报告/进程异常为未完成，不构造源码违规或已修复结论。局部一致结果不得自证项目配置、JS 导入/插件闭包、可信工具批准或完整覆盖。

#### Scenario: Prior report exists or an input digest is missing
- **WHEN** 本轮报告槽位已有文件，或任何显式输入缺少冻结摘要
- **THEN** 启动 Node 前拒绝执行；旧报告不能作为本轮证据

#### Scenario: Version or configuration changes during controlled execution
- **WHEN** 入口报告非预期版本，或版本探测/扫描后配置字节已变化
- **THEN** 返回未完成；配置变化时可保留已解析诊断作调查线索，但不能签发局部一致、任务关闭或门禁通过

#### Scenario: A controlled report is coherent but project context remains unknown
- **WHEN** 实际进程返回与本轮文件、计数和退出码一致的 JSON，但项目配置归属或插件导入闭包未核验
- **THEN** 只返回局部观察，不能升级为完整项目覆盖或批准的白名单处置

#### Scenario: An interrupted ESLint scan has already written a report or writes none
- **WHEN** 扫描启动后取消或共同截止时间到达，无论本轮报告已写出还是尚未生成
- **THEN** 保留 request_cancelled 或 request_deadline_exceeded 原因，不降级成一般报告损坏，不把已写出的零诊断报告当作完成；后续指引不得要求智能体修改无关源码

### Requirement: ESLint configuration discovery SHALL distinguish candidates from effective configuration

项目发现 MUST 静态记录六种原生 flat config 文件、旧 eslintrc 文件及 package.json eslintConfig 线索。MUST 绑定读到的配置/清单字节，保持嵌套配置所在根；发现不得执行 JS、隐式迁移旧配置或套用默认规则。静态存在不能证明逐文件规则、选中配置、TS loader 或插件闭包生效；未发现候选也不能断言外部配置或显式调用参数不存在。MUST 返回具体未确认原因及原生核查动作，不制造源码违规或白名单批准。

#### Scenario: Several flat configuration candidates exist in one root
- **WHEN** 同一目录存在多种 flat config，当前项目调用上下文尚未解析
- **THEN** 分别记录候选与配置选择未确认，不任意拼接规则或把候选认定为已启用

#### Scenario: A nested Node package contains a TypeScript configuration
- **WHEN** 根目录有 JS flat config，子包有 TS/MTS/CTS flat config
- **THEN** 保留不同配置所在根，要求原生逐文件归属与 TS loader 核查；不把根规则强加子包

#### Scenario: No flat config is observed or only legacy declaration exists
- **WHEN** package.json 所在根没有观察到 flat config，或包含旧 eslintConfig
- **THEN** 说明未观察到配置或需原工具版本上下文，提供准备动作；不创建默认配置、不报告源码违规

#### Scenario: Node manifest changes or becomes unreadable during discovery
- **WHEN** ESLint 线索复核读取的 package.json 与本轮清单摘要不一致或不可读取，即使同目录已有 flat config
- **THEN** 标记发现不完整并保留清单阻塞路径和具体准备原因，不能隐藏为普通未知配置或据此把初始化画像标新鲜

#### Scenario: Standalone JavaScript or TypeScript source has no package manifest
- **WHEN** 项目中观察到独立 JS/TS 源码但无 package.json 或根配置候选
- **THEN** 返回配置未观察到的待准备线索及源码引用，不安装包、不创建清单或默认规则，也不省略检查准备反馈

### Requirement: npm native audit observation SHALL retain protocol and coverage boundaries

Rust npm审计适配 MUST 核对具体原工具版本、auditReportVersion、冻结审计阈值的退出契约、原生组件和汇总计数，拒绝重复JSON键及路径越界。原生advisory source编号 MUST NOT 冒充CVE编号，受影响范围 MUST NOT 冒充锁文件解析版本，间接via关系 MUST NOT 复制成直接advisory。直接advisory高危而组件被降级的报告矛盾 MUST 为未完成。静态脚本声明、锁文件存在及离线零诊断均不能证明当前依赖图、漏洞库时效或完整策略覆盖。

#### Scenario: Native audit reports a vulnerability and exits one
- **WHEN** 原生报告按本轮阈值返回退出1且组件/计数一致
- **THEN** 保留原生易受影响组件、严重度、节点、范围及关系观察，不把退出1当作工具故障，不自动签发批准漏洞身份或白名单

#### Scenario: Native audit lacks a lock or emits a contradictory report
- **WHEN** npm返回error对象、报告损坏、版本不同、计数不一致或定位越界
- **THEN** 返回未完成和具体原因，不构造源码违规或干净审计

#### Scenario: Offline audit reports no dependencies
- **WHEN** 显式原工具在私有缓存及用户/全局配置下离线审计空锁文件并返回零发现
- **THEN** 只记录该原生报告一致；不安装依赖、执行fix或项目脚本，不将离线/零依赖观察推广为完整CVE门禁

#### Scenario: A package script merely mentions npm audit
- **WHEN** 脚本含复合Shell命令或自定义参数，而非已识别的明确原生命令声明
- **THEN** 静态配置标记需原上下文复核，不执行脚本；没有观察到声明也不能证明外部CI未配置审计

#### Scenario: npm input-bound runtime observations require unchanged original inputs
- **WHEN** 调用者冻结Node/npm、清单、锁、用户/全局配置及存在的项目npmrc，原生审计在统一runtime中执行
- **THEN** 精确核对输入摘要集合及具体版本，版本和审计沿用相同显式上下文，共用取消与截止；输入变更或新增此前不存在的项目npmrc时返回未完成且不提供可关闭任务的parsed结论；stdout报告有界解析并核对锁节点，局部一致不证明工具模块闭包、数据库覆盖或交付权威

#### Scenario: Per-root npm audit declarations enter discovery and plan previews
- **WHEN** 项目包含多个package.json，脚本分别为明确audit、未观察到audit、自定义复合调用或畸形声明
- **THEN** 按每个构建根保留configured/missing/unknown/invalid及下一步，不执行脚本、不从未观察到脚本推断外部CI缺失；重读清单变化或不可读时标记观察未完成，不能沿用旧声明；TypeScript/JavaScript语言别名及all的计划预览保留node检查器，但不宣称执行或有效质量门禁

#### Scenario: Explicit npm audit registry supports native advisory validation
- **WHEN** 调用者明确选择无凭据HTTPS审计源，或仅用于验收的loopback HTTP源
- **THEN** 原生命令固定registry与audit-registry、不经shell、不安装或执行项目脚本；保留原生advisory source及具体锁节点，不将受控服务夹具或成功请求当作可信数据库时效与CVE通过；认证、系统级网络隔离及完整数据库来源仍需独立核验

#### Scenario: Offline nonempty npm audit returns zero observations
- **WHEN** 私有空缓存、非空锁文件和离线原生命令返回退出0及零漏洞
- **THEN** 可以保留原生依赖数量及锁文件节点观察，但漏洞库覆盖仍为not_evaluated，不推断当前数据库新鲜、网络查询成功、组件安全或CVE检查通过；报告解析一致性不得授予门禁权威

#### Scenario: Native npm audit locations require resolved lock identities
- **WHEN** 原生审计返回组件节点位置，需要关联 npm v3 锁文件版本
- **THEN** 按具体安装位置核对包名与明确解析版本，不将受影响范围当版本、不合并不同位置的同名包；节点数量、名称或位置不一致以及重复字段、链接、别名或不支持结构均为未完成，不能批准白名单或交付通过；节点关联不声称依赖边、直接性或漏洞范围已核验

### Requirement: ESLint task recheck SHALL observe the original effective rule

原 ESLint finding 在同配置复检中未出现时，Rust MUST 使用原工具的逐文件有效配置查询核对原规则；MUST 保留显式原入口、配置、cwd、统一截止时间及输入前后复核。关闭、缺失或无法确认规则不得解释为源码修复或白名单批准。输出 MUST 只展示脱敏规则级别、原因及摘要，不执行报告中的指令、不把完整配置投影到对话。局部规则观察不能自证完整导入闭包或批准覆盖。

#### Scenario: An imported configuration disables the original rule
- **WHEN** 主配置及源码字节不变，但导入配置使原规则关闭或不再出现，原生扫描零诊断
- **THEN** 返回 rule_coverage_requires_review，任务保持 open，next 指向配置与批准依据核查，不建议修改无关源码

#### Scenario: Effective settings query fails or changes inputs
- **WHEN** 原生查询损坏、被忽略目标返回 undefined、超时或显式输入前后不一致
- **THEN** 保留未完成及具体原因，不据零诊断产生修复候选或有效白名单

#### Scenario: User cancels while effective settings are being queried
- **WHEN** 扫描已返回诊断，但用户在同轮有效配置查询期间取消请求
- **THEN** 反馈保留 request_cancelled 与未完成，回收查询进程组并释放自有租约，不将中断保存为正常的 still_present 或问题消失复检事件；原始 finding 与任务继续保留

#### Scenario: A project-local plugin reports an original rule
- **WHEN** 项目原配置加载本地插件并报告带命名空间的规则，源码修复后同配置复检不再报告该规则
- **THEN** 原生发现及任务保留完整插件规则 ID，查询同一规则是否仍启用，保留原插件与配置；局部一致仅生成待批准覆盖核验候选，不能据此声称完整插件闭包或正式关闭

### Requirement: Public ESLint local feedback SHALL retain uncertainty and explicit context

`lint typescript` 的原生接入 MUST 明确 Node、ESLint JS 入口、具体版本、项目原 flat config 及原工作目录，不能从配置所在目录猜测原调用上下文。上下文缺失 MUST 返回准备动作而不安装工具、套默认规则或制造源码违规。当前显式单文件范围 MUST 明示局部覆盖，目录未调度时不能视为已检查；JSON/human反馈 MUST 保留原生规则、位置、严重度及未完成原因，避免泄露原生敏感消息。局部零诊断也 MUST NOT 签发项目门禁或关闭任务；未接持久任务时须明示未接入。

#### Scenario: Explicit directory uses one selected native configuration
- **WHEN** 调用者选择目录、明确原生入口/配置/cwd，目录内有多个 JS/TS 文件
- **THEN** 有界枚举并逐文件调用原工具，共享截止时间，分别保留仓库相对定位、诊断、同步状态和准备任务；核对枚举与显式输入前后变化，列出跳过项和未执行文件，不能暗示已自动选择 monorepo 子配置或完整覆盖

#### Scenario: Caller selects separate monorepo project contexts
- **WHEN** 调用者通过有版本的显式映射，为子项目根分别指定原配置及cwd
- **THEN** 按路径组件选择最深匹配根，未命中范围沿用原参数；拒绝重复根、越界/链接、未知字段及不可读上下文，反馈逐文件的选择来源与范围。映射和选中输入在执行前后核对，变化则保留已取得结果并停止未执行范围；映射不能自行批准规则、覆盖或白名单

#### Scenario: A directory file fails while others produce findings
- **WHEN** 一个文件报告/执行未完成或工作台保存失败，其它文件已有原生发现
- **THEN** 保留各文件发现和具体故障，目录状态为 incomplete；取消/超时保留原因和未执行清单，不能把未执行文件称干净

#### Scenario: The original ESLint configuration is itself source code
- **WHEN** 本轮源码目标恰为同一个原 flat config 文件
- **THEN** 可共享同一个只读字节身份，扫描与同步核对同一摘要；重复源码、其它工具输入别名及报告覆盖输入仍拒绝，不为绕过冲突排除配置源码

#### Scenario: Public lint has no explicit native execution context
- **WHEN** 用户请求 lint typescript 但缺显式入口、版本、原配置或工作目录
- **THEN** 返回配置/环境准备反馈，无源码finding，门禁未判定，不自动创建或迁移配置

#### Scenario: Public native finding disappears after a same-configuration repair
- **WHEN** 原生工具先检出规则，再用相同原配置检查已修复文件而零诊断
- **THEN** 对话分别展示原发现及局部零诊断，仍明确完整项目覆盖和策略未核验；未接持久任务时不虚构关闭事件
