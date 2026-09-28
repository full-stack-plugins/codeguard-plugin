## Purpose

定义 init 对项目语言、版本、构建器、模块关系和架构证据的观察与持久化，以及 AGENTS.md 受管摘要的生成边界，使智能体依据真实项目上下文选择检查和修复动作。

## ADDED Requirements

### Requirement: Initialization SHALL build an evidence bound project profile

init MUST 识别指定项目边界、各构建根、语言/方言、项目版本、语言目标、构建器/包管理器、框架、源集、现有质量配置及检查前置条件。声明、锁定/解析、本机安装版本 MUST 分开；每项附来源和内容身份，未观察到的事实 MUST 标 unknown，不从主语言或本机版本猜测其它模块。读取范围 MUST 遵循批准扫描与配置发现政策。

#### Scenario: Multiple build roots use different languages
- **WHEN** 一个项目含 Java、TypeScript 和 Python 构建根
- **THEN** 逐根保留语言、版本及构建配置，不以主语言覆盖其它根

#### Scenario: Installed runtime differs from the declared target
- **WHEN** 项目声明 Java 17，本机为 JDK 21 或尚未探测
- **THEN** 项目目标仍是 Java 17，本机证据独立记录或 unknown

#### Scenario: Different manifests declare different Java or Rust targets
- **WHEN** 多个 POM/Cargo 清单分别直接声明不同 compiler release/source/target 或 rust-version/edition
- **THEN** 按清单保留 declared_only 目标及原始字节来源，不以单个全局语言版本覆盖其它根；包版本、本机版本和有效模型解析保持独立，继承、变量、重复或非法字段不猜测为已知目标

#### Scenario: Maven or Cargo package version is directly declared
- **WHEN** POM/Cargo 清单直接声明项目包版本
- **THEN** 按清单记录 package_declared_versions，依据同次原始清单摘要；不把项目版本当语言目标、本机版本或已解析依赖版本。父/profile/workspace 继承、变量、重复、错误类型或非法值保持未知，刷新保留人工工作记录

### Requirement: Architecture observations SHALL not become unapproved rules

架构画像 MUST 分别描述表现层、领域组织、依赖结构和部署单元，允许多种风格并存。结论 MUST 区分 declared/observed/inferred/confirmed/unknown/stale，并保留依据。目录名、模型判断或相互冲突文档 MUST NOT 自动激活架构阻断规则；批准约束与观察结果必须分离。

#### Scenario: Domain and controller directories exist without a design declaration
- **WHEN** 仓库仅有 domain/controller 命名线索
- **THEN** 最多产生候选架构及确认任务，不认定已采用 DDD 或强制重构

#### Scenario: Documentation conflicts with source dependencies
- **WHEN** 文档声明的分层与实际观察不同
- **THEN** 同时保留证据和冲突，不选择较松约束或伪称架构已验证

### Requirement: Module graphs SHALL preserve relation types and uncertainty

模块图 MUST 区分构建聚合、构建依赖、源码引用、外部组件及声明的服务/业务关系，附范围、条件和来源。动态关系、未知 profile/feature 或不完整源码图 MUST 明示 unresolved；不能用缺边证明无依赖或缩小检查范围。既有 CodeGraph 证据 MUST 核对身份，init 不得自动安装/初始化/更新索引。

#### Scenario: Aggregated modules have no dependency edge
- **WHEN** 构建根仅声明两个子模块
- **THEN** 生成 contains 边，不虚构子模块间依赖

#### Scenario: Maven declares a local dependency with explicit coordinates
- **WHEN** 项目内 POM 声明完整且唯一的 group/artifact/version，并直接依赖另一个具有相同完整坐标的本地构建根
- **THEN** 模块图分别保留 Maven 聚合声明与 declared build_dependency，附来源清单及字节摘要、scope 和条件；声明边不等于有效 Maven 模型或运行时关系，不据此缩小检查范围

#### Scenario: Maven dependency identity cannot be resolved statically
- **WHEN** 坐标含属性变量、需要父 POM/依赖管理、重复坐标，或 profile 中有条件关系
- **THEN** 保留具体 unresolved，不选择某个目标伪造依赖边；逃出项目的模块路径或未观察到的模块也不能产生已知节点关系

#### Scenario: XML comments split a Maven identity field into multiple text nodes
- **WHEN** 模块或坐标字段由 XML 注释切成多段文本，静态解析器不能准确取得整个字段
- **THEN** 保留未解析状态，不截取首段文本来匹配另一个模块或坐标

#### Scenario: Cargo declares members and local path dependencies
- **WHEN** Cargo 清单显式声明项目内已观察成员或本地 path 依赖，依赖目标 package 名称与声明一致
- **THEN** 保留不同的 aggregation 和 declared build_dependency，记录清单摘要与 normal/build/dev 范围；包重命名按 package 字段核对，不把别名当目标包名。观察不执行 cargo 或 build.rs，不代表有效依赖解析

#### Scenario: Cargo relation needs workspace feature or target resolution
- **WHEN** Cargo 关系涉及继承、optional/target 条件、成员通配或排除、外部/缺失目标或逃出项目路径
- **THEN** 保留具体 unresolved，不自动展开未知条件或连接错误目标；图依赖覆盖保持不完整，不能据此缩小检查或宣称无依赖

#### Scenario: Conditional dependency is unresolved
- **WHEN** 构建依赖由未解析的运行条件决定
- **THEN** 保留未知范围，不以不完整图认证增量覆盖

### Requirement: AGENTS generation SHALL preserve scope and human ownership

init apply MUST 在被检查项目 AGENTS.md 生成明确标记的受管摘要，链接项目画像/模块图，包含规则来源和检查修复入口。区块外人工内容、其它工具区块和子目录指令 MUST 保留；缺 marker 时可追加，marker 异常、受管内容人工修改或并发冲突时 MUST 不盲目覆盖。仓库原始文本 MUST 作为转义数据，不提升为授权指令。

#### Scenario: Existing AGENTS contains several managed and human sections
- **WHEN** Codeguard 更新自身受管区块
- **THEN** 其它内容逐字保持，已有子目录规则继续按作用域生效

#### Scenario: Human changes the managed section after planning
- **WHEN** 写入前内容身份与计划不符
- **THEN** 报告冲突并保留用户修改，不以 force 覆盖

### Requirement: Init SHALL plan and apply without hidden execution

`init [path] [--dry-run|--apply]` 省略模式 MUST 等同 dry-run。dry-run MUST 只返回拟创建任务，不写 findings/tasks 或其它工作树文件；apply 才持久化计划内任务。默认观察不得执行项目 wrapper、构建扩展、package scripts、扫描、安装、服务启动、Git Hook/CI 接管或其它工具初始化。apply MUST 仅写计划明确的自有产物与 AGENTS 区块；分文件身份核对、原子替换及中途失败可恢复，不得谎称跨文件全原子。

#### Scenario: Dry run identifies a required environment blocker
- **WHEN** dry-run 通过有效证据确认必需环境缺失
- **THEN** 返回拟创建的阻塞及修复任务，工作树无新增或修改

#### Scenario: Wrapper prints a version and also changes files
- **WHEN** 项目提供带副作用的 wrapper
- **THEN** init 不执行它，不为获得版本而改变项目，相关事实保持待探测

#### Scenario: Writing the second artifact fails
- **WHEN** 第一份初始化文件已写入而后续文件写入失败
- **THEN** 返回部分未完成，记录可恢复进度，不覆盖并发修改或称全部成功

### Requirement: Profile refresh SHALL preserve findings and detect stale inputs

项目画像与图 MUST 以结构化产物保存，AGENTS/架构 Markdown 是投影，不是政策权威。重复 init MUST 幂等；manifest、锁、规则、相关源码或文件集合增删变化后 MUST 标过期并重算受影响画像。刷新 MUST 保留发现、修复事件与人工备注，不能重建空任务清单冒充问题已解决。

#### Scenario: A module is added after initialization
- **WHEN** 新增模块或构建清单，不属于上次读取的文件集合
- **THEN** 仍识别画像失效并更新模块图，不仅比较旧文件哈希

### Requirement: Initialization status SHALL be separate from quality readiness

init MUST 分别报告操作完成状态和检查前置准备状态。文件生成成功不证明工具可用、检查通过或交付 allow；缺工具/环境/必要信息 MUST 规划相应 blocker/决策/探测任务，在 apply 时持久化，并给出 doctor/check/sync/next 的后续动作。readiness MUST 依据批准检查义务和选中适配器的适用必需前置条件：已确认必需条件缺失、不兼容或冲突优先为 incomplete；否则，集合未确定、无适用义务或存在未探测/未解析/过期证据为 unknown；否则全部具有有效满足证据才为 ready。可选工具缺失 MUST NOT 阻塞此汇总，未探测 MUST NOT 伪称缺失。首次扫描 MUST 不自动豁免存量问题。未知架构仅在必需规则依赖它时影响相应检查，不强迫所有项目先选择架构风格。

#### Scenario: An optional tool is missing and a required runtime is unprobed
- **WHEN** 可选工具已确认缺失，而必需运行时尚无有效探测证据，且无其它已确认必需阻塞
- **THEN** readiness 为 unknown，生成必需运行时探测计划，不因可选工具缺失返回 incomplete

#### Scenario: Required preparation evidence is stale or belongs to another binding
- **WHEN** 必需前置证据过期、来自不同策略/目标/工具绑定，或可信时钟/来源尚未核验
- **THEN** 不能沿用旧 satisfied 或 missing 结论；该前置为 unknown 并要求复核。只有本轮有效的必需缺失/不兼容/冲突优先产生 incomplete，可选条件的失败不改变汇总

#### Scenario: Preparation is ready but checks have not run
- **WHEN** 全部已确定适用必需前置有有效满足证据，readiness 为 ready
- **THEN** ready 仅表示前置准备，不代表原生检查完成、没有 finding 或交付 allow；无适用必需集合、集合未完整确认或重复/歧义归属不能因零阻塞而返回 ready

#### Scenario: Files are initialized but JDK is missing
- **WHEN** 工作区和 AGENTS 生成成功但 Java 工具链未准备
- **THEN** init 可返回操作成功，同时 readiness=incomplete、准备任务可见，交付未经认证

#### Scenario: Preparation tasks retain identity without retaining stale diagnoses
- **WHEN** 同一必需前置的输入绑定或观察状态变化，需要重新规划准备任务
- **THEN** 任务以工作区内前置标识保持稳定逻辑键，更新本轮绑定；有效缺失、不兼容、冲突分别给出恢复、兼容性复核、冲突决策动作，未知/过期/错绑定仅要求重新核验，不沿用旧缺失诊断。可选、不适用、已满足前置不生成修复任务，未核验来源或歧义要求不能生成可执行任务；规划不自动安装、执行命令或授予交付通过，关闭须重新取得当前有效满足证据

#### Scenario: Initialization observations are returned to the agent conversation
- **WHEN** init 以 dry-run 或 apply 观察了语言、构建根及逐清单语言目标
- **THEN** JSON 与 human 均反馈对应观察摘要、声明与未知状态；dry-run 不要求先写文件才能看到结果。摘要不执行工具、不暴露原始清单内容或本机根路径，也不把文件生成/目标声明变成质量通过；项目路径等不可信文本不能伪造终端指令或状态行

#### Scenario: Initialization returns checker configuration separately from execution
- **WHEN** 只读发现器观察检查器的 configured/missing/invalid/unknown 状态
- **THEN** init 按构建根反馈状态、来源、原因和下一步，执行状态固定 not_run；配置清单不完整和义务尚未绑定必须明示。未配置不能自动变成代码违规，配置已声明不能自动变成执行成功或准备就绪，摘要不自动启用/豁免检查器
