# Execution Kernel

## Purpose

为 CLI、MCP、语言检查、Git 门禁和漏洞扫描提供一致且可追溯的外部进程证据，使工具故障不会因入口不同而丢失诊断、冒充通过或被误认成代码违规，同时保留原有用户接口。

## ADDED Requirements

### Requirement: Tool execution SHALL preserve process evidence

执行结果 MUST 保留实际 argv、工作目录、原始退出码、标准输出和标准错误；若外部工具输出超过明确的捕获预算，则 MUST 终止该执行并保留预算内已捕获的诊断，以独立故障标识报告 UNVERIFIED，不得伪造完整输出或 PASS。参数 MUST 以 argv 传递，不隐式增加 shell；工具是否发现代码违规由工具判定策略解释，不能由进程执行器推断。
Git 快照使用同一有界进程边界的原始字节模式，MUST 保留 NUL 与 blob 字节且不在协议校验前解码；路径列举、大小响应及对象内容 MUST 各有明确捕获预算。任何超限或执行故障 MUST 阻止交付快照并成为 SnapshotError，不能以截断数据继续门禁。对象总量预算必须在读取 batch 内容之前由大小响应确定。
工作树预测暂存覆盖层 MUST 以有界缓冲复制普通文件，并同时限制文件数量、单文件与累计字节数；检查期间文件超出预算、变成特殊文件或读取失败 MUST 拒绝交付临时树，不能把不完整覆盖层当准确 Git 快照。删除及文件与目录之间双向转换的预测语义必须保留，不能因覆盖路径迭代顺序不同而改变快照。
同一次准确快照中，拟提交路径与实际物化的覆盖层 MUST 使用同一份已列举的路径集合；不得分别查询两次 Git 工作树后把不同时点的路径清单拼成一个已验证结论。
准确快照 MUST 在交付临时树前及检查器返回后复核所用的 index/HEAD 对象列表身份与 HEAD 提交身份；提交模式的 HEAD 是暂存差异比较基线，推送模式的 HEAD 决定待推送范围，即使文件树相同也不能忽略提交变化。首次提交前须允许不存在的 HEAD，但若检查期间产生首次提交，MUST 报告 Git UNVERIFIED。若路径、模式、对象 ID 或 HEAD 提交在观察窗口内变化，MUST 报告 Git UNVERIFIED，不得把旧 blob 的检查结果称为当前拟提交内容的结论。此复核不声称工作树与 Git 引用具备原子事务语义。

#### Scenario: A checker exits nonzero
- **WHEN** 同一检查器经 CLI、保存 hook、Git 门禁或 CVE 执行并以非零退出
- **THEN** 各入口获得相同的原始进程结果，再使用各自检查契约解释，不擅自改成成功

#### Scenario: An argument contains shell syntax
- **WHEN** argv 参数包含空格、分号或命令替换字符
- **THEN** 它作为单个字面参数到达工具，不作为额外 shell 命令执行

#### Scenario: A checker exceeds the output budget
- **WHEN** 外部检查器向 stdout/stderr 持续写入超过进程执行预算的内容
- **THEN** 执行器有界地保留两个流的已有诊断，终止该检查，返回明确的输出超限故障与非成功退出；下游不得把截断的成功前缀判为 PASS 或宣称已有完整诊断日志

#### Scenario: Git emits more data than the snapshot budget
- **WHEN** Git 路径列举、batch-check 或 batch 内容超过相应捕获预算，即使进程继续输出
- **THEN** 执行器及时终止进程；快照入口报告未验证且不交付部分内容、不得据此前的成功前缀放行

#### Scenario: Many predicted worktree files exceed the aggregate overlay budget
- **WHEN** 每个文件均小于单文件上限，但所有拟暂存工作树文件的实际读取字节总数超过覆盖层预算
- **THEN** 快照不交付部分临时树，门禁报告未验证，原工作树与 Git index 保持不变

#### Scenario: Overlay listing changes between observations
- **WHEN** Git 工作树路径列举在两次调用之间返回不同集合
- **THEN** 单次快照只使用一次列举结果来计算 changed 与构建临时树；不能把第一份 changed 与第二份物化内容配对

#### Scenario: Index or HEAD changes during an exact check
- **WHEN** 已列举对象之后，同名路径被重新暂存为另一个 blob，或检查器运行期间 index/HEAD 的路径、模式、对象 ID 或 HEAD 提交发生变化（即使提交文件树相同，或首次提交刚被创建）
- **THEN** 快照不交付旧内容，或在检查器返回时将该次结论标为 Git UNVERIFIED；不得把两个时点的内容拼成 PASS，观察过程自身不改写真实 index

#### Scenario: A predicted path is a special file
- **WHEN** 拟暂存路径在快照复制时变成 FIFO、socket 或其它非普通文件
- **THEN** 快照拒绝该内容，即使类型检查与打开之间发生替换也不阻塞读取特殊文件，且不把它当作成功删除

### Requirement: Execution failures SHALL remain observable

超时 MUST 保留已捕获输出并记录超时故障；缺失命令与权限/工作目录故障 MUST 返回明确不可验证的执行结果。非 UTF-8 输出 MUST 保留可解码文本并替换非法字节，不能让编码异常吞掉整次检查。不得捕获用户取消或任意编程异常作为成功结果。

#### Scenario: Timeout after useful diagnostics
- **WHEN** 检查器先输出诊断后超时
- **THEN** 返回超时标识、124 和已有诊断，不能伪称没有输出或代码通过

#### Scenario: Tool cannot start
- **WHEN** 命令不存在或文件无执行权限
- **THEN** 返回启动故障；下游 lint 结论为 UNVERIFIED 而非 FAIL 或 PASS

#### Scenario: Invalid output encoding
- **WHEN** 检查器输出包含非法 UTF-8 字节
- **THEN** 保留真实退出码和其余可读输出，不因解码异常丢失结果

### Requirement: Existing entry points SHALL remain compatible

本次重构 MUST 保留原 CLI 子命令、四个 MCP 工具、五类 hook 的路径/JSON/退出语义、用户配置、语言注册表与外部受管技能。执行内核不得导入宿主 SDK 或修改项目文件、Git index、用户环境配置。

#### Scenario: Legacy script invocation
- **WHEN** 用户或 manifest 从原路径直接执行检查脚本
- **THEN** 无需安装新包即可使用原有能力，PASS/FAIL/UNVERIFIED 不因协议转换改变

### Requirement: Check plans SHALL retain execution context

检查计划 MUST 显式区分 repo、delta 与 save，保存物化后的命令、工作目录和逐命令环境覆盖。执行 MUST 按序进行，首个非零结果终止普通检查批次，保留已执行证据；未执行的命令不得计为成功。空计划不得生成 PASS。Java 原生计划给出的环境覆盖 MUST 在子进程中生效，不改变宿主环境。修复后的检查 MUST 复用原计划，不重新扩大范围。Git 门禁的逐文件基线豁免是独立策略，不由通用执行器决定。
语言检查与修复的应用结果 MUST 保留实际运行的每条命令身份、目录、退出码、故障标识和有界输出摘要；MCP 适配不得只保留终止命令，但其公开执行轨迹 MUST 只包含阶段、序号、程序名、退出码、故障标识和输出长度，不得新增暴露原始 argv、命令环境覆盖或任意检查器输出。失败日志 MUST 保留同一检查批次中此前已执行命令在捕获预算内的全部输出，不能只记录最后一条；输出超限必须明确标识未验证，不得宣称日志完整。证据不得把尚未运行的计划命令写成已执行。
MCP `auto_fix` 的 `fix_results` 公开面 MUST 同样只保留状态、退出码、安全元数据和可用诊断路径，不得因复制内部修复字典而回显 formatter 原始 argv 或 stderr。内部兼容 `fixed` 只表示 formatter 命令成功退出；公开结果 MUST 将此事实单独标为 `formatter_succeeded`，公开的逐项 `fixed` 只有在内容变化可唯一归因于这一条成功执行、且复检后身份稳定时才为真。多条 formatter 执行、读取故障或已知失败后有内容变化时，不得把全局差异猜给某条成功命令。实际修复诊断仍应在可写时以私有原子日志保存；日志写入失败不得改变修复和复检结论，也不得回退为公开原文。

#### Scenario: Java commands use the selected JDK
- **WHEN** Java 项目计划选择 JAVA_HOME，且声明多条权威检查命令
- **THEN** 每条实际运行的命令使用该环境；后续命令失败时返回失败而非首条成功，宿主 JAVA_HOME 不变

#### Scenario: Multi-command result retains prior execution evidence
- **WHEN** Java 权威计划的第一条命令输出诊断后通过，第二条命令失败，第三条未执行
- **THEN** 内部检查结果保留前两条的 argv、目录、退出码、有界输出摘要和故障标识；MCP 返回对应的安全元数据与失败日志路径，不回显原始参数或输出；第三条不得出现于执行证据

#### Scenario: Configured command includes a credential argument
- **WHEN** 权威命令的 argv 含凭据文本，且检查器输出也包含该文本
- **THEN** 真实子进程仍收到原始 argv，MCP 的 `check_code_style` 和 `auto_fix` 执行轨迹不回显凭据；日志仍按既有本地路径保存原始诊断

#### Scenario: Formatter stderr contains a credential
- **WHEN** `auto_fix` 的 formatter 命令及 stderr 包含凭据文本
- **THEN** MCP 整个修复结果不包含该文本或原始命令参数；可用时返回仅当前用户可读的诊断日志路径，日志不可用时仍不泄漏原文

#### Scenario: A no-op formatter exits successfully
- **WHEN** formatter 退出码为 0，但修复前、修复后和复检后的目标内容身份相同
- **THEN** `formatter_succeeded=true`，公开 `fix_results[].fixed=false`，并表明内容变化已验证

#### Scenario: Multiple formatters run but a global change cannot be attributed
- **WHEN** 两条 formatter 都执行，最终只有全局文件身份变化，无法可靠分配给其中一条
- **THEN** 顶层仍可报告已观察到的变化，但逐项 `fixed` 不猜测归属，逐项明确未验证

#### Scenario: A failed formatter partially changes a file
- **WHEN** 唯一 formatter 退出非零但已改写目标文件
- **THEN** 保留失败及复检证据，整体 UNVERIFIED 且不声称已确认修复

### Requirement: Diagnostic logs SHALL be private and atomic

CLI/MCP 失败日志与 Git 门禁截断诊断日志可能包含检查器的原始敏感输出。写入 MUST 使用同一基础设施边界，创建的文件在支持 POSIX 权限的平台上 MUST 仅允许当前用户读写；替换 MUST 原子可见，不能跟随预置的日志文件符号链接覆盖其它文件。默认 `out` 日志目录若本身是符号链接，MUST 不向链接目标写入。日志写入失败 MUST 不掩盖已经得出的检查状态，且不得返回并不存在的日志路径。既有日志路径与内容格式保持不变；这不承诺抵御并发替换父目录的完整文件系统竞态。

#### Scenario: A pre-existing diagnostic log is a symlink
- **WHEN** 项目或临时目录里预置的日志文件指向另一文件，检查器随后产生失败诊断
- **THEN** 链接目标内容保持不变，实际日志以仅当前用户可读的完整内容替换日志路径

#### Scenario: The project output directory is a symlink or unavailable
- **WHEN** 默认 `out` 是指向其它目录的符号链接或不可写入的路径
- **THEN** 检查的 FAIL/UNVERIFIED 结论保持不变，不写入链接目标，也不返回虚假的 `log_path`

#### Scenario: Repair retains the original scope
- **WHEN** delta 或 save 检查失败并成功运行 formatter
- **THEN** 复检执行原物化命令，仅包含原检查范围；被跳过的文件不导致漏掉其它文件的复检

### Requirement: CLI fix SHALL account for every repair outcome

同一语言可同时产生跳过子范围与实际 formatter 结果。CLI MUST 遍历应用返回的每条结果，而不是按语言数截断；任何实际 formatter 失败或不可验证结果 MUST 不得被同语言的 SKIPPED 提示掩盖为成功。既有逐条提示与 dry-run 行为保持可见。formatter 退出码 0 仅证明命令执行成功；若 CLI 未采集修复前后内容身份，MUST NOT 将它呈现为已经确认文件发生修复。

#### Scenario: Mixed shell and zsh changes with a failing formatter
- **WHEN** Git 改动同时包含 `.zsh` 与 `.sh`，前者安全跳过 formatter，后者 formatter 实际运行并失败
- **THEN** CLI 同时显示跳过说明与 formatter 失败，退出非零；不得只处理第一条 SKIPPED 结果

#### Scenario: Formatter exits successfully without changing a file
- **WHEN** CLI 对已规范的改动文件运行 formatter，进程退出码为 0，但内容保持不变
- **THEN** CLI 仅报告 formatter 执行成功且文件变化未验证，不宣称 `fixed`

#### Scenario: No executable commands
- **WHEN** 计划没有任何可执行命令
- **THEN** 规划调用方返回 SKIPPED、PLANNED 或 UNVERIFIED；执行器拒绝将空计划解释为成功

### Requirement: MCP auto-fix SHALL observe changed files within a bounded safe scope

MCP `auto_fix` 在运行 formatter 之前 MUST 验证所有拟修复路径仍位于项目根内、不是符号链接或特殊文件，并以有总量预算的流式内容身份记录修复前状态，不得整份载入任意大小文件。路径逃逸、读取故障、并发替换或超预算 MUST 明确 UNVERIFIED 且不启动修复。修复后身份无法可靠采集时 MUST 保留实际修复与复检证据，但不得声称已确认 `fixed`。`fixed` 只可归因于 formatter 已产生且复检后仍保留的目标文件变化；若复检本身改变这些文件，MUST 保留实际执行证据并将整体结果标为 UNVERIFIED，不可把检查器副作用当作已确认修复。已确认的内容或权限变化仍按既有 `fixed` 字段呈现。

#### Scenario: Changed path escapes through a parent symlink
- **WHEN** Git 改动路径经父目录符号链接指向仓外普通文件
- **THEN** `auto_fix` 不读取仓外内容、不运行 formatter，返回明确 UNVERIFIED

#### Scenario: Changed file exceeds the observation budget or changes during reading
- **WHEN** 改动文件超出身份预算、读取失败或被并发替换
- **THEN** 修复前故障不启动 formatter；修复后故障保留已执行结果但不宣称 `fixed`

#### Scenario: Checker changes a repair target after formatter returns
- **WHEN** formatter 返回后目标文件身份可采集，但随后的检查器又改动该文件
- **THEN** `auto_fix` 保留修复与检查执行证据，整体标为 UNVERIFIED，`fixed` 不宣称已确认

### Requirement: Hook state SHALL preserve concurrent and session ownership

统计、绕过明细、冷却与审计的读改写 MUST 在进程锁内完成并原子替换文件。宿主提供 session_id 时，统计 MUST 绑定会话与当前 worktree；Stop MUST 只消费该作用域的记录，并与并发写入互斥。无 session_id 时保留旧共享状态兼容，MUST 明示不能证明跨会话隔离。去重 MUST NOT 把未完成或 UNVERIFIED 的检查当成已完成检查。
Stop MUST 在宿主输出成功刷新后才确认消费；输出失败时记录必须保留供重试。若确认前有并发新写入，允许后续 Stop 重复展示旧统计，但不得删除未展示的新记录。
UserPromptSubmit 与 PostToolUse 的已完成事件、文件去重和会话统计 MUST 在相应 stdout 成功刷新后才登记；写入或刷新失败时不得把未交付反馈标记为已交付。PreToolUse 已得到拦截结论时，即使宿主输出失败也 MUST 保留拦截退出码，并且不得缓存该次未交付结果。

#### Scenario: Concurrent writers preserve all increments
- **WHEN** 多个 Hook 进程同时更新同一统计、绕过记录或审计日志
- **THEN** 累计计数与保留上限内的日志项不因覆盖而丢失，读者不会看见半截 JSON

#### Scenario: Stop only drains its own session and worktree
- **WHEN** 两个会话或两个 worktree 同时有检查记录，其中一个收到 Stop
- **THEN** 只汇总并清理当前作用域，其余记录保持可供各自 Stop 消费

#### Scenario: Stop output fails or state changes during delivery
- **WHEN** Stop 已准备总结但宿主 stdout 写入或刷新失败，或在输出期间有新统计写入
- **THEN** 输出失败时旧统计可在重试中再次展示；并发新统计不得被确认消费误删，允许为了不丢记录而在后续 Stop 重复展示旧统计

#### Scenario: Buffered host feedback fails before delivery
- **WHEN** UserPromptSubmit 或 PostToolUse 已写入反馈，但 stdout 刷新失败
- **THEN** 不登记已完成事件、文件去重或会话统计；下次触发仍可重新检查并交付反馈

#### Scenario: Hard Git block survives host output failure
- **WHEN** PreToolUse 已判定需要拦截，但 stdout 或 stderr 写入或刷新失败
- **THEN** 保持拦截退出码且不缓存该次结果，不能因宿主输出故障改为放行

#### Scenario: Retry follows an unverified save check
- **WHEN** 相同文件未变化，上次保存检查未能获得结论，紧接着再次触发
- **THEN** 再次执行检查，不因此前写入的去重标记而静默跳过

### Requirement: Cached observations SHALL bind their input identity

软门禁缓存 MUST 绑定真实 worktree、Git HEAD/index 内容与推送基线、工作树文件内容、检查范围、用户配置和命令定义；不得仅用 mtime/size 推断内容相同。身份采集失败或超过预算 MUST 跳过缓存而继续检查，不能截断后复用。检查前后身份不一致、结果含未验证项或缓存格式无效时 MUST NOT 复用。硬门禁 MUST 始终从准确快照执行，不消费软缓存。保存去重同样 MUST 绑定已检查的内容与适用配置，检查期间变化不得登记成新内容已通过。

#### Scenario: Content changes without timestamp changes
- **WHEN** 文件内容被等长替换并恢复原 mtime
- **THEN** 下次检查不复用旧结果

#### Scenario: Configuration or linked worktree index changes
- **WHEN** 用户配置、项目配置或 linked worktree 的暂存内容变化
- **THEN** 缓存身份变化，长驻进程也读取新项目配置

#### Scenario: Unknown result or concurrent edit
- **WHEN** 检查工具第一次未验证后恢复，或执行期间输入变化
- **THEN** 不记录可复用完成结果，后续实际重跑检查

### Requirement: Gate application SHALL separate checks from host presentation

门禁应用 MUST 不依赖 hooks 导入或宿主 SDK。单个语言检查 MUST 返回独立结果，汇总 MUST 保持输入顺序，不用共享可变备注列表连接并发检查。准确快照的审计 MUST 保留原 worktree 和会话归属，实际执行目录只作为执行上下文，不冒充项目身份。基线比较遇到未验证工具结果 MUST NOT 产生存量豁免。
基线豁免 MUST 比较逐条诊断内容、出现次数及可识别的文件归属，且基线检查器本身 MUST 确认失败；规则码集合或仅有文本输出不足以证明当前发现已存在。基线临时文件路径可以映射回被检查的仓库相对路径，行列号移动不应单独取消同文件的存量豁免；不同文件的同文本诊断不得互相抵扣。
单个并行语言检查抛出内部异常时，应用 MUST 将该语言标为 UNVERIFIED，保留其余语言已确认的失败和审计，不得让异常抹掉整批结论。Git 安全路径观察抛出预期的快照错误时，应用 MUST 以 additionalContext 明示安全扫描未验证，并保留已有 lint 拦截；只有没有已确认拦截时才沿用既有 fail-open 退出码。内部异常消息不得作为任意原文注入宿主上下文。

#### Scenario: Exact snapshot audit retains ownership
- **WHEN** 带会话 ID 的提交门禁从临时 Git 快照执行检查
- **THEN** 审计记录归属原 worktree 和当前会话，并记录实际执行命令

#### Scenario: A parallel checker crashes after another language finds a violation
- **WHEN** 一种语言的 worker 抛出内部异常，另一种语言真实执行并确认违规
- **THEN** 返回前者的 UNVERIFIED 提示、后者的失败和审计，不能因为异常把整批检查变为成功

#### Scenario: Safety path scan cannot read the proposed Git face
- **WHEN** 语言门禁已有结论，而安全路径扫描无法取得拟入库路径
- **THEN** 宿主收到安全扫描 UNVERIFIED 上下文；已有失败仍拦截，无已知失败时保持既有未验证放行语义

#### Scenario: Baseline tool cannot verify
- **WHEN** 基线检查器输出类似违规文本但退出结果为 UNVERIFIED
- **THEN** 不因文本相似而豁免当前检查

#### Scenario: Baseline evidence must cover every current finding
- **WHEN** 基线检查器返回成功码却打印诊断、同一规则新增第二处违规，或规则码相同但诊断内容变化
- **THEN** 当前违规不得获得存量豁免；只有基线自身确认失败且逐条诊断及出现次数覆盖当前结果时才能豁免

#### Scenario: Identical diagnostics belong to different files
- **WHEN** 当前输出将同一规则和描述归于另一文件，而基线输出归于被检查文件；或者 ShellCheck 的 `In <file> line N` 段属于另一文件
- **THEN** 不得以文本相同授予存量豁免；被检查文件自身仅行列号变化时仍可保留有证据的旧发现豁免

### Requirement: Language services SHALL have explicit input and lifetime

语言注册表 MUST 由同一校验逻辑验证后派生识别与命令表，非法形状和重复 ID 不得静默覆盖。
项目发现 MUST 使用调用方绑定根的配置，不因扫描到嵌套构建文件而丢失扩展名覆盖。
项目配置不存在可以使用默认值；存在但无法解析、字段类型错误或排除正则非法时 MUST 明确报
配置不可验证，不得假装配置不存在。未知扩展字段保留给各领域适配器，不封闭 Java 等现有扩展。
探活 MUST 在目标项目工作目录执行、不消费宿主标准输入，并通过统一执行器处理编码和启动故障。
成功探活只可在同一检查批次内去重；失败 MUST 可立即重试，跨批次 MUST 重新执行。

#### Scenario: A long-lived process observes tool recovery
- **WHEN** 探活失败后工具恢复，或下一批检查前工具环境改变
- **THEN** 重新探活，不使用进程级永久缓存

#### Scenario: Nested source tree uses root override
- **WHEN** 显式项目根配置自定义扩展名，源码子目录另有构建标记
- **THEN** 项目发现仍使用显式根的配置，深层文件可发现其最近的项目根

#### Scenario: Malformed project configuration
- **WHEN** codeguard.json 存在但内容非法
- **THEN** CLI/MCP 返回明确 UNVERIFIED，Hook 保持既有 fail-open 并可见告警；不执行自动修复

### Requirement: Java analysis SHALL separate observation from policy

构建解析、纯模块影响闭包、命令选择、Git 版本差异观察与 JDK 探测 MUST 有明确依赖边界。
影响计算和默认命令选择 MUST 不读取文件、不启动进程；应用层负责验证根内路径、选择
wrapper、装配配置与环境。CLI/MCP 的既有字典字段和只读规划语义 MUST 保留。
Maven 默认 `-DskipTests verify`、Gradle 默认 `check -x test` 和显式 argv 权威覆盖 MUST 保留。
纯版本升级仍可降为 validate/help，但 MUST 有已成功读取的基线和当前内容证明；依赖/插件版本、
编译配置、脚本逻辑或无法证明差异性质时 MUST 不降级。动态构建/缺失静态边仍保守全量。

#### Scenario: Dependency version is not a release-only bump
- **WHEN** 仅修改 POM 中 dependency/version 或编译器配置，改动行不含 dependency 标签
- **THEN** 仍计划 verify，不能仅靠行级关键词降为 validate

#### Scenario: Pure project version update remains lightweight
- **WHEN** 成功读取的前后构建描述只改变项目自身版本号
- **THEN** 保留 validate/help 优化，显式 java.commands 仍优先且原样执行

#### Scenario: Pure impact calculation is isolated
- **WHEN** 独立进程只加载影响与命令策略，输入包含循环依赖与无关模块
- **THEN** 有限时间内获得完整反向闭包且不修改输入，不加载执行器、文件解析器或宿主服务

### Requirement: CVE scanning SHALL separate report evidence from orchestration

五种扫描器的报告解析与阈值判定 MUST 不依赖进程、文件或宿主。扫描 IO、项目选择与修复复扫、
CLI 呈现 MUST 各有单一所有者。只有有效报告且执行状态可解释时才能作出 PASS/FAIL；残缺或
自相矛盾统计、非法分数、缺失发现标识、扫描错误不得伪装为零漏洞。原始退出码、输出和发现
必须保留。缺严重度的发现遵循现有 LOW/高阈值合同，不得在调用工具时提前过滤 UNKNOWN。
只在用户允许且本次有效报告确认需要修复时执行 npm audit fix；保留修复进程结果，最终判定
必须来自同一项目、同一阈值的复扫，不能凭修复命令成功声明已修复。

#### Scenario: Malformed reports never become empty success
- **WHEN** 工具退出 0 但漏洞统计残缺、报告容器类型非法或 CVSS 分数不合法
- **THEN** 返回 UNVERIFIED，给出解析原因，不执行自动修复

#### Scenario: Unknown severity remains observable
- **WHEN** 报告包含有效漏洞标识但没有可比较严重度
- **THEN** 保留发现；LOW 可判定漏洞，其余阈值不可擅自 PASS 或推断高危

#### Scenario: Fix result is followed by a fresh audit
- **WHEN** npm 修复命令执行后复扫失败或返回干净报告
- **THEN** 分别返回 UNVERIFIED 或 PASS，保留修复前报告和实际修复执行证据

### Requirement: Accurate Git snapshots SHALL validate object transport

index/HEAD 对象列表 MUST 是完整的 NUL 分隔记录：每项有合法模式、对象格式对应的 ID、
阶段/类型与非空路径，重复路径或不完整末项不得静默跳过。准确快照 MUST 用独立的
Git 路径列举核对对象列表的路径集合；单次列表在记录边界被截断时也不能交付部分树。
这些协议故障 MUST 归一化为快照 UNVERIFIED，而不是入口异常或空树 PASS。
Git 准确快照 MUST 对 index/HEAD 列出的每个对象，逐项核对 `cat-file --batch-check` 与
`--batch` 响应的对象 ID、blob 类型、非负大小、顺序和完整字节边界。响应缺项、重复项、
内容截断或多余尾部字节 MUST 报告快照 UNVERIFIED，不得把错误对象或部分内容交给语言检查器。
实际 payload MUST 按仓库对象格式重新计算 blob 哈希并与 index/HEAD 对象 ID 一致；
同长度内容被替换也不能通过仅核对响应头而被接受。
大小预算 MUST 基于已验证的逐项大小；二进制内容中的换行与 NUL 必须原样保留。
观察过程不得改写真实 Git index。此要求不改变既有 Hook 对未知结果的 fail-open/可见告警政策。

#### Scenario: Git batch response disagrees with the requested objects
- **WHEN** 批量读取的对象 ID、类型、大小、数量或顺序与已列出的 Git 对象不一致
- **THEN** 准确快照不可交付，门禁报告 Git UNVERIFIED，而不是检查错位或部分内容

#### Scenario: Git object listing is malformed or incomplete
- **WHEN** `ls-files --stage` 或 `ls-tree -r` 缺少终止 NUL、含畸形/重复记录，或虽在完整记录边界结束却漏掉另一列举可见的路径
- **THEN** 准确快照不可交付，门禁报告 Git UNVERIFIED；真实 index 不变

#### Scenario: Batch payload has an invalid boundary or identity
- **WHEN** 对象内容截断、缺少协议分隔符、尾随额外数据或同长度内容与对象哈希不符
- **THEN** 不交付临时树，不改变真实 index；有效二进制 blob 仍可逐字节重建

### Requirement: Predicted staging SHALL preserve repository and pathspec scope

拟暂存范围 MUST 绑定每个 git add 的实际仓库与工作目录，而非整条命令链的最终 cd 或全局
路径并集。显式 pathspec MUST 交由只读 Git 查询成组解析，保留目录、glob、literal、exclude、
引号路径及 -u/-f 的选择差异；展开后的文件名不得再作为 glob 解释。观察 MUST 不改写实际
index 或工作树；不支持的动态/交互式形态必须明确未验证，不得冒充准确暂存面。
仓库定位与拟暂存解析 MUST 使用同一个显式调用目录，不能一处用传入的 cwd、另一处读取
门禁进程的全局工作目录。
显式 `cd` 或 `git -C` 已给出目标时，若该目标不是可解析的 Git 工作树，MUST 阻断
该 Git 副作用命令并报告目标不可确定；不得回退调用者仓或扫调用者一层子仓。
只有命令未给出显式目标且调用目录不是 Git 仓时，才保留既有 workspace 子仓兜底策略。
兜底为每个子仓构造的合成目标 MUST 同时用于暂存观察；不能仍以非 Git workspace 目录
解析 commit，导致脏子仓的已确认违规降级为无阻断的未知结果。
一条命令链触及多个仓库时，commit/push 门禁面和是否存在待提交操作 MUST 按仓库分别
归属；A 仓的 commit 不得使 B 仓的纯 push 检查包含 B 仓尚未提交的 index。若同一仓
同时 commit 和 push，则继续检查该仓已有待推送内容及拟提交内容，不得缩窄既有检查面。
对于没有间接脚本或命令替换的静态命令链，拟暂存面 MUST 按同仓 Git 操作的先后顺序投影：最后一个
commit 之后才出现的 add 不得回溯到已完成的 commit 或随后的 push；最后一个 commit 之前的
add（包括多个 commit 之间的 add）仍须检查。无法可靠排序的一层间接脚本继续采用保守并集
或明确 UNVERIFIED；`$(...)` 和反引号会先执行内层、再执行外层，现有静态展开无执行时钟，
也 MUST 保守合并。不得通过此优化遗漏可能提交的敏感内容。
仓库级 `codeguard.skipGate` 只豁免设置它的仓库，不得因 A 仓豁免而跳过同链 B 仓。
内联 `git -c codeguard.skipGate` 只豁免对应 Git 操作；链式 `git config` 设置/取消
须按命令顺序归属到目标仓，不得把 A 仓的豁免传播到 B 仓或此前操作。写入
其它配置文件的 `git config --file=...` 不构成当前仓库生效的豁免。
链式配置变更只有经 `&&` 确认成功路径后才能传递到后续操作；跨越 `||`、`;`
或换行后的配置状态无法静态证明时，MUST 阻断并提示拆分命令，不得猜测已生效。
命令切分 MUST 区分真实 Shell 分隔符和被引用/转义的字面文本；提交消息、echo 参数
或文件路径中的 `;`、`&&` 不得生成虚假的 Git 操作或豁免设置。
对一层可静态读取的 `bash`/`sh`/`zsh` 内联命令（含 `-lc` 等组合短选项）或脚本，Git 副作用的识别、仓库归属与
拟暂存分析 MUST 使用脚本的实际调用目录和同一份内层命令；外层直接 Git 操作与内层操作
不得互相覆盖。若已识别间接 Git 副作用但不能可靠建立仓库或暂存计划，MUST 报告 Git
意图 UNVERIFIED 并阻断，不得回退扫描无关子仓或以错误仓库的 PASS 放行。
静态可解析的环境赋值、`env`、`command` 与无参数 `sudo` 等裸命令前缀 MUST 在 Shell
解释器检测、直接 Git 检测及 `skipGate` 设置/取消/内联豁免中共享同一归一化语义，
不能让同一个 `bash -c` 的提交因前缀而逃过门禁，也不能漏掉前缀后的豁免状态变更而
错误继承持久豁免；带参数且无法静态解析的 wrapper 不在此保证范围内。

#### Scenario: Two repositories have different staging commands
- **WHEN** 一条命令链对 A 执行 add -A、对 B 只提交已暂存内容
- **THEN** B 的未暂存及未跟踪文件不进入拟提交检查面

#### Scenario: Commit and push belong to different repositories
- **WHEN** 一条命令链提交 A 仓、只推送 B 仓，而 B 仓另有未提交的暂存改动
- **THEN** A 使用 commit 面，B 使用纯 push 的 HEAD 面；B 的暂存改动不因 A 的 commit 被误纳入

#### Scenario: Commit and push belong to the same repository
- **WHEN** 同一仓在一条命令链中先提交再推送
- **THEN** 门禁同时覆盖该仓拟提交 index 和已有待推送 HEAD 内容

#### Scenario: A bypass belongs to its repository
- **WHEN** 同链 A 仓设置了 `codeguard.skipGate`，B 仓没有豁免且包含应拦截内容
- **THEN** 只审计并跳过 A 仓，仍对 B 仓运行完整门禁并阻断其违规内容

#### Scenario: Inline and chain bypasses are not global
- **WHEN** A 仓使用单次 `git -c` 或链式 `git config` 豁免，B 仓在同链执行无豁免提交
- **THEN** 仅 A 的指定操作获得豁免，B 仓仍完整检查；同仓 unset 后的操作也不继承之前的豁免

#### Scenario: A conditional bypass setter cannot be assumed successful
- **WHEN** `git config codeguard.skipGate true` 后以 `||`、`;` 或换行连接提交，或设置写入其它配置文件
- **THEN** 不把该设置当作已生效的本仓豁免；无法证明控制流时报告 UNVERIFIED 并要求拆分命令

#### Scenario: Quoted control characters are data
- **WHEN** `echo` 的引号参数或 commit 消息包含 `; git config codeguard.skipGate true`
- **THEN** 不产生虚假的 config 设置，随后未豁免的提交仍须检查并阻断违规内容

#### Scenario: Shell wrapper commit uses the invocation repository
- **WHEN** 从 Git 仓执行 `bash -c 'git commit'` 或相对路径脚本，脚本内存在待提交内容
- **THEN** 将内层 commit 绑定到脚本调用目录的 Git 仓，而非报无仓或扫描其子仓

#### Scenario: A bare prefix does not hide a shell commit
- **WHEN** 可读的 `bash -c` 或脚本前有环境赋值、`env FOO=1`、`command` 或无参数 `sudo` 前缀，内层提交包含敏感暂存内容
- **THEN** 检测、仓库归属和拟暂存分析仍使用同一内层命令，按目标仓阻断；前缀本身不构成豁免

#### Scenario: A bare prefix does not hide a bypass change
- **WHEN** 仓库原有 `skipGate=true`，同链先执行 `env FOO=1 git config codeguard.skipGate false` 再提交敏感文件
- **THEN** 后续提交不继承原持久豁免，仍运行门禁并阻断；带前缀的 `git -c` 单次豁免仍仅作用于其自身操作

#### Scenario: Script arguments are not interpreter options
- **WHEN** 一个无 Git 副作用的脚本接收名为 `-c` 的普通参数及包含 `git commit` 的文本
- **THEN** 解析器不得把脚本参数当成解释器 `-c` 代码并虚构 Git 副作用

#### Scenario: Inner shell staging remains visible
- **WHEN** 可静态读取的 shell 命令内先 `git add` 敏感文件再提交，或先切换到另一仓再提交
- **THEN** 拟暂存分析包含内层 add 并归属实际目标仓；同链外层 Git 操作仍分别检查

#### Scenario: Staging crosses an interpreter boundary
- **WHEN** 独立的 shell 包装器只执行 `git add`，之后外层或另一个包装器才提交
- **THEN** 无法证明完整拟暂存计划时报告 Git 意图 UNVERIFIED 并阻断；若 add 仅发生于纯 push 之后且无后续提交，不扩张该 push 的检查面

#### Scenario: Unmodelled indirect Git operation cannot borrow another repository
- **WHEN** 非 Shell 解释器脚本静态命中 Git 副作用，但无法可靠推断其执行目录与暂存动作
- **THEN** 返回 Git 意图 UNVERIFIED，不以调用者的其它仓库或兜底子仓的结果替代

#### Scenario: An explicit Git target is not a repository
- **WHEN** 命令从 Git 仓调用，但在 `cd` 到非 Git 目录后运行 `git push`，或使用无效的 `git -C` 目标
- **THEN** 门禁以明确诊断阻断，而不是检查调用者仓或用 workspace 兜底；后续显式 `git -C` 指向有效仓时仍能正确绑定该仓

#### Scenario: Explicit invocation directory binds staging intent
- **WHEN** 应用服务收到的调用目录与门禁进程当前目录不同，命令在调用目录中 `git add` 并提交
- **THEN** 拟暂存路径按传入调用目录的仓与文件解析，不遗漏额外路径，也不纳入进程目录的仓

#### Scenario: Exclusion and literal pathspecs remain exact
- **WHEN** git add 指定包含与排除 pathspec，或字面文件名包含星号
- **THEN** 快照只覆盖 Git 实际匹配的文件，排除项及同名 glob 邻居不会被额外暂存

#### Scenario: Add after the final commit is not retroactive
- **WHEN** 同仓静态命令链先提交已暂存的安全文件，再 `git add .env`，可选地随后执行 push，但没有第二次 commit
- **THEN** 门禁仍检查已提交内容和待推送 HEAD，不把之后才 add 的 `.env` 算进先前提交；真实 index 不被观察过程改写

#### Scenario: Add between commits remains guarded
- **WHEN** 同仓静态命令链先提交安全文件，再 `git add .env` 并进行第二次 commit
- **THEN** 门禁将 `.env` 纳入第二次拟提交内容并阻断整条工具调用

#### Scenario: Another repository's later commit does not extend the cutoff
- **WHEN** A 仓先 commit 后 add 敏感文件，命令链随后在 B 仓 commit
- **THEN** A 仓后置 add 不因 B 仓较晚的 commit 被倒算入 A 的提交；两仓的预测 index 均不被改写

#### Scenario: Command substitution stages before its outer commit
- **WHEN** 外层 `git commit -m "safe $(git add .env)"` 或反引号等价形式触发内层暂存
- **THEN** 不按展开文本顺序将内层 add 裁成“提交后操作”；门禁仍将 `.env` 纳入拟提交面并阻断，index 不被观察过程改写

#### Scenario: Fallback uses its selected child repository
- **WHEN** 调用目录为非 Git workspace，兜底发现一个暂存违规的子仓及一个无提交面的子仓
- **THEN** 暂存观察绑定前者的合成仓根，继续阻断其真实违规，且不连坐后者

### Requirement: Dockerfile checks SHALL preserve scope and incomplete evidence

hadolint 与 Trivy config 的报告解析 MUST 与进程及 CLI 呈现分离。文本和 JSON MUST 使用同一
结构化判定。超时、启动故障、无有效报告、非零无发现和自相矛盾报告 MUST 为 UNVERIFIED，
不能用空发现替代失败。逐文件原始进程结果 MUST 保留，后续工具失败不得删除已有发现。
沿用 Dockerfile 双工具完整性策略：任一工具未验证时整体 exit 1，已确认风险仍逐项可见；
两工具均有效且有风险 exit 2，均无风险 exit 0。JSON 保留原 hadolint/trivy 字段并增加总判定。
显式文件 MUST 只检查该文件，不扫描父目录；不存在的输入和无 Dockerfile MUST 返回可解析
JSON 未验证。目录发现不得因根部文件数达到内部阈值而静默漏掉子目录。

#### Scenario: A scan produces no usable report
- **WHEN** hadolint 超时或 Trivy 输出非 JSON，即使没有可显示发现
- **THEN** 两种 CLI 输出均返回 UNVERIFIED，而非 PASS 或漏洞 FAIL

#### Scenario: One tool fails after another reports a risk
- **WHEN** 一部分文件/工具已返回有效风险，后续工具无法运行
- **THEN** 保留既有发现与逐进程退出码，并将整体标记未完整验证

#### Scenario: Explicit file scope is preserved
- **WHEN** 输入为某个 Dockerfile，旁边还有其它 Dockerfile
- **THEN** 仅对指定文件执行两个工具，不静默扩大范围
