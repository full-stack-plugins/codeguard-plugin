# 本次设计交付验证

## 2026-09-26 `lint go` 原生局部 CLI

相邻 Rust CLI 已接入 `codeguard lint go`，从显式 Go 1.23.4 二进制执行版本探测及 `go vet -json ./...`，把原生规则、相对路径、行列与诊断文本摘要送入 human/JSON 反馈。运行前后复核工具、`go.mod`、可选 `go.sum` 和发现的 Go 源文件；继承环境被清空，Go 工具链/模块网络下载关闭，缓存位于私有临时目录。无工具或无关二进制不产生干净结果，真实违规、干净和编译错误分别有独立反馈，所有结果仍退出 3、交付未评估。反馈 schema 和真实验收范围见 `codeguard-cli/tests/acceptance/go-vet-json-local-probe.md`。任务同步、完整项目/平台覆盖、可信工具与策略，以及注释原生工具尚缺，8.2 未完成。

## 2026-09-26 Go vet JSON 原生局部解析

相邻 Rust `codeguard-adapters` 新增 Go 1.23.4 `go vet -json` 的局部报告解析；本机原生违规、干净、编译失败三样本分别得到 `FindingsObservedUnverified`、`CleanObservedUnverified`、`Incomplete`。JSON 模式中违规样本退出 0、诊断位于 stderr，排除了“退出 0 即无违规”的错误适配。真实测试首次因 macOS `/var`/`/private/var` 路径别名失败，修复根路径归属后通过。坏版本/JSON/包/位置/多包坏块均不生成部分 finding。CLI 调用、Staticcheck 注释、完整覆盖和工具锁尚缺，8.2 继续未完成。详细证据见 `codeguard-cli/tests/acceptance/go-vet-json-local-probe.md`。

验证：`cargo test -p codeguard-adapters --test go_vet_contract --offline` 为 5 通过、1 显式原生用例跳过；`CODEGUARD_GO_TOOL=/usr/local/go/bin/go cargo test -p codeguard-adapters --test go_vet_contract --offline -- --ignored` 为 1 通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。默认工作区回归跳过其余需要显式原生工具的用例。

## 2026-09-26 Go 六类别候选档案

相邻 Rust `rulepacks/go_static_candidate_v1.json` 固化 Go Modules 的 lint/comments/dependencies/cve/security/build 六个适用类别、候选原生工具与版本、五个待验收平台及每类覆盖缺口；Rust 解析器拒绝缺项、重复、虚报 implemented/not_applicable、错类别工具、`gofmt` 冒充注释检测和 CVE 漏数据库新鲜度要求。旧注册表的 Go `stable` 仅保留为迁移元数据，新能力矩阵仍全为 `gap`。这完成 OpenSpec 8.1 的候选/缺口账本，不证明 8.2/8.3 的真实检查能力。依据见 `codeguard-cli/tests/acceptance/go-candidate-baseline.md`。

TDD：新增契约测试先因缺档案/接口失败，补齐后通过；错类别工具反例再次先失败后修正。`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、`openspec validate introduce-rust-codeguard-cli --strict` 和插件 `git diff --check` 均退出 0；显式原生测试仍按原设置跳过。

## 2026-09-25 Maven Javadoc 多文件原生 CLI 探针

相邻 Rust `check java`/`check all` 对已静态配置的 Maven 构建根增加独立多文件 Javadoc 探针：有界源码快照、新私有项目、固定 POM、离线 Maven/JDK 21、原生输出解析与输入/制品复核。真实两文件违规样本产生多条缺注释诊断；源码修正后重新建快照得到 `clean_log_unverified`。两轮均退出 3、交付未评估；固定探针 POM 与项目生效配置/完整类路径不等价，6.3 保持未完成。首次原生失败说明离线仓库中的 Maven 镜像 ID 必须由匹配的 settings 提供；改用现有隔离 settings 后原生用例通过。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0；默认工作区测试跳过显式真实 Maven 用例，该用例另行通过。证据见相邻 `codeguard-cli/tests/acceptance/maven-javadoc-multifile-probe.md`。

## 2026-09-25 源码快照目录替换反例

相邻 Rust runtime 的 `SourceSnapshot` 在 Unix 上改为固定根目录描述符、逐级 `openat`/`O_NOFOLLOW` 读取及复核。测试将子目录反复在真实目录和指向范围外文件的符号链接之间切换，1,000 次捕获只能得到根内预期字节或错误；目标 `source_snapshot_contract` 4 项、`java_javadoc_cli` 普通 4 项和显式 JDK 21 的 1 项均通过。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt 与 OpenSpec strict 均退出 0。仍须区分该输入读取保护与项目级 Maven 执行沙箱：副本写入、插件副作用及完整源集尚未证明，3.7/6.3 不勾选。

## 2026-09-25 Javadoc 输入快照执行边界

项目级 Maven Javadoc 仍不能直接交给当前工作树执行：实际 POM 可能触发额外插件和生成源码，而现有单文件探针没有完整项目配置归属。相邻 Rust runtime 增加有界 `SourceSnapshot`，并接入 JDK Javadoc 单文件入口。相对路径逃逸、重复、预算超限、符号链接文件/父目录、原件或私有副本改变均有负例；快照不宣称源集完整或内核级抵御恶意并发目录替换。`source_snapshot_contract` 3 项、`java_javadoc_cli` 普通 4 项及显式真实 JDK 21 1 项通过；`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0。完整项目级 Maven 运行和 3.7/6.3 验收仍未完成。

## 2026-09-25 Maven Javadoc 干净日志与旧产物反例

本机 Maven 3.9.16/JDK 21/离线 Javadoc Plugin 3.12.0 的完整注释项目，首轮和同目录重跑都成功且没有 Javadoc 诊断块；日志本身不能证明第二轮重新生成了文档。相邻 Rust 解析器新增 `CleanLogUnverified`，只允许已观察的编码提示，保留零诊断但明确 `javadoc_fresh_execution_unverified`；未知警告、额外错误与失败结果仍为 `Incomplete`。这一状态不是项目检查通过，也不能关闭修复任务。独立快照执行器、产物归属和生效配置证明仍缺，6.3 不勾选。

验证：`maven_javadoc_output_contract` 普通 5 项及显式真实 Maven 2 项通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。默认工作区测试仍跳过需要显式本机原生工具的用例；项目执行器尚未实现。

## 2026-09-25 Maven Javadoc 原生输出双路径

在独立临时 Maven 项目上，本机 Maven 3.9.16/JDK 21/离线 Javadoc Plugin 3.12.0 的原生执行证明：`failOnWarnings=false` 时 `BUILD SUCCESS` 仍有缺注释警告；`true` 时 `BUILD FAILURE` 和同一诊断。相邻 Rust adapters 新增有界解析器，只有单一 goal、已知插件版本、完整警告数量、源码字节与规则归属及可信失败签名同时匹配才保留局部诊断；其它结果为 `Incomplete`、不生成部分 finding。首次真实测试发现同目录第二次执行可能复用 `target/site/apidocs`，改为每轮独立项目副本后两种原生路径均通过。这是项目级执行器需要隔离快照的验收前提，并非执行器已实现。

验证：解析器目标测试 3 通过、1 个显式原生测试默认跳过；显式设置 Maven/JDK 路径后真实原生测试 1 通过；`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、`cargo test --workspace --offline -q`、`openspec validate introduce-rust-codeguard-cli --strict` 与 `git diff --check` 均退出 0。默认完整测试仍跳过需显式环境的原生用例。6.3 保持未完成。

## 2026-09-25 `check java` Javadoc 局部原生反馈

相邻 Rust CLI 的 `check java`/`check all` 新增条件调度的 `java.javadoc` 任务：仅静态配置确认为 `configured` 才调用 JDK 21 原生单文件探针，并在 JSON/human 显示缺注释位置与规则。无 Javadoc 配置时不调度，也不把缺失检查器自动升级为必需义务；配置无效/未知仍由 discovery 给出原因。检查反馈协议增量为 0.9.0，Javadoc 结果固定 `project_checker_attribution=unverified`、`coverage_proven=false`、`delivery_decision=not_evaluated`，不进入任务同步、白名单生效或门禁。

验收：目标集成测试先因 `native_results.java_javadoc` 缺失失败，接线后通过；显式本机 JDK 21 的真实最小 Maven 项目用例通过 1 项，返回 `JavadocMissingComment`。把调度条件收紧为“仅已配置”后，相关 `check_all_java_p3c` 为 15 通过/4 显式原生跳过，`check_all_partial_contract` 为 13 通过/1 跳过，真实 JDK 用例再次通过；最终 `cargo test --workspace --offline -q` 退出 0。Clippy、格式检查及 OpenSpec 严格校验也退出 0。项目 Maven Javadoc 插件生命周期、effective model/类路径、Checkstyle、生成源码和完整源集未验收，6.3 保持未完成。

## 2026-09-25 Javadoc 配置误报反例

相邻 Rust Maven 静态探测修正了“声明 Javadoc 插件即认为缺失注释规则可用”的误判：`doclint=none`、`all,-missing`、仅 `syntax`、`failOnError=false` 及未被插件配置覆盖的 `maven.javadoc.skip=true` 均不再返回 `configured`；动态 doclint 返回 `unknown`。`check java` 的 discovery 同轮反馈 `invalid/javadoc_missing_check_disabled`，仍未把这项配置观察当成项目原生执行或门禁通过。

TDD 证据：新增 `detect_cli` 反例先失败（既有输出错误地为 `configured`），实现后目标用例通过。`cargo test -p codeguard-cli --test detect_cli --offline -q` 为 19 通过；`cargo test -p codeguard-cli --test check_all_java_p3c --offline -q` 为 14 通过、3 个显式原生用例跳过；`cargo clippy --workspace --all-targets --offline -- -D warnings` 与 `cargo fmt --all --check` 退出 0。该切片未运行完整 workspace 回归，也未证明 Maven effective model、跨父 POM 属性覆盖或项目级 Javadoc 执行，5.10/6.3 继续未完成。

## 2026-09-25 JDK Javadoc 单文件原生诊断切片

相邻 Rust CLI 新增 `lint java FILE --checker javadoc --java-home ABS_PATH`；JDK 21 `-Xdoclint:missing` 的已知缺失注释、参数和返回诊断可映射到原源码。未知文本、缺少类路径、进程失败或缺失原生产物保持未完成；无诊断只标为 `clean_scope_unproven`，一律退出 3、不签发项目通过。`lint java` 缺省 P3C 行为仍保留。本单文件切片当时尚未接入 `check java`；项目生效配置、任务、白名单生效门禁及 Checkstyle、完整项目级验收仍未完成。

验证：`cargo test --workspace --offline -q` 退出 0；`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、`openspec validate introduce-rust-codeguard-cli --strict` 均退出 0。显式本机 JDK 21 的 `CODEGUARD_JAVA_HOME=... cargo test -p codeguard-cli --test java_javadoc_cli --offline -- --ignored` 通过 1 个真实原生测试，覆盖缺类注释、参数/返回、`{@inheritDoc}`、record 与 Lombok 类路径缺失。默认工作区测试跳过显式原生工具用例；P3C 局部回归 6 通过、2 跳过。P3C 报告 schema 的规则集下限对齐固定原生计划的 10 组。

日期：2026-09-24。性质：架构与规格文档验证，**不是 Rust 实现、真实扫描器或发布验收**。

本文件保留设计阶段的历史快照；文内“未建立 Rust 源码仓”“267 项未勾选”等数字描述的是当时状态。随后启动的实施以 [tasks.md](tasks.md) 为唯一勾选状态，独立 Rust 工程证据记录在相邻 `codeguard-cli/tests/acceptance/`，最新旧源码增量见 [核对记录](../../../docs/rust-cli/legacy-delta-20260924.zh-CN.md)。

## 交付范围

- [设计文档入口](../../../docs/rust-cli/README.md)：架构、技术方案、57 项语言迁移与验收、项目内持久修复工作流、项目初始化与 AGENTS 接入、逐指令架构。
- 本 change 的 proposal、design、11 个 capability delta 和可执行 tasks。
- 持久工作区使用 `./codeguard/`，含自有 .gitignore；以问题、阻塞、任务和复检事件指导修复，规则和最终门禁不由任务文件决定。

## 实际检查

`openspec validate introduce-rust-codeguard-cli --strict --json --no-interactive` 已通过，无 issue。最初的校验发现 MODIFIED scenario 标题未保留，已恢复原 scenario 名称并显式限定旧协议范围，再次校验通过；未删除旧场景来绕过验证。

初始设计交付使用只读脚本核对 Markdown 本地链接、代码围栏、JSON 示例、语言 ID/状态、重复任务编号、proposal/spec 目录和规范任务追踪，最终退出 0、issues=[]。初始范围为 19 份 Markdown、40 个本地链接、57 个语言条目、10 个 capability、43 条 requirement、89 个 scenario、228 项未勾选实现任务。Mermaid 有 9 个代码块，已检查围栏与人工语法，未执行渲染器视觉验收。

`git diff --check` 与 `git diff --cached --check` 在本次文档路径范围均通过。任务初次语言 ID 机器核对发现三项仅写了大小写不同的展示名，已补充 canonical ID 并复核 57 项全部可追踪。

OpenSpec 的 planning artifacts 为 complete 只说明 proposal/design/specs/tasks 已齐备，不意味着实施完成。实现任务全部未勾选；不得据 status 的 isComplete 字段声称二进制可用。

## 初始化设计增量复核

同日补充 init 的项目画像、分类型模块图、AGENTS 受管摘要、静态观察与写入边界、画像刷新和准备状态。沿用同一 change，未建立第二套规格事实源。

增量完成后重新执行 OpenSpec 严格校验，通过且无 issue。文档核对范围为 21 份 Markdown、48 个本地链接、11 个 capability、50 条 requirement、104 个 scenario、240 项未勾选任务；本地链接、代码围栏、JSON 示例、任务编号连续性/唯一性、proposal/spec 目录及能力任务追踪均通过。Mermaid 共 11 个代码块，未执行渲染器视觉验收。`git diff --check` 通过。

独立读者复核促成两项补充：dry-run 仅返回拟创建的任务，apply 才持久化；readiness 只按适用必需前置条件汇总，区分已确认阻塞、未探测和已就绪，避免可选工具缺失误阻塞。init 成功与质量通过继续保持独立。

## 逐指令架构增量复核

同日新增 [逐指令架构](../../../docs/rust-cli/command-architecture.zh-CN.md)，覆盖 C01–C35 的职责/价值、输入输出、副作用、失败恢复、应用服务与调用旅程。细化统一操作协议、准备证据、工具安装、交付输入、执行预算和任务租约/attempt接入，并同步既有规格和任务。

最终 OpenSpec 严格校验与文档静态核对通过：22份 Markdown、57个本地链接、14个Mermaid代码块、11个capability、57条requirement、122个scenario、248项未勾选任务；C01–C35目录与独立章节一一对应，F01–F26场景编号连续。核对覆盖本地链接、代码围栏、JSON示例、任务编号、proposal/spec一致性及能力任务追踪；`git diff --check`通过。Mermaid未执行渲染器视觉验收。

独立读者指出并完成修订：fix缺少已领取任务的租约传参、doctor准备证据缺少明确导入身份、执行预算缺少默认和总deadline；二轮复核进一步区分已初始化批量fix与未初始化私有证据路径。另明确已落盘finish的幂等读取不受后续租约到期影响，不能重新写入新租约状态。

以上只验证设计产物；未构建或运行35项新命令、MCP服务、安装器、租约或真实检查器，未初始化被检查项目。预算默认值仍需实施阶段按真实项目验证，不作为已测性能承诺。

## 实施前规范与计划覆盖审计

同日按用户要求核对全部已确认设计是否落入规范与任务，新增 [实施覆盖索引](implementation-coverage.md)，逐条连接Requirement、命令、语言、平台/宿主及任务，并补充执行里程碑、责任边界与待定参数的关闭任务。索引不维护第二份实施状态。

本轮补齐5条正式Requirement、17个Scenario、19项任务，并强化既有9.4/9.10/9.27的故障验收。具体包括detect/capabilities查询处理、事件/游标中断恢复、过期租约接管、环境任务原义务复检、关联追踪、证据保留、分层评测以及逐平台/宿主验收。独立读者复核5项命令缺口均闭合，执行顺序未见明确循环；评测依赖拆为12.2冻结输入→12.10计算器→12.11真实评测。

当前审计范围为23份Markdown、126个本地链接、15个Mermaid代码块、11项capability、62条Requirement、139个Scenario、267项未勾选任务。机器核对证明每个Requirement恰有一条索引映射、全部267项任务均有规格关联（未映射为0）；35项命令与设计章节一致，57个语言与当前注册表集合及stable/planned状态一致，5个平台和3个宿主均有有效任务引用。Markdown围栏、JSON示例、本地链接、任务编号、proposal/spec及阶段追踪检查通过。

`openspec validate introduce-rust-codeguard-cli --strict --json --no-interactive`通过且无issue；`git diff --check`通过。Mermaid未运行视觉渲染。此结论限定于当前已确认设计的拆分与追踪；P3C兼容版本、平台ABI、签名身份、语料和性能等待实测参数已绑定任务，不声称已确定。代码实现、原生工具、平台/宿主运行及发布仍全部未完成；未运行apply/sync/archive。

## 初始设计独立读者检查

两轮只读审查识别并修订以下六项：

1. 例外同时绑定范围、内容身份和到期时间，不允许无期限例外。
2. 离线执行必须具备可验证的网络隔离条件，不能只转发参数。
3. 可信 CI 验证端与被测脚本执行区隔离，防止项目脚本篡改策略或签发结果。
4. work sync 幂等消费全部匹配未导入报告，不只取最后一次检查。
5. 已启用插件工作流必须经过 scan→sync→RepairBrief；存储失败可见。
6. attempt 开始/结束记录复检前失败和无修改尝试，避免预算失效。

语言任务已细分到具体 language ID；每种语言均有适用性、lint/comments、CVE/security/build 与真实工具验收要求，不用大组汇总掩盖缺项。

## 当前证据边界

源码观察基线为 `03ebb24`，读到的注册表为 54 stable/3 planned。工作过程中存在其他任务切换分支、暂存 release/manifest 文件；本次不创建或切换分支、不修改这些发布文件、不代替其他任务提交。文档最终实现基线须在实施开始时再次核对。

没有建立 Rust 源码仓、编译或执行新 CLI，没有安装工具、测量实际误报率、发布制品、同步市场或验收宿主；没有运行 openspec apply/sync/archive。既有代码全量测试不用于证明本次文档设计已运行。后续实现与发布证据按 tasks 逐项记录。

## 2026-09-24 静态检测族增量

用户明确补充 Javadoc、CVE、依赖检测及其他静态检测。现有 change 增加六类别/28 检测族契约、`dependencies` 命令 C36、逐族义务与真实工具验收任务；相关设计见 [静态检测目录](../../../docs/rust-cli/static-check-catalog.zh-CN.md)。相邻 Rust 工作区的能力矩阵协议从 `0.1.0` 升到 `0.2.0`，57×5×6 共 1710 个能力单元继续全部为 `gap`；计划协议 `1.1` 要求检测族，解析器仍兼容只读 `1.0` 计划。新增 schema/解析器一致性与类别错配反例。

验证：`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、能力矩阵生成器 `--check`、`openspec validate introduce-rust-codeguard-cli --strict` 和 `git diff --check` 均通过。原生 Javadoc、依赖治理、CVE 及其余检测族尚无执行适配器和误报率验收，不能由分类、schema 或通过的单元测试推断为已支持。

## 2026-09-24 配置探测与智能体反馈纠偏

按用户最新说明，上节“逐族义务”不再表示每个项目必须逐项证明执行。28 个检测族改为候选目录；目标流程是“识别项目是否配置检查器 → Rust 调用已配置的原生工具 → 将结果和修复/配置建议送到智能体对话”。`missing/invalid/unknown` 与代码诊断、工具故障分开表达；只有批准策略要求的缺项影响交付门禁。新增对话反馈 Requirement 和 11.16 实施任务。相邻 Rust RunReport 协议升级到 1.1，新增 `checker_statuses` 并校验“未配置不能声称运行结果”，1.0 报告兼容读取；2.2 在协议测试通过后重新勾选，项目配置探测与宿主对话接线仍未完成。

同日继续实施 5.10 的 Maven 切片：Rust `detect` 的 `0.2.0` 报告现在按构建根返回检查器配置状态，`codeguard-adapters` 纯解析 POM，CLI 只做只读观察和 human/JSON 展示。直接声明的 Javadoc/PMD/Checkstyle/Dependency/Dependency-Check/FindSecBugs、未声明、pluginManagement、父 POM、坏 XML/DTD 和 Gradle 未解析模型均有集成样本；详情见相邻 `codeguard-cli/tests/acceptance/maven-config-discovery.md`。配置发现不执行检查器，也不代表能力矩阵可从 gap 升级。其他生态与真实对话宿主仍为未完成。

补充误判边界：Maven 插件显式 `skip=true` 返回 `invalid`，动态 skip 值或动态插件坐标返回 `unknown`，均不标记为 `configured`。`detect_cli` 集成测试 9 项通过；随后 `cargo fmt --all --check`、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、OpenSpec 严格校验及 `git diff --check` 全部通过。默认忽略的原生 P3C 回放未在本轮重跑，且这些检查不构成 5.10 全生态完成或 11.16 宿主对话验收。

再次核对用户的“配置发现与对话反馈”要求后，统一命令与覆盖规格明确：实际义务来自项目已配置且可适配的检查器及批准策略，不来自 28 个候选检测族目录；未配置且非必需的 Javadoc 样本只给建议，明确必需但未配置才导致 incomplete。另将 POM 读取失败与 XML 错误区分：前者 `unknown/pom_unreadable` 且发现操作不完整，后者 `invalid/pom_invalid_xml`。本次有界观察端口回归覆盖了读取失败；修改后重新执行完整 workspace 测试、Clippy、格式检查、OpenSpec 严格校验与 `git diff --check`，均退出 0。默认忽略的原生回放仍不计入本轮验收。

实际运行 `cargo run --offline -q --bin codeguard -- detect tests/fixtures/p3c_native --format human` 退出 0，终端反馈 PMD `configured` 与 Checkstyle、Javadoc、Dependency、Dependency-Check、FindSecBugs 的 `missing` 和逐项下一步。这证明当前 CLI 能把**配置探测**渲染给调用它的智能体；原生检查结果尚无完整 `check` 命令，Codex/ZCode/Kimi Hook 对话接线未验收，不能将终端输出冒充 11.16 完成。

## 2026-09-24 运行结果对话摘要切片

相邻 Rust CLI 增加 `conversation_feedback`：从结构已校验的 RunReport 生成宿主可消费的 JSON/human 摘要，区分配置状态、运行状态、有效规则 ID、未完成义务和复检 argv，输出显式标记“来源尚未绑定”。自由文本原生诊断、summary 和 next_actions 不进入反馈；注入和凭据样本断言两个格式均无泄漏。RunReport 升级到 1.2，finding 要求源码/依赖/项目定位并校验相对路径和一基行列；检查器状态按构建根区分，旧 1.0/1.1 报告继续可读取。目标报告测试 14 项通过，反馈 JSON schema 与生成物顶层字段一致；详情见 `codeguard-cli/tests/acceptance/conversation-feedback-baseline.md`。这还不能代替来源校验、真实检查报告、规则公开解释或三宿主现场验收；11.16 保持未完成。

此切片完成后复跑 `cargo fmt --all --check`、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`openspec validate introduce-rust-codeguard-cli --strict` 与 `git diff --check`，均退出 0。默认忽略的原生 P3C 和依赖外部环境的回放未作为本轮通过证据。

## 2026-09-24 Ruff 项目配置与原生规则切片

沿 Python 文件目录层级只读探测 Ruff 配置，依官方优先级区分 `.ruff.toml`、`ruff.toml`、含 `[tool.ruff]` 的 `pyproject.toml`，用 Rust TOML 解析器区分明确 lint、仅格式化、坏配置与未解析 extend。既有单文件 Ruff probe 新增可选的项目配置绑定；绑定时禁止沿用忽略配置的 `--isolated`，执行前后校验配置摘要，并通过原生 `--show-files` 核对目标确实被选中。未绑定模式仍只作隔离基线。

`detect_cli` 12 项通过；`ruff_probe_contract` 默认 4 项通过、5 项需 Ruff 的真实测试在 `/opt/anaconda3/bin/ruff` 0.16.8 上通过。原生 E501 样本证明非默认项目规则加载，被 `force-exclude` 排除的文件明确未完成；具体命令与边界见相邻 `codeguard-cli/tests/acceptance/ruff-config-discovery.md`。这不等于项目全量 Python lint、正式 `check` 或三宿主对话接线，5.10/7.2/11.16 均保持未完成。

随后 `cargo fmt --all --check`、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings` 均退出 0；真实 Ruff 5 项在最终代码状态复跑也通过。新增 TOML 解析依赖的 crate 边界白名单已同步，仅允许 adapter 使用；初次全量测试发现旧发现测试按全局总数断言 Maven 六项、以及白名单未包含 TOML，均按新范围修正后复跑通过。OpenSpec 严格校验与插件 `git diff --check` 通过。原生 P3C 等其他忽略测试本轮未运行。

## 2026-09-24 Python 项目扫描与对话数据切片

相邻 Rust CLI 的库服务现按 Python 文件匹配已发现的 Ruff 项目配置，逐文件调用原生 Ruff 并保留诊断与未完成原因。发现器不再把 `.venv` 等点目录当普通源码，但仍读取 `.ruff.toml`；`python_lint_feedback` 将配置、规则 ID、行列、运行状态、修复建议和复检 argv 输出为可展示 JSON，原始原生消息不进入反馈，交付判定固定为 `not_evaluated`。无需为每个候选检测族额外生成执行证明。见相邻 `codeguard-cli/tests/acceptance/python-lint-scan.md`。

`python_lint_scan_contract` 默认 3 项通过、2 项忽略；在 `/opt/anaconda3/bin/ruff` 0.16.8 上真实 2 项通过，覆盖配置规则发现与排除文件不假通过。`detect_cli` 13 项通过。该切片验证时，`cargo fmt --all --check`、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`openspec validate introduce-rust-codeguard-cli --strict`、插件 `git diff --check` 均退出 0。当时尚无公开项目 `lint python` 命令；后续入口见下一节。完整 Python 六类适配、已批准策略门禁及 Codex/ZCode/Kimi 宿主接线仍未完成，5.10/7.2/11.16 仍不勾选。

## 2026-09-24 公开 Python lint 入口

相邻 Rust CLI 现提供 `codeguard lint python [path] [--ruff-tool ABS_PATH] [--format human|json]` 的局部原生入口。先探测项目配置，未配置时不启动 Ruff；已配置时查找可执行文件、通过受控 runtime 读取原生版本，再逐文件调用 Ruff。JSON/human 都反馈配置、运行状态、有效规则和位置、修复建议与复检信息。工具来源尚未获批准，完整 Python 六类别与项目政策门禁未完成，因此 `tool_approval=unverified`、`delivery_decision=not_evaluated`，命令固定退出 3；它不签发局部或项目质量通过。

新 `lint_python_cli` 默认 5 项通过、2 项需 Ruff 的真实测试在 `/opt/anaconda3/bin/ruff` 0.16.8 上通过，覆盖缺配置不调用、缺工具、错误程序、human 输出、显式路径与 PATH 自动发现的原生 F401 到 CLI JSON。最终 `cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings` 退出 0；`cargo fmt --all` 已执行，OpenSpec 严格校验和插件 `git diff --check` 通过。三宿主自动对话接线、可信工具锁和完整策略未实现，7.2/11.16 不勾选。

## 2026-09-24 Ruff 报告归属与多配置回归

相邻 Rust CLI 新增真实嵌套配置样本：根目录 E501、子目录 F401 均仅由自身生效 Ruff 配置产生，`python_lint_scan_contract` 的真实工具样本增至 3 项通过。另用受控假 Ruff 返回混合 JSON，证实旧 `ruff_probe` 会把别的文件诊断误归到当前源文件；修复后先将报告路径解析回本次源，再过滤异源诊断。同文件有效发现仍保留，整次标记 `report_source_mismatch`/未完成，不把异源发现展示为当前文件的问题。目标反例先失败后通过，原生 Ruff 5 项回归通过。该修复只覆盖本次文件归属，工具批准、策略、全项目覆盖与宿主接线仍缺。

最终 `cargo fmt --all --check`、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings` 退出 0；真实 Ruff 的 CLI 2 项、单文件探测 5 项、项目扫描 3 项分别通过；`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 退出 0。未运行的其它外部工具测试不计入本次验收。

## 2026-09-24 误报白名单规格补充

新增精确误报白名单设计，并将匹配、可信审批、失效重审、任务归因、带例外交付决策及协议升级写入 rulepack-governance、verdict-integrity、unified-cli-contract、remediation-workflow，映射到 S02/S04/S09/S12 的未完成任务。此轮只验证文档和规格一致性；Rust 1.2 报告、CLI 命令、白名单匹配器与宿主门禁尚未实现本设计，不能声称白名单已经生效。

`openspec validate introduce-rust-codeguard-cli --strict` 与 `git diff --check` 均退出 0。本次未改 Rust 源码，因此未把既有 Rust 测试作为白名单实现证据。

## 2026-09-24 误报白名单精确身份匹配切片

相邻 Rust Core 新增精确身份模型与纯比较函数：源码路径/内容，或依赖组件/版本/图/advisory，连同 finding、原生规则、工具、适配器和 rulepack 身份必须完全一致；通配、越界与缺摘要失败。目标契约测试先因接口缺失失败，随后 5 项通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check` 均退出 0。详见 `codeguard-cli/tests/acceptance/false-positive-identity-baseline.md`。此函数不验证批准，不能改变 gate；OpenSpec 4.8 及后续协议/宿主/验收任务仍未完成。

该切片随后补充版本化候选 schema 与 Rust 严格解析器：6 个目标契约测试先因接口/schema 缺失失败，随后通过；补充未知检查类别反例也先失败后通过。全工作区测试、Clippy、`cargo fmt --all --check`、OpenSpec 严格校验与插件 `git diff --check` 均通过。`approved=true`、坏身份、无期限、错 kind/版本和缺复现/批准引用均不能形成合法候选。解析成功仍不验证批准来源或到期时钟，不能接入放行门禁；4.8 仍保持未完成。

继续实现候选集合纯筛选：四个目标测试先因接口缺失失败，后共 10 项通过；同一精确身份的两条候选即使其中一条已过期仍报冲突，缺上下文、策略修订不符、未来生效、到期和超过政策期限上限均拒绝进入权威核验。`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、OpenSpec 严格校验与插件 `git diff --check` 均通过。返回的 `ReadyForAuthorityCheck` 不是批准；可信策略/时钟来源、批准凭据、同 PR 自批与门禁接线仍缺，4.8 不勾选。

## 2026-09-24 RunReport 1.3 误报处置消费协议

新增 RunReport 1.3 的原始/已处置/活跃阻断集合与 `allow_with_exceptions` 结构消费，conversation feedback 0.2 对话摘要显示批准引用和到期时间并注明来源未核验；局部检查、另一真实阻断、另一未完成义务、错策略修订、重复处置、坏引用及未完成的原检查均有反例。7 项目标测试先因字段缺失失败，随后通过；旧报告 14 项回归及全工作区测试、Clippy、fmt 均通过。详见相邻 `codeguard-cli/tests/acceptance/run-report-allowlist-protocol.md`。这尚不是可信报告生产或全格式宿主门禁，2.10/12.12 保持未完成。

## 2026-09-25 批准快照字节绑定切片

相邻 Rust CLI 增加 `approval-snapshot:1.0` 严格协议与纯比较器。候选须存在于快照的 ID/原始字节摘要集合，快照须与外部预期摘要一致，并与传入的原生发现身份精确匹配；候选更改批准文字、同次新增、快照篡改、重复条目、未知字段、不同原生发现、缺时钟和到期均有拒绝测试。目标测试先因模块不存在失败，随后 7 项通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、OpenSpec 严格校验及插件 `git diff --check` 均退出 0。`BoundToPinnedSnapshot` 只证明输入间绑定：外部摘要可能由项目自行计算，调用方传入的 finding/时钟来源也尚未核验，所以不签发批准或交付放行。4.5/4.8/12.12 仍未完成。

## 2026-09-25 分层质量评测纯计算切片

相邻 Rust Core 新增 `evaluate_quality`，按 cohort/语言/类别/适配器分层统计 TP/FP/FN、precision/recall 和双侧 95% Wilson 区间。零发现不可估计，争议/未裁定、覆盖差异、未完成和工具故障误判单列；真问题漏报与假通过失败，任一分层未达或证据不足不由其它层平均覆盖。目标测试先因模块缺失失败，扩展后 8 项通过。详见 `codeguard-cli/tests/acceptance/quality-evaluation-baseline.md`。正式 12.2 冻结配置和 12.11 真实回放尚无证据；12.10 仍不勾选。

## 2026-09-25 点前缀范围汇总切片

相邻 Rust `detect` 的 DiscoveryReport 升级为 0.3.0，普通发现点前缀排除根和配置例外文件在 `scope_summary` 中按总数显示，不输出普通排除路径的逐文件报告；入库安全明确 `not_evaluated`。`.hidden.py`、`.hidden_dir`、`.env` 及两项配置例外的目标测试先因旧协议失败，随后 `detect_cli` 14 项通过。详见 `codeguard-cli/tests/acceptance/dot-prefix-scope-baseline.md`。这不是 F18 全部验收：Git 安全例外和完整检查范围仍缺，4.6 不勾选。

## 2026-09-25 Git index 路径安全预览

相邻 Rust Core 实现旧插件入库路径政策的纯判定；Rust CLI 通过受控 Git 原生命令按 NUL 协议读取真实 index，校验记录、对象格式、阶段、OID 和前后列表，并尊重替代 `GIT_INDEX_FILE`。公开 `codeguard gate pre-commit` 只报告拟提交路径违规，固定 3/incomplete/not_evaluated；公开预览 schema 不含 allow。纯路径测试 3 项、真实 Git/CLI 测试 9 项通过，含真实 SHA-256 仓库；目标测试先因模块缺失失败，随后通过。全工作区 `cargo test --workspace --offline -q`、Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 退出 0。见 `codeguard-cli/tests/acceptance/git-index-safety-preview.md`。Git 工具批准、对象内容、完整质量义务、真实 Hook/pre-push/CI 与宿主接线仍缺，相关任务均未勾选。

## 2026-09-25 Git index blob 字节核验增量

相邻 Rust CLI 增加受控 `git cat-file --batch-check/--batch`，独立按 Git blob framing 重算 SHA-1/SHA-256 OID，记录脱敏的内容 SHA-256、长度与类型；symlink、gitlink、LFS 指针、超出预算或读取失败保持 unresolved，且路径违规不会因对象读取失败消失。公开预览 schema 升至 0.2.0，区分 verified/unresolved/failed/not_observed，仍固定 3/incomplete/not_evaluated。真实 Git/CLI 目标测试 13 项通过，含暂存与工作树字节分离、特殊对象和超预算失败；全工作区 `cargo test --workspace --offline -q`、Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 退出 0。见 `codeguard-cli/tests/acceptance/git-index-safety-preview.md`。Git 工具批准、工作树/ref 原子快照、完整质量义务及真实 Hook/CI 仍缺，相关任务未勾选。

## 2026-09-25 白名单候选只读查询切片

相邻 Rust CLI 接入 `rules whitelist list/explain --candidate FILE`；候选文件经既有严格解析器校验，输出始终 `authority=unverified`、`gate_effect=none`，不回显自由文本依据。错误文档、重复 ID 或不存在的 explain 目标为 incomplete/退出 3；有效查询退出 0 只表示查询完成。目标测试先因命令不存在失败，随后 `whitelist_command_contract` 4 项通过；全工作区 `cargo test --workspace --offline -q`、Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 退出 0。见 `codeguard-cli/tests/acceptance/whitelist-candidate-inspection.md`。自动发现、propose、可信批准及本次原生 finding 的门禁绑定仍缺，4.9 与 12.12 未勾选。

## 2026-09-25 `init` 工作区预览与局部 apply

相邻 Rust CLI 接入 `init` 的默认只读预览和显式 `--apply`：复用静态发现，生成项目画像、仅有 contains 边的模块图及用户指定的工作区目录；受管文件预检冲突、逐项创建并记录已创建目录/文件，现有 AGENTS 人工内容不触碰。为维持重复 init 的稳定性，普通发现精确排除受管文件及记录目录，仍保留 `codeguard/src` 用户源码。目标测试先因命令缺失失败，随后 `init_command_contract` 7 项通过；全工作区 `cargo test --workspace --offline -q`、Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 退出 0。见 `codeguard-cli/tests/acceptance/init-workspace-preview.md`。该实现缺 AGENTS 受管摘要、准备任务、可信策略、画像刷新及完整来源身份，apply 固定 partial/退出3；9.1/9.2/9.15–9.25 仍未勾选。

## 2026-09-25 AGENTS 受管摘要增量

相邻 Rust CLI 在 `init --apply` 时生成根 AGENTS Codeguard 区块，链接项目画像、模块图和架构观察，仅引用已生成文件的 SHA-256 与当前可用命令，不复制项目自由文本。规划时解析成对 marker，写前再次核对 AGENTS 原字节，保留区块外人工内容/其它工具块及原权限；异常/重复 marker、人工改写、符号链接或规划后字节变化均返回冲突。为避免自身生成的 AGENTS 造成画像循环漂移，普通发现精确排除根 AGENTS；Git 入库安全入口仍独立。目标测试先因行为缺失失败，随后 `init_command_contract` 11 项与规划后修改单测通过。跨外部编辑器的强制并发锁、刷新事务、准备任务及完整检查仍缺，相关任务保持未勾选。

## 2026-09-25 画像刷新与白名单纠错边界

相邻 Rust CLI 将工作区/画像/init 计划协议升级为 0.2，记录受管投影摘要、清单和锁文件字节摘要，以及源码路径集合摘要。重新 init 可以刷新仍与旧摘要一致的投影和 AGENTS 区块；人工修改或无效工作区身份返回冲突，workspace 最后更新，findings/tasks 保留。刷新目标测试先因旧实现失败，随后 `init_command_contract` 17 项通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings` 和 `cargo fmt --all --check` 通过。OpenSpec strict 与插件 `git diff --check` 通过。9.23 的规则配置语义、完整源码关系和强制跨进程锁尚未实现，继续未勾选。

补充误报白名单的纠错分流：精确误判才走候选和独立批准；系统性规则不适用走规则包修订，真实问题走风险接受，工具/配置/覆盖问题保持 incomplete。现有 `rules whitelist list/explain` 仅检查候选结构，固定 `authority=unverified`、`gate_effect=none`；未实现可信批准及本轮 finding 的门禁绑定，不声称白名单已放行。

## 2026-09-25 规则配置刷新与版本语义增量

相邻 Rust CLI 将 Ruff/预提交配置的原始字节 SHA-256 加入项目画像；同名配置的新增、修改、删除触发受管刷新，无法有界读取时 `observation_complete=false` 且 `profile_stale=null`。`package.json` 的包版本独立存为 `package_declared_versions`，语言目标版本仍为 unknown，不据包版本选择检查规则。规则变更与包版本目标测试先因旧行为失败，随后 `init_command_contract` 20 项通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check`、OpenSpec strict 与插件 `git diff --check` 均退出 0。其它语言配置和源码关系尚未完成，9.23 不勾选。

## 2026-09-25 受管刷新恢复反例

相邻 Rust CLI 新增 AGENTS 区块外人工文本保留及“画像已更新、workspace 标记仍旧”的中断重试契约；重试可继续完成并在下一次运行保持幂等。`init_command_contract` 增至 22 项且通过。完整事务日志、外部编辑器的强制并发保护与其它语言配置仍未完成，9.21–9.23 保持未勾选。

## 2026-09-25 跨语言精确配置输入观察

相邻 Rust adapter 读取旧语言清单的 `linter_config_files` 候选字段；discover 只读取其中精确单文件名，包含受配置发现例外保护的点文件，不遍历普通点前缀源码。注册表解析拒绝通配、路径穿越、控制字符与同语言重复配置名。`checkstyle.xml`、`eslint.config.mjs` 与 `.eslintrc` 的变更均使 init 画像过期；存在配置文件不升级为“检查器已配置”。相关测试先因旧实现缺失失败，随后 `init_command_contract` 24 项、`detect_cli` 14 项及 adapter 注册表目标测试通过；全工作区 `cargo test --workspace --offline -q`、Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。嵌套点目录、未登记配置、实际规则解析和源码关系仍缺，9.23 继续未勾选。

## 2026-09-25 Python 局部修复提示与输入失效

相邻 Rust CLI 的 Python Ruff 局部反馈升为 0.2：完成的 F401/E501 提供限定文件、扫描前源码摘要、谨慎修复步骤与原工具复检条件；未知规则只给调查提示，原生自由文本不进入对话。若后续文件扫描改动先前源码或 Ruff 配置，受影响文件转为 incomplete，原诊断保留待复查且不产生可执行修复提示。模拟原生工具跨文件改动的反例通过，`python_lint_scan_contract` 5 项普通与固定 Ruff 0.16.8 的 3 项原生测试均通过；全工作区测试及 Clippy 通过。该局部提示不构成持久 RepairBrief、可信白名单或完整交付门禁；7.2、9.7、12.12 保持未完成。

## 2026-09-25 白名单候选身份纠错查询

相邻 Rust CLI 的 `rules whitelist explain` 可选择显式观察身份文件，复用核心精确匹配并报告身份相同或失配。坏观察文件、坏候选、重复 ID 和不同 ID 重复处置同一身份均不展示有效匹配；schema 0.2 固定 `authority=unverified`、`gate_effect=none`。发现身份文件是普通本地输入，并非本轮原生检查证据；匹配不能作为批准。`whitelist_command_contract` 6 项、全工作区测试与 Clippy 通过，OpenSpec strict 与 `git diff --check` 通过。可信身份来源、候选期限/审批核验、propose、config validate 和真实门禁仍缺，4.8/4.9/12.12 未勾选。

## 2026-09-25 Ruff 局部稳定发现身份

相邻 Rust CLI 对本轮完成且源码稳定的 Ruff 诊断生成行号无关的 `finding_id`/完整指纹。源码行锚点、原生规则与私有消息摘要共同区分同文件问题；跨文件、跨规则或重复同源诊断不误合并。两项身份单测与固定 Ruff 0.16.8 双轮扫描验证：前插一行后 ID 不变而文件 SHA-256 改变；无法核对定位或输入变化时不签发身份。`python_lint_feedback` 升至 0.3，仍固定局部 `not_evaluated`。持久归并、重命名匹配、环境 blocker 和复检关闭尚未实现，9.3 未勾选。

## 2026-09-25 工作区 ID 与局部报告绑定

相邻 Rust `workspace.json` 0.3/init 计划 0.3 加入稳定 `workspace_id`，刷新沿用既有身份；旧版工作区能升级且不清理 findings，损坏身份拒绝刷新。`lint python` CLI 反馈 0.4 在工作区有效时引用该 ID，未初始化、旧版未绑定和损坏状态分开报告；始终为局部 `not_evaluated`。目标 `init_command_contract` 25 项、`lint_python_cli` 6 项普通测试及固定 Ruff 0.16.8 的 2 项真实 CLI 测试通过；全 Rust 工作区测试、Clippy、fmt、OpenSpec strict、插件 diff 检查均通过。此处只完成未来 `(workspace_id, run_id, report_digest)` 导入键的前置身份，不表示 `work sync` 已实现；9.4 保持未完成。

## 2026-09-25 Ruff 报告持久同步与自动串接

相邻 Rust CLI 加入 `work sync` 初版及已初始化 `lint python` 的自动保存→同步链路。脱敏局部报告保存在 Git 忽略的 reports，按 workspace_id/run_id/原报告字节摘要核对；完整且源码仍匹配的 Ruff finding 创建首次 fact、observed event 和任务 Markdown，重复扫描只更新 Git 忽略的消费标记。写入先暂存并同步到忽略的 state 后硬链接创建目标，标记最后持久化；标记丢失重试、旧源码历史化、同 run ID 摘要冲突、坏报告与好报告并存均有反例。固定 Ruff 0.16.8 的真实两轮扫描只生成一张任务；记录目录不可用时 CLI 仍显示原生 F401 并报告 `backlog_update_failed`。任务不含原生消息，所有同步结果 `not_evaluated`/退出 3。`work_sync_contract` 4 项普通和 2 项固定 Ruff 原生测试、全 Rust 工作区测试、Clippy、fmt、OpenSpec strict 与插件 diff 检查通过。见相邻 `codeguard-cli/tests/acceptance/work-sync-ruff-baseline.md`。该切片尚无环境 blocker、跨类别 RunReport、完整事件状态机、attempt/lease、`next` 和复检门禁，相关 9.3–9.14/11.16 仍未完成。

## 2026-09-25 白名单纠错规则体系补充

在既有精确误报白名单设计上，明确了白名单只位于原生 finding 之后的处置层、单点误报与系统性规则误报的不同纠正路径，以及候选/驳回/批准/过期/撤销/失配与稳定任务的关联。OpenSpec 增加系统性误报和撤销反例，tasks 新增 4.10；白名单前原始发现与人工裁定仍纳入误报/漏报评测。本轮为设计与规格更新，未改变 Rust CLI 行为，可信批准、纠错事件流与真实门禁仍未实现。

`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。

## 2026-09-25 Ruff 环境 blocker 持久归并

相邻 Rust CLI 的 `work sync` 对 Ruff 局部 `incomplete` 文件新增稳定环境 blocker：同构建根、同原因归并多个文件，不同构建根分别建任务；每轮观察事件保留受影响路径。缺工具与缺配置的真实 CLI 反例产生环境准备任务，不伪装成源码违规或质量通过。同步预览 schema 升至 0.2，新增 blocker record/event schema；`lint python` 对话反馈的 `backlog_sync` 新增 `new_blockers`。详见相邻 `codeguard-cli/tests/acceptance/work-sync-ruff-blockers.md`。

`work_sync_contract` 7 项普通测试及固定 Ruff 0.16.8 的 2 项显式原生测试、Rust 全工作区测试、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均通过。跨语言工具链依赖、正式任务依赖图、复检关闭和完整门禁仍缺，9.3/9.6/9.7 保持未完成。

## 2026-09-25 本地只读 next 简报预览

相邻 Rust CLI 新增 `codeguard next [path] --format human|json`，从工作区 Ruff finding/blocker 事实生成结构化局部简报。未初始化提示 init；未消费报告先提示 sync；任务空但无全量认证证据时返回 verification_required。缺配置要求决策，缺工具指向环境准备；源码内容变化后不再推荐旧修复步骤。任务 Markdown 自由文本不进入简报，损坏事实和消费标记不能被解释成可交付。协议固定 `authority=local_unverified`、`delivery_decision=not_evaluated`；成功 exit 0 只表示视图完整。见相邻 `codeguard-cli/tests/acceptance/next-local-brief-preview.md`。

`next_command_contract` 6 项、Rust 全工作区测试、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均通过。完整 status/show、任务依赖/租约/attempt 预算、版本化 recipe、跨类别选择及任务关闭仍缺，9.7、9.13、9.26 保持未完成。

## 2026-09-25 Python 扫描自动返回局部简报

相邻 Rust `lint python` 现在复用 `next` 的只读服务，在已初始化工作区的本地报告保存与同步成功后，直接把结构化下一步放入同一 CLI 对话反馈。公开版本为 0.5，私有本地报告仍为 0.4；失败时分别呈现 backlog 与简报读取状态，不丢原生诊断。缺配置的普通 CLI 测试得到 needs_decision；固定 Ruff 0.16.8 的真实 F401 扫描在同一响应中得到 actionable 简报。见相邻 `codeguard-cli/tests/acceptance/lint-python-auto-brief.md`。

`lint_python_cli` 8 项普通与 3 项显式原生 Ruff 测试通过；这仅证明 Rust CLI 内的 Python/Ruff 局部链，插件 Hook/MCP、多语言检测族、可信策略与完整交付门禁仍未完成，9.13/11.16 不勾选。

## 2026-09-25 Ruff 任务原工具复检观察

相邻 Rust CLI 新增 `codeguard task verify <CG-id>`，复用公开 Python/Ruff 的同一原生扫描路径，保存本轮局部报告、同步新发现，并为原任务追加 `verification_observed` 事件。`next` 核对任务、工作区、事件和报告摘要后，才将原问题缺失或环境恢复显示为待策略核验候选；再次扫描检出问题会恢复待处理指引。本地忽略的复检报告在另一机器缺失时，不沿用未核验的恢复结论。fact 始终 open，CLI 固定 `local_unverified`、`not_evaluated`、退出 3，不能因此签发白名单或关闭任务。

`task_verify_contract` 的 5 项普通测试、固定 Ruff 0.16.8 的 2 项显式原生测试、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check` 均通过。见相邻 `codeguard-cli/tests/acceptance/task-verify-native-observation.md`。可信工具/规则/覆盖、任务租约与 token、正式 resolved/reopen、跨类别复检仍缺，9.10 保持未完成。

## 2026-09-25 白名单候选缺证据边界

复核现有 `codeguard/findings` Ruff fact 与误报候选 schema 后确认：fact 只存首次规则、路径和发现指纹，缺本轮工具制品、适配器、rulepack 身份，不能安全拼成可批准候选。已在白名单设计、rulepack-governance、unified-cli-contract 与任务 4.9 固化 `propose` 的前置条件和反例：证据不全返回未完成及补证据动作，不猜测摘要、不写候选、不改变门禁。`openspec validate introduce-rust-codeguard-cli --strict` 和插件 `git diff --check` 通过。此时只更新规格；命令预览进展见下一节。

## 2026-09-25 白名单 propose 缺证据预览

相邻 Rust CLI 已实现 `rules whitelist propose <finding-id> [path]` 的保守入口：读取稳定任务并返回复检命令与本轮缺失的工具/适配器/rulepack 身份；环境 blocker 和未知任务不能产生候选。输出协议固定 `candidate=null`、`authority=unverified`、`gate_effect=none`、`not_evaluated`、退出 3，不写 decisions。目标测试先因命令不存在失败；实现后 2 项普通测试及固定 Ruff 0.16.8 的 1 项显式原生测试、Rust 全工作区测试、全目标 Clippy 和 fmt 通过。见相邻 `codeguard-cli/tests/acceptance/whitelist-propose-incomplete-preview.md`。完整候选生成、批准来源与门禁仍未实现，4.9 保持未完成。

## 2026-09-25 Ruff 完整文件的工具与配置观察摘要

相邻 Rust 扫描结果仅对原生证据完整且输入稳定的文件携带本轮工具/配置字节 SHA-256；扫描结束后再复核工具，身份变化使相关文件 incomplete 并清空摘要。公开反馈 0.6、本地持久报告 0.5；同步器兼容旧 0.4，但新版完整文件缺有效摘要或未完成文件虚报摘要均拒绝导入。局部 `next` 接受两版复检报告，保留原任务 open。`lint_python_cli` 8 项普通/3 项真实 Ruff、`python_lint_scan_contract` 5 项普通/3 项真实 Ruff、`work_sync_contract` 8 项普通及 `task_verify_contract` 5 项普通/2 项真实 Ruff 测试通过；全 Rust 工作区测试、Clippy、fmt 与 JSON 语法检查通过。见相邻 `codeguard-cli/tests/acceptance/ruff-observed-artifact-identity.md`。这不是可信工具批准；适配器、rulepack、候选绑定及完整门禁仍缺，相关 4.8/4.9/5.2/9.10 保持未完成。

## 2026-09-25 propose 最新本地观察绑定

相邻 Rust `rules whitelist propose` 预览升至 0.2：只选择最新的本地 Ruff 报告，先核对工作区、结构化报告、当前源码与已同步标记，再展示同一稳定 finding 的报告/源码/工具/配置摘要。真实 Ruff 测试先因旧预览不含观察而失败；实现后覆盖最新观察、较新报告未同步、源码变化及新扫描问题消失，均不会用旧记录生成候选。2 项普通与 1 项真实 Ruff 目标测试通过。`candidate=null`、退出 3、`not_evaluated` 保持不变；`rulepacks/` 当前只有旧语言清单，不能用配置摘要冒充受批准 Ruff rulepack，适配器及可信批准身份仍缺，4.8/4.9/12.12 不勾选。见相邻 `codeguard-cli/tests/acceptance/whitelist-propose-incomplete-preview.md`。

## 2026-09-25 Ruff 候选规则映射观察身份

相邻 Rust 工程加入 `rulepacks/ruff_lint_preview_v1.json`，精确映射 Ruff 0.16.8 的 F401/E501，记录版本、来源、许可、原生/CodeGuard 规则 ID 与原始字节 SHA-256，状态固定 `candidate_unapproved`。解析拒绝通配、重复、错误来源/许可和自批准。完整局部报告 0.6 仅在版本匹配且 finding 原生规则已映射时附观察身份；未知规则及版本不匹配仍保留原生诊断但无映射。同步器拒绝改写映射摘要；公开反馈为 0.7。`propose` 0.3 从最新已同步、源码及配置未变的报告展示该观察，并明列 `approved_rulepack_identity` 缺失，固定 `candidate=null`、门禁 none、退出 3。见相邻 `codeguard-cli/tests/acceptance/ruff-rulepack-observation.md`。

`ruff_rulepack_contract` 3 项、`work_sync_contract` 普通测试、`lint_python_cli` 8 项普通与 3 项真实 Ruff、`whitelist_propose_contract` 2 项普通与 1 项真实 Ruff 均通过；Rust 全工作区离线测试、全目标 Clippy `-D warnings`、fmt、四个 JSON 文件语法检查、OpenSpec strict 和插件 `git diff --check` 通过。P3C 等未显式运行的原生忽略测试仍不计入本次证据。候选清单不配置 Ruff 覆盖，不具受保护批准或可信策略身份，4.3/4.8/4.9 均保留未完成。

## 2026-09-25 Ruff 原生设置与规则覆盖缺口

相邻 Rust runtime 在配置项目的 Ruff 0.16.8 扫描中新增 `check --show-settings` 原生步骤；受限解析器只提取 F401/E501 全局启用状态、是否配置逐文件忽略和设置输出摘要。公开反馈升为 0.8、本地报告升为 0.7；二者均明确 `coverage_proven=false`。设置输出损坏或找不到、规则未启用却返回相应诊断时，局部扫描 incomplete 并保留已有诊断。同步器仅对 0.7 完整文件接受结构有效且不自称覆盖已证明的设置观察；缺失或伪称的报告拒绝导入。真实 Ruff 的 E501/F401、逐文件忽略及原任务复检链均通过，见相邻 `codeguard-cli/tests/acceptance/ruff-effective-settings-observation.md`。

适配器解析 2 项、局部扫描 6 项普通及 4 项真实 Ruff、同步 10 项普通、`lint_python_cli` 8 项普通及 3 项真实 Ruff、白名单 propose 1 项真实 Ruff、任务 verify 2 项真实 Ruff测试通过；Rust 全工作区离线测试与全目标 Clippy通过。`noqa` 与其它原生 suppression、批准 required rule 集合、完整目标覆盖及可信门禁仍缺，OpenSpec 5.4/7.2 保持未完成。

## 2026-09-25 Ruff 源码注释抑制原生对照与任务复检

相邻 Rust runtime 对配置项目的 Ruff 0.16.8 在普通 JSON 扫描后以同一总截止时间执行 `--ignore-noqa` 原生对照，校验工具/配置/源码、报告归属及普通诊断包含关系；损坏或矛盾的对照不能变成干净证据。公开反馈升为 0.9、本地报告升为 0.8；仅被注释抑制且无活动 finding 的文件标记 `suppressed`，公开展示对照摘要、抑制数和规则 ID，但抑制诊断不生成活动 finding。`task verify` 预览/事件升为 0.2：原 F401 添加 `# noqa: F401` 后返回 `suppression_requires_review`，`next` 要求核查抑制，原 fact 保持 open；真正移除违规仍只形成待策略核验候选。见相邻 `codeguard-cli/tests/acceptance/ruff-native-suppression-observation.md`。

固定 Ruff 0.16.8 原生样本已验证 `# noqa`、`ruff: ignore`、文件级注释抑制与无抑制行为；`python_lint_scan_contract` 5 项真实样本、`lint_python_cli` 4 项真实样本及 `task_verify_contract` 5 项真实样本通过。额外真实反例证明禁用原规则与新增逐文件 ignore 都不会被当成修复。同步器 0.8 缺抑制观察或伪称计数的反例通过。Rust 全工作区离线测试、全目标 Clippy `-D warnings`、fmt、三个更新 schema JSON 语法检查、OpenSpec strict 和插件 `git diff --check` 均退出 0；真实 human CLI 对 `# noqa` 显示 `suppressed`、抑制数 1、退出 3 和 `not_evaluated`。批准策略、逐文件配置忽略的精确目标归属、完整覆盖及正式交付门禁仍缺，4.2/5.4/7.2/9.10 不勾选。

随后收紧 0.8 本地报告导入：`suppressed` 必须有非零抑制差额且无活动 finding，普通 `passed` 不能隐藏抑制；旧报告不能凭新增状态绕过。合法 `suppressed` 可同步但不产生新活动 finding。`work_sync_contract` 11 项普通测试和全目标 Clippy 通过；这项校验不把本地报告提升为可信交付证据。

## 2026-09-25 C06 只读计划预览

相邻 Rust CLI 新增 `codeguard plan <类别|check> <语言|all> [path]`，优先校验类别与 canonical 语言 ID，然后复用静态项目发现。预览 0.1 列出选中类别、语言、检查器配置、待定候选和未解析条件；`policy_identity=null`、`obligations=[]`、候选命令 null，固定 `not_evaluated` 与退出 3。它不伪造正式 CheckPlan、批准规则或原生执行能力。见相邻 `codeguard-cli/tests/acceptance/plan-readonly-preview.md`。

目标测试先因命令缺失失败；实现后首 2 项通过，含伪造 Ruff 工具不执行、项目目录不新增文件、非法类别与未知语言在观察前返回 2；随后增补 P3C 静态候选反例，现为 3 项。`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all` 与新 schema JSON 语法检查通过。可信策略、完整义务/DAG、工具锁和正式计划身份仍缺，2.1/2.4/2.7 保持未完成。

## 2026-09-25 Maven P3C 静态配置独立识别

相邻 Rust `detect` 将 `java.maven.p3c` 与通用 `java.maven.pmd` 分开。明确的 P3C 2.1.1 制品依赖、已核对的内置规则路径和 `skipPmdError=false` 形成静态 configured；缺项、动态值和处理错误跳过有独立状态及恢复动作。测试先因没有 P3C 检查器项失败，随后 `detect_cli` 的正反例及 `plan_preview_cli` 的 Java 候选测试通过。见相邻 `codeguard-cli/tests/acceptance/maven-config-discovery.md`。此处只确认直接 POM 声明，未验证 Maven effective model 或原生规则运行，5.10/6.2 保持未完成。

全工作区测试首次指出不可读 POM 的静态检查器数由 6 增至 7；修正该旧断言后全工作区测试退出 0。随后补齐父 POM 下直接 PMD 声明的保守 unknown 反例，定向 `detect_cli` 16 项与 `plan_preview_cli` 3 项、全目标 Clippy、OpenSpec strict、插件 `git diff --check` 均通过。此补充没有重新执行显式 ignored 的原生 Maven/P3C 哨兵，不将静态配置探测当作原生运行证明。

## 2026-09-25 冻结义务清单对照

相邻 Rust Core 的交付判定增加应有义务 ID 与实际计划的集合对照。新的反例先证明旧代码会在遗漏 `java/cve` 时给出 `Allow`；实现后漏项、额外项与重复冻结 ID 都为 incomplete，`conclude_check` 还把漏项带到请求退出 3。见相邻 `codeguard-cli/tests/acceptance/frozen-obligation-ledger.md`。这只是纯领域一致性校验，可信清单来源及正式 CLI 接线未实现，OpenSpec 2.4 保留未完成。

`delivery_gate_contract` 14 项、`check_session_contract` 6 项及 `cargo test --workspace --offline -q` 全部通过；`cargo clippy --workspace --all-targets --offline -- -D warnings`、`openspec validate introduce-rust-codeguard-cli --strict` 和插件 `git diff --check` 退出 0。显式 ignored 的原生外部工具测试不计入此轮执行证据。

## 2026-09-25 C09/C10 只读配置观察与白名单自授权隔离

相邻 Rust CLI 新增 `config validate/explain [path]` 的保守入口：有界只读解析旧 `codeguard.json` 和结构化工具锁，计数并标记旧 `exclude`、`gate_scope=delta`、`java.commands` 为待批准迁移；未知/损坏字段、坏工具锁和符号链接为未完成。项目内伪造 `codeguard/decisions/` 批准无效。输出协议 `config_inspection` 0.1 固定 `authority=unverified`、`gate_effect=none`、`effective_policy=null`、`not_evaluated` 与退出 3。目标测试先因命令缺失失败，实施后 6 项通过，见相邻 `codeguard-cli/tests/acceptance/config-readonly-inspection.md`。

`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`openspec validate introduce-rust-codeguard-cli --strict` 和插件 `git diff --check` 均退出 0。完整可信质量策略、正式 config schema 迁移、原生配置差异、白名单独立审批和真实交付门禁未接通；4.1、4.2、4.5、4.7、4.9、12.12 均保持未完成。

## 2026-09-25 质量策略候选协议与工具锁引用

相邻 Rust CLI 增加 `quality-policy-candidate` 1.0 严格解析与 `config validate/explain --policy-candidate FILE` 只读展示。候选要求非空必需检查、已登记语言/检测族、具体规则与源集、阻断严重度、规则包/工具锁摘要、CVE 库时效和测试要求。候选源码排除限定精确单文件路径、内容摘要、结构化原因和到期字段；未知字段、自写批准、通配/路径穿越、重复或空义务均拒绝。工具锁原始字节相符显示 `matched_untrusted`，失配显示 `mismatch`，均不赋予策略权威。`config_inspection` 升至 0.2，含请求 ID、命令状态与警示，固定 `effective_policy=null`、`gate_effect=none`、退出 3。设计与测试见相邻 `codeguard-cli/tests/acceptance/config-readonly-inspection.md`。

新增 7 项质量策略候选测试与 6 项配置观察测试通过；最终代码状态的 `cargo test --workspace --offline -q` 全工作区回归、全目标 Clippy、fmt、两个 JSON schema 语法检查、OpenSpec strict 与插件 `git diff --check` 均退出 0。部分依赖外部原生工具的测试按显式 ignored 保持未运行，不能算本轮验收。可信基线/批准来源、同 PR 策略变更隔离、有效策略绑定、逐项原生配置差异、规则/覆盖和交付门禁仍缺，4.1、4.5、4.7、4.9、12.12 不勾选。

## 2026-09-25 公开 Java P3C 单文件原生诊断

相邻 Rust CLI 新增 `lint java FILE` 局部入口，用固定的 Maven PMD 3.11.0/P3C 2.1.1/PMD 6.15.0 配置，在私有临时项目中复制单个 Java 输入并通过统一 runtime 调用原生 Maven；固定 `-o` 和显式离线仓，前后复核源码、复制件、POM/settings、Maven/JDK 入口及仓库树。公开只展示规则/规则集/位置，不回显原生消息。结构报告 `java_p3c_local_feedback` 0.1 固定 `coverage_proven=false`、`checker_identity=unverified`、`delivery_decision=not_evaluated`、退出 3。假 Maven 退出 0 却不生成报告、错误仓库摘要及复制源码被修改均为未完成。

本机 4.4 GiB 通用 Maven 仓超过运行时 512 MiB 树预算，故从已缓存制品复制出 340 MiB 测试仓，并在 `-o` 下先验证真实 Maven 生成含 `ClassNamingShouldBeCamelRule`/`AlibabaJavaNaming` 的 XML。其观测树摘要为 `ead9fd901ba10e3bddf60cc3543b64839d7650f967326b2c94b9442d556cedef`；以该临时仓显式运行 `java_p3c_cli` 的两个原生 ignored 测试，违规样本返回结构化 finding，干净样本返回 `clean_scope_unproven`，两者均退出 3，测试退出 0。原生测试仓和显式摘要只是本地观察，不构成独立批准或离线网络隔离证明。详见相邻 `codeguard-cli/tests/acceptance/java-p3c-cli-native-local.md`。

正式多模块扫描、有效项目原生配置/覆盖证明、工具与规则批准身份、finding/task 同步、Java 注释/CVE/安全/构建及 `check java/check all` 仍缺；5.4、6.2、6.6、6.7 保持未完成。

进一步用同一 340 MiB 仓和 JDK 26 显式复跑原有 `p3c_native_replay --ignored`：违规、干净和坏规则集三项原生哨兵及执行前后树摘要均通过。新增 Java 分派首次全工作区回归暴露 Python `lint` 参数截断；已修正分派，并把未知语言反例改为 Ruby。修正后 Python 与 Java 两组目标测试、最终代码的全工作区离线测试、全目标 Clippy、fmt、JSON schema 语法检查、OpenSpec strict 和插件 `git diff --check` 退出 0。随后仅调整 human 输出去掉 JSON 引号，目标测试与 Clippy 再通过；真实 human CLI 在最终代码上显示 `Bad_Name.java:1 ClassNamingShouldBeCamelRule` 与未核验提示，命令退出 3。未把任何局部结果算作交付允许。

## 2026-09-25 误报白名单撤销快照切片

相邻 Rust `approval-snapshot` 增加 1.1 协议与必填 `revoked_decision_ids`。被撤销的决策即使其原字节摘要还在快照中也返回 `Revoked`；同一修订可固定替代候选，重复/通配撤销 ID、1.1 缺字段及 1.0 越权添加撤销字段使快照无效。旧 1.0 快照仍可读取。目标测试先因缺 `Revoked` 变体编译失败，实施后 10 项通过；全工作区离线测试、全目标 Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0。撤销表达仍只证明本地快照与候选输入之间的关系；可信快照来源、修订历史事件、独立批准、真实门禁和任务重开未接通，4.8、4.10、12.12 仍未完成。

## 2026-09-25 重复扫描的本地证据与审计事件去重

相邻 Rust `work sync` 修正同一 Ruff finding 的重复扫描证据：每轮当前源码匹配的发现都在默认忽略的 `state/observations/<finding-id>/<run-id>.json` 记录报告与源码摘要、位置和工作区身份；相同内容不重复改 tracked finding/task/event。复检后重新检出只增加一次恢复观察事件，后续相同扫描继续记本地证据。坏报告、过时源码仍不生成当前问题或认证。目标测试先因缺第二轮观察失败，复检去重反例先因第四轮多出事件失败；实现后十轮扫描只保留一个问题、一个任务、一条首次事件与十份本地观察，复检后重现只多一条事件，消费标记丢失重试幂等。

`work_sync_contract` 12 项普通测试及固定 Ruff 0.16.8 的两项原生测试通过；最终状态的全工作区离线测试、全目标 Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 退出 0。当前本地观察不作为可信规则/工具批准或交付证据，跨语言同步、重命名、父事件关系、并发事务与正式关闭仍缺，9.3–9.5 保持未完成。

## 2026-09-25 Unix 本地任务租约基础

相邻 Rust CLI 新增 `task claim/heartbeat/release`：在 runtime 的独占文件锁下，以稳定任务 ID 串行化本地状态；32 字节随机 token 只返回领取者，本地仅保存 token SHA-256，generation 防止同名 owner 的旧 token 操作新租约。默认期限 5 分钟，释放同 token 可幂等重放，过期且没有公开 attempt 状态时可被新一代领取。无效任务不建锁、符号链接状态拒绝、四进程并发只有一个领取成功；锁繁忙立即返回未完成，不无限等待；所有输出均固定 `local_unverified`/`not_evaluated`。目标测试初次因命令不存在失败，随后 6 项通过。首次全工作区测试暴露 CLI 直接依赖 libc 违反 crate 方向；已将文件锁移至 runtime，crate 边界测试与全工作区离线测试、全目标 Clippy、fmt、OpenSpec strict、插件 `git diff --check` 均退出 0。之后补充非阻塞锁目标测试及 Clippy 通过；全工作区需在最终状态复跑。

最终非阻塞锁改动后的 `cargo test --workspace --offline -q` 再次退出 0。以上还不是 S09 租约验收：未结束 attempt 的过期接管与 abandoned 事务、token 绑定的 verify/fix、Windows 实现及跨机器行为均未完成，9.8、9.9、9.10、9.27 保持未勾选。详见相邻 `codeguard-cli/tests/acceptance/task-lease-local.md`。

## 2026-09-25 Unix 修复尝试与无进展预算切片

相邻 Rust CLI 新增 `task attempt start/finish`，并将 RepairBrief 接到受控 action-id 和本地历史。首次定向测试因 action-id/attempt 命令不存在而失败；实现后 13 项 `task_lease_contract` 通过，覆盖错误 token、动作改名、不可重复 open attempt、未结束拒绝 release、同结果 finish 重放、矛盾的 no-change、两次同输入无进展停止推荐、过期接管先记 abandoned、旧 token 不能改写，以及环境 blocker 不改源码仍可进入待复检。新事件采用不可覆盖的 start/finish 文件；事件/响应和扩展简报各有版本化 schema。`cargo test --workspace --offline`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。详情见相邻 `codeguard-cli/tests/acceptance/task-attempt-local-ledger.md`。

该切片仅记录任务受影响路径的字节变化，不等同完整 patch 或环境工具身份；`ready-to-verify` 不证明原检查器复检或受保护规则覆盖，正式 fix 自动登记、verify 租约绑定、Windows 等价实现与故障注入矩阵仍缺。真实 Ruff/P3C 原生验收未因这组本地契约测试自动完成，9.8、9.9、9.10、9.27 继续未勾选。

## 2026-09-25 task verify 租约绑定

相邻 Rust CLI 的 `task verify` 新增 Unix 本地租约预检和提交前再核验。无占用时短期自领并在复检后释放；已有占用时只借用匹配的 owner/token，错误 token 和未带凭据的冲突请求在调用原生扫描前返回 3，借用结束不释放别人的租约。定向测试先因缺 `--owner` 参数与自有租约而失败，实现后 `task_verify_contract` 普通 7 项及 `task_lease_contract` 13 项通过。固定 Ruff 0.16.8 的显式原生复检 6 项通过，其中新增真实 finding 下错误 token 不产生 native_scan/新报告、正确 token 保留 active 借用租约的样本，详见相邻 `codeguard-cli/tests/acceptance/task-verify-lease-binding.md`。可信身份、长操作自动续租与取消、Windows、正式任务关闭/重开仍缺，9.10 不勾选。

最终状态下 `cargo test --workspace --offline`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、`openspec validate introduce-rust-codeguard-cli --strict` 和插件 `git diff --check` 均退出 0；工作区默认测试不包含显式 ignored 的原生样本，上述 6 项 Ruff 用例已单独运行。

## 2026-09-25 attempt 与原工具复检关联

此前 `ready-to-verify` 可在没有新复检的情况下再次 start，绕开无进展预算。现由验证事件 0.3 记录对应 attempt-id；下一次 start 在该尝试没有可核对原工具报告时返回 `verification_required_before_retry`。同一输入的复检仍显示问题或检查未完成时计入预算；复检确认问题不再出现时清除等待，但仍不自动关闭 finding。丢失 Git 忽略的本地原报告后旧事件不作为复检凭据，重新运行原工具可恢复。定向契约测试先因缺这项约束失败，随后新增的等待/两次复检预算/报告丢失恢复用例通过；本机 Ruff 0.16.8 显式原生复检 7 项通过，新增修复后任务仍 open 的实测样本。完整 patch/环境身份、可信规则覆盖、正式关闭/重开和跨平台语义仍缺，9.9/9.10 不勾选。

最终状态下 `cargo test --workspace --offline`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。默认工作区测试未包含显式 ignored 的真实 Ruff 样本；7 项原生复检已单独执行。

## 2026-09-25 源码变化后的复检状态转换

修复 `next` 对同一问题的状态死角：源码变化先要求复检；`task verify` 原生 Ruff 仍检出同一稳定 finding，且报告中的目标源码摘要与当前文件一致时，简报恢复 `actionable`，展示复检观察和 run/report 摘要；复检后源码再变则重新要求复检。`task attempt start` 只接受当前 actionable 简报，防止借租约绕过复检继续修改。两个定向测试先分别因旧行为失败，再在实现后通过；其中一个使用固定 Ruff 0.16.8 的真实原生复检。最终 `cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 及插件 `git diff --check` 均退出 0。该局部状态仍不关闭 finding、不产生交付认证；9.7、9.9、9.10、9.27 仍未完成。

误报白名单另有独立的精确处置规格与 4.8–4.10、9.28、12.12 验收任务。当前未将本次复检观察用于白名单批准或放行；可信审批、本轮完整身份及真实门禁仍缺。

## 2026-09-25 白名单替代候选与撤销的局部绑定

相邻 Rust 增加 `false-positive-decision` 1.1 替代候选协议：必须指明不同于新 ID 的 `replaces_decision_id`，1.0 仍拒绝该字段。`approval-snapshot` 1.1 绑定要求在同次快照撤销旧 ID；普通绑定在缺旧决策时返回未核验，专用绑定核对旧 ID、稳定 finding、原生检查器/规则/类别和精确目标归属，防止把一个目标的误报纠正扩到另一个目标。定向测试先因缺字段/返回类型编译失败，随后候选与快照共 24 项通过；全工作区离线测试、全目标 Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 退出 0。详见相邻 `codeguard-cli/tests/acceptance/whitelist-replacement-binding.md`。

这些是本地结构与字节绑定，不证明旧决策来自此前受保护修订，也未校验多级修订链无环、本轮复检引用或执行真实门禁。OpenSpec 4.10 和 12.12 继续未完成。

## 2026-09-25 白名单前序快照关系核对

相邻 Rust 新增替代候选的前序快照绑定：除同轮新候选与撤销集合外，还核对旧决策字节已列入另一份固定摘要的前序快照、旧决策声明的策略修订一致、前序未撤销且新旧修订不同。缺前序摘要、错误摘要、旧字节更改、前序撤销和同修订反例均拒绝绑定。定向测试先因前序接口缺失编译失败，随后 `approval_snapshot_contract` 14 项通过；最终 `cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0。旧摘要来源和修订时间顺序仍须由受保护 CI/宿主证明，不能用本地生成的两份摘要自签授权；多级无环修订链、纠错 CLI、任务事件与真实门禁仍未完成，4.10/12.12 保持未勾选。

## 2026-09-25 白名单多跳修订链结构校验

相邻 Rust 新增最多 32 跳的前序链绑定：从当前替代候选向前追溯至普通根候选，逐跳验证决策字节所属快照、前驱引用、同一 finding/精确目标、子快照撤销前驱、策略修订唯一及当时允许的最大有效期。完整 A→B→C 样本通过；截断、乱序、根后多余节点、重复 ID 成环及超长链拒绝。目标测试先因接口缺失编译失败，随后 `approval_snapshot_contract` 15 项通过；最终 `cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。 随后的 schema 审核移除了 check feedback 与纠错事件的跨文件相对 `$ref`，避免 URN `$id` 下引用不可解析；两个受影响的集成测试文件及 JSON 语法复核通过。可信快照来源、真实修订时间顺序、纠错命令/任务事件与实际门禁仍缺，4.10/12.12 不勾选。

## 2026-09-25 白名单纠错只读提案

相邻 Rust `rules whitelist propose` 增加 `--correct-decision/--correction-reason/--verification-run` 及可选 `--replacement`。旧候选必须与稳定 finding 的 Ruff 规则/目标一致；run ID 必须绑定最近由 `task verify` 保存、事件及报告摘要可复核的原工具结果。原 finding 仍存在时可预览撤销，问题消失且复检后源码未再变化时支持 `root_cause_fixed` 仅撤销；错误 run、环境 blocker、扩大到其它文件、源码再次变化均不生成提案。替代草稿只展示 ID 与候选摘要，本轮观察可核对的源码/工具/发现指纹必须匹配，但由于适配器和已批准 rulepack 身份缺失，状态保持 `evidence_incomplete`。输出始终退出 3、`authority=unverified`、`gate_effect=none`，不写 `decisions/`、不关闭任务、不放行。

普通 `whitelist_propose_contract` 4 项通过（2 项需原生工具而默认忽略）；固定 Ruff 0.16.8 的纠错端到端样本显式通过，`task_verify_contract` 的 8 项原生复检回归显式通过。`cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 最终退出 0。完整批准身份、可信旧决策来源、持久纠错事件/任务投影、原生跨语言复检与真实门禁仍缺，4.10/12.12 保持未完成。见相邻 `codeguard-cli/tests/acceptance/whitelist-correction-preview.md`。

## 2026-09-25 白名单纠错本地事件

相邻 Rust CLI 的 `rules whitelist propose --record` 在任务锁下重新核对原生复检与精确范围，把纠错提案写入稳定 finding 的追加事件目录。相同提案由内容摘要确定文件名，重放不重复；环境 blocker、证据过期和源码变化不能新增事件。事件与输出均为 `authority=unverified`、`gate_effect=none`，不触碰 `decisions/` 或交付门禁。原生 Ruff 端到端及普通契约测试通过；`next` 会在本轮复检引用仍匹配时给原稳定任务添加待审事件引用和 `needs_decision` 指引，过期事件不能占用当前任务。持久任务 Markdown 投影、可信批准和策略发布仍未实现，4.10 保持未完成。

## 2026-09-25 白名单领域门禁聚合

相邻 Rust Core 增加 `AllowlistDisposition` 和原始/已批准/活跃 finding 集合，以及独立的 `allow_with_exceptions` 交付决策与 `passed_with_exceptions` 请求结论。先写的反例揭露同一批准 ID 可跨两条 finding 复用、取消后仍保留 allow；修正后定向 `delivery_gate_contract` 18 项与 `check_session_contract` 8 项通过。过期、目标失配、自批、重复批准、混合真实阻断及不完整义务也保持不放行。当前数据仍由测试显式提供；真实 CLI 没有受保护批准输入，不能据此宣称白名单已经生效。`cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0；新增 serde 默认值后定向 26 项回归及 Clippy 再次通过。

## 2026-09-25 全项目检查局部入口

相邻 Rust CLI 初版新增 `check all` 0.1，复用现有 Python Ruff 原生扫描→本地报告保存→`work sync`→`next`；初版把其它语言/六类别称为未完成义务，这一语义已由下方 0.2 纠正。先写的测试因命令不存在失败；实现后普通 4 项、固定 Ruff 0.16.8 的 F401 原生样本显式通过。JSON/human 均保留配置、原生违规与未完成原因，固定退出 3/incomplete，不签发项目 allow。完整 RunReport、可信策略/工具锁、其余适配器及正式项目门禁仍缺，2.3/2.4/12.7 不勾选。`cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。

## 2026-09-25 `check all` 候选/义务边界纠正

复核 native-tool-adapters 与 verdict-integrity 规格后，发现初版 `check all` 把每个已发现语言的六类别称为“未完成义务”，会错误暗示所有候选检测器都是项目必需项。修订 `check_feedback` 为 0.2：`category_candidates` 仅是能力候选，`required_obligations=null`、`obligation_status=unresolved` 明示尚无可信策略；Ruff 原生失败为 `native_incomplete`，仅本轮局部扫描完整才为 `observed_unverified`。先改反例使普通测试失败，修复后普通与真实 Ruff 测试均通过。完整策略、冻结义务及正式门禁仍缺，任务保持未完成。`cargo test --workspace --offline -q`、全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。

## 2026-09-25 `check all` 局部总预算接线

相邻 Rust `check all` 新增 `--timeout`（正整数加 ms/s/m/h，默认 30m、最大 24h），参数错误在原生执行前返回 2。参数解析后建立一次 `Instant` 截止时间，并传入已接入的 Ruff 版本探测与逐文件扫描；原生超时给出 `request_deadline_exceeded`，不生成局部完整证明，整体仍为 `incomplete`/退出 3。测试先证明原命令拒绝有效 `--timeout`，接线后 `check_all_partial_contract` 6 项通过、1 项默认忽略；固定 Ruff 0.16.8 的 F401 真实用例显式通过。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、`cargo fmt --all --check`、OpenSpec strict 与插件 `git diff --check` 均退出 0。此切片尚未使发现、持久同步、简报和清理受到硬截止时间约束，也未统一 jobs、重试或其它命令预算；2.8 保持未完成。详见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。

## 2026-09-25 `lint python` 检查类预算复用

相邻 Rust `check_budget` 现统一解析检查类 `--timeout`（默认 30m、最大 24h），`lint python` CLI 与 `check all` 共享同一参数契约；CLI 在参数解析后建立一次截止时间，传给 Ruff 版本探测与逐文件扫描。先写的原生探测超时用例因旧 CLI 拒绝有效 `--timeout` 失败；接线后 `lint_python_cli` 普通 10 项通过、4 项默认忽略，固定 Ruff 0.16.8 的原生 F401 反馈用例显式通过。非法预算在启动前返回 2，原生超时保留 `request_deadline_exceeded` 和 `not_evaluated`，无假通过。全工作区离线测试、全目标 Clippy `-D warnings`、fmt、OpenSpec strict、插件 `git diff --check` 均退出 0。任务复检、预算来源报告、持久 I/O/清理硬截止时间及其它命令仍未实现，2.8 保持未完成。详见相邻 `codeguard-cli/tests/acceptance/lint-python-auto-brief.md`。

## 2026-09-25 `task verify` 局部预算与超时复检

相邻 Rust `task verify` 现复用检查类 `--timeout` 解析和默认 30m 截止时间，并将同一时间传入原生 Ruff 探测与逐文件扫描。先写的有效预算用例在旧 CLI 返回 2；接线后非法预算在获取租约前返回 2，超时扫描显示 `request_deadline_exceeded`，复检观察为 `incomplete`、不追加验证事件，自有租约释放，稳定任务保持待处理。`task_verify_contract` 普通 9 项通过、8 项默认忽略，固定 Ruff 0.16.8 的源码修复复检用例显式通过；全工作区离线测试、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 及插件 `git diff --check` 均退出 0。租约、持久 I/O、清理的硬截止时间与完整来源报告仍缺，2.8/9.10 保持未完成。详见相邻 `codeguard-cli/tests/acceptance/task-verify-native-observation.md`。

## 2026-09-25 检查预算公开来源协议

相邻 Rust `check_feedback` 0.3、Python 对话反馈 0.10 与任务复检预览 0.3 新增严格的 `execution_budget`：最终 `timeout_ms`、`source=cli|builtin_default`、`enforcement=native_execution_only`。三个入口的默认 30m 和显式 100ms 路径都有 CLI 契约断言；前置任务不可用的复检 JSON 也保留来源字段。先改 schema 测试确认旧协议失败，再升级 schema/输出与消费者版本断言。原始 0.8 扫描报告保持独立；其它语言、项目/环境预算来源与全 I/O 硬截止时间仍待接线，不能把公开值当作完整预算验收。全工作区离线测试、全目标 Clippy `-D warnings`、fmt、固定 Ruff 0.16.8 的三个真实 CLI 样本、OpenSpec strict 和插件 `git diff --check` 均退出 0；前置任务不可用的新增断言随后单独通过。见相邻 `codeguard-cli/tests/acceptance/{check-all-partial-native,lint-python-auto-brief,task-verify-native-observation}.md`，2.8 仍未勾选。

## 2026-09-25 已登记超时环境变量优先级

相邻 Rust 三个局部入口现在只读取明确登记的 `CODEGUARD_TIMEOUT`，按显式 CLI > 环境变量 > 内置 30m 解析，公开 `execution_budget.source` 新增 `registered_environment`。先写的 `check all` 250ms 环境来源用例因旧实现仍取 30m 失败；实现后 CLI 覆盖、非法环境值在原生/租约前拒绝及两个其它入口的契约测试通过。非 UTF-8 环境值由解析拒绝；未登记变量不会改变预算。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、固定 Ruff 0.16.8 的 `check all` F401 样本、OpenSpec strict 与插件 `git diff --check` 均退出 0。项目运行默认值、jobs 和全部 I/O/清理总预算尚未实现；2.8 保持未完成。

## 2026-09-25 项目运行默认值及优先级

相邻 Rust 增加可选 `codeguard/runtime.json` 1.0，仅允许 `timeout`，有界普通文件读取并拒绝文件/父目录链接、错误协议、非法预算、过大文件及任何额外质量排除字段。三个局部入口在无显式 CLI 和已登记环境值时读取项目默认，公开反馈显示 `project_default`；截止时间从请求解析后开始计，不把配置读取成本重置掉。先写的项目默认测试在旧实现仍返回内置 30m 而失败；实现后 `check_all_partial_contract` 普通 10 项、`lint_python_cli` 普通 11 项、`task_verify_contract` 普通 10 项通过，其余真实工具用例保持显式运行。固定 Ruff 0.16.8 的 `check all` F401 样本现用项目默认 30s 并显式通过，原发现仍可见。全工作区离线测试、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。运行默认值不构成规则/白名单授权；jobs、跨命令预算及持久 I/O/清理硬截止时间仍缺，2.8 保持未完成。见相邻 `codeguard-cli/schemas/runtime-options.schema.json` 和 `tests/acceptance/check-all-partial-native.md`。

## 2026-09-25 `check all` 双语言局部原生观察

相邻 Rust CLI 新增 Cargo Clippy 机器报告解析和局部调用，`check all` 对适用的 Python/Ruff、Rust/Clippy 建立两个独立 DAG 节点。先写的 Rust 原生契约在旧 CLI 的 `--cargo-tool` 路径上失败；接线后普通目标测试 13+6 项通过、各 1 项原生用例默认忽略，真实 Cargo Clippy 临时项目的显式用例通过。混合项目测试验证 Python 工具缺失不吞掉 Rust 的有效诊断；编译错误、坏报告、缺 Cargo 工具都保持 incomplete，已解析的有效部分发现保留。human/JSON 反馈显示检查器配置观察、原生状态、Clippy 规则/位置和复检命令，`check_feedback` 升至 0.6，交付始终为 incomplete/退出 3。

变更后 `cargo test --workspace --offline -q` 退出 0；最后补充的人类可读输出和非零退出细分又经两个目标契约测试、真实 Cargo Clippy、全目标 Clippy `-D warnings` 与 fmt 检查通过。OpenSpec strict 和插件 `git diff --check` 通过。此结果只证明本地默认 features/all-targets 的局部原生观察；可信工具锁、批准规则包、完整 workspace/features、构建脚本隔离、Rust finding 任务同步、其它五类别及全格式门禁仍缺，2.3/2.8/3.4/7.1 均不勾选。见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。

## 2026-09-25 Rust Clippy 任务同步与白名单自批反例

相邻 Rust CLI 的 `check all` 现在为已初始化工作区保存 Clippy 局部原生报告，将当前源码仍匹配的 finding 与缺 Cargo blocker 归并为稳定任务，并在 JSON/human 反馈返回 `next` 简报。重复扫描不复制任务；Rust `task verify` 尚未接通，明确返回 `rust_checker_verify_not_integrated`，原任务不会借 Ruff 复检关闭。新增反例在项目可写 `codeguard/decisions/` 写入 `approved=true` 后重新运行 Clippy，原始 finding 和修复任务仍可见，交付仍为 incomplete。这仅验证本地自批不会在当前局部链隐藏问题，不证明可信白名单已经生效。

目标契约测试先因 Rust 缺同步字段失败，接线后 `check_all_rust_native` 普通 9 项通过、1 项默认忽略，相关 `check_all_partial_contract`、`work_sync_contract`、`next_command_contract`、`task_verify_contract` 定向测试通过，真实 Cargo Clippy 临时项目显式通过。首轮全工作区测试仅在 SIGINT 时序测试未等到原生启动标记而失败；该测试单独重跑通过，第二轮 `cargo test --workspace --offline -q` 退出 0。全目标 Clippy `-D warnings`、fmt、JSON schema 解析、OpenSpec strict 与插件 `git diff --check` 均通过。工具/规则权威、跨类别义务、Rust 原工具复检、可信批准及正式交付门禁仍缺，4.8/7.1/9.3/9.10/9.13/12.12 保持未完成。见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。

## 2026-09-25 Rust Clippy 原工具任务复检

相邻 Rust CLI 的 `task verify <CG-id> --cargo-tool ABS_PATH` 现在对 Rust Clippy finding/blocker 复用任务租约、项目发现、原生 Cargo Clippy、报告同步及 `verification_observed` 事件。`next` 按 checker 身份核对保存报告和事件摘要；同一发现仍在为 `still_present`，检查完成但未再报告时为 `rule_coverage_requires_review`，因为当前尚不能排除 `allow`、Cargo lints、特性组合及规则身份变化。环境任务恢复为 `environment_restored_unverified_policy`。任务事实始终 open，交付仍为 `not_evaluated`/退出 3；不存在 Rust 到 Ruff 的替代复检。

先修改的 Rust 任务测试因旧 CLI 不接受 `--cargo-tool` 而失败；接线后 `check_all_rust_native` 普通 10 项通过、2 项默认忽略，`task_verify_contract` 普通 10 项与 `next_command_contract` 6 项通过。显式真实 Cargo Clippy 样本确认持久任务复检先得到 `still_present`，再对源码加 `#[allow(clippy::needless_return)]` 得到 `rule_coverage_requires_review` 且 fact 仍 open。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings` 与 fmt 通过。可信工具/规则、Rust 原生抑制对照、完整特性覆盖、正式关闭/重开和跨平台租约仍缺，7.1/9.10 保持未完成。详见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。

## 2026-09-25 Clippy 原生强制告警抑制对照

本机独立原生探针确认：同一带 `#[allow(clippy::needless_return)]` 的源码，普通 Cargo Clippy 零诊断，`--force-warn clippy::needless_return` 返回原规则诊断。相邻 Rust `task verify` 现在只在普通 Clippy 完整且原稳定 finding 消失时对该规则执行同截止时间的原生对照；把两轮脱敏报告、目标源码摘要、工具与 manifest 身份放入同一 0.3 本地报告。对照重现原 finding 为 `suppression_requires_review`，两轮均无发现为 `candidate_absent_unverified_policy`；对照坏报告、工具/manifest/源码变化或超时保持 incomplete。`next` 复核事件和报告摘要，源码再变化时要求重跑，任务不关闭；白名单和门禁不因本地观察生效。

先把真实抑制用例改为期望原生对照识别，旧实现失败；接线后 `check_all_rust_native` 普通 11 项通过、2 项默认忽略，真实 Cargo Clippy 复检用例显式通过，坏强制告警报告反例也通过。`cargo test --workspace --offline -q` 与全目标 Clippy `-D warnings` 通过。局部对照仍不证明受保护工具锁、完整 features/targets、批准规则覆盖或正式解决，7.1/9.10/12.12 保持未完成。详见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md` 和 `task-verify-native-observation.md`。

## 2026-09-25 Java/P3C 进入 `check all` 的局部原生观察

相邻 Rust CLI 的 `check all` 0.7 新增 `java.p3c` DAG 节点。Java 源文件根据最近 Maven 构建根的 P3C 配置逐份决定是否运行隔离的原生 Maven/PMD 探针；未配置的源码不会借其它模块的配置启动 Maven。文件级 JSON/human 反馈保留配置状态、原生原因、P3C 规则与位置。节点使用整轮截止时间和取消标志；原生探针仍只加载 P3C 2.1.1 命名规则集，故即使出现真实 finding，Java lint 候选仍标 `native_incomplete/p3c_naming_subset_only`，覆盖与交付保持未完成。

普通契约覆盖未配置不启动、已配置诊断可见及嵌套模块配置归属；显式真实 Maven/JDK 21 用例使用本机 340 MiB 固定离线仓，使 `Bad_Name.java` 的 `ClassNamingShouldBeCamelRule` 出现在 `check all`，命令仍退出 3。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、JSON schema 解析、OpenSpec strict 与插件 `git diff --check` 均退出 0。此局部接线没有完成 `check java`、全部 P3C/其它 Java 规则、finding→稳定任务→原工具复检、可信白名单/策略或代表性项目修复前后对照；2.3、3.4、6.2、6.7、9.13 均不勾选。证据见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。

## 2026-09-25 Java/P3C 稳定任务与原工具复检

相邻 Rust CLI 的 Java/P3C 局部报告现在绑定已初始化工作区和本轮 run；`work sync` 从原生诊断生成稳定 finding，并将缺配置或原生前置条件按 Maven 构建根归并为 blocker。重复扫描只保留一张任务，`check all` 的 JSON/human 反馈显示同步状态及下一步。`task verify` 对 Java 任务重新运行原生 Maven/P3C，保存报告与 `verification_observed` 事件；原问题仍在返回 `still_present`，干净单文件报告仅为 `rule_coverage_requires_review`，配置恢复仍为 `environment_restored_unverified_policy`。任务事实保持 open、正式交付固定未评估；源码在复检和落盘之间变化时拒绝沿用观察。schema 已允许 Java 原生扫描对象。

`check_all_java_p3c` 普通契约 6 项通过、2 项真实用例默认忽略；显式真实 Maven/JDK 21 与固定离线依赖仓的两个用例均通过，包括初始化工作区复检后仍存在的原生 `ClassNamingShouldBeCamelRule`。`cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、JSON 语法、OpenSpec strict 和插件 `git diff --check` 退出 0。仍未验收 POM/源码并发变化的全部窗口、完整 P3C 规则覆盖、可信白名单批准、原生 suppression 对照、正式关闭/重开与完整 Java 门禁；2.3、3.4、6.2、6.7、9.3、9.10、9.13、12.12 保持未勾选。证据见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。

## 2026-09-25 P3C 十规则集声明与第二规则正例

相邻 Rust CLI 的隔离单文件 POM 从 `ali-naming.xml` 扩展为 P3C 2.1.1 制品里的十个 `ali-*.xml` 规则集。公开本地反馈升至 0.2，列出声明清单与受控 POM SHA-256；`check all` 的 Java lint 原因改为 `p3c_declared_rulesets_unverified_coverage`，仍为 incomplete。固定 340 MiB 离线仓内的 P3C JAR 列出了全部十个资源；独立原生试跑同时检出 `ClassNamingShouldBeCamelRule` 与 `ClassMustHaveAuthorRule`。先在 CLI 真实用例中新增第二规则期望，旧单规则实现确实失败；扩展后，公开类 `Bad_Name` 同时检出两条，包内可见类没有作者注释诊断，原命名 finding 的任务复检仍为 `still_present`、fact 保持 open。两条真实 CLI 用例在 JDK 21、固定离线仓显式运行并通过。

这组证据证明两个规则在所测上下文真实触发，不能证明十个规则集全部规则均有效、项目 POM 的生效模型或全源集覆盖；可信工具/规则包批准和白名单门禁也未取得。局部报告始终 `coverage_proven=false`、交付未评估。OpenSpec 2.3、6.2、6.3、6.7 仍不勾选。详见相邻 `codeguard-cli/tests/acceptance/{java-p3c-cli-native-local,check-all-java-p3c-partial}.md`。

最终验证：本轮 `cargo test --workspace --offline -q` 退出 0；新增的声明清单与受控 POM 一致性契约另经 `java_p3c_cli` 目标测试通过，`check_all_java_p3c` 目标普通 6 项通过、真实 2 项显式通过。全目标 Clippy `-D warnings`、`cargo fmt --all --check`、OpenSpec strict 和插件 `git diff --check` 均退出 0。全工作区默认测试跳过需要原生 Maven/JDK 的用例，真实 2 项是单独运行的验收。

## 2026-09-25 `check java` 局部语言选择

相邻 Rust CLI 新增 `codeguard check java [path]`，沿用 `check all` 的原生 Java/P3C DAG 节点、报告持久同步与任务简报。混合 Python/Rust/Java 项目只启动 Java 节点，只列 Java 候选；Java 简报按 checker 过滤已有其它语言任务。公开 `check_feedback` 升至 0.8，以协议条件绑定 `selection=java`、`delivery_decision=not_evaluated`、退出 3；`check all` 仍为全项目 `incomplete`。无 Java 目标明确 `java_target_absent_or_unobserved`，不从空选区推断通过。新增目标测试先因旧入口拒绝 `java` 而失败，实施后普通混合项目、现存 Python 任务和空 Java 目标反例通过；真实 Maven/JDK 21 固定离线仓的 `check java` 显式测试同时返回 `ClassNamingShouldBeCamelRule` 与 `ClassMustHaveAuthorRule`，交付未评估。

这仍是局部 P3C 观察，不证明 Javadoc、CVE、依赖、安全、构建等 Java 义务已实现，也没有可信策略、完整项目覆盖或交付 gate。OpenSpec 2.3、6.2、6.3–6.8 保持未完成。证据见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。

最终 `cargo test --workspace --offline -q` 退出 0；`check_all_java_p3c` 普通 9 项、`check_all_partial_contract` 普通 13 项通过，真实 `check java` 用例另行显式通过。全目标 Clippy `-D warnings`、fmt、JSON schema 语法、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认工作区测试跳过原生工具用例，真实 Maven 测试的通过只覆盖所述 JDK、离线仓与样本。

## 2026-09-25 P3C 项目规则集误报纠正

复核发现前述“项目真实 POM 命中两条规则”的结论混淆了配置发现和隔离探针：验收 POM 实际只启用 `ali-naming.xml`，探针却固定执行十个规则集，因此原作者注释诊断不能算该项目有效 finding。相邻 Rust CLI 现从已发现且摘要稳定的直接 POM 提取精确 P3C 规则集子集，构造仅含该子集的隔离 POM；扫描前后及任务复检/同步时核对项目 POM 字节。未知规则、动态/继承配置或 POM 变化保持未完成，不能借误报白名单掩盖适配器错误。无项目上下文的 `lint java FILE` 仍为十规则集的未授权局部诊断。

真实 Maven/JDK 21、固定离线仓的三个显式用例重新运行通过：只配置 naming 的 `check all` 不再报告 `ClassMustHaveAuthorRule`；同时配置 naming/comment 的 `check java` 报告两条原生规则；原命名任务 `task verify` 仍保持 open。普通反例新增未知规则集不启动 Maven和扫描中 POM 变化丢弃 finding。此修复仅减少局部观察的配置外误报，仍未实现可信白名单批准、完整生效 Maven 模型或 Java 交付门禁；OpenSpec 2.3、6.1、6.2、6.7、9.10、12.12 保持未完成。

## 2026-09-25 P3C 原生诊断规则归属与报告重放复核

相邻 Rust adapter 增加 P3C 2.1.1 的十个规则集、56 个规则 ID 的归属目录。对本地 JAR（SHA-256 `e7afec9340a0f30f56f4fdcd3b9c49e79ed24253719fcb9f457f5bcb43e54860`）只读提取 XML `name` 和各规则 ID，对照 Rust 目录，十组及 56 个 ID 完全一致。`java_p3c_command` 在生成 finding 前核对规则集已被本轮 POM 选择、原生 ruleset 名称和规则 ID 归属；错误归属只返回 `native_rule_outside_selected_rulesets` 与 incomplete。

持久化边界发现真实缺口：将已保存的有效 Java 报告改写 `ruleset` 并以新 run ID 重放时，旧 `work sync` 的定向测试先以 `failed_reports=0` 失败，证明它会接受改写。修复后，同步重新核对当前 POM 子集、探针 POM 摘要及每条诊断归属；改写 ruleset、声明子集或探针摘要的三份报告均导入失败，不新增 finding。adapter 目标测试、`check_all_java_p3c` 普通 13 项、Rust 全工作区离线测试、全目标 Clippy `-D warnings`、fmt、OpenSpec strict、JSON schema 语法和插件 `git diff --check` 均通过。最终代码上显式真实 Maven/JDK 21 固定离线仓的三项项目扫描与原工具任务复检也通过，仍固定交付未完成/未评估。此处只是局部低误报证据，不证明受保护 rulepack、全部规则执行覆盖或正式交付门禁；6.2、9.10、12.12 保持未完成。

## 2026-09-25 白名单身份失配解释

相邻 Rust CLI 的 `rules whitelist explain` 只读查询协议升至 0.3.0：对显式提供的候选与观察身份，列出源码/依赖目标、finding、原生规则及工具/适配器/rulepack 的**失配字段名**，并提供原工具复检、修复候选或核验独立批准的下一步动作；不回显观察值。先新增目标反例，旧实现缺字段且协议仍为 0.2.0，测试失败；实施后 `whitelist_command_contract` 8 项通过。`authority=unverified`、`gate_effect=none` 保持不变，查询不签发批准，也不把候选文件当成门禁授权。

本轮 `cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、JSON schema 语法、OpenSpec strict 和插件 `git diff --check` 均退出 0。需原生工具的默认忽略用例未由这次改动重新验收。可信本轮 finding、独立批准、期限与正式门禁仍缺，4.8–4.10、12.12 保持未完成；局部行为见相邻 `codeguard-cli/tests/acceptance/whitelist-candidate-inspection.md`。

## 2026-09-25 Maven Javadoc 原 POM 私有重放

此前 `check java` 的 Maven 多文件探针使用固定 POM，即使项目声明不同构建内容也会得到配置外的局部诊断。相邻 Rust adapter 现在只接受无继承、依赖、profile、模块、扩展或其它插件的简单静态 POM，直接固定 Javadoc Plugin 3.12.0 与 `doclint=missing`；Rust runtime 将原 POM 和显式 Java 文件同批快照复制到私有新目录，核对与配置发现一致的 POM 字节摘要，并在原生命令后复核原件及副本。其它 POM 在运行前返回 `project_pom_replay_ineligible`，不以合成 POM 替代。公开 `check-feedback` schema 同步描述现有 `java_javadoc` 0.2 多文件字段及原 POM 模式。

adapter 正反例覆盖简单/命名空间 POM、父 POM、动态属性、其它插件、DTD、未知配置与重复字段；CLI 单元反例确认复杂 POM 及发现后 POM 摘要变化不会启动原生探针。真实 Maven 3.9.16、JDK 21、固定离线仓的两文件违规和修正样本显式重跑通过，报告 `native_plan_sha256` 等于项目 POM 字节摘要；修正后的干净日志仍为 `clean_log_unverified`。有效 Maven 生效模型、完整类路径/源集、生成源码、可信规则策略和交付门禁尚未证明，6.3 保持未完成。局部验收见相邻 `codeguard-cli/tests/acceptance/maven-javadoc-multifile-probe.md`。
## 2026-09-25 Java 依赖、CVE 与安全检查器配置反馈

相邻 Rust CLI 的 `check java`/`check all` 现按 Java 源码最近构建根，分别反馈 Maven Dependency、OWASP Dependency-Check、FindSecBugs 的静态声明状态、检查器身份和下一步。已声明但未执行的检查器为 `native_incomplete`，缺失声明为 `not_configured`；动态或混合模块配置保持 `configuration_unresolved`，Gradle 和 Maven/Gradle 混合项目不冒称 Maven 检查器。FindSecBugs 依赖要求完整 groupId/artifactId，避免同名伪依赖造成“已配置”误判。原生依赖图、CVE 数据时效和安全扫描尚未接入，交付保持 `incomplete`，OpenSpec 6.8 不勾选。

本轮 `cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、反馈 schema JSON 解析、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。普通测试通过，显式要求真实 Maven/JDK 等工具的 ignored 用例不计入本轮验收。白名单仍只在精确 finding、原生复检、独立批准和有效期限齐备后才允许例外；这轮配置反馈既不产生漏洞扫描结论，也不提供白名单授权。

## 2026-09-25 Maven 原生依赖图解析基线

相邻 Rust 适配器新增 Maven Dependency Plugin JSON 依赖树解析。4 项目标契约先因接口缺失失败、实现后通过；显式真实测试用 Maven 3.9.16 离线调用插件 3.8.1，JUnit 4.13.2 → Hamcrest Core 1.3 的边与组件版本均可解析。官方格式依据见 [Maven Dependency Plugin 文档](https://maven.apache.org/plugins/maven-dependency-plugin/examples/tree-mojo.html)。解析器不运行 CodeGuard 原生任务，也不形成漏洞结论；隔离调用、项目生效模型、私服/动态版本、CVE 数据库身份和对话反馈仍缺，6.8 不勾选。目标验收见相邻 `codeguard-cli/tests/acceptance/maven-dependency-tree-native-parser.md`。

本次修改后 `cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、OpenSpec strict 和插件 `git diff --check` 均退出 0；真实 Maven 用例另以 `--ignored` 显式运行通过。全工作区普通测试并不包含被忽略的其它原生工具用例。

## 2026-09-26 Maven 依赖图原生 `check java` 接线

相邻 Rust CLI 0.11 在 Java 项目中将已声明的 Maven Dependency Plugin 作为独立 DAG 节点，使用私有原 POM 快照、显式 Maven/JDK/离线仓库树摘要运行原生 `tree`，把节点与传递边反馈到 JSON/human。配置缺失、POM 不适合静态重放、工具/仓库/原 POM 不稳定或报告不完整均保持未完成。真实离线测试揭示 Maven 的 `BUILD SUCCESS` 可伴随 POM 缺失警告并漏掉传递依赖；新增日志反例使这种结果返回 `native_dependency_resolution_warning`，不把图当作完整。随后在约 420 MiB 的测试专用离线闭包中对齐 JUnit 元数据来源，Maven 3.9.16/JDK 21 真实 `check java` 用例确认 JUnit→Hamcrest 原生边可见，CVE 类别仍未验证。此为局部原生观察，未认证项目全量依赖治理、漏洞匹配或交付。见相邻 `codeguard-cli/tests/acceptance/maven-dependency-tree-check-java.md`。

本轮全工作区 `cargo test --workspace --offline -q` 退出 0；之后因 Clippy 指出的同分支重复而合并条件，相关 `check_all_java_p3c` 21 项普通测试和 `check_all_partial_contract` 13 项普通测试复跑通过。全目标 Clippy `-D warnings`、fmt、schema JSON 解析、OpenSpec strict、插件 `git diff --check` 均退出 0。真实 Maven 用例需显式 `--ignored` 和经准备的离线仓库；最初缺闭包、随后镜像来源不一致的失败也保留为诊断证据，不计作通过。

## 2026-09-26 无源码 Maven 依赖构建根调度

复核 `check java` 发现依赖任务曾以 `.java` 源码存在为前提，因此只有 POM/依赖声明的项目完全没有依赖图任务；父根有 Java 源码而子根无源码时也会漏掉子 POM。新增 CLI 反例先失败，再改为按每个静态确认配置了 Maven Dependency Plugin 的构建根调度，候选结果显式给出 `java.maven.dependency`、`native_incomplete` 和缺少原生前置条件。`check all` 同样保留该任务；P3C/Javadoc 仍由源码存在决定。无源码不再等于无依赖义务，缺 Maven/JDK/离线仓库时不会生成空图通过。

定向 `check_all_java_p3c` 23 项普通测试通过、6 项需要原生工具的用例保持忽略；全工作区 `cargo test --workspace --offline -q` 在功能改动后退出 0，随后仅将空源码集合改为具名局部变量，定向测试再通过。全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。该修复只补静态已配置构建根的调度，未证明 Maven 生效多模块模型、动态版本、许可证、SBOM、CVE、可信执行边界或交付门禁，OpenSpec 6.8 仍未完成。

## 2026-09-26 OWASP Dependency-Check JSON 解析基线

相邻 Rust adapter 新增有界 OWASP JSON 1.1 解析器，依据官方 `jsonReport.vsl` 的 `scanInfo`、`projectInfo`、`dependencies`、活动与原生抑制漏洞字段。目标测试先因接口缺失失败；实施后又添加重复 `dependencies` 键反例，旧解析会以后值覆盖前值并通过，现递归拒绝所有重复 JSON 键。坏 schema、缺依赖数组、分析异常、错误标志、坏组件摘要、坏漏洞 ID/分数均返回解析错误；无评分漏洞、原生 suppression 和空数据源保留为事实，不推导为清洁或数据库新鲜。输出不保留原生文件路径。

`cargo test -p codeguard-adapters --test owasp_dependency_check_contract --offline -q` 5 项通过；全工作区 `cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 diff 检查均退出 0。默认测试不含需真实 OWASP 插件及漏洞库的原生验收。尚缺本轮原生执行、数据库时效、Maven 图归属、对话结果和正式门禁；OpenSpec 6.4/6.8 保持未完成。局部范围见相邻 `codeguard-cli/tests/acceptance/owasp-dependency-check-json-parser.md`。

## 2026-09-26 OWASP 与 Maven 图精确归属候选

相邻 Rust adapter 新增独立归属函数：只有 OWASP 包标识中的唯一 Maven PURL 与原生 Maven 图中唯一非根节点的 group/artifact/version/type/classifier 完全一致，才返回坐标候选及节点索引。错误版本、组、类型、classifier、缺 PURL、未知/私服限定符、多个冲突标识及图中重复坐标均不能归属；原生 suppression 仍由漏洞观察保留。先写的接口契约因缺函数而失败，实施后目标 3 项测试通过。它只证明报告与图的精确坐标关系，不能证明两份报告来自同轮可信执行、制品摘要相同、漏洞库新鲜或 CVE 真实有效。真实 OWASP 调用、对话反馈与门禁仍未接线，6.4/6.8 保持未完成。见相邻 `codeguard-cli/tests/acceptance/owasp-maven-attribution.md`。

本轮 `cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、OpenSpec strict 和插件 `git diff --check` 均退出 0。普通测试中的 ignored 原生用例未算入此次验收。

## 2026-09-26 OWASP/Maven 制品字节身份候选

相邻 Rust adapter 在既有精确坐标归属之后新增 SHA-256 比较：OWASP 报告和 Maven 制品观察任一方缺摘要、摘要损坏或值冲突，均不能得到同一制品候选；只有相等摘要返回 `ExactDigestCandidate`，仍不证明报告或仓库来源可信。先写的接口契约因缺类型/函数失败；实施后 4 项 OWASP–Maven 定向测试通过。Maven 原生图探针从固定离线仓库读取可无损定位的普通制品字节并在读取后复核仓库树摘要，缺文件/未知类型保持 null；CLI 反例先因缺摘要字段失败，实施后真实字节摘要进入 JSON 反馈。`check_feedback` 协议升至 0.12、依赖图局部协议升至 0.2，schema 同步，零源码依赖构建根的计数下限也对齐为 0。真实 OWASP 调用、数据库身份/时效、同轮报告绑定和最终 CVE 门禁尚未实现，6.4/6.8 仍未完成。见相邻 `codeguard-cli/tests/acceptance/{owasp-maven-attribution,maven-dependency-tree-check-java}.md`。

复查接口后将摘要绑定改为从本次报告与图重算坐标归属，不接收外部旧归属列表；错误版本反例返回未归属，定向 4 项再次通过。摘要向量来源仍待受保护运行时核验。

本轮 `cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、schema JSON 解析、OpenSpec strict 及插件 `git diff --check` 均退出 0。普通测试仍跳过显式依赖原生工具的 ignored 用例；CLI 制品摘要测试使用模拟 Maven/JDK 和固定离线仓库，不能替代真实 OWASP 验收。

## 2026-09-26 OWASP Maven 原生局部反馈

相邻 Rust CLI 为直接声明 OWASP Maven 插件的构建根新增 `java.cve` 任务和 `check_feedback` 0.13 的 `java_cve` 局部结果。静态 POM 计划先以 3 项契约暴露缺接口，现只接受固定版本的简单直接项目；父 POM、动态版本、额外插件及跳过/排除配置在执行前返回不适用。原生探针读取并核对 Maven/JDK/离线仓库和 CVE 数据目录字节身份，将原 POM 与数据库复制到私有工作区，调用插件固定版本的 JSON goal；本轮解析后的漏洞来源、ID、分数、包标识及 suppression 进入 JSON/human 对话反馈。CLI 两项目标测试先因命令不接受数据目录参数和缺 `java_cve` 结果失败，接线后通过。错误项目名或数据库摘要变化的反例保持 `incomplete` 且不输出 advisory；旧配置测试确认混合 Maven/Gradle 与多构建根仍保持范围未解析，不因某一 POM 已配置而概括全项目。

本地数据库摘要不证明漏洞库时效，原生报告也不自证完整扫描。现在 `database_freshness=unverified`、`coverage_proven=false`、交付仍未评估；真实 OWASP 插件/合格数据库、系统级网络隔离、同轮依赖图与制品绑定及受保护策略门禁均未验收，6.4/6.8 不勾选。局部验收见相邻 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`。

定向 POM 3 项、模拟 CLI 2 项、既有 Java 29 项（其中 6 项 ignored）、检查反馈 14 项（其中 1 项 ignored）均通过。全工作区 `cargo test --workspace --offline -q` 退出 0；全目标 Clippy 首次指出既有测试在更新预期后的相同 if 分支，合并断言后 Clippy `-D warnings`、fmt、schema JSON 解析及受影响 Java 29 项复测均退出 0。OpenSpec strict 与插件 `git diff --check` 退出 0。本机可见 Maven/JDK 和部分 OWASP 插件 jar，但未找到可用的离线漏洞数据库，故没有真实 OWASP/数据库时效验收；普通全工作区测试中的 ignored 用例未计入通过范围。

后续补充“根 Maven 报告已有漏洞、子根为 Gradle”的端到端反例：局部原生报告仍可见，但项目级 CVE 候选保持 `checker_build_systems_mixed`、无 Maven checker ID，防止一处成功覆盖未解析的其它模块。定向 CLI 2 项、既有 Java 29 项及全目标 Clippy 复测退出 0；全工作区测试是在此新增反例之前运行，未把后续改动说成再次全量回归。

## 2026-09-26 CVE 反馈脱敏与白名单边界

模拟 OWASP 报告加入携带私服 `repository_url` 的 Maven PURL，先证实原反馈会回显地址，再将对话 JSON 中的未知限定符包标识替换为稳定 `redacted-sha256`；标准 Maven PURL 保留，异常 advisory 来源、ID 和数据库来源/时间戳也只显示安全格式或摘要。定向 `check_java_cve_native` 2 项通过，确认私服地址不进入反馈。误报白名单设计同步明确：脱敏摘要不可当作 CVE 组件身份，只有本轮原生 advisory、依赖图/制品身份和新鲜数据库可核验时才可能进入精确误报裁定；当前 `database_freshness=unverified`、`coverage_proven=false`，白名单不放行。

本次改动后 `cargo test --workspace --offline -q`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。真实 OWASP 与数据库验收、可信白名单批准及门禁绑定仍未实现，6.4/6.8/4.9/12.12 均保持未完成；ignored 原生测试不计入通过范围。

## 2026-09-26 OWASP 与 Maven 图同轮候选归属

此前两个私有原生探针都只接受自身一个插件，同一 POM 无法同时执行依赖图和 OWASP。相邻 Rust adapter 现在只增开“固定 Maven Dependency Plugin 3.8.1 + 固定 OWASP 插件”的严格双插件形状，重复、额外、动态和复杂插件仍拒绝。`check_feedback` 升至 0.14：同一 `check` 的两个构建根、POM、Maven/JDK 和离线仓库摘要一致时，逐条展示精确 Maven PURL、图节点与制品 SHA-256 的候选状态；身份失配或图缺失不复用历史观察。公开反馈中若另有被脱敏的私服 PURL，即使同时有标准 PURL，也标为 `unsupported_purl`，防止在信息损失后误归属。

先写的双插件资格契约因旧单插件限制失败，修复后 adapter 4+2 项定向测试通过。模拟原生 CLI 的双插件正例、制品摘要冲突和私服限定符反例通过；另有不同 POM 摘要及图未完成的定向单元反例。最终生产代码与集成反例后的 `cargo test --workspace --offline -q` 退出 0；最后新增的单元反例另由 `cargo test -p codeguard-cli --lib java_cve_attribution::tests --offline -q` 验证通过。全目标 Clippy `-D warnings`、fmt、schema JSON 解析、OpenSpec strict 与插件 `git diff --check` 退出 0。测试中的 Maven/JDK/数据库仍为模拟，真实 OWASP 与可信漏洞库、数据库 freshness、工具锁、全构建范围和正式门禁未验收，6.4/6.8 保持未完成；ignored 原生测试不计入通过范围。

## 2026-09-26 CVE 局部报告持久任务

相邻 Rust `check java` 把 0.3 CVE 局部报告绑定到已初始化工作区的 `workspace_id/run_id`，自动保存后由 `work sync` 按摘要导入。原生 OWASP 有 advisory 或空报告但数据库 freshness 未核验时，生成 `cve_database_freshness_unverified` 环境/证据 blocker；缺数据库或工具时按原生结构化原因生成 blocker。任务引用报告、构建根和复检参数，`java_cve.next` 返回只读 RepairBrief。此切片**不**将未经核验的 advisory 升为源码 finding，不关闭旧问题，也不改变交付门禁。未初始化项目不写受管目录。

先写的集成反例因 `backlog_status` 缺失失败；实施后模拟原生报告、重复扫描仍只有一张同身份任务、缺数据库的环境任务、已消费报告被改后 `work sync` 拒绝摘要冲突均通过。`check_feedback` 协议升至 0.15；`cargo test --workspace --offline -q`、Clippy `--all-targets -D warnings`、fmt、schema JSON 解析、OpenSpec strict 与插件 `git diff --check` 退出 0。真实 OWASP/合格数据库、CVE 任务的 `task verify` 关闭与重开、跨类别完整报告事务及可信门禁仍缺，6.4/9.4/9.7 保持未完成；ignored 原生用例不计入通过范围。

## 2026-09-26 CVE 任务原工具复检观察

先写 `cve_blocker_verify_uses_original_checker_and_keeps_task_open` 集成测试，旧路由实际返回 `python_lint_feedback` 而失败。现按 CVE checker ID 重跑原生 OWASP Maven 探针，显式接受 Maven/JDK/离线仓库/漏洞库路径和摘要；复检报告经 `work sync` 后附带 `verification_observed`，`next` 与 attempt 历史校验事件的原报告身份。缺库任务仍为 `still_blocked`；模拟 advisory 再现时漏洞库时效仍未核验，亦为 `still_blocked`。两者均保持 open、`local_unverified`、退出 3。POM 复检后变动不沿用恢复候选，需重新扫描。

`check_java_cve_native` 三项集成测试通过；`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、`openspec validate introduce-rust-codeguard-cli --strict` 与插件 `git diff --check` 均退出 0。ignored 原生用例不计入通过范围。此处仅证明任务分派和本地事件链，真实 OWASP 插件与合格漏洞库、CVE 正式关闭/重开、跨类别完整门禁仍未验收，9.10 保持未完成。

## 2026-09-26 Blocker 重复扫描的本地证据与 Git 噪声

新增集成反例：同一 CVE 前置阻塞扫描两次原先留下两条 tracked `observed` 事件，断言期望仅一条而失败。现有 blocker 与 finding 一样，每轮在忽略入库的 `state/observations/<id>/<run_id>.json` 保存脱敏报告摘要和受影响路径；首见写一条 tracked 事件，复检后再现补一条，之后重复扫描不再增加 tracked 事件。Rust `work sync` 同时识别 Ruff、Rust Clippy、Java P3C 和 CVE 的 run 序列以判断复检后的再现；重复导入仍受 `write_once` 和消费标记保护。新增 `local-blocker-observation` 0.1 schema。`check_java_cve_native` 的重复/复检/再现样本与 `work_sync_contract` 的 Ruff 多文件归并样本通过。跨模块公共前置关系、正式状态机、可信门禁仍缺，9.3/9.5/9.6 不勾选。

回归时一条 `task_verify_contract` 旧断言仍期待“重复扫描新增 tracked 事件”，改为核对首次与复检事件以及两轮本地观察后通过。最终 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、JSON schema 语法、OpenSpec strict 与插件 `git diff --check` 退出 0；默认忽略的原生用例未纳入通过范围。

## 2026-09-26 status 与 task show 局部只读视图

先写 CLI 集成反例，旧入口对 `status` 和 `task show` 返回未知命令且无 JSON。相邻 Rust CLI 现复用 `next` 的受限 fact/事件检查，`status` 汇总开放 finding/blocker、待同步报告和下一步，`task show` 定位指定任务的结构化 RepairBrief。恶意任务 Markdown 不进入输出；坏 ID 返回 2，缺失或损坏事实返回 3；未初始化与空任务均不表示门禁通过。两份局部结果 schema 已加入；`status_show_contract` 四项定向测试通过。完整事件父关系、历史通过证据 freshness、依赖和正式关闭/重开仍缺，9.7/9.26 保持未完成。

最终 `cargo test --workspace --offline -q --no-fail-fast`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、fmt、两份 schema JSON 语法、OpenSpec strict 与插件 `git diff --check` 退出 0；默认 ignored 的真实原生用例未纳入通过范围。

## 2026-09-26 Ruff→CVE 跨类别待导入与游标恢复

同一初始化项目先生成 Ruff 报告再生成 CVE 报告，阻断自动 sync 后仍保留两份本地报告。恢复后添加一份坏 JSON，单次 `work sync` 同时导入两类 blocker、坏报告单独失败；再次删除两份消费标记并同步，标记恢复且任务/事件数量不变。`cargo test -p codeguard-cli --test work_sync_cross_category --offline` 的一项 CLI 集成验收通过。此切片不包含任意崩溃点或多进程并发的事务证明，也不代表可信 CVE 或完整 gate，OpenSpec 9.4 保持未完成。

## 2026-09-26 失败报告收据与误报白名单边界

在上述跨类别验收中加入坏报告的后续 `next`/`status` 断言：原实现反复返回 `pending_reports_require_sync`，目标测试先失败。现在每次可归属且有界的导入失败都留下忽略入库的脱敏收据，绑定工作区、run ID、报告 SHA-256 和静态错误码；`next` 返回 `failed_report_requires_repair` 与安全的报告引用，不重复推荐无变化的同步。改写坏报告后，旧收据不适用，重新同步才记录新失败。收据写入失败时先尝试处理其余报告，然后明确返回未完成。收据不是 finding 或白名单批准；该反例已补入 rulepack 与修复流程规格。

最初新增的 RepairBrief schema 少一个闭合括号，首轮全工作区测试的 schema 契约因此失败；修正后 `next_command_contract` 6 项及跨类别集成 1 项通过。之后全工作区离线测试退出 0；最后调整失败收据写入错误的批处理边界后，受影响两组测试再次通过。全目标 Clippy `-D warnings`、fmt、两份 JSON schema 语法、OpenSpec strict 与插件 `git diff --check` 均退出 0。普通测试中的 ignored 原生工具用例没有运行。正式可信批准、完整门禁、并发与崩溃矩阵仍未实现，4.8–4.10、9.4、12.12 保持未完成。

## 2026-09-26 同工作区同步互斥与失败协议

先写 `sync_rejects_a_concurrent_import_before_writing_records`：测试进程持有现有跨进程文件锁，另一个 `work sync` 原先照样导入报告，反例失败。现同步在枚举报告前取得 `state/work-sync.lock` 的非阻塞独占锁，忙碌时先返回 `work_sync_busy`，不写 finding、任务、事件或消费标记；释放后重试导入一次，再重试只计已消费报告。用例同时发现失败响应仍使用 0.1 协议，与已发布的 0.2 work-sync schema 不符；已统一为 0.2。`work_sync_contract` 普通 13 项（2 项原生依赖 ignored）及 Ruff/CVE 跨类别 1 项通过。

本轮最终 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认 ignored 的真实原生工具用例没有运行。互斥只在当前 Unix 本地同步入口证明；跨平台并发、任意崩溃点事务和完整 RunReport 尚未验收，9.4 不勾选。

## 2026-09-26 首轮报告导入持久边界重放

在四个独立初始化工作区中，先取得同一 Ruff finding 的完整原始记录，然后分别重建“仅任务”“任务加 fact”“已写本地观察”“已写 tracked 事件但尚无消费标记”的持久状态。`work sync` 重放后逐字恢复 fact、任务、观察和事件，恢复消费标记，事件目录仍只有一条。另用真实缺 Ruff 工具的扫描形成环境 blocker，重建已写 fact、未写观察/事件/标记的状态，同样可重放。两项新定向用例和 `work_sync_contract` 普通 15 项、跨类别同步 1 项均通过；2 项显式 ignored 原生用例未运行。全目标 Clippy、fmt、OpenSpec strict 与插件 `git diff --check` 退出 0。本次只重建了磁盘中间态，未实际强杀进程或注入磁盘故障；9.4 继续未完成。

## 2026-09-26 事件落盘后子进程退出验收

新增仅在 Rust `cfg(test)` 构建存在的故障注入点，位于 `import_one` 已持久化 finding/观察/事件之后、写消费标记之前。父测试建立真实初始化工作区和未消费 Ruff 报告；子进程在该点直接退出 97。父进程确认事件存在、标记不存在，随后同一报告重新同步，标记恢复、原事件字节不变且仅一条；这同时验证进程退出后同步文件锁可重新取得。测试先因缺注入点以退出 101 失败，接线后通过。生产构建不包含注入入口。

最终 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0。默认 ignored 的原生工具用例没有运行。此结果证明该单一真实进程退出点；磁盘故障、其它中断点、多记录/CVE 事务及跨平台仍未验收，9.4 不勾选。

## 2026-09-26 残留 staging 与 PID 复用恢复

`write_once` 原先用 PID 加进程内计数形成一次性 staging 名；若旧进程留下同名临时文件且 PID 复用，`create_new` 直接失败，目标记录无法在重试中写入。先写的目标契约因缺有界重试接口而编译失败；实现后，写入器遇 `AlreadyExists` 最多尝试 32 个新名字，绝不读取、覆盖或删除旧文件。单个残留名测试证明目标写入且旧字节不变；全部 32 个名字占满时返回 `staging_name_exhausted`，目标仍不存在，全部旧文件保留。这里是恢复活性改进，不是自动垃圾清理或断电持久性证明。

两项定向单元测试、全工作区 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0；默认 ignored 原生用例未运行。磁盘写失败、跨平台文件系统语义、全类别事务及完整门禁仍未验收，9.4 保持未完成。

## 2026-09-26 白名单与重复 finding ID 的门禁碰撞

审计纯领域门禁发现：若两个义务的原生 finding 意外共用一个 ID，但规则不同，原实现把原始阻断 ID 收进集合；一条精确批准只匹配其中一个原生规则，却会按同一 ID 从活跃阻断集合中移除两者。先写的 `same_finding_id_from_another_rule_cannot_be_waived_by_one_exact_decision` 实际得到错误的 `AllowWithExceptions`，目标断言失败。现门禁先统计全轮 finding ID；重复 ID 使每个受影响义务账本无效，白名单对该 ID 失效，活跃阻断保留，交付为 `Incomplete`。无白名单的单义务重复 ID 也保持未完成，防止集合去重掩盖报告错误。原始 finding 仍留在传入的原生结果中，不按文本相似度合并。

`delivery_gate_contract` 20 项、`check_session_contract` 8 项、全工作区 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 和插件 `git diff --check` 均退出 0；默认 ignored 原生工具用例未运行。这是领域门禁反例与修复，不证明 CLI/宿主已绑定可信策略、批准、时钟和真实原生身份；2.4、4.8、12.12 均未完成。

## 2026-09-26 内部故障仍返回已取得的原生发现

`check all/java` 原先在任务图返回任一 `InternalFailure` 时立即退出 4，兄弟任务槽位中已经取得的原生 finding 不进入对话反馈。先写的定向契约因缺报告构造函数而编译失败；现增加 `check_aborted` 0.2 局部报告，记录失败任务 ID、所有执行任务状态、项目发现和各原生结果。只有内部任务故障时退出 4，同轮取消优先退出 130；`check all` 的交付状态为 incomplete，局部 `check java` 为 not_evaluated。Python 扫描若只留下内部错误结果，也按同一路径反馈。白名单不能利用内部故障把已发现的问题转为通过。

定向单元测试构造 Python F401 与 Rust 内部故障，验证 F401 未丢失、失败任务可定位和 schema 可解析。`cargo test --workspace --offline -q --no-fail-fast`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、`openspec validate introduce-rust-codeguard-cli --strict`、插件 `git diff --check` 均退出 0。默认 ignored 的真实原生用例未运行；调度器自身失败、真实同轮工具异常注入、取消路径、完整义务账本与可信白名单门禁仍待验收，2.3 不勾选。

## 2026-09-26 SIGINT 取消优先级与并行原生发现

既有 SIGINT 集成测试暴露 `check all` 已把任务标成 cancelled，却仍以普通未完成退出 3。先把同一用例的目标改为 130，实测失败（实际 3）；接着将 `check_feedback` 协议升至 0.16，在任务取消或进程 SIGINT 时输出 `command_status=cancelled`、`reason=request_cancelled` 和退出 130，交付依然 incomplete/not_evaluated。测试进一步放入并行 Rust Clippy 原生诊断：Ruff 子进程收到 SIGINT 并清理后，已经取得的 `clippy::needless_return` finding 留在 `native_results`，延迟写入标记仍证明 Ruff 后台子进程已终止。该定向集成测试通过。

另以纯单元反例构造“Python 已有 F401、Rust 内部故障、Java 取消”，核对 `check_aborted` 0.2 优先返回 130，保留 F401 和故障任务 ID。局部 `check all/java` 取消反馈仍不是完整 RunReport，也未证明 `lint python` 等其它入口遵循 130、调度器自身异常携带全部部分证据或可信白名单门禁。OpenSpec 2.3 不勾选。

最终 `cargo test --workspace --offline -q --no-fail-fast`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、两份相关 schema 的 JSON 解析、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认 ignored 的真实原生工具用例未运行。

## 2026-09-26 `lint python` 取消出口对齐

既有真实 SIGINT 用例中 Ruff 原生探测取消并回收子孙进程，但 CLI 固定退出 3。先把目标断言改为 130，实测仍为 3；修复后公开 `python_lint_feedback` 0.11 在收到 SIGINT 或扫描明确返回 `request_cancelled` 时，标记 cancelled、退出 130，保留原局部反馈与取消原因。定向 SIGINT 用例通过。原始工作区扫描报告仍保持 0.8，未把对话协议字段写回发现事实。其它命令的取消语义和完整聚合尚未证明，2.3 不勾选。

本轮最终 `cargo test --workspace --offline -q --no-fail-fast`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all -- --check`、三份相关 schema 的 JSON 解析、OpenSpec strict 与插件 `git diff --check` 均退出 0；默认 ignored 的真实原生工具用例未运行。

## 2026-09-26 三种 planned 语言的显式缺口验收

COBOL、ArkTS、Metal 原先在能力查询中可见 planned/gap，但含 `.cbl`、`.ets`、`.metal` 源码的 `check all` 仅输出通用 `not_integrated`，未把旧登记与当前能力缺口带给智能体。先写集成反例，因候选缺 `legacy_status` 而失败；现 `check_feedback` 升至 0.17，每语言六类别候选同时列出旧登记 planned、当前能力矩阵一致为 gap、`planned_language_adapter_gap` 和原生适配/正反例的下一步。请求固定退出 3、交付 incomplete、正式义务仍为 null；没有空适配器或 `not_applicable`。跨平台能力不一致时，单一候选能力字段为空，避免把某平台结果概括到所有平台。

定向 `planned_language_gaps` 集成测试覆盖三种真实扩展名、18 个候选、能力查询、缺口条件与不生成正式义务；加入 `capability_status` 后复测通过。最终全工作区 `cargo test --workspace --offline -q --no-fail-fast`、Clippy `-D warnings`、fmt、schema JSON 解析、OpenSpec strict 和插件 `git diff --check` 均退出 0；默认 ignored 的真实原生用例未运行。8.145–8.147 的显式 planned/gap 验收已满足；54 个旧 stable 语言的原生适配与 8.148 汇总仍未完成。

## 2026-09-26 白名单 finding 与未完成状态的 SARIF 投影

相邻 Rust CLI 增加 `feedback_sarif` 纯转换器。定向测试先因模块缺失编译失败；实现后，结构有效 RunReport 中的白名单 finding 仍是 SARIF `result`，附处置与批准引用但不生成 `suppressions`，并标明报告所称批准来源未核验。同轮另有活跃阻断时两个结果都保留且总体为 `deny`。未完成且零 finding 的报告仍以 `executionSuccessful=false`、错误级工具通知及未完成义务计数显式表达。原生消息、路径和证据引用不复制到公开 SARIF，规则与 finding ID 用哈希投影。见相邻 `codeguard-cli/tests/acceptance/sarif-feedback-baseline.md`。

定向 `sarif_feedback_contract` 3 项、全工作区 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认 ignored 的原生工具用例未运行；转换器尚未接入正式 CLI/MCP/Hook，报告来源、内容身份及批准权威未被验证，2.5、2.10、12.12 均保持未完成。

## 2026-09-26 `check all/java` 局部 SARIF 命令输出

当前实际检查入口使用 `check_feedback`/`check_aborted`，不是完整 RunReport；直接复用上节转换器会丢失局部原生发现。先写 `check_sarif_cli` 2 项命令反例，旧参数解析均退出 2；实现后 `check all/java --format sarif` 由同轮局部报告投影嵌套原生 finding，固定 `executionSuccessful=false` 与失败通知，保留原退出码 3/4/130。模拟 Clippy finding 可见，诊断内 `token=private` 不公开；零 finding 的 Java 局部检查仍为 `not_evaluated`。另有内部故障保留两个检查器已取得 finding 的单元反例。CVE advisory 与依赖图节点未经归属，不伪装为 SARIF finding。见相邻 `codeguard-cli/tests/acceptance/check-partial-sarif.md`。

定向 CLI 2 项及转换器单元 1 项通过。首次全工作区并行回归中 `check_sarif_cli` 曾间歇失败，单独重跑及第二次全工作区回归退出 0；失败断言未保存，仍需后续观察。全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认 ignored 原生工具用例未运行；完整 RunReport、其它检查类格式、`--output`、可信门禁及白名单批准仍未接通，2.5/2.10/12.12 不勾选。

## 2026-09-26 JSON/SARIF 局部报告原子导出

在 `check all/java` 上实现 `--output PATH` 的 JSON/SARIF 局部导出：同目录创建私有暂存文件，完整写入与同步后原子发布；新目标用不覆盖现有路径的硬链接创建，替换目标只接受可解析的既有 CodeGuard 报告。目标父目录不存在时，扫描已经取得的 finding 仍完整输出到 stdout，stderr 提供 `output_parent_unavailable` 恢复原因，退出保持未完成 3；已有源码文件不会被输出覆盖。目标可写时，导出文件与 stdout 是同一所选格式的文档。先写的导出成功/失败反例因旧解析器拒绝 `--output` 而失败；已有源码保护反例也先证实旧实现会覆盖源码，修复后通过。

定向 `check_sarif_cli` 6 项、全工作区 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认 ignored 原生工具用例未运行。当前输出仍是局部 `check_feedback`/`check_aborted`，human/其它检查命令未接入，非 UTF-8 可逆路径、多位置/包身份、完整 RunReport 与跨工具等价归并尚未实现；2.9 保持未完成。

## 2026-09-26 导出失败进入智能体结构化反馈

上一节导出失败只写 stderr；若宿主只消费 stdout，智能体看不到保存失败。先把 `check_sarif_cli` 改为要求失败时 SARIF `codeguardExportStatus=failed`/受限原因码，成功文件与 stdout 同报 `saved`，JSON 成功报告也带 `export.status=saved`；旧行为的 3 项断言均实际失败。现 `check_feedback` 0.18、`check_aborted` 0.3 要求结构化 `export`，默认 `not_requested`；尝试导出前构造 `saved` 文档，仅成功发布才输出该版本，失败则输出 `failed` 文档并保留同轮发现。局部 SARIF 从同一状态投影。没有扩大白名单或签发完整检查。

定向 `check_sarif_cli` 6 项、`check_all_partial_contract` 13 项普通/1 项忽略、`check_all_java_p3c` 23 项普通/6 项忽略、全工作区 `cargo test --workspace --offline -q --no-fail-fast`、全目标 Clippy `-D warnings`、fmt、两份 JSON schema 语法、OpenSpec strict 和插件 `git diff --check` 均退出 0。默认 ignored 的真实原生工具用例未运行；宿主对 stderr/stdout 的消费、human/其它命令导出与完整 RunReport 仍待验收，2.9 不勾选。

## 2026-09-26 Go vet 局部 CLI、白名单纠错场景与并行回归

相邻 Rust 工程新增 `codeguard lint go` 局部入口：显式 Go 1.23.4 工具路径、离线隔离执行、原生 `go vet -json ./...`、本轮源码/manifest/工具摘要复核和脱敏 JSON/human 对话反馈。原生诊断与清洁样本均已在本机 Go 1.23.4 下执行；编译错误保持 incomplete。CLI 始终退出 3、`coverage_proven=false`、`delivery_decision=not_evaluated`，尚未接入 `check all`、工作任务和正式门禁。见相邻 `codeguard-cli/tests/acceptance/go-vet-json-local-probe.md`。

用户要求能通过纠正白名单处置不合理误判。本 change 已有精确身份、原生复检、候选/独立批准/撤销链与 `allow_with_exceptions` 设计；本次补充从用户反馈到再次检查、对话说明的可观察场景，并写入 12.12 验收。可信批准、任务闭环、真实门禁和 CLI/MCP/Hook/SARIF 一致性仍未实现，相关任务保持未勾选。

全工作区首轮并行回归暴露 `check_sarif_cli` 间歇失败：已有源码文件有时在读取前变空，报告暂存文件有时在发布前消失，替换返回 OS 错误 2。测试用进程 ID 与时钟纳秒生成临时目录，缺进程内唯一序号；给目录名增加原子递增编号后，该测试并行连续运行 10 轮均通过。`cargo test --workspace --offline -q`、`cargo fmt --all --check`、OpenSpec strict 和插件 `git diff --check` 均退出 0；此前全目标 Clippy `-D warnings` 与本轮 Go 真实忽略用例分别通过。并行失败的根因由症状和修复后稳定性推断，未取得碰撞路径日志；原生 P3C 等默认忽略用例不在全工作区通过范围。

## 2026-09-26 Go 多模块与诊断源集归属

`lint go` 的局部扫描使用根模块 `go vet ./...`。新反例先证实：当目标下存在第二份 `go.mod` 时，旧 CLI 继续进入版本探测，没有向智能体指出嵌套模块漏检。现只读发现同时保存 Go manifest 集合；非单一根 `go.mod` 返回 `go_multiple_modules_unvalidated`，提示逐模块核查。另构造有界假原生报告，其位置在根内但文件未列入本轮源码集合：解析后整轮返回 `go_vet_diagnostic_outside_discovered_sources`，不输出该诊断为 finding。该测试首次因 macOS `/var` 与 `/private/var` 路径别名得到解析层拒绝，改用规范根路径后命中目标归属检查。

`cargo test -p codeguard-cli --test go_lint_cli --offline` 4 项普通测试通过、1 项原生测试默认忽略；显式 `CODEGUARD_GO_TOOL=/usr/local/go/bin/go ... -- --ignored` 的真实 Go 1.23.4 违规/干净/编译错误用例通过。仍无逐模块执行、完整 build tags/目标平台证明、可信工具/规则策略或 Go 注释适配，8.2 不勾选。

本次修改后的 `cargo test --workspace --offline -q`、`cargo fmt --all --check`、全目标 Clippy `-D warnings`、OpenSpec strict 与插件 `git diff --check` 均退出 0；全工作区默认忽略的原生环境用例不计入通过范围。

## 2026-09-26 Go 多模块原生复检

上一节只识别嵌套模块并返回范围阻塞。本轮从真实反例继续：根模块干净而嵌套模块含 `printf` 违规时，旧 CLI 返回 incomplete，未运行第二个模块；先写的验收断言失败。现对只读发现的最多 64 个 `go.mod` 按相对根逐一执行 `go vet -json ./...`，把诊断绑定到已发现源码及其所属模块，反馈 0.2 列出每模块状态。根模块有原生违规、嵌套模块编译失败时，公开结果保持 incomplete，已完成根模块的 finding 仍保留。若工具/任一模块 manifest、可选 `go.sum` 或源码在检查中变化，丢弃本轮 finding。模拟报告指向未发现源码或从根模块指向嵌套模块时，该模块保持未完成，不把报告位置误认作有效发现。

本机 Go 1.23.4 的真实单/双模块、局部干净、违规及失败样本通过；普通 CLI 4 项通过。仍未验收 build tags、目标平台/CGO、完整依赖图及规则策略，也未接入 `check all`、任务同步、注释检查和可信门禁，8.2 不勾选。

修改后全工作区 `cargo test --workspace --offline -q`、`cargo fmt --all --check`、全目标 Clippy `-D warnings`、Go 反馈 schema 语法、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认忽略的其它原生用例仍不计入全工作区通过范围。

## 2026-09-26 Go 接入统一局部检查

新 `check_all_go` 反例先要求 Go 项目在统一检查中保留缺工具原因和 `go.lint` 任务，旧行为缺 `native_results.go_lint`，断言失败。现 `check all --go-tool ABS_PATH` 复用 `lint go` 的受控观察服务，接入共享 TaskGraph、deadline/jobs、类别候选、内部故障快照及 JSON/human/SARIF 汇总。真实 Go 1.23.4 的 `printf` 诊断在统一 JSON 与 SARIF 保留，SARIF 仍 `executionSuccessful=false`；整体交付为 incomplete，Go 子报告仍不签发质量通过。缺工具、相对路径、Java 选择误用 Go 参数和 2 秒预算下的慢版本探测均有明确反例；超时映射为 `deadline_exceeded`。Go 子报告沿用 0.2，统一检查反馈升为 0.19、内部故障反馈升为 0.4。

`check_all_go` 普通 3 项、Go CLI 普通 4 项通过；显式真实 Go 的统一检查 JSON/SARIF 及单/双模块用例各 1 项通过。使用已安装的 `/opt/anaconda3/bin/python3`/jsonschema 对真实违规、缺工具和 Java 选择的实际输出执行 Draft 2020-12 校验通过；项目 shell 的另一个 Python 缺 jsonschema，未安装依赖。此验证辅助程序不属于 Rust 产品运行时。Go 尚无持久任务/原工具任务复检、完整规则/平台覆盖或可信门禁，8.2/9.13 仍未完成。

本次修改后全工作区 `cargo test --workspace --offline -q`、`cargo fmt --all --check`、全目标 Clippy `-D warnings`、相关 schema 语法、OpenSpec strict 与插件 `git diff --check` 均退出 0。默认忽略的其它原生环境用例未包含在全工作区通过范围。

## 2026-09-26 Go 稳定发现身份前置能力

新增 `go_finding_identity` 契约测试先因模块未导出而编译失败，随后实现稳定身份并接入原生观察。Go 子反馈 0.3 与统一反馈 0.20 要求稳定 ID、完整指纹和本轮源码摘要。指纹以模块/package/路径/原生规则/源码行锚点/原生消息/重复锚点序号绑定；绝对行号与整文件摘要不参与稳定 ID。排序原生发现和同位置诊断去重避免原生数组顺序制造重复任务；字节摘要独立绑定本次输入。模块内任一位置越界不发布部分有效发现，输入变化清空本轮发现。

纯身份 3 项、Go CLI 普通 5 项、统一 Go 普通 3 项通过。显式 Go 1.23.4 的 CLI 原生验收和统一 JSON/SARIF 各 1 项通过，CLI 包含重复扫描/插入空行、修复、编译错误、双模块和部分模块失败。两种实际含违规输出通过 Draft 2020-12 schema 校验。局部能力没有新增交付批准；Go 持久报告工作区/运行归属、同步、next 和 task verify 未实现，8.2 保持未完成。

本轮全工作区回归退出 101：`maven_probe_contract::delegated_bundle_mutation_during_validate_invalidates_local_evidence` 期望 `bundle_identity_changed`，实际 `version_execution_incomplete`。该测试使用 2 秒总预算，但现有结果不含该次进程具体终止原因，不能据此确认是超时。单独重跑该测试文件的 7 个普通用例通过、3 个原生环境用例忽略；原失败尚未解释，不报告全工作区通过。Go 相关普通/显式原生专项、实际 schema 验证、全目标 Clippy、fmt 和 OpenSpec strict 通过。后续须保留进程终止证据定位 Maven 回归干扰，再重新取得完整回归退出 0。

## 2026-09-26 Maven 版本失败可诊断性

从上一轮全量失败继续：检查发现 `run_maven_probe` 对所有非零/异常版本阶段统一返回 `version_execution_incomplete`，无法区分时间预算、启动权限或执行层故障。新增 100ms 预算的长进程反例和普通文件缺可执行权限反例，两者先按期失败（得到通用原因），实现后分别得到超时/启动前耗尽和启动失败原因，均不启动 validate、不生成源码违规。其余终止类别也显式保留；没有放宽产品或测试截止时间。

Maven 普通契约现为 9 项，连续五轮均通过，各轮 3 个本机原生环境验收未执行；全目标 Clippy、格式、OpenSpec strict 和 diff 检查通过。此前 bundle mutation 的一次失败仍无法恢复具体终止原因，重复通过不等于根因确认。完整工作区回归的终态另行记录；6.1 及完整计划保持未完成。

本轮完整 `cargo test --workspace --offline -q` 最终退出 0，原 Maven bundle mutation 用例通过，新增超时/启动失败反例也包含在该轮回归。全量日志 `/tmp/codeguard-maven-reason-workspace.log` 仅作本地执行记录，不作为长期规格事实源。默认忽略的原生工具用例仍未计入本轮全量通过范围；偶发失败根因不因本轮成功而标为已确认。

## 2026-09-26 Go 报告归属与持久修复任务

缺工具场景的新 `go_work_sync` 测试先因缺 `backlog_status` 失败，接通保存与同步后又暴露 next 拒绝 Go checker；现已统一 `lint go` 和 `check all` 的本地保存/同步函数，并让 next 返回 Go 原工具参数及环境/策略指引。Go 子反馈 0.4、统一反馈 0.21 新增 workspace/run、各模块 manifest/go.sum 身份和同步反馈。尚未初始化或无效工作区不写队列，保存失败不改变原生 finding 或签发门禁。

同步器验证工作区和运行文件名、已完成模块、诊断计数、归属及源码位置；单模块计数有上限，过大输入不让求和溢出。源码或模块内容已改变的报告只计历史；错工作区、计数矛盾、越界路径、模块错属和坏位置不生成源码任务。合成报告测试只验证本地一致性，字段及摘要不能自证可信原生来源或策略批准。

Go 同步普通 3 项通过，包含多个畸形报告与历史输入子场景；显式本机 Go 1.23.4 原生 1 项通过，发现自动生成具备证据/规则/范围/步骤/复检/历史/关闭条件的 Markdown 任务，重复扫描不复制，修复后任务仍 open。Go CLI 普通 5 项、统一 Go 普通 3 项及统一协议普通 13 项通过。已初始化项目的实际 Go 和统一含违规输出通过 Draft 2020-12 schema 校验；Clippy 与 fmt 通过。Go task verify、可信规则/平台覆盖及正式关闭/重开仍缺，8.2/9.13 不勾选。

当前 Go next 源码分支按首次事实摘要保守提示是否需要复扫；新报告的当前源码摘要已写入独立本地观察，但完整最新复检观察消费仍待 Go task verify 接线。不能把当前简报或同步成功说成修复闭环完成。

本轮全工作区回归最终退出 0。计数上限和 human 工作台提示的最后调整另经 Go 同步/CLI 专项、统一协议专项、最终全目标 Clippy 与 fmt 验证；默认忽略的原生环境用例不因全量通过而变为已执行。实际 Go 原生同步与报告 schema 验证如上；完整目标的剩余任务不因这轮回归成功而勾选。

最终版本显式重跑本地 Go 1.23.4 的 `check_all_go`、`go_lint_cli`、`go_work_sync` 三个原生验收，各 1 项全部通过，覆盖初始化/未初始化、统一 JSON/SARIF、单/双模块、稳定身份、修复、编译失败和持久任务同步；不涉及自动安装或网络下载。

## 2026-09-26 Go 原工具任务复检与简报消费

环境任务复检新测试先得到 task_checker_unsupported，接通原生调用后又暴露旧事件消费者不识别 Go run ID/report；现 task verify、next、尝试历史与同步事件排序均识别 Go。复检使用显式绝对 Go 路径、同一 runtime 和预算，沿用任务租约/锁、完成尝试绑定和事件原子写入。Go 源码复检子报告 0.5 带 task/path/本轮源码摘要与输入稳定标记，公开任务反馈升为 0.4，追加事件保持 0.3/state_after=open。普通扫描仍为 Go 0.4/check 0.21。

真实 Go 1.23.4 环境下仍有原发现为 still_present；同文件同规则出现另一指纹为 rule_coverage_requires_review，不能凭指纹变化推导修复；修复后为 candidate_absent_unverified_policy，编译失败为 incomplete。缺工具环境复检为 still_blocked 并保留事件；原覆盖/策略任务不会因为原工具能运行而标为恢复。next 绑定同一报告字节，原生观察后源码或模块配置变化会要求重新复检，均不关闭任务或签发门禁。

普通 Go 同步/复检 4 项通过，显式本机 Go 的同步与任务复检 2 项通过（任务复检还验证模块清单变更使候选失效）。使用现有 jsonschema 对四种实际任务反馈与 Go 子反馈执行 Draft 2020-12 验证通过。一个专项命令误写不存在的 task_attempt_contract，未执行测试；已改用实际包含尝试流程的 task_lease_contract，与 Go/next/task_verify 回归重新运行，原错误不计通过。Clippy 和 fmt 通过；全工作区回归终态另记。正式关闭/重开、全语言完整覆盖、策略批准和宿主接线仍未完成。

本轮全工作区 `cargo test --workspace --offline -q` 最终退出 0（默认忽略的原生环境用例未计执行）。末尾的同规则身份变化分流和 Go 参数归属检查经 Go/next/task_verify/task_lease 目标回归、实际 Go 四类输出 schema、最终 Clippy 和 fmt 验证；显式 Go 原生任务 2 项通过。计划仍有正式关闭/重开、完整覆盖与策略/宿主接线缺口，不因本地通过而归档该 change。

## 2026-09-26 Go 原生文件范围与观察失效

先实际复现 RED：旧源码复检在目标被 build tag 排除时返回未检出候选。新增 go list 连续 JSON 解析与复检范围观察后，标签、CGO 和非宿主平台三种排除均为 rule_coverage_requires_review，保持 open，并提示构建范围复核；清单或身份失败为 incomplete。普通 Go 0.6、源码复检 0.7、check 0.22 绑定整组源码摘要，vet/list 之间及事件采纳时输入变化不可用；next 在后续任一 Go 源码变化时要求复扫，同步旧源码仅保留历史。

解析器两项、普通 go_work_sync 四项、next 六项及 task_verify 十项通过。显式 Go 1.23.4 原生 go_work_sync 三项退出 0，包含排除三子场景及后续源码变更。独立临时工作区的 still_present、excluded、candidate_absent_unverified_policy、incomplete 四类实际 task verify 与其 Go 子报告，以及普通 Go/统一检查输出通过 Draft 2020-12 JSON Schema；版本为 Go 0.6/0.7、check 0.22、task preview 0.4。

全工作区离线回归最终退出 0；整组源码历史校验的最后调整另经普通 Go 同步回归与最终真实原生/schema 检查。默认忽略用例不计执行。fmt 校验与最终 `cargo clippy --workspace --all-targets --offline -- -D warnings` 均退出 0。完整 Go 注释、平台/规则策略与正式关闭/重开尚未完成；8.2/9.13 不勾选，全部计划仍有 265 项未勾选。

## 2026-09-26 白名单纠错可读任务附件

RED：真实 Ruff 纠错测试在旧实现缺 projection_status/可读文件时失败。现显式 --record 在同一任务锁内复核收据、生成事件与历史附件，反馈用锁内提案，避免锁前预览与记录混合。附件含七项任务信息，引用同一稳定 finding、旧决策、本轮复检与事件；候选 Markdown/HTML 标点实体化。事件成功但附件失败单独反馈，无覆盖用户编辑；重复记录能恢复删除的附件。next 只展示匹配当前事件重建字节的附件，不从 Markdown 执行或授权。

普通 next 六项、白名单提案四项和转义反例一项通过；显式 Ruff 0.16.8 原生提案两项通过。纠错原生用例额外核对七节投影、幂等引用、用户编辑保留、冲突不丢事件、删除重建及 next 对修改附件不采信。0.2 投影状态协议保留 0.1 读取，recorded/failed 区分引用与失败原因；独立临时 Ruff 项目的预览、已记录、附件冲突、删除重建、事件及 next 实际输出通过 Draft 2020-12 Schema；最后添加具体检查器/规则/目标展示后，原生两项与转义反例再次通过，最终 Clippy 与 fmt 均退出 0。完整工作区离线回归最终退出 0；最后的具体检查器/规则/目标展示补充另经最终原生两项、转义反例、Clippy 和 fmt 验证。默认忽略的原生环境用例不计执行。独立批准、可信发布、全事件链和正式任务处置仍缺，4.10/9.28 未勾选。

## 2026-09-26 Ruff 复检配置变化与优先级

真实 RED 一：F401→E501 修改配置后，next 仍以 still_present 复检驱动旧纠错事件和附件。真实 RED 二：在原 ruff.toml 字节未变时新增同内容 .ruff.toml，普通误报 propose 仍返回旧本地观察。现用当前只读项目发现核对目标所选配置路径和字节摘要；发现不完整、配置缺失/无效/未知、路径或摘要变化及旧报告缺配置身份均不沿用旧观察。next 要求原工具复检，纠错不产生新提案，普通 propose 不展示旧身份；历史记录保留。

普通 next 六项、task_verify 十项、白名单提案四项及 work_sync 十五项通过。显式 Ruff 原生任务复检八项与白名单提案两项通过；新增反例覆盖规则配置修改、高优先级配置切换以及未检出候选后再改配置。独立临时项目对配置内容变化、配置优先级变化、删除配置及恢复原配置的实际 next/correction/propose 输出通过 Draft 2020-12 Schema，失效时没有旧事件/附件引用或新提案，恢复后原事件可继续调查且不产生批准。fmt 与最终 Clippy 均退出 0；完整工作区离线回归最终退出 0。普通 propose 优先级核对的最后调整另经上述四组目标回归、原生两项与实际 Schema 验证，默认忽略的原生用例不计执行。

本增量只复核当前项目配置，不执行项目脚本、不认证规则包或独立批准；完整候选生成、可信发布、正式门禁及任务关闭仍缺，4.9/4.10 不勾选。

## 2026-09-26 批准签名与严格快照桥接

两个 RED 分别为签名核验 API 缺失与核验后候选绑定入口缺失。Rust 新增 Ed25519 原文/域分隔核验、宿主上下文和非授权结果类型，依赖 ring 0.17.14 从已有缓存离线解析。载荷绑定工作区、修订、受保护基线、序号、期限及快照原始字节；普通候选桥接仍严格解析快照并核对内外修订，最后使用签名得出的摘要走原有精确绑定。未提供项目自选公钥、自批开关或生产签发 CLI。

签名四项、原批准快照十五项通过；反例包括换私钥/目标/基线/快照、签名原文空白变化、错误签名域、密钥撤销/失效/未来、批准未来/过期、无时钟、回滚/超期限、重复已知字段、额外 approved、坏版本/长度/零签名、快照内外修订错配和候选字节篡改。Clippy 通过；格式、schema、OpenSpec 和完整工作区终态另记。当前仅证明给定宿主输入下的密码学核验；公钥来源、可信时钟/防回滚持久状态、完整签名修订链及实际门禁接入仍缺，4.5/4.8 不勾选。

分层完整回归首先退出 101：crate_boundaries 拒绝 CLI 直接生产依赖 ring。此失败未忽略，未以目标测试通过替代。密码学原语已移至 runtime；CLI 保留协议解析且仅 dev 依赖 ring 用于测试签名，边界新增 CLI normal/build 和 core 直接 ring 的拒绝反例。修正后的目标边界/签名/快照通过，后续完整回归结果见下。

修正后边界三项、签名四项及批准快照十五项退出 0；实际 Cargo metadata 仅有 runtime normal 与 CLI dev 两条 ring 边。另从 RFC 8032 §7.1 TEST 1 获取独立公钥/签名向量，runtime 原语两项验证标准向量、篡改、无效公钥/签名及超限输入均通过；Clippy 与 fmt 通过。封装/载荷 schema 的结构及拒绝自写 approved 样本通过 Draft 2020-12 校验；这些结构样本不证明签名有效，密码学证据来自 Rust 测试。OpenSpec 严格校验及 diff check 通过。修正后的完整工作区离线回归最终退出 0；启动后新增的 runtime 标准向量两项另经目标执行与最终 Clippy/fmt 验证，未计为该次默认套件的已运行项。默认忽略的原生环境用例不计执行。

## 2026-09-26 多跳签名白名单修订链

RED 为签名链入口与前序输入类型缺失。局部实现逐跳核验签名和快照内外修订，再沿用精确替代/撤销绑定；历史摘要只由验签结果推导。前序序号严格递减，历史签发/审核不得越过子批准签发，旧候选必须在受保护历史审核时刻有效。历史今天过期不抹去当时合法记录，但本轮宿主提供的撤销状态仍须生效。当前批准按本轮时钟核验；超 32 跳在验签前拒绝。

首次目标执行有一项测试错误地 unwrap 乱序链的拒绝错误，已修正拒绝断言，并保留失败记录。最终签名链三项、单快照签名四项、旧快照十五项和依赖边界三项共 25 项通过，覆盖正常三修订链、截断/乱序/多余节点、前序私钥不符、序号回滚、未来批准、跨工作区、缺历史时钟、旧候选未生效、历史密钥撤销、空链及上限。最终 fmt 和全目标 Clippy 退出 0。完整工作区回归终态另记；默认忽略的原生环境用例不计执行。宿主信任来源、Git 基线祖先关系、可信发布与实际门禁仍缺，4.10 不勾选。

补充时序分支反例：前序签名在历史审核时刻有效，但审核晚于替代批准签发，明确返回 approval_revision_order_invalid。最终链测试四项全部通过，fmt 与全目标 Clippy 再次退出 0。此新增反例在已经启动的完整回归之外单独执行，不将其追溯算入那轮全量套件。

完整工作区离线回归最终退出 0，日志为本地 /tmp/codeguard-signed-chain-workspace.log；默认忽略的原生环境用例未计执行。新增第四项时序反例另经专项执行，最终 fmt/Clippy 和 OpenSpec 严格校验、git diff check 通过。完整计划与可信门禁仍未完成，change 不归档。

## 2026-09-26 签名链的原生 Git 基线关系

两次 RED 分别为 runtime 原生祖先观察缺失、CLI 联合入口缺失。实现后在宿主明确指定的 Git/仓库上，先核验签名与精确替代链，再逐跳检查完整非零同格式提交 ID、commit 对象类型、非浅历史及祖先关系。Git 参数/环境禁用 replace、graft、commit-graph 加速、lazy fetch 和可选锁，所有步骤与各跳共享宿主截止时间及取消标记。Git 失败/未知输出不能转为批准。

本机 Git 2.54.0 的 runtime 四项通过，涵盖 SHA-1/SHA-256、同提交/反向/无关、tree/短引用/零/缺对象、replace/graft、浅历史、缺工具/取消/超预算，以及 config/index 字节不变；部分克隆本地假传输有正对照确认能被普通 Git 启动，而 Codeguard 禁取对象观察不启动它，不接外部服务。签名链五项（含真实三提交链、签名有效但无关基线、浅历史）、单快照四项、旧快照十五项及边界三项通过。完整工作区和最终 Clippy/fmt/OpenSpec 终态另记。联合入口不证明公钥/历史时刻/最低序号与仓库/工具可信来源，不签发门禁，4.5/4.10 未勾选。

补充签名链用例确认上层取消标记确实传递，不在每跳重置；随后 RED 复现普通签名入口接受有效签名中的全零基线。Rust 与 signed-approval-payload schema 现统一拒绝两种零 ID。最终单快照五项、签名链五项、旧快照十五项和边界三项通过；Draft 2020-12 六个基线结构样本通过（不作为签名证据）。这些后补调整单独执行，不追溯计入已启动的全量回归。

本轮完整工作区离线回归最终退出 0，日志为本地 /tmp/codeguard-git-approval-workspace.log。后补的取消与全零基线调整另经上述最终专项、全目标 Clippy 和 fmt 验证；OpenSpec 严格校验与 git diff check 通过。默认忽略的原生环境用例未计执行。联合 Git/签名入口没有升级为可信策略发布或最终门禁，完整计划继续保持未完成。

## 2026-09-26 白名单处置与原生主目标关联

RED 一/二分别复现原生 finding 工具不同、主目标不同或缺主定位时仍被处置为白名单。DeliveryInput 增加默认空的 native_checker_bindings，宿主须冻结 checker/tool/category/obligation 关联；领域门禁核对唯一映射与实际 finding 工具/义务、类别，再核对第一处主定位。源码/项目核对精确路径，依赖核对组件和非缺省版本；次要位置不能替代不同主目标。旧输入可读，但缺映射不应用白名单；普通无白名单结果保留兼容。

RED 三复现冲突输入的首条仍在 whitelisted 集合。门禁现预先统计所有重复 finding 引用与重复批准决策 ID，冲突双方全部不应用；原始/活动阻断保留，反转输入顺序结果相同。正例现提供明确主定位与冻结映射，不将缺定位伪装为完整。

最终门禁 26 项、会话汇总 8 项、RunReport 14 项、带例外报告反馈 7 项与 SARIF 3 项通过；core 自身回归通过，最终全目标 Clippy 与 fmt 通过。专项第一次误用不存在的 conversation_feedback_contract 等 target，命令退出 101 未执行测试；改为实际目标后上述回归通过。完整工作区终态另记。以上是合成领域/协议用例，不证明真实原生或批准来源；制品/源内容/依赖图/advisory 归属及签名批准到实际宿主的完整接线仍缺，4.8/4.10 未勾选。

后补 RED 四复现错误义务归属仍留下 whitelisted 状态；现在源结果 ID 与 finding.obligation_id 必须一致，源义务无 invalid/incomplete/coverage_mismatch 标记才可参与处置。第 27 项包含错归属、未知义务与覆盖失配，要求保留活动阻断。此修改在已启动的完整回归之外单独验证，终态另记。

后补修改的最终目标结果：门禁 27 项、会话 8 项、RunReport 14 项、带例外反馈 7 项及 SARIF 3 项通过；core 自身回归全部通过，全目标 Clippy 与 fmt 退出 0。OpenSpec 严格校验及 diff check 通过。完整工作区终态另记；未将这些合成域模型用例计为真实宿主或原生完整验收。

完整工作区离线回归最终退出 0，日志为本地 /tmp/codeguard-native-disposition-workspace.log；默认忽略的原生环境用例未计执行。启动后补充的源义务有效性检查另经上述最终专项、core 回归、Clippy 与 fmt 验证，不追溯计入原全量快照。完整计划和实际宿主门禁仍未完成，change 不归档。

## 2026-09-26 最终门禁时钟与签名到期元数据

两个 RED 分别为 DeliveryInput 缺最终判定时钟、已验签结果缺只读到期方法。领域门禁现要求非零最终时刻满足 observed_at <= gate_time_unix < expires_at；到期瞬间、缺最终时钟或时钟回退均保留活动阻断与未完成，不能沿用旧取证时间。旧输入可读，无白名单普通门禁不因缺新增时钟改变结论。VerifiedApprovalSnapshot 的私有到期值来自已验签载荷，不新增授权效果；宿主应约束当前批准的最早到期边界，不将历史合法记录的旧期限套到当前替代条目。

第一轮目标门禁 29 项、会话 8 项、RunReport 14 项、带例外反馈 7 项、SARIF 3 项、签名与签名链各 5 项及快照 15 项、core 回归通过，Clippy 与 fmt 退出 0。补充只读到期元数据后相同受影响目标、依赖边界与最终静态检查终态另记。本轮未改原生进程或适配器，不重跑无关原生环境用例，也不将合成时刻视为真实宿主时钟验收；可信时钟来源、批准生产及宿主门禁仍缺，4.5/4.8 未勾选。

最终相同受影响目标、依赖边界三项及 core 回归全部退出 0；全目标 Clippy、fmt、OpenSpec 严格校验及 diff check 通过。本轮没有执行完整工作区或原生环境套件，不将前轮全量结果当作本轮证据。完整计划与真实宿主门禁仍未完成，change 不归档。

## 2026-09-26 当前策略修订与签名处置预览

两个 RED 分别为 DeliveryInput 缺当前策略修订、签名处置入口缺失。领域门禁现要求待应用处置与宿主独立冻结的当前修订完全一致，缺/空/不同修订均保留活动阻断。新增只读 BoundFalsePositiveDisposition，普通入口先核验签名/快照/候选，替代入口先核验完整签名/Git 链；候选有 64 KiB 上限。结果固定候选及快照摘要、范围、精确身份、引用、序号与最早当前期限；内部构造且不支持从项目 JSON 反序列化，独立批准标记始终 false。

最终门禁 30 项、会话 8 项、处置 3 项、签名与签名链各 5 项、快照 15 项、边界 3 项、RunReport 14 项、带例外反馈 7 项、SARIF 3 项与 core 回归通过，全目标 Clippy/fmt 退出 0。实际 Git 链用例补充合法替代的预览期限、普通入口拒绝替代及无关基线拒绝；其它原生 identity/来源审核为合成模型。测试中显式模拟独立来源审核只为检验字段消费，不是产品批准接口，也不认证真实宿主来源。未执行完整工作区或其它原生工具套件；OpenSpec/diff 终态另记。可信来源、真实批准生产与宿主门禁仍缺，4.5/4.8 未勾选。

## 2026-09-26 批准范围到最终门禁

相邻 Rust 工程新增 `ApprovalScope`，独立冻结的门禁范围与处置批准范围必须精确一致；签名预览保留范围且仍没有独立批准权威。跨工作区、错基线、缺范围，以及双方同填全零/HEAD/大写/短摘要等非法身份均不能处置 finding。基线指当前批准上下文，不从工作树 HEAD 推导；旧 JSON 可读，但缺范围的白名单不能放行。

新增测试先因范围类型与字段缺失失败；实现后受影响 CLI 契约 80 项（含门禁 32、会话 8、签名预览 3、签名链 5、普通签名 5、边界 3、报告 14/7、SARIF 3）及 core 单元/契约 9/8/5/3 均通过。领域门禁的独立来源为合成输入；签名链含本地实际 Git，均不能证明可信宿主批准或全语言交付。OpenSpec strict 与 git diff --check 通过。workspace all-target Clippy（-D warnings）与格式检查均终态通过。验收说明：相邻 `codeguard-cli/tests/acceptance/approval-scope-gate-binding.md`。完整计划仍有 265 项未勾选；4.8 不勾选，本轮未运行 workspace 全测试。

## 2026-09-26 Maven 静态模块关系与画像刷新

相邻 Rust 工程新增同次清单字节绑定的 Maven 模块观察模型与图 0.2；contains、aggregation、declared build_dependency 分开。完整唯一直接坐标才连接本地依赖，记录来源、SHA-256、scope/声明条件；变量、父模型、profile、依赖管理、特殊属性、重复坐标及逃逸/未知模块保留具体 unresolved。图不能用于缩小扫描范围，不等于 Maven 生效模型。历史 0.1 schema 单独保留。

新增 init 用例先因旧图仍为 0.1 且无直接声明关系失败，实现后 init 28 项通过；受影响 check-plan/config/边界/detect/plan 共 38 项及 CLI 库 18 项通过，adapter 常规测试通过（8 项 ignored 原生用例未执行）。曾因回归目标名写错而未运行 CLI 回归，已更正实际目标名后通过；Clippy 首次发现新导出位于 test module 之后；首次调整漏掉了导出，第二次已恢复到测试模块之前，新增 adapter 3 项与 init 28 项重跑通过；该阶段 Clippy/格式已通过；分段文本修复后的最终轮次见补充记录。

真实 CLI init 输出经现有 JSON Schema 验证：当前图正例与历史图正例有效，6 个错误状态/摘要/条件/scope/来源/完整性反例拒绝；验证辅助不是产品 Python 实现。初始化未执行 Maven 或 wrapper，刷新依赖版本改变图且保留人工任务备注、重复刷新幂等。OpenSpec strict 与 diff 检查通过，完整计划仍未完成，9.18 不勾选。验收：相邻 codeguard-cli/tests/acceptance/maven-static-module-graph.md。

补充：复核发现 XML 注释切分文本时首段可能错误匹配另一模块；新增反例先失败，现拒绝分段标量并记录 unresolved。adapter 4 项与受影响 CLI 66 项重跑通过；追加 Scenario 的 OpenSpec strict 与 diff 校验通过。最后一轮 workspace all-target Clippy（-D warnings）与格式检查均终态通过。

## 2026-09-26 Cargo 静态模块图

同次 Cargo.toml 字节观察新增 CargoModuleModel；模块图 0.3 区分成员聚合与 path 依赖，保留 normal/build/dev、来源清单摘要与声明条件。package 重命名核对真实目标包名；workspace/optional/target、通配/排除、外部/缺失/逃逸目标及版本/feature 解析缺口保持 unresolved。依赖完整性 false，不用于缩小检查。历史 0.1/0.2 schema 单独保留。

新增 init 用例先因旧图 0.2 没有 Cargo 声明而失败。实现后 Cargo adapter 3 项、Maven adapter 4 项，CLI 受影响契约 69 项（init 31、detect 20、check-plan/config 各 6、边界/plan 各 3）与 CLI 库 18 项通过。刷新更名依赖会移除旧边并保留人工备注，重复刷新幂等；没有生成 Cargo.lock/target，也没有执行 build.rs。

实际 CLI 产物通过 JSON Schema 验证，5 个错误 scope/basis/status/摘要/完整性反例拒绝，0.1/0.2 历史正例有效。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查均终态通过。产品观察/投影是 Rust，schema 辅助不作为产品 Python 实现。未执行 Cargo 有效模型、完整 workspace/所有原生语言检查或端到端交付；完整计划仍在实施，9.18 不勾选。验收：相邻 codeguard-cli/tests/acceptance/cargo-static-module-graph.md。

## 2026-09-26 逐清单 Java/Rust 语言目标

相邻 Rust adapter 扩展同次清单模型；project profile 0.3 保留 Java compiler release/source/target 与 Rust rust-version/edition 的逐清单 declared_only 事实、构建根和原始摘要。汇总语言版本、本机版本保持 unknown/null，不用包版本、默认值、父/profile/workspace 推断。变量、重复/嵌套/分段 XML、继承/错类型/非法值记录具体缺口；旧 profile 0.2 schema 单独保留。

新增 init 用例先因 profile 仍为 0.2 失败，实现后语言目标 adapter 4 项、Cargo/Maven 3/4 项、CLI 契约 71 项与 CLI 库 18 项通过。声明由变量变为 17 后画像刷新并保留人工任务备注，重复刷新幂等。实际 CLI profile 通过 JSON Schema，6 个语言/edition/status/摘要/来源/伪造本机版本反例拒绝，历史 0.2 正例有效。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查终态通过。

没有执行原生有效构建模型、安装或本机版本探测；没有运行完整 workspace/全语言/端到端交付，不能把声明当检查能力或质量通过。9.16/9.17 保持未勾选，完整计划仍有 265 项未完成。验收：相邻 codeguard-cli/tests/acceptance/declared-language-target-profile.md。

## 2026-09-26 init 画像的 JSON/human 反馈

init_plan 0.4 新增 profile_summary，在默认 dry-run 和 apply 反馈语言/文件数量、构建根、逐清单目标与未知状态。human 从同一结构投影，所有不可信路径/字段及已创建/冲突路径均转义；不公开原始清单、本机根路径，不把声明或写文件变成准备/质量通过。旧 init_plan 0.3 schema 单独保留。

新增用例先因旧输出 0.3 无摘要失败，实现后 init 36 项与受影响其它 CLI 契约 38 项、CLI 库 18 项通过。真实 CLI 验证 dry-run 不写文件、与 apply 摘要一致、两种格式同目标/未知状态、换行/ESC 目录名不生成伪造状态行，根路径不公开。真实 JSON 通过 schema，6 个伪造就绪/架构/有效模型/目标确认、缺摘要、交付 allow 反例拒绝；历史 0.3 正例有效。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 和 diff 检查终态通过。

未运行完整 workspace/原生全语言/宿主对话端到端，完整 readiness、准备任务及接线仍缺，9.25 不勾选，完整计划继续实施。验收：相邻 codeguard-cli/tests/acceptance/init-profile-conversation-feedback.md。

## 2026-09-26 init 检查配置反馈

init_plan 0.5 按构建根展示静态检查器配置的 configured/missing/invalid/unknown、来源、原因和下一步。每条固定 not_run、required_by_policy=null、gate_effect=none，整体 checker_inventory=partial；不把缺配置变成源码违规或把声明当执行成功，未知继承保持未知。旧 init_plan 0.4 schema 单独保留。

新增用例先因旧 0.4 无检查配置反馈失败，实现后 init 39 项与其它受影响 CLI 契约 38 项、CLI 库 18 项通过。实际临时项目验证四个 Maven 构建根状态及 human/JSON 一致；Python 缺 Ruff 配置不产生 finding，源码不变，dry-run 不落盘或启动检查。真实四状态输出通过 schema，6 个伪造配置通过/执行完成/必需策略/门禁/完整清单/缺下一步反例拒绝，旧 0.4 正例有效。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查终态通过。

没有运行完整 workspace/全语言原生检查或宿主对话端到端；批准义务、准备任务与完整 readiness 仍未接入，9.24/9.25 不勾选，完整计划继续推进。验收：相邻 codeguard-cli/tests/acceptance/init-checker-configuration-feedback.md。

## 2026-09-26 preparation readiness 领域判定

新增分文件的要求/观察/状态/输入/结果契约和纯 evaluate_readiness。只处理批准且适用必需前置，以当前绑定和可信时钟检查证据；有效必需缺失/不兼容/冲突优先 incomplete，未探测/未解析/过期/错绑定/歧义为 unknown，完整非空适用集合全部满足才 ready。可选失败与旧证据不影响汇总。verified 字段是宿主输入约定，不构成本地 JSON 授权；CLI 未接入可信来源，init 仍 unknown。

新用例先因类型/函数不存在编译失败，实现后 readiness 8 项、受影响会话 8/门禁 32/init 39/边界 3 共 90 项，以及 core 单元/契约 9/8/5/3 通过。联合用例确认准备 ready 不提供缺失的原生检查证据，交付仍 incomplete；不从零阻塞/零必需集合或可选缺工具推导假就绪。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 和 diff 检查终态通过。

这些是领域合成输入，不证明真实工具探测或批准/来源核验；未运行完整 workspace/原生全语言或宿主端到端。可信来源、实际准备清单、任务规划/持久化及 CLI接线仍缺，9.25 不勾选，完整计划继续实施。验收：相邻 codeguard-cli/tests/acceptance/preparation-readiness-domain.md。

## 2026-09-26 Maven/Cargo 直接包版本画像

已有 package_declared_versions 现在记录当前清单直接包版本，绑定同批原始字节 SHA-256。Maven 不要求完整 GAV，不从父/profile 或变量恢复；只观察有界字面值，不证明 Maven 生效语义。Cargo 使用本地已缓存 semver 1.0.28（锁文件固定）校验直接字符串，保留预发布和构建标识；继承、错类型和非法版本保持未知。包版本与语言目标/本机版本分离，画像刷新保留人工任务记录并幂等，不执行项目构建器。

新增混合项目用例先因包版本字段 Null 而失败，实现后 init 41 项通过。package version 2 项、Cargo 模块 3 项、Maven 模块 4 项通过；检测/配置/检查计划/计划预览共 35 项与 CLI 库 18 项通过。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查通过。验收入口及反例见相邻 codeguard-cli/tests/acceptance/declared-package-version-profile.md。

依赖边界检查首次因新增 semver 未登记而失败；将其限定为 adapters 普通解析依赖后，4 项边界用例通过，反例拒绝 core/runtime/CLI 和 adapter 构建依赖。重新运行 all-target Clippy 与格式检查均终态通过。

未运行完整 workspace、全语言原生检查或宿主端到端。其它生态、有效构建模型、解析依赖版本、本机版本探测与可信准备任务仍缺，9.16/9.17 不勾选；完整计划保持进行中。

## 2026-09-26 准备任务领域规划

核心 plan_preparation 使用同一 readiness 输入与当前判定。已确认必需缺失/不兼容/冲突分别规划恢复、兼容复核、冲突决策；未知只要求重新核验，不保留过期或错绑定的旧诊断。工作区内稳定逻辑键不受绑定/状态变化影响，当前绑定更新，任务排序与重复规划幂等。未核验来源、非法/重复要求不生成行动任务，可选/不适用/满足条件不生成修复任务。固定中文步骤和关闭条件不拼接项目命令，不自动执行/安装或产生质量 allow。

目标用例先因类型/函数缺失失败。实现后规划 7 项、readiness 8 项、init 41 项、边界 4 项、交付门禁 32 项、检查会话 8 项共 100 项通过，core 单元/契约 9/8/5/3 共 25 项通过。部分清单仍保留已确认阻塞与未知兄弟，旧证据不误导安装；向计划注入 delivery_decision 被严格消费拒绝。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查终态通过。验收见相邻 codeguard-cli/tests/acceptance/preparation-task-planning.md。

证据为合成领域输入，不证明真实工具探测或批准来源。未运行完整 workspace/全语言原生或宿主端到端。真实要求生产、证据/历史关联、工作区持久化、doctor/check/sync/next 与 CLI 接线尚缺，9.25 不勾选；完整计划保持进行中。

## 2026-09-26 tools verify 只读 CLI 接线

新增 tools verify 入口及 human/JSON 同源反馈，默认读取 codeguard.lock.json 或显式候选，有界普通文件读取拒绝链接锁。复用工具三来源及独立 runtime/bundle 核验，逐项展示摘要/可执行位、issue 和恢复建议，隐去路径与锁原文。仅当前平台条目形成观察，版本保持 lock_declared_only，字节匹配仅 matched_untrusted。固定 incomplete、authority=unverified、readiness=unknown、gate_effect=none 与退出 3，不启动 wrapper、联网、安装或写工作区。

入口缺失时最初 4 个用例因无 JSON 输出失败；实现及扩展后 CLI 8 项、静态身份 8 项、配置 6 项、边界 4 项共 26 项通过。测试 wrapper 含副作用但没有运行；运行时/目录包缺口与入口匹配分开。跨平台测试首次用了非协议平台名，改用正式平台清单反例后通过，未放宽解析。报告 0.1 schema 验证 2 份实际 CLI 输出及 6 项伪造批准/就绪/门禁/执行/版本反例。workspace all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查通过。

mock 及静态制品核验不是原生启动或可信工具锁来源证明。未执行完整 workspace/全语言原生或宿主端到端；tools list/install、可信锁来源、doctor 有界原生诊断、准备报告持久化及 work sync 仍缺，5.2/5.6 不勾选。验收见相邻 codeguard-cli/tests/acceptance/tools-verify-command.md；完整计划保持进行中。

## 2026-09-26 原生版本探测故障分类

runtime 新增分文件的原生版本请求/观察与共享探测服务，限制版本参数并核对工具前后字节、精确 stdout、无异常 stderr、私有日志及共同截止时间。超时/启动前耗尽/取消/spawn/signal/输出超限/管道/清理/平台/非零退出分别保留诊断码和 termination；版本不符、stderr、字节变化和记录失败不再合并。现有 Ruff 版本启动阶段复用服务，失败不继续源码扫描，结果没有策略批准或质量通过权限。

目标用例先因类型/函数缺失失败。模拟探测与显式选择真实 Ruff 的 7 项、边界 4 项、默认 Ruff probe 5 项、Python scan 6 项、runtime process 15 项/private log 6 项共 43 项通过。随后明确设置 CODEGUARD_RUFF_BIN，补跑原有两套各 5 项 ignored 真实 Ruff 0.16.8 扫描回归，共 10 项全部通过；没有把默认跳过当成通过。all-target Clippy（-D warnings）、格式、OpenSpec strict 与 diff 检查终态通过。

测试目录最初含 macOS 临时路径链接导致私有日志被拒，改用规范化路径而未放宽守卫。执行期间字节变化测试最初追加非法命令导致真实非零退出，修正成合法注释以验证零退出但制品变化。真实版本用例只调用版本；真实扫描用例单独证明已有局部 Ruff 配置/范围/报告行为，均不代表完整策略门禁。

doctor CLI、可信工具锁来源、完整兼容/环境诊断、其它适配器复用及准备报告持久化/同步仍缺；未运行完整 workspace、全语言或宿主端到端，5.2/5.6 不勾选。验收见相邻 codeguard-cli/tests/acceptance/native-version-diagnostics.md；完整计划保持进行中。

## 2026-09-26 doctor 局部配置/Ruff 入口

新增 doctor 命令及 human/JSON 反馈；默认只观察项目配置，工具未选择不等于缺失。仅显式绝对路径 Ruff 进入固定版本参数探测，复用统一 runtime、0700 私有临时运行区及空继承环境。单探测上限 10s 并受剩余总预算约束（默认 2m，静态发现非硬预算覆盖）；脚本入口无隔离时启动前拒绝，Mach-O/ELF 格式筛选不代表批准或网络隔离。本地原生成功仅 observed_untrusted、版本 Ruff 0.16.8，公开输出无工具/临时路径或原生文本；readiness unknown、交付 not_evaluated、quality_checks not_run、gate_effect none。取消退出 130，其它局部状态退出 3。

目标行为缺失时三个用例因没有 JSON 输出失败；实现后 doctor 6 项（含显式真实 Ruff）、版本观察 7 项、初始化 41 项、工具核验 8 项、边界 4 项共 66 项通过。四份实际 CLI 未选择/缺工具/脚本拒绝/原生版本输出及项目摘要通过 doctor 0.1 和现有 init 摘要 schema；7 项伪造批准、ready、交付、质量执行、门禁、保存或必需策略反例拒绝。all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查终态通过。

临时日志仅本次观察使用，不写 codeguard/ 或导入准备任务，persistence=not_saved；输出不是正式 PrerequisiteReport。可信锁/必需前置绑定、其它工具与运行环境、完整隔离/预算覆盖、持久报告与 work sync/next 仍缺。未运行完整 workspace/全语言原生或宿主端到端，5.2/5.6 不勾选；验收见相邻 codeguard-cli/tests/acceptance/doctor-local-ruff.md，完整计划继续实施。

## 2026-09-26 doctor 报告持久化与稳定环境任务

doctor 0.2 已在绑定工作区保存不可变报告并自动同步；显式 Ruff 失败产生稳定环境调查任务，原因变化记录独立观察且不增生任务。未选择不制造必需缺失，真实 Ruff 版本恢复后原任务仍 open；next 返回 doctor 恢复路径，不修改无关源码。落盘 queued 与对话 synced_partial/backlog_update_failed 分开，报告不原地改写。导入检查严格字段、预算、工作区及未获授权状态，拒绝伪造批准/就绪；保存目录链接被拒。旧检查器没有新增 null 诊断字段。

目标回归 54 项通过、10 项 ignored；CODEGUARD_TEST_RUFF 明确指向本机 Ruff 0.16.8，doctor 原生版本与恢复用例实际运行。10 份实际输出/落盘记录通过公开 schema；6 项伪造授权与通过反例拒绝。首次 Clippy 指出函数置于测试模块之后；移动时误放入局部函数，编译检查发现后改至模块级。最终 all-target Clippy（-D warnings）通过，格式、OpenSpec strict 与 diff 检查通过。详情见相邻 tests/acceptance/doctor-workspace-sync.md。

完整可信 PrerequisiteReport、批准义务/工具锁来源、其它工具、doctor 专用原生复检关闭及宿主端到端仍缺。没有运行全 workspace 测试、发布或安装，不勾选完整任务，目标保持进行中。

## 2026-09-26 doctor 环境任务原生复检

task verify 识别 python.ruff.doctor，复用固定版本诊断、剩余预算及报告同步，失败保留具体原因，未选择不推导恢复；成功仅 environment_restored_unverified_policy，原任务保持 open。next、同步时间序列及尝试账本接入 doctor 运行身份和严格报告分类。next 提示仅版本观察、核验批准前置并运行原受阻质量检查，未关闭或签发质量通过。

最初两个新增用例因不支持检查器失败；实现后 next 查询暴露尝试账本不识别 doctor run_id，补齐该消费者后通过。65 项相关测试通过、10 项 ignored；真实版本恢复用例显式指定 Ruff 0.16.8，默认不把未选原生环境算通过。12 份实际复检/原生/落盘/事件 schema 验证与 allow 篡改反例通过。all-target Clippy（-D warnings）及格式通过，OpenSpec strict/diff 检查通过。详见相邻 tests/acceptance/doctor-task-verification.md。

正式 PrerequisiteReport、可信义务来源、当前证据时效、全工具及正式关闭/重开尚缺；全 workspace 测试、其它原生与宿主端到端未运行，不勾选完整任务，目标保持进行中。

## 2026-09-26 tools list 声明库存入口

新增 tools list，共用有界锁读取、严格解析、三来源及独立运行时/发行包制品核验。稳定列出声明版本、适配器/规则来源、平台及具体制品缺口；其它平台仅 not_inspected，候选锁不获得必需策略或准备权限。公开报告固定 declared_lock_only、required_inventory unverified、required_by_policy null、readiness unknown、gate none 与退出 3，不启动 wrapper、联网、安装或写工作区。现有 verify 报告字段保持。

四项入口缺失测试先失败，实施后六项库存用例加八项原有 verify、八项身份、六项配置，共 28 项通过。五份实际库存 schema 验证覆盖缺锁、三来源及其它平台，五项批准/就绪/必需/门禁篡改被拒。all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/tools-list-command.md。

可信完整必需库存、tools install 与发行恢复未实现，全 workspace 测试/原生启动/宿主端到端未运行；5.6 保持未完成，继续原目标。

## 2026-09-26 受管安装原子缓存发布基础

新增 runtime 冻结字节发布 API，128 MiB 上限、非零预期 SHA-256、取消/预算检查；缓存根归属和权限检查，固定目录 FD 独占暂存、0700、同步/重读校验、linkat 不覆盖原子发布、最终普通文件再核验。正常清理本次暂存，不删除遗留/冲突目标；相同制品重新核验后复用。收据不表达批准或质量状态，正式来源批准/下载/CLI 尚缺。

初始五项测试因 API 缺失失败；补齐后十项普通发布用例通过，覆盖摘要、取消、期限、链接/FIFO、权限、硬链接、超限、遗留及并发恢复。fresh_report/private_log/边界/身份/工具 CLI 相关用例共 53 项通过。另显式指定本机 Ruff 0.16.8，1 项原生临时缓存发布及统一版本观察实际通过；未用默认 ignored 代替执行。all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/tool-cache-publication.md。

该基础不证明可信发行来源或全平台安装；不可中断文件系统调用和同用户改写不具有强隔离保证，发布后失败可保留完整制品并需重验。未运行全 workspace/Windows/网络下载/压缩包/宿主端到端，不勾选 5.3/5.6，继续完整目标。

## 2026-09-27 tools install 候选预览与 apply 边界

新增显式 --lock、默认 dry-run 的安装预览入口，共用有界静态锁/制品核验。候选报告绑定锁、二进制和来源引用摘要，区分当前/其它平台及恢复动作。来源尚未批准时 apply 明确 blocked_before_mutation，不启动、下载、写入或调用发布服务，固定 unknown/unverified/无门禁效果。

三个入口用例先失败；实施后工具 CLI/身份/配置共 32 项通过。三份实际输出 schema、两种模式冲突和四项伪造完成反例通过；all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/tools-install-preview.md。可信源披露/批准、下载、发行包、正式 apply 与全平台/宿主验收仍缺，全 workspace 未运行；5.3/5.6 不勾选，目标继续。

## 2026-09-27 发行清单解析与精确锁绑定

新增 distribution-manifest 1.0 schema、严格有界解析及绑定 API，核对锁原始字节和精确制品身份；绑定重新验证对象，raw 交叉字段及两种归档相对入口分别限定。http 1.5.0 只解析 URI，无网络客户端；新增依赖边界验证。

11 项契约与 4 项 crate 边界通过（无 ignored）；schema 4 正例/16 反例通过，all-target Clippy（-D warnings）通过。详细验收见相邻 tests/acceptance/distribution-manifest-binding.md。清单只表达声明子集；可信来源、下载、展开及正式 apply/CLI 接线仍缺，5.3/5.6 不勾选，完整目标继续。未运行全 workspace 或宿主端到端。

## 2026-09-27 tools install 显式清单预览

新增 --distribution-manifest FILE，0.2 报告及旧 0.1 schema 保留；有界读取、严格解析、原始锁精确绑定，固定状态和逐工具脱敏包声明。子集声明不证明其它工具/独立运行时覆盖，apply 继续写前阻塞。

22 项 CLI、11 项清单、4 项边界共 37 项通过；7 份实际报告 schema 和 4 项伪造权限反例通过。见相邻 tests/acceptance/tools-install-manifest-preview.md。可信下载、展开、批准发布、完整 apply/宿主验收仍缺，5.3/5.6 不勾选；未运行全 workspace，目标继续。

## 2026-09-27 展开前发行包流验证

新增 runtime 有界包流校验 API，精确大小、SHA-256 和共享截止时间；超长最多读取声明加一，读取前后检查预算/取消，中断继承预算，固定脱敏失败。验证只是冻结字节，不授予发行来源或安装权限。

6 项初始缺 API 测试失败，补齐及扩充后包流 9 项和缓存发布 10 项通过。临时缓存串联验证 raw 字节发布/复用；错误包不进入发布。1 项原生 Ruff 用例本轮 ignored，未计运行。all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/package-stream-verification.md。网络层单次超时、HTTPS/TLS、可信下载及归档/正式 apply/宿主仍未接通；全 workspace 未运行，5.3/5.6 保持未完成，完整目标继续。

## 2026-09-27 静态输入 FIFO 卡住修复

先以独立子进程复现共享静态读取器在无写入端 FIFO 的 open 上阻塞，父进程超时后终止并回收，回归失败。Unix 打开增加 O_NONBLOCK/O_CLOEXEC，仍拒绝目标链接，并由同一句柄类型/大小检查拒绝特殊输入。

修复后 runtime 库 4 项、真实 FIFO 读取 1 项、CLI 命令 23 项和 crate 边界 4 项，共 32 项通过，无 ignored。CLI 中 install 的锁及清单 FIFO 均明确 unreadable/退出 3，不写工作区、无准备通过。格式、OpenSpec strict/diff 检查通过；见相邻 tests/acceptance/bounded-input-fifo.md。

此修复不保证任意文件系统硬超时或 Windows 特殊文件语义，未完成发行授权、网络下载、归档、正式 apply/宿主验收；全 workspace 未运行，完整目标继续。

## 2026-09-27 ZIP/tar.gz 内存展开基础

新增 runtime 归档请求/冻结文件及内存展开 API，固定 tar/zip/flate2 Rust 后端依赖且只允许 runtime 普通依赖接入。核对包/入口摘要，全成员路径、文件类型、重复/大小写/祖先冲突；最多 10000 成员、512 MiB 文件预算，tar 头和填充另给有界 16 MiB。gzip/ZIP 完整读取、损坏与隐藏尾部拒绝，ZIP 注释仍支持，SFX/加密/不支持算法及 tar GNU/PAX 等明确未完成。

三项缺 API 测试先失败，补齐后归档逐步扩充至 11 项；两格式均实际串联包流校验→内存展开→临时受管缓存发布。相关包流 9 项、缓存 10 项、crate 边界 5 项、清单 11 项和工具 CLI 23 项通过，共 69 项（1 项原生工具 ignored 不计运行）。见相邻 tests/acceptance/package-archive-expansion.md。

尚未实现全 tar 扩展、bundle 树核验/完整目录发布、实际下载、可信发行批准或正式 CLI apply；当前工具链不等于实际 MSRV/全平台验收，未运行全 workspace/宿主端到端。5.3/5.6 不勾选，完整目标继续。

## 2026-09-27 GNU/PAX 有界局部扩展

新增 TarExtensionState，逐记录精确长度及完整消费校验，GNU 有界 NUL 路径、局部 PAX path/size、无害全局描述。拒绝危险/重复/矛盾/孤立扩展、大小溢出及不支持的全局路径/大小、sparse/linkpath/字符集变换；不恢复权限、时间、所有权或 xattr。

两项正例先因不支持类型失败；PAX size 合法覆盖旧头又因相等限制失败，随后改为用 tar 头字段解析与校验和核对、按生效大小推进实际数据边界。标准 tar 迭代交叉核对旧头为零而 PAX size=4 的样本及后续 LICENSE 边界。完整 GNU UTF-8 路径覆盖旧头截断字节回归通过，局部扩展不跨成员。

归档 17 项、包流 9 项、缓存发布 10 项、crate 边界 5 项，共 41 项通过；1 项原生缓存用例 ignored 不计运行。最终 all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/tar-extension-verification.md。全局 PAX/sparse/链接、bundle/目录发布、可信下载批准、CLI apply 与全平台/宿主尚缺，全 workspace 未运行；5.3/5.6 不勾选，完整目标继续。

## 2026-09-27 完整内存树与既有 bundle 摘要关联

新增 UnpackedArchive、完整树展开入口及内存 hash/verify；保留空目录、补全父目录，旧文件集合接口仍可用。公开对象重验规范路径/父目录/冲突/总量，单文件和树资源边界与既有本机 bundle-tree-v1 对齐；按本机 Path 排序及原目录栈顺序记录，内容按块检查共享预算/取消。

三项初始 API 缺失测试失败；实施后真实临时目录和内存树摘要精确相同，乱序不变、库篡改/空目录缺失/伪造形状/无效预期摘要/取消到期均拒绝或失配。两种归档验证空目录及隐式父目录保留，父目录大小写冲突拒绝。归档 19、包流 9、缓存 10、原有制品身份 8、边界 5、完整树 3，共 54 项通过；1 项原生缓存用例 ignored 不计运行。最终 all-target Clippy（-D warnings）、格式、OpenSpec strict/diff 检查通过。见相邻 tests/acceptance/unpacked-bundle-tree.md。

此处仅本机内容等价验证，不是可信批准或正式安装。包前缀到锁 bundle 根的映射、完整目录原子发布、网络下载/批准、CLI apply/恢复及全平台/宿主尚缺，全 workspace 未运行；5.3/5.6 不勾选，完整目标继续。

## 2026-09-27 显式归档目录投影

完整原树先验证，显式规范目录按路径边界去前缀；选中空目录保留，未消费成员以原路径和内容返回，不复制文件内容。只读投影核对既有 bundle 树摘要，不授予来源或安装批准。初始四项契约因 API 缺失失败；实施后 projection 4、归档 19、包流 9、缓存 10、完整树 4、制品身份 8、crate 边界 5，共 59 项通过。包括投影实际写入临时目录与既有 CLI 摘要一致，以及兄弟目录、非法外部成员、缺根/错根、篡改和取消/预算反例。1 项原生缓存用例 ignored，不计运行。all-target Clippy -D warnings 通过。详见相邻 tests/acceptance/bundle-root-projection.md。

正式发行清单映射、可信来源、实际下载、目录发布、CLI apply/恢复及平台/宿主验收仍未完成；未运行全 workspace，5.3 不勾选。

## 2026-09-27 发行清单 1.1 与 bundle 内容关联

两项清单测试先因不支持版本/字段失败，三项内容关联测试先因 API 缺失编译失败。实现后清单 13、关联 3、安装观察回归 23，共 39 项通过。固定 ZIP 实测包大小/摘要、精确入口、完整树与指定 bundle 根；错包/入口/根/锁、缺映射、取消和到期均拒绝。schema 4 正例/10 反例通过，旧 1.0 schema 单独保存。all-target Clippy -D warnings、格式检查通过。见相邻 tests/acceptance/distribution-bundle-binding.md。

内容关联不授予批准或安装完成；实际缓存根映射、可信来源/下载、目录发布、CLI apply/恢复与平台/宿主验收仍缺，未运行全 workspace，5.3 保持未完成。

## 2026-09-27 完整工具目录发布基础

新增 macOS/Linux publish_tool_bundle、目录 FD I/O、独占暂存清理与 InstalledBundle。冻结完整树/预期摘要先验证；成员以 0700 写入，文件/目录同步并重新比较成员集合、内容及类型/权限/单链接，原生独占重命名发布，不覆盖已有目标。最终再次核验，同树并发只有一个新发布，另一方核验后复用。发布收据不包含批准权威。

初始 5 项 API 缺失编译失败；实施后 6 项目录发布、4 项投影、10 项已有缓存及 57 项 CLI 相关测试，共 77 项通过。1 项原生缓存 ignored，不计运行。包括真实暂存出现后取消清理，以及固定发行包经清单/锁/入口/子树关联后发布，并与既有磁盘 bundle 摘要精确一致。Clippy 曾指出新增测试无用闭包/单位绑定，已修正，重跑串联 4 项和最终 all-target Clippy -D warnings 通过。OpenSpec strict/diff 检查通过。

本机仅 macOS 实测；Linux/Windows、跨进程及故障注入全集、同权限恶意进程隔离未验收。缓存根到锁路径映射、未消费包成员与运行时、可信下载/批准、正式 CLI apply/恢复/宿主验收仍缺；未运行全 workspace，5.3 保持未完成。详见相邻 tests/acceptance/tool-bundle-publication.md。

## 2026-09-27 完整安装布局与原锁定位

清单 1.2 声明完整 install_tree_sha256，归档必需/raw 禁止，旧 1.0/1.1 保持观察但不能猜布局。绑定精确锁入口和可选 bundle 根到同一完整树内容寻址目录，不重写锁。只读布局保留全部原包路径/普通成员/空目录，核验完整树及可选子树；空包内根与无 bundle 均可核验。

新增契约先因 API 缺失编译失败；5 项包/布局、14 项清单、23 项观察、8 项制品身份、5 项边界，共 55 项通过。实际临时缓存发布后原锁的入口摘要/基础可执行位和 bundle 摘要一致。bundle 外内容不符即使重建相符声明/锁路径也被完整树拒绝，错入口/根亦拒绝。schema 5 正例/7 反例与 all-target Clippy -D warnings 通过；增强精确错误码后目标契约重跑通过。见相邻 tests/acceptance/distribution-layout-binding.md。

正式 CLI 布局反馈、可信来源/下载、raw/运行时安装、恢复及其它平台/宿主尚缺；未运行全 workspace，5.3 不勾选。

## 2026-09-27 安装布局预览反馈 0.3

新契约先因反馈仍是 0.2 失败；新增脱敏 layout 投影与 JSON/human 阶段解释，完整声明绑定、缺完整树及 raw 不适用分别显示，内容核验 not_run，未批准 apply 不写入/不准备/不放行。0.2 schema 独立保存，新枚举覆盖 bundle/完整布局错误原因，禁止格式/阶段矛盾。

24 项命令、14 项清单、5 项包/布局、5 项边界，共 48 项通过；补 human 与 raw 断言后命令 24 项再次通过。最终 schema 的 8 份真实命令输出通过；4 个伪造批准/准备/写入/内容完成与 2 个阶段矛盾被拒，旧 schema 拒绝新版本。all-target Clippy、目标 Clippy、格式检查通过。见相邻 tests/acceptance/tools-install-layout-preview.md。

来源批准、实际包下载/核验/安装、raw 定位、恢复与平台/宿主仍缺；未运行全 workspace，5.3/5.6 保持未完成。

## 2026-09-27 raw 内容与原锁缓存定位

新增 1.2 raw 精确入口约束和不可变借用内容 API；旧清单不猜定位，错误路径连同相符来源摘要仍拒绝，包长度/摘要/原锁字节与共享期限/取消均核对。结果不复制制品内容，Debug 不输出原字节，不赋予来源/门禁权威；预览相符新版定位指向后续包内容核验，旧版要求映射，content_verification 仍 not_run。

初始因 API 缺失编译失败；4 raw、14 清单、5 包/完整布局、25 命令、5 边界，共 53 项普通测试通过。另显式 CODEGUARD_TEST_RUFF=/opt/anaconda3/bin/ruff 执行真实 0.16.8 字节关联/临时私有缓存发布/runtime 原生版本观察，1 项通过，2.17 秒。该未批准测试声明未下载或执行 lint，不证明规则覆盖/发行批准。4 份实际 raw 预览 schema 与伪造内容完成反例通过；all-target Clippy -D warnings 通过。见相邻 tests/acceptance/distribution-raw-binding.md。

可信来源/真实下载、运行时安装、正式 apply/恢复和平台/宿主仍缺，未运行全 workspace，5.3 保持未完成。


## 2026-09-27 有界 HTTPS 包传输

新增冻结请求与异步 runtime API，采用 TLS 验证、精确长度/摘要、五跳手动 HTTPS 重定向、显式 authority 范围、共享绝对期限/取消和固定诊断。不采用环境代理、自动重试或内容解压，不写缓存、不授予来源/安装权威。仅 cfg(test) 信任本地测试 CA；生产无根替换/关闭验证参数。

API 缺失先编译失败，TLS 正例在测试服务显式清除 macOS 接受连接的非阻塞继承后通过。加强反例要求请求已到达且诊断精确；gzip, chunked 新例先意外返回成功，生产增加编码校验后通过。11 TLS 与 96 相关不同回归通过；两个真实 Ruff ignored 不计已运行。154 已缓存 registry manifest 无高于 1.85 的声明，14 非本机/wasm 未缓存未核验；不是实际 1.85 或跨平台验证。见相邻 tests/acceptance/package-https-transport.md。

完整发行源/网络授权、清单到下载及发布正式接线、运行时安装、apply/恢复与宿主仍缺，未运行全 workspace，5.3 不勾选。

最终 runtime/CLI all-target Clippy -D warnings、cargo fmt --check、OpenSpec 严格校验与插件 git diff --check 均通过。


## 2026-09-27 下载归档完整树及临时发布串联

新增 download_verified_archive，请求前校验包声明一致及展开输入，下载后原归档解析与入口/完整树核验使用共享预算。新测试最初因 API 缺失失败，实现后 15 HTTPS 目标项通过；新增 ZIP/tar.gz 和 raw 实际本地 TLS 至私有临时缓存证据，空目录/入口完整，错误树/包摘要拒绝，声明冲突/坏展开输入不发请求。见相邻 tests/acceptance/downloaded-package-publication.md。

来源与网络授权、正式 CLI 下载到安装编排、运行时/恢复、远端发行源及全平台/宿主仍缺，5.3 不勾选，未运行全 workspace。

最终回归：runtime 单元 19、归档 19、完整树发布 6、raw 缓存 10，共 54 项通过；1 项真实 Ruff ignored 不计已执行。runtime all-target Clippy -D warnings、格式、OpenSpec 严格校验及插件 diff 检查通过。


## 2026-09-27 发行专属签名与清单/锁绑定

新增独立 distribution.v1 Ed25519 域和版本化载荷/封装，精确固定原始清单/锁、范围、序号和有效期，并继续严格制品绑定。API 缺失先编译失败；8 项目标签名契约覆盖篡改/协议重放/失效或撤销/回滚/范围/坏清单锁/输入限制。两份 schema 结构正例与必填缺失/未知批准反例单独校验，不等于密码学验证。见相邻 tests/acceptance/signed-distribution-binding.md。

独立宿主真实信任来源、轮换撤销及防回滚持久状态、网络许可、最终时钟和正式下载/install 编排仍缺，5.3 不勾选，未运行全 workspace。

最终验证：签名 8、清单 14、完整布局 5、raw 4、tools 预览 25，共 56 项通过；1 项真实 Ruff ignored 不计运行。两份 Schema 2 个结构正例/15 个缺字段或未知批准反例通过。CLI all-target Clippy -D warnings、格式检查、OpenSpec 严格校验和插件 diff 检查通过。


## 2026-09-27 签名发行包与缓存发布编排

新增明确调用的离线包编排，绑定签名/原始锁与清单、本机平台和精确工具；raw 与完整归档布局在同一预算下核验并调用受控缓存发布，入口保持原锁。前/发布前/发布后可信时钟与签名复核，取消和截止共享，发布后失败不返回成功且重试必须重验。5 项目标契约先因缺 API 失败、实现后通过，见相邻 tests/acceptance/signed-package-publication.md。

真实宿主信任/撤销及防回滚来源、网络授权、正式 CLI 下载至安装编排、运行时/恢复、其它平台/宿主仍缺，5.3 不勾选，未运行全 workspace。

最终验证：发布编排 5、签名 8、完整布局 5、raw 4、tools 预览 25，共 47 项通过；1 项真实 Ruff ignored 不计运行。CLI all-target Clippy -D warnings、格式检查、OpenSpec 严格校验及插件 diff 检查通过。


## 2026-09-27 签名网络下载及缓存发布编排

新增网络服务请求前核对签名/本机平台/精确工具/清单 1.2/宿主精确 authority，下载后进入签名包发布服务共享预算。前置五类反例无写入；显式固定 Rust 官方仓库提交 LICENSE-MIT，以测试 key/时钟调用生产公共 TLS 客户端，真实下载及临时发布 1 项通过（0.70 秒），内容不执行，未替代真实发行根。见相邻 tests/acceptance/signed-network-publication.md。

真实宿主信任/网络许可来源、正式 CLI apply 接线、原生工具包/运行时/恢复与全平台仍缺，5.3 不勾选，未运行全 workspace。

最终回归：网络前置 1、签名 8、发布 5、tools 预览 25、runtime HTTPS 15，共 54 项普通测试通过；另 1 项显式真实公共 HTTPS 下载发布通过。CLI/runtime all-target Clippy -D warnings、格式、OpenSpec 严格校验与插件 diff 检查通过。


## 2026-09-27 Javadoc 明确 Maven 模式不回退单文件

真实 First 引用 Second 样本先复现孤立 JDK 探针的无关 native_execution_incomplete；现在明确 Maven 时只运行原 POM 多文件检查，缺前置保留具体原因而不回退，未选择 Maven 的 JDK 局部模式保留。反馈 0.23.0/Javadoc 0.3.0 显式区分模式及检查器，旧 schema 单独保留。真实警告与文档完整两轮均成功，不签发项目覆盖；两份实际反馈 schema 正例及四个混合模式/错检查器反例通过。见相邻 tests/acceptance/javadoc-project-mode-selection.md。

并行回归的 schema 旧版本断言已更新；另取消用例未在两秒内观察到任务齐备，独立重跑通过但根因未定位，不能声称消除。生效模型/类路径/生成源码/Checkstyle/任务门禁等仍缺，6.3 不勾选。

最终验证：Java check 24、partial 13（随后串行）、Javadoc CLI 4，共 41 项普通测试通过；另 3 项明确执行的真实 Maven/JDK 测试通过。2 个实际 Maven 报告与 1 个实际 JDK 单文件报告通过新 schema，4 个混合模式/错检查器反例被拒，旧 schema 拒绝新版。CLI all-target Clippy -D warnings、格式、OpenSpec 严格校验和插件 diff 检查通过。取消用例先前一次并行启动窗口失败仍未归因，不作为已解决问题。

## 2026-09-27 取消夹具准备屏障

受控慢准备复现旧断言失败，但实际报告确认两个任务已启动；旧 Rust 标记代表诊断准备而非启动。仅修正测试夹具，分离准备窗口与取消屏障并回收失败子进程，仍核验退出 130、诊断保留与子孙进程无迟到写入。默认并行 partial 13 项通过；随后三份受影响测试共 41 项通过、8 项真实工具未执行，Clippy 通过。见相邻 tests/acceptance/cancellation-preparation-barrier.md。此前偶发失败的主机负载原因未独立证实；生产取消代码未修改，完整 OpenSpec 任务不因此勾选。

## 2026-09-27 Checkstyle XML 纯解析

6.3 新增 Checkstyle 原生 XML 的 Rust 有界解析，保留完整 source/模块 ID、严重度、文件级零行与可选列；异常与无文件事件不制造源码违规。先因缺 API 编译失败，再完成协议夹具正反例。适配器整包回归 89 项通过、8 项原生工具未执行（其中 Checkstyle 当时 5 项）；随后新增边界及混合异常断言，最新 Checkstyle 6 项全部通过。格式、adapter all-target Clippy -D warnings、OpenSpec 严格校验与插件 diff 检查通过。见相邻 tests/acceptance/checkstyle-xml-observation.md。

未执行真实 Checkstyle，原生执行/配置/范围/报告 freshness、任务/白名单/门禁和完整 Java 注释正反例仍缺；6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 原生参数和版本差异

参数规划先因缺 API 编译失败，新增 Rust CheckstyleCommand 后 2 项契约通过；XML 6 项回归通过。新增显式 Java/10.21.4 JAR 原生正反例入口，20 秒截止与回收/临时清理，但本机相关缓存没有找到 JAR，1 项真实测试未执行。原生源码核对发现 10.21.4 自定义 ID 在 source 中单独输出，修正了原生验收断言，并新增旧版 ID 原样保留测试；不猜测规则类名。adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验与 diff 检查通过，见相邻 tests/acceptance/checkstyle-native-command.md。生产执行及正式配置/任务/门禁仍未完成，6.3 不勾选。

## 2026-09-27 Checkstyle 真实运行与配置纠偏

从官方固定 release 获取临时测试 JAR，内容摘要见相邻 checkstyle-native-command.md；该摘要是本地观察，不是发行批准。真实测试先因无 DOCTYPE 的配置被原工具拒绝且无报告失败；采用原版 ConfigurationLoader 映射的内置标准 DTD 后，将验收调用接入统一 runtime 新鲜报告/私有日志/清空环境/20 秒截止。真实公共类型、缺 @param/@return、自定义模块 ID 及补全文档两轮 1 项通过（0.63 秒）；另参数与解析 8 项通过。adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验和 diff 检查通过。

没有任意项目配置的独立网络隔离或身份/范围证明；生产 Checkstyle 服务/正式 CLI、完整 Java 注释变体、任务/白名单/门禁仍缺，6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 退出/范围判定

新增 Rust evaluate_checkstyle_report，独立版本/冻结文件集合/正常退出一致性；空或重复预期范围、实际范围不符、异常/坏报告/退出冲突保持未完成。warning/info 退出零和 Unix 256 错误退出截断均保留诊断，未知版本/平台不套用本契约。目标 API 缺失先编译失败，4 项契约通过；连同解析/参数共 12 项通过。真实 10.21.4/Java 21 通过统一 runtime 运行 error/clean/warning 三轮，实际 XML 均经新判定，1 项通过（0.81 秒）。256 错误为协议夹具，非真实大规模执行证明。

adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验和 diff 检查通过；见相邻 tests/acceptance/checkstyle-exit-scope-coherence.md。项目原配置/身份/范围权威及正式 CLI/任务/门禁仍缺，6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 输入绑定执行

新增单对象文件请求/结果与 runtime 编排，独立冻结四个不同物理路径摘要，执行前后复核且共同预算/取消贯穿。新鲜 XML/私有日志及原生范围退出已接线，输入变化保留局部报告但不产生完整结论。缺 API 先编译失败；4 项模拟契约覆盖配置中途变更、陈旧报告、摘要、截止取消和缺失/额外/别名身份，8 项 PMD 执行回归通过。另真实 10.21.4/Java 21 通过该生产服务进行缺注释/补全文档两轮，1 项通过（最终 4.93 秒）。CLI all-target Clippy -D warnings、格式、OpenSpec 严格校验与 diff 检查通过，见相邻 tests/acceptance/checkstyle-input-bound-probe.md。

该局部服务尚未接正式 CLI/project check；JDK 动态闭包、配置资源/自定义模块闭包、独立网络隔离、同用户篡改恢复竞争及可信原项目身份/规则范围仍未证明。完整注释变体、任务/白名单/交付门禁仍缺，6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 正式局部 CLI

lint java --checker checkstyle 接入显式 Java/JAR/原配置与私有源码/配置快照，结束复核原输入；仅已支持的静态注释配置可直接调用，其它上下文不替换默认规则。缺入口时目标断言先失败，接入后命令 2、Javadoc 4、配置识别 2 共 8 项普通测试通过；实际 binary/Checkstyle 10.21.4/Java 21 1 项通过（3.94 秒），显示 1 条公共类型诊断。两份实际缺前置/原生反馈 schema 正例与 4 个伪造权威反例通过。CLI/adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验和 diff 检查通过。见相邻 tests/acceptance/java-checkstyle-cli-local.md。

公开反馈 0.1.0 仍固定本地未核验、覆盖 false、交付 not_evaluated/退出 3；正式 project check、完整配置与工具闭包、所有注释变体、任务/白名单/门禁仍缺，6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 原生来源歧义纠偏

新增共享模块 ID 反例先复现旧配置识别错误接受；现在重复默认检查来源、共享自定义来源和同模块重复属性保持上下文待解析，不自动合并或选先/后值。同类检查的不同 ID 静态正例保留。真实 CLI 验证单规则原生诊断、两个模块共享 ID 时不生成活动 finding、改为独立 ID 后原生类型及参数/返回三条诊断，1 项通过（7.71 秒）。CLI 2、Javadoc 4、配置 3、退出/范围 4 共 13 项普通回归通过；CLI/adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验及 diff 检查通过。

见相邻 tests/acceptance/checkstyle-rule-source-ambiguity.md。该修正尚不证明批准规则/义务绑定、稳定任务或白名单门禁已接通；完整项目和配置上下文仍缺，6.3 不勾选，未运行全 workspace。

## 2026-09-27 Checkstyle 注释变体与生成范围

新增 MissingJavadocMethod/JavadocType 原模块识别，目标配置断言先失败后通过。实际 10.21.4/Java 21 CLI 验收 record 参数文档正反例、带参数/返回的 inheritDoc、Override/Generated 默认例外及移除注解的缺文档，保留同一行类/方法及单行方法体的原生行为差异；最终该真实用例通过（28.63 秒）。前两次期望 missingMethod 的断言失败，随后保持原生输出并新增多行方法体的正例，不删除诊断、不自动批准白名单。

另真实 Lombok 1.18.38（缓存 Manifest 与本地摘要核对）delombok 对照用例通过：原 @Getter 文件零诊断，展开 getter 文件 missingMethod；路径保持展开范围，不冒充原注解行。两个真实用例分别通过，普通配置/退出/CLI/Javadoc 回归共 14 项通过。CLI/adapter all-target Clippy -D warnings、格式、OpenSpec 严格校验和 diff 检查通过，见相邻 tests/acceptance/checkstyle-comment-variants.md。

样本不能证明所有 record 构造器、继承形式或 Lombok 注解/版本/编译类路径；生成来源、完整项目/规则范围与任务/白名单门禁仍缺，6.3 不勾选，未运行全 workspace。

## Checkstyle 修复反馈关联增量

局部反馈升级 0.2.0；普通 CLI 两项、绑定两项与真实 10.21.4 CLI 一项通过。验收说明见相邻 codeguard-cli/tests/acceptance/checkstyle-repair-feedback-binding.md。此增量不完成 6.3 的完整配置、项目覆盖与门禁。

补充验证：配置/退出范围/XML 回归 14 项通过，CLI/适配器全目标 Clippy 与格式检查通过；schema 两份真实输出通过、五个错误变体被拒、旧 0.1 消费者拒绝 0.2。首次路径断言按未规范化临时目录比较失败，改为规范化原输入路径后通过；未修改产品路径行为。OpenSpec 严格校验和差异空白检查通过。

## Checkstyle 显式工作台连接

新增局部报告、稳定 finding 导入、可读任务与 next 修复依据恢复；任务关闭与完整宿主门禁尚未完成。TDD 与历史收据误报修复详见相邻 codeguard-cli/tests/acceptance/checkstyle-local-workbench.md。

本轮最终验证：25 项普通回归通过；一项真实 Checkstyle 10.21.4 工作台回放通过（10.53 秒），覆盖同任务重复扫描、无关空行、配置变化、手工勾选及陈旧新报告拒绝。四份实际产物 schema 通过，三种错误授权/关闭变体及旧 0.2 消费者拒绝新反馈。CLI 全目标 Clippy、OpenSpec 严格校验及差异空白检查通过。

## Checkstyle 稳定任务原工具复检

34 项普通回归、六轮真实复检及工作台真实回归通过。暂未检出、规则失配和工具失败均不关闭任务；首次工具身份固定，后续观察不自授权。实现与反例详见相邻 codeguard-cli/tests/acceptance/checkstyle-task-recheck.md。

补充协议验收：两轮真实 still_present/缺前置复检及对应 next 产物通过三个专用 schema；错误 coverage_proven=true 被拒。首次 next schema 仍沿用 Ruff 的 lint-复检 ID 和缺少 incomplete 枚举而拒绝真实输出，已改为 Checkstyle 专用 run ID 与明确未完成值；未放宽授权字段。CLI 全目标及后续局部变更 Clippy、格式、OpenSpec 严格校验和差异空白检查均通过。

## Checkstyle 环境准备槽位

新增稳定环境任务、最新诊断投影与同范围后续原生观察指引；普通来源/幂等/备注/范围反例及真实原工具回归见相邻 codeguard-cli/tests/acceptance/checkstyle-preparation-tasks.md。正式关闭、模块粒度与可信批准仍未完成。

最终验证：27 项普通回归通过；已有源码工作台真实回归通过（10.03 秒），准备恢复真实回放通过（8.36 秒）。四份实际反馈/观察/任务/next 产物 schema 通过，旧 0.3 消费者拒绝新反馈；取消观察的 schema 与导入反例拒绝。后续同范围原生观察和配置变化失效均按实际产物验证。全目标 Clippy、格式、OpenSpec 严格校验与差异空白检查通过。

## Checkstyle 环境准备任务复检

原工具 task verify 接通准备任务，局部恢复产生的原生源码 finding 进入稳定任务；仍受阻与恢复均保存原因/历史且保持任务 open。53 项普通受影响回归通过，真实 Java/Checkstyle 恢复回放通过（8.36 秒）；实际 blocked/recovered 报告、反馈与 next 专用 schema 通过，错误覆盖声明被拒。租约反例无执行与事件；临时工作区字段对历史读取的误报已修正。完整准备义务与可信关闭尚缺，详见相邻 codeguard-cli/tests/acceptance/checkstyle-preparation-recheck.md。

本轮最后检查：Rust 全 workspace/all-targets Clippy（-D warnings）、格式检查、OpenSpec 严格校验和插件差异空白检查通过；不扩大为完整计划验收。

## Checkstyle 准备尝试无进展闭环

专用测试先复现失败复检导致第二次修复 task_not_actionable，随后修正有效输入下的前置恢复指引。两轮 ready-to-verify 的 still_blocked 原生复检各自绑定尝试并计入预算，第三次重复动作被拒，next 要求决策且任务 open；源码变化反例仍要求复检。29 项相关普通回归与显式真实恢复回放（9.28 秒）通过，详见相邻 tests/acceptance/checkstyle-preparation-recheck.md。正式关闭与完整义务仍未实现。

## Checkstyle 恢复尝试交接与工具观察失效

真实准备恢复事件关联 ready-to-verify 尝试，解除等待状态且保留开放任务；修改测试复制 JAR 的字节后旧恢复结论不能继续用于 task show/next。原反例在正确 task 字段上复现旧恢复仍显示，产品修复后扩展回放通过（10.28 秒）。39 项普通受影响回归、CLI 全目标 Clippy（-D warnings）、格式、OpenSpec 严格校验与插件差异空白检查通过；仍不代表批准或正式关闭。

本轮后续六轮真实 Checkstyle 源码复检回归通过（45.25 秒），未扩大为完整项目验收。

## Checkstyle 失效原因与状态消费者

原复检原因与当前输入失效原因分开，status 任务摘要保留二者；真实 JAR 改动和删除回放通过（9.77 秒）。17 项普通相关回归、CLI 全目标 Clippy、格式、OpenSpec 严格校验与差异空白检查通过。实际反馈/简报/status schema 通过，覆盖伪造和任务 closed 变体被拒；不代表完整批准与关闭协议。详见相邻 tests/acceptance/checkstyle-preparation-recheck.md。

## Checkstyle 当前失效优先于历史 still_present

真实配置改动反例先复现失效状态被旧 still_present 覆盖成 actionable。调整当前工具、配置、已绑定源码核对的优先级后，扩展六轮真实回放通过（57.00 秒），覆盖配置注释和源码空行变化后的 task show。33 项普通相关回归、实际三类失效简报/schema、CLI 全目标 Clippy、格式、OpenSpec 严格校验及差异空白检查通过。任务保持 open，完整义务和可信关闭仍缺；详见相邻 tests/acceptance/checkstyle-task-recheck.md。

## 原生字段 Javadoc 适配

增加 JavadocVariable 精确原配置绑定和本版 scope/excludeScope/ignoreNamePattern 原参数；原生报告生成字段修复任务并支持同任务复检。TDD 暴露未知类与范围参数被拒后完成修正。26 项普通回归、三轮真实字段回放（24.99 秒）、实际字段 finding/任务/复检/失效简报 schema、覆盖与关闭伪造反例通过。CLI/adapter 全目标 Clippy、格式、OpenSpec 严格校验及差异空白检查通过。只验证 public 范围与指定忽略/字段/局部变量边界，不冒充枚举常量及完整 Java 义务验收；6.3 保持未勾选，详见相邻 tests/acceptance/checkstyle-field-javadoc.md。

## 字段访问范围与原生必需 token

静态 JavadocVariable tokens 支持经 TDD 先失败后实现，未知 token 和跨模块借用拒绝。七组真实范围/枚举回放通过（32.86 秒）；scope public/protected/package/private、excludeScope、配置字段 token 和配置枚举 token 的结果逐项核验。固定 10.21.4 JAR 的 getRequiredTokens 返回 VARIABLE_DEF，因此仅枚举配置仍检出字段，修正规格和预期而不篡改原输出。同行枚举 Javadoc 被原工具检出的首次假设错误已记录，正常文档夹具改为独立行。17 项普通回归、全目标 Clippy、格式、OpenSpec 严格校验和差异空白检查通过。完整项目义务及其它语法仍缺，6.3 不勾选；详见相邻 tests/acceptance/checkstyle-field-javadoc.md。

## Checkstyle 官方名称与稳定任务归属

官方完整名称的纯绑定先因返回 None 失败，再完成固定名称映射；支持既有五类 Javadoc 检查的短名/Check 后缀短名/官方完整名及 Checker/TreeWalker 完整名。未知包名和同 source 的短名/完整名重复声明拒绝，原 XML 不重写。28 项普通相关回归、字段四轮真实名称与复检回放（21.95 秒）、CLI/adapter 全目标 Clippy、格式、OpenSpec 严格校验和差异空白检查通过。字段三种名称复用同一 finding/task，无伪配置 blocker；其余检查类本轮仅有名称绑定回归，完整配置及门禁仍缺。6.3 保持未勾选，详见相邻 tests/acceptance/checkstyle-official-module-names.md。

## MissingJavadocMethod 原配置参数

静态原参数绑定先因不支持返回 None 失败，实现后支持范围、注解、属性方法、方法长度和名称正则，原 XML 保留，非法及跨模块静态参数拒绝。19 项普通相关回归、四组真实配置筛选回放（19.03 秒）、CLI/adapter 全目标及最终夹具单测试 Clippy、格式、OpenSpec 严格校验和差异空白检查通过。单行非空方法不检出的最初误解由固定 JAR 行数/默认阈值逻辑核对后纠正，多行夹具区分属性 true/false；原工具规则未重写，零诊断不关闭历史任务。完整构造器/record/token 和项目生效模型仍缺，6.3 不勾选，详见相邻 tests/acceptance/checkstyle-missing-method-properties.md。


## 2026-09-27 MissingJavadocMethod 原生 token 选择

静态绑定新增模块限定的 METHOD_DEF/CTOR_DEF/ANNOTATION_FIELD_DEF/COMPACT_CTOR_DEF，跨模块或未知 token 不猜测。目标测试先失败，修改后绑定七项及配置四项通过；真实 Checkstyle 10.21.4/Java 21 五组选择与两次紧凑构造器复检共七轮通过（51.11 秒），稳定任务不重复、原生修复候选不关闭事实。见相邻 codeguard-cli/tests/acceptance/checkstyle-method-tokens.md。任务 6.3 仍未完成，未宣称完整项目或批准门禁。

该增量的 20 项普通目标/回归测试通过（adapter 11、CLI/workbench 9）；显式原生用例单独运行通过，不将其它 ignored 用例计入已运行证据。受影响两 crate 全目标 Clippy、cargo fmt --all --check、OpenSpec strict 与 git diff --check 均退出 0。


## 2026-09-27 Checkstyle 原始配置连续性

真实字段任务在增加 ignoreNamePattern 后原生零诊断，旧复检错误显示缺失候选；先 RED 后修正，简报现从首次摘要绑定报告恢复 original_configuration_input，classify 在问题缺失时核对首轮配置摘要，连续两轮配置排除要求 rule_coverage_requires_review。恢复原配置并实际补注释后仅给 candidate_absent_unverified_policy，事实仍 open。四轮原生执行通过（40.99 秒）；可选新增 schema 字段保留旧简报可读性，缺身份不沿用修复候选。语义等价配置、批准来源及正式关闭仍缺，9.7 不勾选。

该修正的 CLI/workbench 九项普通回归、实际原生准备/源码报告与简报 schema、全目标 Clippy、fmt、OpenSpec strict 和 diff whitespace 检查通过。token 矩阵原首轮使用全 token，后续使用仅紧凑构造器 token；其源码补文档后的期望须随本修正改为 rule_coverage_requires_review，早前该矩阵给出局部候选的验收结论不再代表当前行为。首次配置不变的字段修复正例仍给出局部候选。

最终代码下，调整期望的 token 矩阵七轮原生复跑通过（42.08 秒），目标测试 Clippy 与 fmt 再检查通过。


## 2026-09-27 JavadocMethod 原生标签参数

核对固定 Checkstyle 制品 API/token 后，新增 JavadocMethod 专属访问修饰符、允许缺参数/返回、throws 校验与共享注解/token 静态适配；未重写原 XML。合法参数测试先 RED 后修正，绑定八项及配置四项通过；真实六组原生配置按预期产生 4/2/2/0/2/5 项诊断，恢复首次配置后 still_present 与真实文档修复局部候选的两次复检通过，八轮共 57.23 秒。稳定事实保持 open，允许标签选项不自成白名单。全语法、项目配置/覆盖及批准仍缺，6.3 不勾选，验收见相邻 tests/acceptance/checkstyle-method-tag-options.md。

该增量 21 项普通目标/回归（adapter 12、CLI/workbench 9）通过；上述八轮原生测试单独显式运行通过，其它 ignored 用例不计入本轮运行证据。受影响两 crate 全目标 Clippy、fmt、OpenSpec strict 与 git diff --check 均退出 0；未修改反馈协议字段。


## 2026-09-27 原生类型注释配置

核对固定制品 API/token 后补齐类型检查范围/注解/标签参数，原 XML 不重写；合法参数先 RED 后修正，绑定九项及配置四项通过。十组原生配置按预期产生 MissingJavadocType 5/4/1/1 与 JavadocType 2/1/1/0/1/1 项诊断；恢复首次 typeTags 配置并真实修正文档复检形成局部候选，事件保存、事实均 open，十一轮 58.02 秒。作者/版本格式只有静态适配证据，其它 Scope/全部 token 语法、完整配置与批准覆盖仍缺，6.3 不勾选。验收见相邻 tests/acceptance/checkstyle-type-options.md。

该增量 22 项普通测试（adapter 13、CLI/workbench 9）通过；原生十一轮单独显式执行，其它 ignored 不计入本轮证据。Adapter 全目标和受影响 CLI 工作台目标 Clippy、fmt 检查通过。
OpenSpec strict 与插件 git diff --check 均退出 0。


## 2026-09-27 类型作者/版本格式及修复指引

原 JavadocType 指引只有参数核对，作者/版本诊断缺实际修复方向；目标断言先 RED，修正后保留项目事实及不编造约束。固定 10.21.4/Java 21 的原 author/version 正则对缺失、错误、部分及完整补齐产生 2/2/1/0 诊断，原配置 task verify 为局部候选；无效正则两轮保持 incomplete，配置准备任务只新增一次、无源码 finding，事实仍 open。七轮真实执行通过（38.35 秒）。静态绑定十项及配置四项通过；完整正则/标签变体、项目模型及批准门禁仍缺，6.3 不勾选。验收见相邻 tests/acceptance/checkstyle-type-formats.md。

该增量普通目标/回归共 23 项通过（adapter 14、CLI/workbench 9）；原生七轮单独显式运行，其它 ignored 不计入。Adapter 全目标与 CLI 工作台目标 Clippy、fmt、OpenSpec strict 和插件 git diff --check 均退出 0；未新增反馈字段。


## 2026-09-27 原生正则配置失败修复方向

核对固定原生 stderr 后新增有界纯失败分类：254 正常退出、官方非法属性和正则因果异常组合；只有不一致/缺失报告时细分，不向对话回显值或堆栈。公开反馈与准备简报新增正则配置修复方向。分类 API 缺失先 RED 后实现，probe 缺报告且输入变化再 RED 后修正为冻结输入/取消/截止优先；正常一致报告仍保留。真实七轮格式回放通过（38.75 秒），验证特定 reason、对话动作与准备简报，事实保持 open。未知失败/其它版本/完整项目及批准覆盖仍缺，6.3 不勾选，验收见相邻 tests/acceptance/checkstyle-regex-failure-guidance.md。

普通目标/回归共 49 项通过（adapter 15、probe 5、CLI/workbench 9、next 6、status/show 4、task verify 10）。原生七轮显式回放通过，另一次实际原生配置失败的反馈与准备简报 schema 校验通过；未计入其它 ignored。两 crate 全目标 Clippy 通过；随后缺报告输入变化修正的 CLI lib/probe Clippy 与五项 probe 回归通过。最终 fmt、OpenSpec strict 和 git diff --check 退出 0。


## 2026-09-27 ESLint JSON 原生报告协议原型

核对 ESLint 官方 formatter 与 exit/max-warnings 文档后新增按对象拆分的有界 Rust 解析，保留 warning 和有效规则，区分 fatal/无 ruleId/suppression，核对具体版本、文件集合和计数。API 缺失先 RED 后实现；dot 路径额外反例因 Path 组件折叠再 RED 后修正为原始段检查。此为协议夹具，未安装/执行 ESLint，未接通生效 JS 配置、TS parser/monorepo、Node 闭包、CLI/依赖及任务门禁；7.3 保持未完成。验收见相邻 tests/acceptance/eslint-json-observation.md。

最终 22 项目标/回归测试通过（ESLint 7、既有 Checkstyle 15）；adapter 全目标 Clippy、fmt、OpenSpec strict 与 git diff --check 均退出 0。当前原生 ESLint 执行为 NOT_RUN，JSON 夹具版本仅用于具体身份比较反例，不证明所标版本制品兼容。


## 2026-09-27 ESLint 原生字面命令计划

缺 EslintCommand API 先 RED 后补齐固定字面 argv；显式 Node/JS/原配置/完整源码/独立报告与可选 max-warnings，禁用自动配置查找，不 Shell/npx/隐式改源码。四项路径/参数/重复/冲突/预算契约通过。显式 Node 24.18.0 的统一 runtime argv 观察脚本通过（0.05 秒），保留 metacharacters 字面、源文件/配置原字节，无 Shell 展开；不等于 ESLint 原生执行。闭包、物理别名、有效项目配置、ESLint/TS/monorepo/CLI/依赖及批准仍缺，7.3 不勾选，见相邻 tests/acceptance/eslint-native-command-plan.md。

最终 13 项普通目标/回归通过（ESLint 命令 4、报告 7、Checkstyle 命令 2），Node 字面 argv 原生测试另行显式运行通过；ESLint 原生仍 NOT_RUN。Adapter 全目标 Clippy、fmt、OpenSpec strict 和插件 git diff --check 均退出 0。

## 2026-09-27 ESLint 输入绑定受控执行

Rust 公开执行服务现通过统一 runtime 运行显式 Node/ESLint JS 入口的版本探测与扫描。完整显式摘要集合、物理路径、精确稳定版本、安全 run_id、私有新鲜报告、共享截止时间/取消和扫描前后输入复核均接入；错误不转换为源码违规。缺 API 编译 RED 后补齐模块与入口。初次实际 Node 夹具因原10秒预算在调试摘要校验阶段耗尽返回未完成；正常测试改60秒，独立截止时间拒绝反例保留。

最终19项普通目标/回归测试通过（ESLint 命令4、报告7、执行前检查1、Checkstyle 命令2及执行5）。实际 Node 七种受控 JSON 模式单项测试113.72秒通过，包括干净、warning、error、坏报告、错版本、扫描时输入变化、退出2/缺报告。它是项目自有JS夹具，不是 ESLint 原生检查；原生 ESLint NOT_RUN。CLI lib/新执行测试 Clippy、adapter 全目标 Clippy、fmt、OpenSpec strict 和插件 git diff --check 均退出0。验收见相邻 tests/acceptance/eslint-input-bound-probe.md。

JS配置/插件闭包、TS parser/tsconfig、monorepo、可信工具和项目有效配置、公开CLI/依赖审计及完整任务门禁仍未完成，7.3保持未勾选；局部执行一致不授予覆盖或白名单权威。

## 2026-09-27 ESLint 运行中断诊断

扫描实际启动后取消/超时，分别覆盖已写有效零诊断报告与未写报告四种 Unix 受控模式。扫描标记及报告存在性明确验证前提。取消且无报告反例先RED（一般报告失败覆盖取消），修正为请求中断/真实终止原因优先；版本留证失败也沿用。其它失败明确区分报告预检、执行留证、报告读取；退出2/无报告仍未完成，不是源码违规。

最终18项普通受影响/回归测试通过（ESLint 执行2、报告7、命令4、Checkstyle执行5），新增中断四模式测试3.28秒；实际Node七模式受控JSON复跑109.10秒通过。CLI lib/新执行测试Clippy、fmt、OpenSpec strict及git diff --check均退出0。夹具不是ESLint原生检查，原生ESLint仍NOT_RUN，完整7.3和整体实现验收仍未完成。

## 2026-09-27 ESLint 静态配置发现接入 detect/init

按 ESLint 官方配置文件文档核对六种 flat config 文件名、TS loader 与配置选择上下文，新增 Rust 静态候选观察。package.json 再次读取须匹配本轮原摘要；配置候选字节纳入原有画像输入。嵌套配置所在根分别保留，不将文件存在当成规则生效、不执行JS、不隐式迁移旧配置。未观察到配置不证明外部/显式参数不存在，保持unknown并给原生核查动作。

新增两项先RED（无候选观察），实现后加嵌套TS配置反例。初次回归暴露既有init测试仍断言空列表；更新为精确node.eslint/unknown，保留不能声称就绪和改/删配置导致画像过期的原契约。最终67项通过（detect23、init41、discovery端口3），CLI相关Clippy、fmt、OpenSpec strict和git diff --check通过。原生ESLint、逐文件规则/导入插件闭包、TS parser/monorepo实际执行及完整7.3仍未完成。验收见相邻 tests/acceptance/eslint-static-configuration-discovery.md。

## 2026-09-27 ESLint 原生核心规则验收及发现补充

两项缺口先RED后修正：独立JS无package/config原来无准备反馈；package复核变更或不可读原来仍可能发现完整（flat config存在时还会隐藏具体原因）。现提供源码引用/核查动作，输入失效标发现不完整及清单阻塞路径。66项目标/回归通过（detect24、init41、发现端口1），执行层2项普通回归通过，共68项；相关CLI Clippy/fmt通过。

本轮找到本机既有npm缓存ESLint10.11.0，无安装/升级，使用显式Node24.18.0通过Rust runtime运行六轮真实原生检查：干净、no-unused-vars warning、no-debugger error、解析失败、eslint-disable抑制、同原配置修复复检，104.56秒通过。warning/error保留，解析/抑制待核查，零诊断不签发任务关闭或门禁允许。早先记录的原生ESLint NOT_RUN为当时边界，现只对该核心规则测试完成原生验收；TS/parser/tsconfig、插件/导入闭包、有效配置归属、完整CLI/任务/门禁仍未完成，7.3不勾选。见相邻 tests/acceptance/eslint-native-core-rules.md。OpenSpec严格校验与插件diff检查通过。

## 2026-09-27 ESLint 公开局部lint命令

接通lint typescript FILE与help，显式Node/JS入口/版本/原flat config/原cwd，避免按配置目录猜原调用上下文。缺上下文先RED（旧路由退出2），实现后返回准备反馈3；非法参数仍2。JSON/human显示原规则、位置、严重度与下一步；原生消息仅输出摘要，明确临时证据退出清理、workbench未接入、coverage=false、门禁未判定。

23项普通相关回归通过（CLI3/probe2/Go5/Python12/语言缺口1）；本机既有ESLint10.11.0/Node24.18.0经过公开CLI检出no-debugger，源码修复后同配置零诊断，两轮35.44秒通过，均不签发项目通过。CLI lib/bin/新测试Clippy、fmt、公开缺上下文反馈Draft202012 schema校验、OpenSpec strict与git diff --check通过。未安装工具。完整项目、持久任务、TS/plugin/闭包/依赖和7.3仍未完成，验收见相邻tests/acceptance/eslint-public-lint-feedback.md。

## 2026-09-27 ESLint 稳定任务输入前置

持久化接线审查发现需要先稳定问题身份与原生Unicode定位。缺API先RED后新增投影：相对路径/规则/锚点/序号，排序去重；源码行号与原生措辞变更不重复建问题，错误范围/定位使整组失败。UTF16列与CRLF、CR/LF、U2028/U2029处理避免字节列误判。

四项身份契约及CLI/probe共9项普通回归通过；现有Node/ESLint10.11.0原生定位三条no-debugger，emoji后列7与后两行2/3均与投影一致，0.23秒通过。Clippy/fmt、OpenSpec strict/diff检查通过，无安装。这里只完成稳定任务输入，未完成队列/任务/next接线，当前公开反馈仍workbench未接入，7.3/9.7不勾选；见相邻tests/acceptance/eslint-stable-task-input.md。

## 2026-09-27 ESLint 脱敏观察入队及稳定任务连接

当前公开lint typescript FILE --workspace ABS_PATH复核摘要后保存eslint_workbench_observation并同步稳定finding/任务；反馈0.2返回同步状态、next或next_error。严格导入拒绝自授权allow、错误范围/投影/输入；历史已消费报告按不可变字节收据处理。重复扫描保留同一任务与用户备注，status/task show展示开放状态。next核查本轮报告及首次工具/配置连续性，不从局部零诊断、抑制或勾选推断关闭。

配置改变后的备用指引回归先失败（recheck_argv[2]为python），修正后选择typescript及显式待核验的ESLint上下文。33项相关普通回归通过（身份4、CLI4、next6、status/show4、sync15）；补充CLI工作台status/task show联通再跑1项通过。受控插件ID只是协议样例，未执行TS插件。当前公开feedback及actionable/失效配置两类简报以Draft202012 schema实测通过，目标CLI lib/bin/eslint_lint_cli Clippy -D warnings与fmt通过。

本机既有Node24.18.0与ESLint10.11.0通过公开CLI执行初始化后两轮真实检查，no-debugger发现入队，原配置修复源码后零诊断，next转verification_required、任务仍open，两轮均退出3且coverage=false/delivery not_evaluated。显式ignored原生用例本轮69.88秒通过，无安装或升级。原生临时输出退出后仍清理，仅脱敏结构化观察持久保存。验收见相邻tests/acceptance/eslint-workbench-sync.md。

Node环境阻塞任务、原生完整证据留存、正式task verify关闭/重开、全项目/多文件、TS插件及配置闭包、依赖/CVE与真实宿主门禁未完成，7.3/9.7不勾选。全计划未完成，不同步/归档当前change。

## 2026-09-27 ESLint 检查完整性准备任务

早期缺上下文以及工具/配置/版本/报告未完成路径接通Rust准备观察、严格同步和环境任务，源码finding与准备任务分开。取消、外部目标、不支持范围与未初始化工作区不制造成功。诊断变化保留同目标稳定任务。next从最新已消费摘要绑定报告核对当前范围，较新有效扫描使旧环境任务转正式核查而非继续重复旧动作；仍不能关闭任务。human/JSON直接反馈当前任务步骤。

缺上下文用例先RED（not_connected），实现后重复两次只建一个blocker；缺工具更新最新诊断不建第二张任务，受控恢复后next转verification_required且复检路径仍为原源码；外部工作区目标拒绝。相关普通回归35项通过（身份4、CLI6、next6、status/show4、sync15），准备feedback及独立简报Draft202012 schema通过。实际现有Node24.18.0/ESLint10.11.0遇原配置不存在规则，公开CLI生成环境任务1/源码finding0，不签发门禁，显式ignored原生验收13.71秒通过，无安装/升级。最终Clippy/fmt检查见本轮结果。

完整构建模型和跨文件共同环境根因归并、正式关闭/重开、完整原生证据及真实宿主门禁仍未完成；7.3/9.7不勾选。验收见相邻tests/acceptance/eslint-preparation-workbench.md。

## 2026-09-27 ESLint 稳定任务原工具复检

task verify接通源码/准备任务，显式Node/ESLint入口/版本/原配置/cwd，参数预检查、租约、统一截止时间、同步与尝试历史复用现有Rust流程。不执行Markdown或历史报告里的程序。当前输入与首次原工具/配置连续性不一致时需核查；原生抑制不当修复。仍存在、局部消失候选、环境恢复或未完成均保留任务open，不签发allow或resolved。

缺上下文入口先RED（task_checker_unsupported），新事件又复现attempt历史不认识ESLint报告/时间，修正后next/status/attempt和重复扫描一致。57项相关回归通过（ESLint6、next6、status/show4、租约/尝试16、verify10、sync15），另分类1项通过，覆盖上下文变化、仍存在、抑制和目标错误。CLI夹具显式复检still_present与无上下文事件保存通过。实际既有Node24.18.0/ESLint10.11.0通过公开发现、任务复检仍存在、修复源码后同配置复扫、任务复检局部消失四轮，194.36秒通过；事件保存但任务保持开放，均局部门禁未判定，无安装/升级。

公开未完成及原生观察task verify反馈分别通过统一preview与eslint-task-recheck schema；实测发现原统一schema不认识ESLint，追加严格分支后通过。临时原生输出仍清理，只有脱敏结构化观察持久化。完整JS配置/导入闭包、required规则覆盖、TS插件/全项目源集、可信宿主策略和正式关闭重开仍缺，7.3/9.7不勾选，change不归档。验收见相邻tests/acceptance/eslint-task-verification.md。


## 2026-09-27 ESLint 原规则有效配置核查

Rust task verify 增加同轮原生 --print-config 查询，绑定显式源码/主配置/Node/入口前后字节与统一截止时间；只保存规则级别、原因和摘要。复检协议0.2新增effective_rule，历史0.1仍只读识别。规则关闭或缺失时零诊断必须rule_coverage_requires_review，查询损坏/输入变化为未完成，next指向配置核查；不批准白名单或关闭任务。

44项普通相关回归及分类单元用例通过，最终9项规则解析/公开CLI普通测试、目标Clippy -D warnings和fmt通过。既有Node24.18.0/ESLint10.11.0原生启用/off/缺规则三轮38.50秒通过；实际公开CLI只改导入mode.cjs关规则、主配置和源码不变的反例108.38秒通过，仍要求覆盖核查且保存事件，无安装升级。受控CLI实际产物通过统一复检、ESLint复检及简报三份Draft202012 schema；简报lint-only复检ID正则先失败后补入eslint-task前缀。schema产物使用受控协议夹具，不冒充原生工具验收。

完整导入/插件闭包、TS/全项目源集、required规则批准覆盖、可信宿主门禁和正式关闭重开仍缺，7.3/9.7保持未完成。验收见相邻codeguard-cli/tests/acceptance/eslint-effective-settings.md。


## 2026-09-27 ESLint 有效配置查询取消

公开task verify受控进程反例先RED：查询收到SIGINT后，原因丢失并保存成still_present。Rust查询与任务复检现优先保留取消/期限；共享任务入口取消后不保存正常复检事件，并释放自有租约。真实进程组延迟写副作用未出现，再次复检能获取租约。目标用例3.84秒通过，36项相关普通回归、目标Clippy -D warnings和fmt通过。脚本仅为受控协议夹具，不冒充原生ESLint；Windows、跨宿主、中断历史协议及完整I/O预算仍缺，3.3/7.3/9.7不勾选。见相邻tests/acceptance/eslint-effective-interruption.md。


## 2026-09-27 ESLint 项目本地插件原生验收

使用既有Node24.18.0/ESLint10.11.0及项目原flat config加载guard.cjs本地规则。公开lint保留完整workspace/no-debugger ID并生成稳定任务；只修源码后，task verify通过原扫描及原生print-config确认规则仍启用，保存局部消失候选，插件与主配置不改，status门禁未评估。真实测试91.56秒通过，没有安装/升级。

此证据补齐局部本地插件规则穿过公开CLI/任务复检的真实样本，不证明完整插件闭包或可信批准。TS parser/tsconfig、monorepo完整范围、依赖审计、required规则/正式关闭及宿主门禁仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-local-plugin.md。取消路径及本地插件两项增量在同一change跟踪，不同步或归档未完成计划。


## 2026-09-27 ESLint 显式目录调度

lint typescript PATH现支持有界目录清单及逐文件原工具执行，保留排序相对路径、局部反馈、跳过项和未执行清单；共享deadline，前后清单/显式输入变化、单文件失败及工作台保存失败均未完成。codeguard内用户源码照常扫描，点条目/node_modules/链接未选择原因显式反馈。仍使用调用者指定的单一原配置/cwd，不声称自动选择monorepo子配置。

目录入口先RED，配置源码又复现输入冲突及同步路径重复拒绝；现只允许原配置与源码共享同一只读字节身份，报告覆盖/其它输入别名及重复源码仍拒绝。受控样本首次4稳定任务、重复0新增，单文件退出2保留其它发现，链接跳过、100ms共同预算3文件未执行及画像缺失工作台失败反例通过。48项普通相关回归通过，最终目标Clippy -D warnings/fmt通过，公开目录JSON通过Draft202012 schema。实际既有Node24.18.0/ESLint10.11.0公开目录三文件（违规、干净、配置源码）62.34秒验收通过，无安装升级；schema样本是受控夹具，与原生证据分开。

完整TS/tsconfig、monorepo原生源集及配置归属、插件闭包、依赖/CVE、聚合硬I/O预算、原生证据及可信正式关闭/宿主门禁仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-directory-feedback.md。


## 2026-09-27 ESLint 显式子项目配置映射

目录入口新增--config-map绝对路径，1.0有界协议逐项声明项目根/原配置/cwd，组件边界及最深显式根匹配，未命中沿用原参数。不从目录名推断原cwd，不批准规则。重复根/字段、未知字段、越界/链接或不可读配置启动前拒绝，映射与全配置摘要纳入前后及子任务前检查。反馈0.2保留逐文件配置范围和来源及映射摘要，schema仍接受历史0.1。

未知选项先RED；受控a/ab边界、根`.`选择、重复/越界/approved字段及首轮改写映射后停止余下三文件反例通过。45项普通相关回归通过，最终补充根`.`用例及目标Clippy/fmt通过；映射及当前公开反馈Draft202012 schema通过受控实际产物，越界schema反例被拒绝。既有Node24.18.0/ESLint10.11.0真实双项目四文件80.78秒通过，根规则没有强加子项目，保留配置源码检查，无安装升级。

自动配置归属、完整TS/插件闭包/源集、依赖审计、批准覆盖、聚合硬I/O与正式关闭/宿主门禁仍缺；7.3/9.7不勾选，不归档change。验收见相邻tests/acceptance/eslint-config-map.md。


## 2026-09-27 npm原生审计基础

Rust新增npm11/auditReportVersion2有界观察及离线原生命令计划，保留组件、严重度、范围、节点、原生advisory source和间接关系；版本/计数/定位/退出/重复JSON键或error对象不自成干净结果。原生source不是CVE编号，range不是解析版本；依赖类别有重叠，不简单相加。只读package脚本配置API区分明确声明、未观察到、复杂调用和损坏，不执行清单脚本，也不能证明外部CI未配置。

缺API先RED；组件低危但直接advisory高危反例再RED后修正。5项协议/参数/配置用例及9项既有ESLint回归通过，共14项普通测试；CLI目标、adapter库Clippy -D warnings及fmt通过。既有Node24.18.0/npm11.16.0经统一runtime验证版本、空锁JSON及缺锁error，0.68秒通过，包/锁字节不变，无node_modules或脚本副作用，无安装升级。合成advisory是协议夹具，不冒充真实漏洞数据库检出。

配置API尚未接detect/init，公开CVE/依赖命令、非空依赖/真实漏洞、解析版本/图绑定、漏洞库时效、稳定任务/原工具复检及可信门禁仍缺；7.3/7.5不勾选。见相邻tests/acceptance/npm-audit-observation.md。

## 2026-09-27 npm锁文件节点关联进展

新增 Rust v3 普通安装节点解析与原生审计精确位置/名称/版本关联；两项锁文件契约及五项 npm 审计回归通过。链接、别名、缺版本、重复字段和身份不匹配保持未完成。仅协议夹具，不是实际非空依赖审计；依赖边、范围求值、库新鲜度、公开命令及工作台闭环仍缺，7.3/7.5 保持未勾选。验收见相邻 `codeguard-cli/tests/acceptance/npm-lock-binding.md`。

## 2026-09-27 npm离线非空依赖反例

扩展实际 Node 24.18.0/npm 11.16.0 原生验收为私有空缓存的空锁、一个普通依赖节点的非空锁、缺锁三种情况。实验发现非空离线审计也能退出0并返回零漏洞，不能把零发现当成库覆盖或CVE通过。Rust观察新增固定 `advisory_coverage=not_evaluated`，节点关联保持局部身份观察。测试检查清单/锁不变、无安装及脚本副作用；尚缺在线/可信缓存的真实漏洞正例及库新鲜度、完整命令/工作台，因此7.3/7.5不勾选。

本轮验证：原生三场景测试通过（0.77秒），7项普通契约通过；adapter lib与CLI三项test target的Clippy（-D warnings）、格式及OpenSpec严格校验通过。此前把非空离线结果预期为原生错误的测试失败，实际观察到零发现后修正覆盖语义；新增覆盖字段验收先因API缺失失败，再实现通过。

## 2026-09-27 npm原生advisory与复检

显式无凭据registry命令API已提供HTTPS根源及验收loopback HTTP源，固定audit-registry、不安装/不执行脚本；受控原生npm执行证实1.2.3被advisory命中、修订2.0.0后同工具复检无发现，503源失败为npm_native_error。两项原生测试通过（0.58秒），六项审计契约、Clippy/格式通过。受控源不是可信库，coverage固定not_evaluated；早期一次原生正例出现未分类错误，已增加诊断而不能宣称稳定性完全证明。真实库/时效、公开命令及完整工作台仍缺，7.3/7.5不勾选。见相邻`codeguard-cli/tests/acceptance/npm-native-advisory.md`。

最终重复原生验收2项通过（0.55秒）；审计与锁关联8项普通契约通过，OpenSpec严格校验及diff检查通过。重复运行未再次出现早期原生正例错误，其原因仍未确定。

## 2026-09-27 npm审计配置发现与预览接线

node.npm.audit已按原package.json摘要逐根进入共享发现、init数据来源及detect/plan/check all的配置反馈；manifest重读变更/不可读保留unknown与观察未完成。修复plan按语言筛选遗漏node检查器的问题，typescript/all预览均保留四态；check all人类反馈显示根、原因与下一步。新binary流程与发现/计划/初始化70项不同用例通过，Clippy/格式通过。仍未自动执行npm审计、覆盖其它包管理器/CI声明、库时效、稳定任务和门禁，7.3/7.5保持未完成。见相邻`codeguard-cli/tests/acceptance/npm-audit-discovery.md`。

## 2026-09-27 npm输入绑定runtime服务

新增独立请求/结果及Rust原生版本-audit-报告-锁节点关联服务，冻结精确输入SHA及npmrc存在性；缺身份、版本错配、输入修改/配置新增、取消与超时均未完成、不提供可用于关闭任务的解析结论。三模式反例与八项审计/锁回归通过；真实npm局部服务首轮通过，最终版本参数修改后复验。完整工具/配置/环境闭包、可信库时效、公开命令与任务闭环仍缺，7.3/7.5保持未完成。见相邻`codeguard-cli/tests/acceptance/npm-input-bound-probe.md`。

最终验证：九项普通契约通过（1项输入服务三模式、6项审计、2项锁关联），两项真实npm验收通过（21.68秒）；CLI lib与输入服务/原生测试target的Clippy（-D warnings）、格式、OpenSpec严格校验和diff检查通过。服务未接入公开CVE入口，任务仍不勾选。

## 2026-09-27 npm公开CVE局部反馈

Unix `cve typescript` 已接显式Node/npm/版本/用户与全局配置/可选审计源，冻结输入并以human/JSON返回脱敏原生组件、锁版本、严重度、advisory source及下一步。缺上下文给准备状态，局部零发现仍not_evaluated；未接工作台，不假称关闭。10项普通契约、真实binary npm空锁（21.75秒）、两份实际schema报告及四个伪造权威反例通过，Clippy/格式及OpenSpec严格校验通过。真实库、自动check all、完整预算默认来源及持久任务闭环仍缺，7.3/7.5不勾选；验收见相邻`codeguard-cli/tests/acceptance/npm-public-cve-feedback.md`。

## 2026-09-27 npm共享预算默认值接线

公开npm CVE入口复用CLI/登记环境/项目runtime/内置默认值选择器，坏候选项目文件或符号链接在原生执行前返回准备未完成，显式高优先级值不受低优先级坏配置影响。反馈0.2记录预算/来源及native_execution_only，保留严格旧0.1schema。预算、公开命令、发现与输入绑定四项普通测试通过，哨兵未启动；Clippy/格式及OpenSpec严格校验通过。真实命令及实际schema结果后补。硬I/O预算、可信库与工作台仍缺，7.3/7.5不勾选；验收见相邻`codeguard-cli/tests/acceptance/npm-runtime-defaults.md`。

最终验证：真实Node/npm公开命令通过（21.50秒）；三份实际0.2预算反馈通过schema，历史0.1兼容输入通过，四项非法预算反例被拒。最终diff检查通过；不把预算接线当成完整CVE或工作台验收。

## 2026-09-27 npm稳定工作台与next接线

初始化根中的公开npm审计自动保存脱敏原生组件/advisory/锁版本观察，严格复核输入与字段，经现有同步器创建按根稳定的CVE完整性任务；执行原因作为诊断历史，不伪装源码漏洞或关闭。next识别检查器并给原工具复检步骤。重复扫描一张任务、坏节点/重复字段不产生新任务；反馈0.3及持久观察schema已提供，旧0.1/0.2反馈保留。24项不同普通回归与真实npm公开命令持久化（21.50秒）、实际schema通过，Clippy/格式及OpenSpec严格校验通过。自动check all、早期准备阻塞全覆盖、父工作区映射、npm task verify与可信库/门禁仍缺，7.3/7.5不勾选。验收见相邻`codeguard-cli/tests/acceptance/npm-workbench.md`。

追加正例验收：公开受控组件报告保留advisory及解析版本，依赖变更仍复用同一任务。测试先暴露已消费npm历史报告被当前锁变化错误重演的问题；现纳入不可变字节收据消费分支，新报告仍复核当前输入。历史字节变化仍按run_id_digest_conflict拒绝。最终24项普通回归及Clippy/格式结果见本轮输出。


## 2026-09-27 npm显式父工作区与白名单纠错约定

公开npm入口新增--workspace物理父目录，原生cwd保持子项目，预算默认读取所选父工作区，持久任务按构建根分离；next保留归属。8项相关普通测试通过，目标Clippy及格式通过，见相邻tests/acceptance/npm-workspace-scope.md。可信库、自动调度、完整关闭与门禁仍缺，7.3/7.5不勾选。

白名单文档补齐用户新增/修改/撤销/失效的操作与对话状态，OpenSpec明确修改字节须重新批准、不能记为源码修复。既有精确身份5项、报告处置7项、只读查询8项、提案4项普通契约通过；2项需要指定原生Ruff的测试未运行。这是现有局部契约回归，不是正式审批发布或宿主门禁验收，4.8/4.10/12.12保持未完成。


## 2026-09-27 npm task verify原工具复检

稳定npm完整性任务接入task verify、共享预算、借用/自有租约、原服务及锁内输入复核；保存严格npm观察和关联尝试的verification事件，next/历史识别npm序列并给下一步，输入变化不沿用旧结果。局部一致为still_blocked，原生失败为incomplete，任务仍open、无白名单批准。缺参数入口先RED；随后测试暴露两个事件消费者未接npm时间序列，已补齐。

36项不同普通相关用例通过；真实Node24.18.0/npm11.16.0公开扫描+原工具task verify通过（43.44秒）。实际复检反馈schema通过，三项伪造覆盖/权威/allow反例被拒；目标Clippy/格式最终检查后补。8项依赖显式原生Ruff的复检用例本轮未运行。完整漏洞库/策略覆盖、正式关闭/重开、宿主门禁及自动check all仍缺，7.3/7.5/9.7不勾选；见相邻tests/acceptance/npm-task-verification.md。

最终检查：目标Clippy（-D warnings）及fmt通过；最终局部回归11项通过，human实际复检显示原生诊断/组件数/下一步并保存记录，OpenSpec严格校验与diff检查通过。未增加完整能力勾选。


## 2026-09-27 npm复检收据严格归属与过期分流

next与尝试历史新增npm原字节重复键拒绝、同任务检查器/稳定义务/构建根核验；报告解析先完成静态结构再核对当前工作区与清单/锁摘要及节点，锁重读也核对摘要。只有结构有效但输入已变/不可读的历史观察失效后允许重新复检，损坏证据不冒充输入过期。

新增十个组合反例（五种篡改乘当前输入未变/已变），同时改写报告、验证事件及消费收据摘要；错构建根先RED，旧实现曾接受另一个根的incomplete失败结果并确认当前尝试已经复检，补精确归属后拒绝。49项不同普通回归通过；10项需要指定原生Ruff的用例本轮未运行。真实既有Node24.18.0/npm11.16.0公开扫描与task verify通过（45.05秒）；目标Clippy、fmt、OpenSpec严格校验及diff检查通过。

完整受保护工具/配置/审计源上下文、可信漏洞覆盖、正式关闭/重开及宿主门禁仍缺，7.3/7.5/9.7保持未勾选。验收见相邻tests/acceptance/npm-verification-receipt-integrity.md。


## 2026-09-27 check all npm逐根原生编排

显式Node/npm/版本/用户与全局配置上下文接入共享任务图，每个发现package根独立cwd/私有运行区，统一jobs和deadline；执行后串行同步稳定npm完整性任务并反馈next，原生失败不变源码违规。缺上下文保持配置发现，check java拒绝npm选项，预算到期不启动剩余任务。协议check_feedback0.24/check_aborted0.5新增npm逐根结果，旧0.23/0.4 schema保留。

新入口参数先RED；实际schema验收发现候选原因码遗漏并补齐。两根并发/稳定任务、混合成功失败、500ms统一截止时间、参数及语言范围反例已通过。早期并发回归出现临时私有目录创建失败；源码旧运行ID仅PID/时间不能保证并发唯一，已增加原子序列，同刻度64个ID用例先RED再通过。不将原失败误归为代码违规，具体当次OS失败原因未单独留存。

真实既有Node24.18.0/npm11.16.0 check all→稳定任务→next初次21.80秒、最终22.30秒通过；无安装、包脚本或node_modules，清单和锁不变。当前含npm/无上下文实际反馈schema、三项伪造门禁/权威/覆盖反例及旧0.23形状校验通过。最终普通回归、Clippy/格式结果待追加。

可信上下文自动解析、早期阻塞全覆盖、完整漏洞库/依赖图及关闭/重开、其它语言/类别调度、跨平台与宿主门禁仍缺，7.3/7.5保持未勾选。验收见相邻tests/acceptance/check-all-npm.md。

最终检查：66项不同普通用例通过（63项integration、3项领域/调度单元），目标Clippy（-D warnings）和fmt通过；真实npm check all最终22.30秒通过。其它9项显式原生用例本轮未运行，不将普通夹具作为它们的验收证明。OpenSpec严格校验及diff检查通过。7.3/7.5不勾选，不归档change。


## 2026-09-27 npm缺少上下文的准备阻塞持久化

已有可读清单/锁的初始化工作区，公开cve缺参数与显式选择npm的check all部分参数，现在保存本地未验证准备观察并生成稳定CVE完整性任务；随后原生检查复用任务。task verify缺上下文也保留incomplete复检事件，不签发关闭。准备观察固定零组件、空advisory；矛盾记录被严格解析器及当前报告schema拒绝。先通过缺任务和虚构advisory两个RED反例确认问题，再实现修复。

36项受影响普通回归通过，实际准备反馈/观察/复检通过Draft202012 schema验证，四个伪造变体被拒；CLI及相关测试Clippy -D warnings通过。真实npm回归结果另附。缺锁/坏清单的独立准备协议、没有显式npm上下文的check all自动任务、工具上下文可信来源、覆盖/审批/真实门禁仍缺。7.3/7.5/9.7及相关完整任务保持未完成；本进展不是完整CVE或白名单放行验收。详见相邻codeguard-cli/tests/acceptance/npm-missing-context-workbench.md。

补充验收：显式使用既有Node v24.18.0/npm11.16.0的公开CVE原生回归通过（44.13秒）；不安装、不执行包脚本。实际check all准备反馈schema通过，当前嵌入观察schema与独立schema字节结构一致；fmt检查通过。其余2项本轮普通命令忽略的原生测试未运行，不当作通过。


## 2026-09-27 npm缺锁准备协议与稳定任务

初始化工作区、可绑定清单且确实缺package-lock.json时，CVE/check all显式npm/task verify在启动工具前保存schema0.2本地准备观察：lock_state=missing、lock_sha256=null、零组件和空advisory；缺锁不伪装为漏洞。补齐锁后旧观察失效，后续普通0.1观察复用稳定任务。悬空链接、伪造状态/摘要/覆盖、未知版本及缺锁收据在锁恢复后重放均被拒；取消、时间预算及物理路径约束继续生效。

消费者版本同步为check_feedback0.25、task_verification_preview0.5、check_aborted0.6；独立npm观察读取0.1/0.2，历史schema原字节归档。51项普通集成回归通过；真实npm check all回归通过（22.98秒），原清单/锁不被修改、不安装或执行包脚本。实际缺锁观察/check/verify通过Draft202012校验，五个伪造变体及旧版观察消费者拒绝。abort实际中断运行未在本轮外部schema验收，不将schema静态有效当作运行通过。

仍缺不可读/坏清单的独立准备任务、未显式选择npm的check all自动准备调度、可信上下文、完整CVE覆盖和正式任务关闭/宿主门禁；7.3/7.5/9.7保持未完成。验收文档：相邻codeguard-cli/tests/acceptance/npm-missing-lock-workbench.md。

最终补充：2项check_command中断/兄弟结果保留单元测试通过，连同51项集成共53项普通用例；Clippy -D warnings、fmt、当前四schema Draft202012静态校验及嵌入协议一致性回归通过。OpenSpec严格校验及diff空白检查通过。观察0.1不能声称npm_lock_missing，缺锁必须采用0.2明确状态。


## 2026-09-27 npm坏清单启动前诊断与任务

RED用例证实已识别无效清单仍启动工具，错误被表达成npm_version_mismatch。现将无效JSON、重复字段和非法scripts类型在原生启动前拦截；绑定清单/锁及当前配置解析，保存零组件/空advisory的准备观察，CVE/check all显式npm/task verify复用稳定任务。next及可读任务明确检查package.json语法/重复字段/scripts类型和锁文件，再恢复原工具；修正输入后旧复检收据失效。当前字节有效却声称清单坏的伪造报告被拒。

35项不同普通回归通过；实际坏清单观察/check/verify通过Draft202012，3个伪造组件/advisory/覆盖变体拒绝。真实Node v24.18.0/npm11.16.0 check all回归通过（22.50秒），不安装/执行包脚本；其余10项普通命令忽略的原生测试本轮未执行。观察0.1/缺锁0.2与check0.25/verify0.5协议字段不变，仅准备原因的结构约束同步加固；旧schema归档不改。详见相邻codeguard-cli/tests/acceptance/npm-invalid-manifest-workbench.md。

不可读或缺清单/目录输入的持久准备协议、可信上下文、完整CVE覆盖与正式任务关闭/门禁仍缺；7.3/7.5/9.7未完成，不以本轮回归代替全计划验收。

最终检查：CLI和新增用例Clippy -D warnings、fmt、OpenSpec严格验证及diff空白检查通过。


## 2026-09-27 check all默认自动npm准备任务

RED确认无参数check all发现两个npm根却无准备任务。现Unix支持平台默认将发现的npm根接入共享任务图；缺显式上下文只保存准备观察与稳定任务，不启动原工具、不安装/继承凭据。重复扫描、随后补齐上下文的原生检查复用任务，串行同步及next无需调用者手工串接。未初始化项目仅反馈workspace_not_initialized、不创建codeguard；Java-only检查不触发npm。

47项不同普通用例通过，涵盖多根准备/后续原生调用、Java隔离、缺锁/坏清单、预算/取消、SARIF与新未初始化反例。实际默认多根check all通过Draft202012，首次两任务、重扫零新增；真实Node v24.18.0/npm11.16.0 check all回归通过（23.03秒），不安装/执行包脚本。其余7项本轮普通命令忽略的原生用例未执行。Clippy -D warnings、fmt通过。

只接通CLI默认准备调度；未取得可信工具上下文自动解析、完整CVE覆盖、宿主Hook和正式任务关闭/门禁。Windows该路径仍未支持；不可读/缺清单的持久状态仍缺。7.3/7.5/9.7保持未完成。详见相邻codeguard-cli/tests/acceptance/npm-automatic-preparation.md。


## 2026-09-27 npm不可用输入状态协议与历史

新增Rust有界输入状态观察及严格准备报告0.3：present/missing/not_regular/path_alias/unavailable，可读普通文件有SHA，其余null；原因与状态严格一致，零组件/空advisory。公共CVE及task verify可在清单缺失、目录、悬空链接或超限时保存稳定环境任务，不读取链接目标；锁非普通文件也可在默认check all中产生准备任务。旧0.1普通观察/0.2缺锁继续严格识别，消费者升至check0.26/verify0.6/abort0.7，旧schema原字节归档。

RED先暴露缺失被当作缺上下文；随后反例暴露目录使next返回attempt_input_unreadable。npm阻塞任务现在以有界输入状态形成尝试指纹，可读与缺失沿用原摘要格式，其余只记录状态，不能成为关闭证明。当前输入恢复后旧复检不再解释本轮；6种结构/身份伪造及一个过期报告被拒，不增任务。

78项不同普通回归通过（76集成+2中断单元），包括租约/无进展预算、Java、SARIF、任务复检与旧协议；真实Node v24.18.0/npm11.16.0 check all回归通过（22.42秒）。实际新观察/check/verify通过Draft202012，6个伪造变体拒绝、旧消费者拒绝新协议；其余16项忽略的原生用例本轮未执行。有界不可用fixture为超限，不声称已完成独立权限EACCES运行验收。abort本轮仅既有单位用例和schema静态检查，未外部验证真实中断新观察。

仍缺丢失清单后从历史/基线恢复完整根发现、外部工具/配置文件不可用的持久准备、Windows、可信上下文/完整CVE覆盖、宿主Hook及正式关闭/门禁。7.3/7.5/9.7保持未完成，见相邻codeguard-cli/tests/acceptance/npm-input-state-workbench.md。

最终核验：最新新增用例及CLI的Clippy -D warnings、fmt、OpenSpec严格验证与diff空白检查通过；输入状态及坏清单最新修复指引回归实际执行通过。


## 2026-09-27 npm历史构建根的准备恢复

默认check all现可从与本地受管摘要一致的0.3初始化画像恢复清单不可用但物理目录仍存在的npm准备范围。严格校验递归重复字段、协议标记、相对路径/别名、物理归属及有界输入状态；历史根不使用旧摘要或显式工具参数启动原工具。当前兄弟根仍正常调度，画像错误以historical_npm_scope_unavailable及具体原因反馈，不吞掉其结果。清单恢复后重新发现，稳定任务不重复。

新增npm_historical_roots_cli由双根只剩一根的RED推进到通过，覆盖重复同步、混合原生参数调用轨迹及画像失配/越界/别名/错类型/重复字段反例。最终新增矩阵通过；CLI及新增测试Clippy -D warnings、fmt通过。相邻验收：codeguard-cli/tests/acceptance/npm-historical-roots-workbench.md。

这是本地准备范围恢复，非可信审批或CVE覆盖。目录整体消失只明示未完成；旧画像版本、刷新画像删除旧根后的完整义务恢复、外部工具/配置、Windows、可信上下文、完整覆盖及宿主闭环仍未完成。7.3/7.5/9.7保持未勾选。

最终普通验收：61项不同普通集成用例通过（Java24、check all npm2、部分契约13、SARIF6、npm audit1、历史根1、输入状态1、坏清单1、缺锁1、父工作区1、task verify10）；17项显式原生用例在普通命令中忽略。独立执行的历史-only默认检查实际反馈通过Draft202012，两轮稳定任务且历史清单摘要null。OpenSpec严格校验、diff空白检查通过。真实npm回归单独记录。

原生补充：显式既有Node v24.18.0/npm11.16.0的check all回归实际通过（22.45秒）；不安装、不执行包脚本。普通命令忽略的其余16项原生用例本轮未执行。准备恢复和本地一致性不等于漏洞库覆盖或白名单批准，完整计划仍未完成。


## 2026-09-27 npm画像刷新后保留已记录准备范围

RED证实清单删除后再次init刷新画像，默认check all遗漏已有稳定npm问题。现从本工作区有界普通物理finding.json恢复清单不可用、物理目录仍存在的准备范围；核对结构、工作区/检查器、稳定指纹与ID、scope、两项输入归属及状态。画像与事实两类来源独立，不因画像失配吞掉可核验事实范围。只恢复本地准备，不沿用旧结果或启动该根的原工具。可编辑Markdown附件删除/勾选不能消除该范围；附件缺失仍暴露同步问题，不宣称任务已修复。

新增npm_recorded_roots_cli覆盖刷新后重复检查、附件删除、事实身份/路径损坏、当前兄弟根保留及输入恢复；已有画像拒绝测试更新为事实恢复仍保留范围，同时明示画像错误。目录整体丢失、删除全部事实且画像已刷新后的防逃逸仍需独立受保护义务来源；本地记录不是可信批准。完整7.3/7.5/9.7保持未完成，不据此归档。


最终验收：27项不同普通集成用例通过（默认npm2、部分契约13、SARIF6、历史画像1、输入状态1、坏清单1、缺锁1、已记录根1、父工作区1）。最新已记录根用例扩展到9项身份/状态/范围错误反例，当前兄弟根均保留；其中运行ID反例用非法分隔符，普通字母本身合法，不为迎合测试收紧契约。实际刷新画像后仅事实来源的两轮check反馈通过Draft202012，清单摘要null，new_blockers=0。显式既有Node v24.18.0/npm11.16.0原生check all回归通过（23.40秒），无安装或包脚本；普通命令忽略的另一项Ruff原生用例本轮未执行。CLI/新增测试Clippy -D warnings、fmt及OpenSpec严格校验、diff空白检查通过。完整计划仍未完成。


## 2026-09-27 Rust全工作区回归与严格静态检查（进行中）

扩大到cargo test --workspace与cargo clippy --workspace --all-targets -- -D warnings。首次全目标Clippy发现work_sync.rs在测试模块后定义validate_eslint_observation（items_after_test_module）；已将同一函数原样移到测试模块之前，无行为或协议变更，不以allow压制告警。fmt检查通过。全目标Clippy复检和同步模块单元回归仍在运行，未提前记录通过；全工作区测试沿原进程继续，当前已收集15组结论、60通过/0失败/3忽略，为中间进度而非整轮验收。

已确认普通工作区回归不执行显式ignored原生工具用例；MSRV1.85工具链当前未安装，Windows/宿主验收未运行。13.2及全计划保持未完成。此记录需待同一运行终态更新，不因等待超时重复启动。

后续终态：修复后的全工作区all-targets Clippy -D warnings实际通过（1分32秒），同步模块3项恢复/重放单元测试实际通过。全工作区普通测试仍沿原进程运行，尚未签发整轮通过结论。


## 2026-09-27 全工作区依赖边界失败与修复

上一全工作区测试已终止为exit101：52组结论累计271通过、1失败、23忽略，失败为crate_boundaries的真实Cargo metadata检查；不记录整轮通过。核对发现adapters两个原生测试调用runtime造成dev越层，且网络下载实现新增的runtime依赖和CLI测试异步依赖未登记。已将Checkstyle原生重放和Node字面参数原生测试移入CLI测试层，删除adapters→runtime dev依赖；保留adapters任何kind不得依赖runtime的红线。仅允许runtime normal reqwest/tokio/tokio-util/futures-util/idna_adapter与runtime dev rustls；CLI tokio只允许dev。新增对应正常/错误crate、build/dev/normal反例，现6项依赖边界与4项纯ESLint命令契约通过。迁移保留原生用例内容及ignored边界，不靠放宽生产依赖方向消除失败。

额外原生证据：已实时核验既有/opt/anaconda3/bin/ruff为0.16.8，check all部分结果1项、task verify8项、whitelist propose2项共11项真实Ruff用例通过；包含noqa、规则关闭、per-file-ignore、恢复环境不假关闭及纠错提案不自批。106份schema的静态合法性与本地引用检查通过，不能代替运行报告验收。MSRV1.85、Windows、三宿主仍未验收。修复后全工作区测试与all-targets Clippy重新运行，结果另附；13.2保持未完成。

补充终态：修复后all-targets Clippy -D warnings通过（29.62秒），fmt通过；迁移后的Node v24.18.0原生字面参数用例实际通过（1项），只证明argv安全转发，不冒充真实ESLint规则检查。Checkstyle重放迁移保留且本轮未运行。新的全工作区回归仍在原进程运行。


## 2026-09-27 当前规格到任务的覆盖索引修正

只读审计发现implementation-coverage.md缺43个后来新增的Requirement映射。已按当前正式规格追加binary-distribution7、execution-kernel5、native-tool-adapters15、remediation-workflow12、unified-cli-contract4项，引用已有实施任务而非另建任务。检查108个当前Requirement各有唯一精确spec/title映射，追踪ID不重复、没有失效Requirement、任务ID及任务区间均存在。每行仍覆盖该Requirement全部Scenario，不拿局部契约通过替代整项验收。

此为13.7的规格→任务追踪部分修复，未证明命令/语言/平台/宿主实现及全量双向验收，13.7与完整计划保持未完成。修复依赖边界后的工作区测试仍沿原运行继续；当前23组中间结论95通过/0失败/4忽略，不签发整轮通过。


## 2026-09-27 Checkstyle原生补充与受管技能一致性

实时核验现有Checkstyle10.21.4 all.jar（19631994字节，SHA256 3c1d94d6ecc83e02dff587c9ba5b6b4ec4fec38c7a958eb587efec9b28e2f318）与本机JDK21.0.12.1。迁至CLI层的原生重放1项、record/继承/生成范围1项实际通过。首次一并调用Lombok变体时缺CODEGUARD_LOMBOK_JAR，测试在读取该前置条件时失败，不归因于产品误报；随后明确选择本机Lombok1.18.38（SHA256 1e1e427c36ff63c44fd30ef292d9e773ea3154460ab6265d3fed7e6f5bc50fb9）重跑失败项，实际通过（8.99秒）。没有下载或安装新工具，本地摘要不是独立发行批准。java_checkstyle_workbench的13项原生验收仍运行，终态另附。

skill_vendor.py check --offline与在线check均实际通过；在线核验codeguard-skills v0.1.2锁定提交2c0c8071f96de48dc53e11de2499c083c100e44c。不修改受管技能或lock，检查脚本不是Rust产品运行时。修复依赖边界后的全工作区普通回归仍沿同一进程运行，未签发整轮通过；13.2及完整计划保持未完成。

原生终态：java_checkstyle_workbench 13项全部通过（68.70秒）；连同迁移重放、record/继承/生成与补齐参数后的Lombok变体，本轮共16项不同Checkstyle原生用例通过。范围含字段/枚举、方法/构造器、参数返回/泛型、类型选项、原配置抑制、准备恢复、稳定任务和原工具复检。旧失败保留，不把本地原生观察升级为完整项目覆盖、可信规则/白名单批准或任务关闭。6.3/9.7仍未完成。


## 2026-09-27 Cargo Clippy原生补充验收

明确选择本机stable-aarch64-apple-darwin的真实Cargo（Rust工具链1.98.1），执行check_all_rust_native两项ignored用例，实际2项通过（6.70秒）。包含原生局部扫描及已初始化稳定任务复检；原生allow抑制经force-warn对照不能解释成已修复，局部缺失仅为未核验策略的候选，任务不自动关闭。此结果不是MSRV1.85实测、完整features/targets覆盖、可信工具/规则政策、Windows或交付门禁验收，7.1/9.7及全计划保持未完成。

修复依赖边界后的全工作区测试仍沿同一运行继续，最新中间结果105组、581通过/0失败/72忽略；忽略项不算通过，原生补充另列，未提前签发整轮成功。

## 2026-09-27 全工作区回归终态与旧插件兼容验收

修复依赖边界后的同一轮 cargo test --workspace 已实际结束，退出码0；完整日志149组结果、880通过、0失败、91忽略（组数含零测试的doc-test组）。日志/private/tmp/codeguard-workspace-boundaries.5rmnN9，SHA256 61690f3e20d0eecb6e9ce06cf98814ba76428763037253214f398ed61c97e899。前述中间数字均为当时进度，本段才是整轮终态。忽略项不算通过，独立原生补充按各自范围记录；详细边界见相邻codeguard-cli/tests/acceptance/workspace-regression-20260927.md。

旧插件使用本机既有/opt/anaconda3/bin/python 3.13.5和Ruff 0.16.8执行兼容检查，不作为新Rust产品的实现路径：

| 检查 | 实际终态 | 范围 |
|---|---|---|
| python -m unittest discover -s tests -q | 退出0；632项运行、621通过、11跳过；111.689秒 | 既有单元与跨进程兼容语义；跳过项未验收 |
| python tests/run_all.py | 退出0；142通过、0失败、1跳过 | 旧语言结构及宿主协议模拟；不等于已安装宿主运行 |
| python scripts/validate_languages_json.py | 退出0；57条目、11条schema规则通过 | 54 stable/3 planned的旧注册表结构，不证明新适配器可用 |
| python scripts/check_architecture.py | 退出0 | 旧实现声明依赖和导入环 |
| ruff check hooks scripts tests | 退出0 | 既有Python兼容代码静态检查 |
| openspec validate introduce-rust-codeguard-cli --strict --no-interactive | 退出0 | 当前增量规格格式与结构有效，不是实现验收 |

旧协议测试中的CODEGUARD_SKIP_GATE等历史行为只证明兼容夹具期望，没有批准新Rust门禁沿用逃生机制。旧单元日志/private/tmp/codeguard-legacy-unittest-20260927.log，协议日志/private/tmp/codeguard-legacy-harness-20260927.log。未静默安装缺失检查器；跳过不改记为通过。此前相同Rust源码状态的fmt、all-targets Clippy和vendor离线/在线检查已记录；本段补全等待中的Rust回归终态及旧插件适用测试。

13.2取得当前macOS/既有工具链的新增回归证据；MSRV1.85、其它平台、三宿主、完整规则/审批/任务关闭与门禁仍缺，不能把本段提升为全计划完成或发布验收。

## 2026-09-27 rules list入口与候选规则目录

按既有4.7/C08及rulepack-governance规格实现Rust只读rules list <language|all> [path]，补充同一Requirement的三项Scenario，不另建事实源。复用静态发现与已有严格版本化Ruff映射，分别展示配置声明、候选映射和逐语言六类目录缺口；不执行动态配置/工具、不修改项目文件、项目同名规则包及自批字段不授权。配置存在不证明具体规则启用，候选始终unverified/not_run；报告0.1固定未完成/退出3，无门禁效果。Node检查器明确映射到TypeScript生态，不以语言前缀遗漏ESLint。

RED：初次新增5项测试在旧入口为1通过/4失败；实现后5项通过。增加Node配置归属反例后再现失败，明确生态映射后修复。中断前启动的相关回归和Clippy句柄后来不存在，且进程检查未见存活任务，不能推断那轮通过；本轮重新执行并保留日志。

当前终态：rules_list_cli 6项、config_inspection_contract 6项、whitelist_command_contract 8项，共20项通过/0失败/0忽略，进程退出0。实际二进制Python/TypeScript/Java/all四份输出通过rules-inventory Draft202012 schema，四种伪造批准/通过变体被拒，动态ESLint配置无副作用。fmt检查退出0；新源码的全工作区all-targets Clippy仍在运行，终态另附。当前OpenSpec strict及git diff空白检查退出0。日志/private/tmp/codeguard-rules-list-tests-20260927.log、/private/tmp/codeguard-rules-list-clippy-20260927.log；验收说明见相邻tests/acceptance/rules-list-static-inventory.md。

未证明完整项目有效规则目录、可信工具锁/政策、逐文件原生配置与suppression差异、已批准例外或三宿主接线；4.7与完整计划仍未完成。之前880项工作区通过属于本入口新增之前的源码状态，不升级为本次新源码全工作区回归证明。

静态检查终态：新源码的cargo clippy --workspace --all-targets -- -D warnings实际退出0（3m44s，含锁等待），没有以中断前未知结果替代；fmt及本轮最终OpenSpec严格校验/diff空白检查已退出0。入口既有单元回归另行运行，终态另附。

入口回归终态：cargo test -p codeguard-cli --bin codeguard退出0，5项既有参数/登记/发现测试通过。连同三个集成套件，本轮25项不同普通用例通过，无忽略；不等于所有工作区套件或原生工具/宿主验收。日志/private/tmp/codeguard-rules-list-entry-tests-20260927.log。

## 2026-09-27 Rustdoc原生适配验收

核对Cargo rustdoc官方命令与本机最小原生输出，确认missing_docs进入Cargo JSON诊断，不能复用Clippy过滤器。按现有7.1/原生证据Requirement增加独立Rust解析器及两项Scenario，保持同一OpenSpec事实源；规则/级别/唯一主定位及原生package/manifest/target仅作观察，待执行层绑定。重复键、歧义定位、异常结束、未知警告、编译错误为未完成，不按自由文本或退出非零生成注释违规。

初态新API缺失导致契约测试编译失败；实现后cargo_rustdoc_contract 7项通过。crate_boundaries 6项通过；显式已有CODEGUARD_CARGO_BIN的rustdoc_native_replay 1项通过（1.95秒），五种原生输入涵盖缺文档/正常/坏链接/编译失败/源码allow抑制，源码不变，无安装。总计14项不同测试通过；不能将五个循环输入写成五项独立测试。相关两测试目标的Clippy -D warnings退出0（15.09秒），fmt退出0。

原生重放使用Rust1.98.1，只执行局部库目标。未实现公开comments rust、稳定任务/复检闭环、原配置与完整目标归属、前后字节绑定、可信工具/规则、全部features/workspace、跨平台与宿主；7.1仍不勾选。验收说明见相邻codeguard-cli/tests/acceptance/rustdoc-native-observation.md；先前880项全工作区成功不是本次新增源码的全量证明。

## 2026-09-27 comments rust公开入口与输入归属

延续7.1，同一Rust服务接入comments rust，显式Cargo经共享runtime运行锁定离线库目标机器流，采用私有target目录和共享预算。SourceSnapshot捕获根清单/锁/全部本轮已发现Rust源码，运行后复核字节及发现集合；Cargo入口摘要前后绑定。原生主定位、根清单和库目标源码归属不匹配为未完成。human/JSON反馈明确显式规则探针、未批准政策/覆盖、任务尚未接入及原工具复检，不把零诊断解释为修复或交付。

RED：入口缺失时普通测试1通过/3失败、原生1忽略；实现阶段一次错误Result::filter调用导致编译失败，修正后4项普通CLI测试通过。显式本机Cargo/Rust1.98.1的原生CLI用例实际1通过（3.43秒），含补文档前后两轮；不是两项独立测试。随后最终源码4项CLI契约及5项入口单测通过（共9项普通、1项默认忽略）；原生独立补充计1项，不能把忽略项重算为默认通过。相关CLI目标Clippy -D warnings通过（最终2.50秒）。

实际缺工具与原生有发现两份报告通过rustdoc-local-observation Draft202012，篡改授权/交付/覆盖/关闭的四个变体被拒。该校验的Python不在Rust产品运行链。验收说明见相邻tests/acceptance/rust-comments-cli.md。

当前backlog_status固定not_integrated；未实现稳定文档任务、task verify、抑制对照、check all调度、完整配置/运行时闭包、可信工具/规则、全部workspace/features/targets或跨平台/宿主，7.1仍未完成。旧全工作区回归不能升级为本次新增源码的全量证明。

取消反例追加：真实SIGINT与源码变化同轮发生时，首次测试失败，退出3而非130；修正取消优先级后rust_comments_cli 5项普通通过/1项默认忽略（1.39秒），相关CLI目标Clippy -D warnings退出0（6.54秒）。前面的4项为该反例加入前的历史记录。原生补文档前后用例在最终源码上再次运行，终态另附；5项入口单测已有通过，完整工作区未重跑，完整计划不勾选。

最终原生补充实际1项通过（3.45秒），普通5项及独立补充均不失败；fmt、OpenSpec strict和diff空白检查退出0。仍不提升为完整任务或全部工作区验收。

## 2026-09-27 Rustdoc范围身份与歧义反馈

持久任务接线前审计发现旧行锚点/序号可能错认同一行的crate与函数诊断。新增独立纯身份服务，保留原生字节范围并校验真实UTF8切片及行列；指纹采用规则、相对目标与原生范围字节，不采用行号或输出序号。完全相同原生记录去重；不同范围候选指纹碰撞时保留观察但finding_id为空、identity_status=ambiguous，运行未完成，不能生成正式任务身份。

新增身份API最初缺失导致编译失败；重复声明CLI反例最初错误返回native_observed_unverified。修复后3项身份契约、6项CLI普通及7项协议回归通过。反馈升级0.2，旧0.1 schema原字节副本保留；实际原生0.2报告通过schema，crate/函数ID不同，伪造歧义仍保留ID的变体被拒。之后补强范围与行列一致性并复跑普通回归仍通过；最终原生/静态结果另附，不复用补强前结果。

这是7.1/9.7的身份前置，不是完整符号身份、持久任务或task verify交付。已知同文件同声明的不同符号仍需语义归属，目前只调查歧义；完整配置/构建组合、可信来源、三宿主及任务关闭重开仍缺，不勾选。验收见相邻tests/acceptance/rustdoc-native-span-identity.md。

补强后终态：两项原生独立用例均通过，CLI用例追加中文文档坏链接的真实UTF8范围/行列核对（5.12秒），原生重放用例通过（1.26秒）。相关adapters/CLI测试目标Clippy -D warnings退出0（7.69秒），普通6+3与协议7已有通过；合计18项不同测试，两个原生测试均显式独立执行，不把默认忽略计为通过。全工作区未重跑，完整计划保持未完成。

## 2026-09-27 Rustdoc逐问题修复简报

comments rust报告0.3为每条原生发现生成七项修复信息；missing_docs区分内部/外部文档，broken_intra_doc_links要求核对真实符号及作用域。简报绑定本轮源摘要、原生范围及复检argv，修改范围限于原目标；输入变化/身份歧义等未完成观察只给调查及重新检查，修改范围为空。attempt_history空数组明确history_status=not_integrated，不能证明没有历史失败。保留0.2 schema，当前协议升级0.3。

TDD先验证缺简报的两项失败；实现后7项普通CLI和3项身份测试通过，1项真实Cargo CLI独立执行通过（4.34秒，含缺文档、补齐、中文坏链接），相关Clippy -D warnings通过（5.77秒）。真实原生报告通过Draft202012协议；删除七项修复字段的七个变体及未完成却保留源码修复指引的变体均被拒。Python校验仅为独立验收，不在Rust产品执行路径。

尚未实现Rustdoc持久同步、task verify、尝试历史读取、抑制对照、正式关闭/复发重开、check all调度和完整配置/工具/策略覆盖；7.1、9.7保持未完成。全工作区未重跑，完整目标继续。验收见相邻codeguard-cli/tests/acceptance/rustdoc-repair-brief.md。

## 2026-09-27 Rustdoc自动持久同步与next

comments rust报告0.4加入工作区绑定、独立run_id和原生目标相对路径，保留0.3历史schema。已初始化时保存queued报告并自动调用统一work sync；新原生发现生成稳定fact、Markdown七项任务与观察，同一问题再次扫描不重复建任务。导入重建原生范围指纹和简报，核对源码、清单及锁的当前字节；陈旧证据作为历史并生成重扫准备阻塞，坏身份/额外字段/范围或工具状态矛盾拒绝导入。未完成观察只生成检查准备任务，不创建源码违规。next识别rust.cargo_rustdoc并给同一原工具重扫指引；尚无task verify时不指示自动关闭。

TDD初始化扫描缺持久同步时先RED；新增重复扫描/next、缺工具准备、队列入库后清单变化、伪造指纹四个契约。最终相关普通回归：rust_comments_cli 11、identity 3、work_sync 15、cross_category 1、next 6，共36项通过，3项默认忽略不计通过。真实Cargo CLI显式独立运行1项通过（5.56秒），追加初始化、真实发现任务文件及自动同步检查；相关Clippy -D warnings终态通过（10.28秒）。实际绑定反馈与queued报告通过Draft202012，task文件存在，缺工作区ID反例被拒。fmt/OpenSpec结果另记。

7.1/9.4/9.7未完成：原配置/完整目标覆盖、可信工具规则、文档task verify/尝试历史/抑制对照/关闭复发及跨宿主尚缺。旧全工作区回归不代表本轮全量；验收见相邻tests/acceptance/rustdoc-workbench-sync.md。

## 2026-09-27 Rustdoc任务复检与原生抑制对照

复用comments rust的同一观察服务，接通task verify --cargo-tool；同一预算与任务租约内执行普通rustdoc及force-warn对照，捕获全部已发现Rust源/清单/锁并核验两轮输入与工具摘要。原问题仍在为still_present，同文件同规则身份变化为rule_coverage_requires_review，抑制重现为suppression_requires_review；两轮局部零发现仅candidate_absent_unverified_policy，任务保持open。环境恢复同样待策略核验。复检保存同一问题事件并关联准备好的attempt；next/历史读取识别rustdoc时间序列，源码/清单/锁变化后不沿用旧观察。未稳定封套的导入不生成源码修复任务。

协议：rustdoc_task_recheck 0.1封套包含普通/强制原生观察与输入身份；文档task_verification_preview升级0.7，其它既有预览继续0.6。保留原0.6schema；当前schema接受具名旧协议及新封套，不赋予门禁/关闭权威。实际原生预览及两轮嵌套报告通过Draft202012，校验Python仅独立验收。

TDD缺入口先RED，随后暴露历史读取器缺新checker与序列格式导致第二次复检失败，补齐后连续仍在/抑制/缺失契约通过。相关普通回归：文档CLI12、next6、同步15、任务租约16、任务复检10，共59项不同测试通过；11项默认忽略不计通过。原生CLI独立1项实际通过（14.07秒），包括初始化/稳定任务、真实缺文档复检、补齐文档与源码allow的force-warn反例、中文坏链接；同一测试多轮不重复计数。相关最终Clippy结果另附。

仍缺正式关闭与复发重开、完整原配置/workspace/features/targets/符号归属、可信工具/规则/批准、全部语言类别及宿主；7.1/9.7不勾选。未来工具文件变化的旧复检不能作为批准工具证明，本地来源始终未核验。本轮没有全工作区回归。验收见相邻tests/acceptance/rustdoc-task-recheck.md。

最终补充：相关五个CLI测试目标Clippy -D warnings退出0（9.51秒）；fmt --check退出0，OpenSpec严格校验及git diff --check退出0。原生验收后仅调整next/任务说明文字和复检argv指向，CLI12与next6再通过；全工作区及完整正式闭环仍未验收。

## 2026-09-27 Rustdoc强制对照导入身份修正

反例先RED：普通观察合法时，强制对照的伪造指纹及重复输入归属均被旧同步器消费，failed_reports=0。现把复检导入交给独立Rustdoc封套解析：严格检查顶层键与唯一输入路径归属，稳定输入绑定源/目标及清单/锁；普通和强制观察分别进入同一严格原生范围/指纹解析。强制argv及原始证据保留在封套，只在内部核验投影规范化参数，不修改原始报告或将抑制当修复。输入不稳定/当前失配时只导入准备阻塞，不生成源码任务。

同一反例验收三种变体：伪造强制指纹和重复输入被拒，不稳定封套只生成一项重扫阻塞；没有新增源码任务。相关普通回归13项文档CLI、15项同步、6项next，共34项通过；3项默认忽略不算通过。真实Cargo CLI独立1项通过（14.49秒），覆盖正常文档发现/修复复检、原生allow/force-warn和中文链接；相关Clippy -D warnings退出0（7.18秒）。真实报告协议验收另记；schema增加重复行拒绝，唯一字段归属仍由Rust核验。

这是任务复检证据的完整性修正，不是正式批准或关闭；7.1/9.7保持未完成。全工作区未重跑，完整目标仍需持续推进。验收见相邻tests/acceptance/rustdoc-forced-evidence-binding.md。

协议终态：真实本机Cargo文档task verify报告及嵌套普通/强制观察通过当前Draft202012；重复输入行变体被schema拒绝。独立校验退出0；fmt --check、OpenSpec严格校验及git diff --check均退出0。没有全工作区或完整交付批准验收。


## 2026-09-27 Rustdoc 接入 check all

完整检查入口新增独立 rust.comments 节点，复用 comments rust 观察服务与持久同步；与 Clippy 共用总预算和 Cargo 资源互斥，分别保留结果/完成状态/准备任务。取消标记传入原生进程，避免新节点绕开任务取消。文档原生发现进入统一对话反馈和 next；检查器成功不覆盖其它未完成。check_feedback 0.27、check_aborted 0.8 自包含嵌入 Rustdoc 0.4，旧 0.26/0.7 协议保留。

TDD：缺调度时新契约先失败；接线后回归暴露旧任务计数、协议自包含以及独立准备任务 next 预期，已修正。真实验收新增断言最初误用 local_complete 字段失败，改为既有 local_scan_complete 后通过，不改生产协议迎合测试。普通相关 Go3/Java24/npm2/部分结果13/Rust11/文档14，共67项通过，12项默认忽略不算通过。显式既有 Cargo 原生3项通过：Clippy两项7.03秒、Rustdoc一项12.96秒；增强后的原生完整检查实际断言 missing_docs 及独立两节点。相关 Clippy -D warnings 通过（1.20秒）。

真实未初始化/初始化 check_feedback 0.27 均通过 Draft202012，初始化文档同步状态 synced；check_aborted 0.8 仅静态 schema 合法性，本轮未声称实际异常中止协议验收。Python仅独立验收，不在产品执行路径。正式规则/完整构建组合、可信工具策略、关闭复发与宿主仍缺；7.1/9.7不勾选，全工作区未重跑。详见相邻 tests/acceptance/rustdoc-check-all.md。


## 2026-09-27 当前 Rustdoc 集成后的全工作区验收启动

当前源在完整 Rustdoc/check all 接线后启动 cargo test --workspace 和 cargo clippy --workspace --all-targets -- -D warnings。两项运行尚未终止，不能以旧880项通过替代本轮终态；测试日志 /tmp/codeguard-workspace-current-20260927.log，Clippy日志 /tmp/codeguard-clippy-current-20260927.log。本轮首批13组59项通过/0失败/0忽略，只是中间结果，13.2保持未完成。

独立协议静态审计115份schema合法且本地引用可解析；实施索引核对108项Requirement均有对应行且无重复标题，仅证明映射。OpenSpec strict及git diff --check退出0。未安装工具、未修改规格要求、未发布；完整计划继续，后续沿同一进程核验终态，不因观察等待重启。


## 2026-09-27 全目标 Clippy 终态

同一运行 cargo clippy --workspace --all-targets -- -D warnings 已退出0，耗时2m01s，日志SHA256 ba479f2fe8cb4e988013460eed8c16cd6d506830b65530f8804107cf89c7695d。不是部分目标检查。全工作区测试仍运行，中间17组、74通过/0失败/1忽略；不得用中间结果宣布全通过。13.2及完整计划保持未完成。


## 2026-09-27 插件兼容静态与 vendor 校验终态

既有架构脚本通过，语言注册57条（54 stable/3 planned）及11项schema规则通过；受管技能离线和在线check均退出0，在线核验 v0.1.2 -> 2c0c8071f96de48dc53e11de2499c083c100e44c。未更新lock、未安装或发布。旧Python脚本只是既有插件兼容验收，不新增Rust产品中的Python检测路径。

Rust全工作区测试同一运行仍在继续，本次中间25组/103通过/0失败/4忽略，不能宣布终态。全目标Clippy本轮已通过，115 schema静态校验和108 Requirement映射也通过，均不等于所有原生/平台/宿主验收。13.2不勾选。


## 2026-09-27 既有插件测试与解释器边界

协议模拟 tests/run_all.py 终态142通过/0失败/1跳过。第一轮unittest实际632项/93.819秒，1失败/21跳过：主进程3.13.5而Bash CLI子进程PATH选到系统3.9，zip(strict=True)报错，不能将该轮计通过。仓库CI明确3.11/3.12/3.13。统一PATH到既有/opt/anaconda3/bin后，失败所在CLI合同3项实际通过（0.539秒），随后启动同一环境完整unittest，日志 /tmp/codeguard-plugin-unittest-python313-20260927.log，尚未终态。未修改Python生产逻辑、未安装解释器；保留首轮失败。Rust全量沿原进程继续，完整验收仍未完成。


## 2026-09-27 统一解释器插件 unittest 终态

明确 PATH=/opt/anaconda3/bin:$PATH，主/子进程使用既有Python3.13.5；完整unittest退出0，632项/99.003秒，其中621通过、11跳过。日志SHA256 10f2e398b7d644ab8abf9cb3efebdfd637efc9994fd80fb41b454f12b0eff71e；首轮3.9子进程失败仍保留，不伪称系统3.9兼容。协议模拟142通过/1跳过、全目标Rust Clippy、架构/语言/schema/OpenSpec/vendor检查分别记录。Rust测试同一运行仍在继续，中间74组/432通过/0失败/34忽略，尚无完整终态；13.2及总目标保持未完成。


## 2026-09-27 Rust 构建实现前验收约束

继续既有7.1与Rust command plans SHALL preserve explicit build levels要求，追加原生Cargo check的可归属编译错误与报告损坏两场景；不新增change或改验收目标。后续适配须保留package/manifest/target与原生诊断，类型检查固定test_execution=false，不改称Clippy/文档/安全违规。成功/失败结束、原生退出、重复键、结束后事件及无可归属诊断的失败须分别核验；裸退出不生成源码违规或通过。当前只有规格补齐，尚无Cargo构建实现或测试通过声明；7.1仍未完成。OpenSpec strict和git diff --check退出0。现有Rust全工作区测试继续原运行，未因等待重启。


## 2026-09-27 Rustdoc集成后全工作区测试终态

同一 cargo test --workspace 运行已退出0：154组、910通过、0失败、93忽略。包括当前Rustdoc/check all/任务复检及所有既有普通回归；忽略原生测试、MSRV1.85、Windows和宿主不计通过。日志 /tmp/codeguard-workspace-current-20260927.log，SHA256 8d647e591bac5d2d247e33a3e648922d102da3639c72909a0513ecb3b91c5ff8。当前 source 的全目标Clippy已退出0，既有插件unittest621通过/11跳过、协议模拟142通过/1跳过，115schema静态/OpenSpec/架构/语言/vendor另有终态。

当前全量结果替代旧880项基线，不抹去首轮Python3.9子进程失败；93项忽略须各自具备条件后独立验收。实际原生Cargo3项和反馈0.27的两种绑定情况验收另列，不把普通协议夹具当真实工具。原配置/全构建组合、可信策略、关闭复发、全部语言类别与发布宿主仍缺，13.2及完整目标不勾选。下一实现为已有7.1下Cargo原生构建契约，新增两场景只是验收准备。


## 2026-09-27 Cargo 原生构建解析前置

新增独立 CargoBuildDiagnostic/CargoBuildParsed 对象与 Cargo check JSON流解析，保留编译器错误码、package/manifest/target及唯一主定位范围，不借Clippy/文档规则过滤。结束成功与退出、成功却带error、失败无可归属错误、坏/重复键/未知记录/结束后事件、规模上限等均未完成；前序有效观察保留仅供调查。纯解析尚无源字节/工具/配置绑定，不授予正式源码finding、覆盖或交付权威。

TDD缺入口先因unresolved import失败；实现后8项新协议、adapter库6项、Rustdoc7项、依赖边界6项，共27项普通回归通过。真实既有Cargo原生1项通过（0.94秒），包括E0308类型错误、成功但故意失败测试未运行、build.rs执行失败不被误报为源码；首次路径断言因macOS临时路径别名失败，核对实际manifest路径后通过，未改生产解析规则。相关Clippy -D warnings退出0（10.63秒）。未安装或下载工具。

公开build rust、共享runtime服务、原输入/工具/目标归属、持久修复任务、复检、check all与完整构建组合仍缺，7.1不勾选。此前154组/910通过全量是本前置之前的基线，本轮新源仅上述受影响验证，不宣称重跑全量；完整目标继续。验收见相邻tests/acceptance/cargo-build-native-observation.md。


## 2026-09-27 build rust 公开类型检查探针

新增 build rust [path] --cargo-tool ABS_PATH --timeout DURATION --format human|json，使用共享预算/runtime/SourceSnapshot与私有target调用原生Cargo check --locked --offline --all-targets --message-format=json；不执行测试，不生成锁，不安装工具。前后核验已发现源码集合、根清单/锁和工具字节，原生目标须归属本轮源及根清单，UTF8范围及行列重建候选指纹。保留包身份摘要和原生目标类别，避免公开本机package路径；不同目标类别同候选指纹不按原生顺序消歧。输入/工具变化、取消/超时等不给源码修改范围；取消优先130，普通局部命令保持3/not_evaluated/coverage_proven=false。

每发现给七项静态修复/调查信息，历史not_integrated且不授权关闭。反馈 rust_build_local_observation 0.1及严格自包含schema新增build_level=type_check/test_execution=false/build_success；没有队列、任务或门禁接线。真实错误和成功反馈均通过Draft202012，六个伪造授权/覆盖/状态及缺包身份变体被拒；独立Python只验收，不在产品路径。

TDD缺公开入口先RED。最终相关普通26项（build6、Rustdoc14、边界6）通过、2项默认忽略不计通过；真实公开Cargo1项通过（7.15秒），包含E0308、补齐成功但panic测试未执行、构建脚本失败不生成源码违规；相关Clippy -D warnings最终退出0（5.63秒）。中途一次输入变化测试得到source_discovery_incomplete，已加强fixture的原子序列路径隔离，之后全组通过；该次底层原因未完全归属，保留失败，不改生产失败判定。

7.1/9.7仍未完成：公开命令仅原生类型检查局部探针，缺完整配置/workspace/features/targets/可信工具策略及任务同步/verify/关闭复发/check all接线；新源未重跑全工作区，此前910项基线不覆盖本次新增行为。验收见相邻tests/acceptance/rust-build-cli.md。


## 2026-09-28 Rust构建报告自动同步与next

build rust局部观察协议升级0.2，保存0.1原始schema；每条finding增目标源码摘要，初始化工作区自动入队并sync。严格导入核对工作区/run/file键、原生状态、根清单锁与当前源码及目标普通文件字节，重算UTF8原生范围指纹；导入改用SourceSnapshot读取源码/目标以拒绝路径别名。包摘要保持未核验观察，不冒充可信来源。有效发现生成稳定fact和七项任务，同一问题重复扫描只更新观察。旧目标即使错误源码未变也只留历史并生成重扫准备任务；伪造指纹拒绝。缺工具生成稳定准备任务，next显示同一原生构建复扫指引。

TDD缺自动同步先RED。相关普通：build9、work sync15、next6，共30项通过，3项默认忽略不计通过；真实公开Cargo1项通过（7.70秒）；实际绑定反馈与queued 0.2均通过Draft202012，任务文件存在，缺目标摘要反例拒绝。Clippy第一次发现一处不必要借用，已按诊断修正且重新执行，终态见后续证据。

7.1/9.7/9.4均未完成：正式task verify、关闭复发、可信包工具/规则策略、完整workspace/features/targets及check all仍缺。0.2队列同步不是构建通过、风险接受或白名单批准；历史0.1不能作为当前可导入报告。全工作区当前新源码尚未重跑；旧910项基线不得挪用。验收见相邻tests/acceptance/rust-build-workbench-sync.md。

## 2026-09-28 Rust 构建任务局部复检

任务从RED `task_checker_unsupported` 到同一原生Cargo的复检事件。41项受影响普通回归通过（build10、work sync15、next6、task verify10）；12项条件性忽略不算通过。显式既有Cargo真实复检1项通过，证明E0308持续与修复后局部零诊断两条路径，后者仍为`candidate_absent_unverified_policy`、`test_execution=false`、`delivery_decision=not_evaluated`。相关all-targets Clippy -D warnings退出0；119份schema静态合法性及本地引用存在性通过。实际本地任务复检封套与公开反馈通过Draft202012验证，伪造delivery allow反例被拒；该局部验收不替代全工作区回归、可信批准、正式门禁、关闭复发、MSRV/Windows/宿主验收。

全工作区当前源码的 `cargo test --workspace` 已以退出0结束，覆盖适配器、CLI、核心、运行时的默认测试和doc-tests；默认跳过的显式原生/平台条件用例仍不计通过。此次全量是在Rust构建任务复检代码和回归测试加入后执行，替代旧910项基线，但不证明全部OpenSpec计划已实现。受影响包all-targets Clippy及OpenSpec strict通过；正式白名单宿主审批、关闭复发、完整语言与构建矩阵仍未完成。

## 2026-09-28 check all 接入 Rust 原生类型检查

TDD 首先复现 `check all` 虽运行 Rust Clippy/rustdoc，却把构建类别留在 `not_integrated`。现新增独立 `rust.build` 节点，在现有共享预算与 Cargo 目标资源下调用原生 Cargo check；编译诊断独立于 Clippy/文档发现，完成后同步本地稳定任务，环境或报告故障保留具体未完成原因。旧 Clippy 待修任务继续优先显示，构建任务可独立从 next 读取；不把任务清空、零诊断、项目可写批准候选解释为交付通过。反馈 0.28 增 `rust_build`、`rust.build`，故障反馈 0.9 增构建结果，旧协议 schema 原字节留存。

新场景先 RED 后通过。调整后受影响的 Rust 原生/部分合同/Java/npm/SARIF/rustdoc 集成测试全部通过；一次回归揭示旧 Clippy 下一步被构建环境任务抢占，已修正优先顺序。另一次实际报告验证揭示 schema 漏列 `rust.build` 节点，已补齐。最终 `cargo test --workspace --quiet` 完整退出 0；当前反馈实际 JSON 通过 Draft202012，121 份 schema 文档静态合法；schema 改动后再次运行的 Rust 与部分合同两组分别为 12/13 通过、2/1 忽略。`cargo fmt --check`、CLI 全目标 `cargo clippy -D warnings`、OpenSpec strict、插件 `git diff --check` 均退出 0。

这只验收局部原生类型检查与任务指引；未证明全部 Cargo workspace/features/targets、测试执行、受批准规则/工具、白名单可信批准、正式关闭复发或交付门禁。7.1/9.7/4.8/13.2 保持未完成，默认忽略的原生条件用例不计本轮通过。

## 2026-09-28 白名单原生 finding 身份二次绑定

新增失败反例先证明：裁定和附带观察身份相等，但原始 finding 缺完整身份时，旧领域门禁错误返回 allow_with_exceptions。现领域 finding 可携本轮完整身份，只有它与裁定观察逐字段相同且既有原生规则、工具、主定位、义务及宿主冻结映射均匹配时，才可能标精确误报。旧报告缺字段、源码内容/指纹/工具/适配器/rulepack 摘要、依赖图或 advisory 变化均保留原始及活动阻断，结论 incomplete。项目 JSON 自填该字段不能证明它来自真实原工具；可信宿主来源和正式白名单门禁仍缺，4.8 未完成。

受影响门禁 34 项、会话 8 项、签名处置 3 项、core 包普通测试均退出 0。全工作区 `cargo clippy --workspace --all-targets -- -D warnings`、`cargo fmt --check`、OpenSpec strict 与插件 diff 空白检查均退出 0。随后首次全工作区测试在编译阶段退出 101：另一个进程同时对同一 CLI workspace 执行 `cargo clean --manifest-path .../codeguard-cli/Cargo.toml`，删除 `target/debug/.fingerprint`，Cargo 报多个 dep-info 目录不存在。该次不是测试通过，也不是源码失败；在清理结束、构建目录稳定后须重新运行完整回归。

## 2026-09-28 RunReport 1.4 白名单身份声明约束

新增 1.4 报告协议：每条 finding 带完整 `native_identity`，每条误报处置带 `decision_identity`，解析时要求两者逐字段相等，并核对规则、声明的工具摘要、检查器类别及主目标。历史 1.3 schema 原样保留，旧版本不能借新字段伪称 1.4；未来未知版本拒绝。新增目标反例先因解析器不认识 `native_identity` 失败，随后 9 项白名单合同、14 项既有报告合同、4 项 SARIF 合同通过。依赖图/advisory 改变复用旧处置被拒，SARIF 仍保留未核验处置结果且不泄露私有令牌。独立 Draft202012 对实际 1.4 正例接受，对缺 finding 身份、缺处置身份的变体拒绝。详见相邻 `codeguard-cli/tests/acceptance/run-report-allowlist-protocol.md`。

字段仍由报告自行声明，结构解析不证明本轮原生工具输出或真实源码/依赖图字节，更不证明受保护审批、撤销和可信时钟。真实报告生产、独立来源核验、正式 CLI/MCP/Hook 门禁仍未完成；2.10、4.8 均不勾选。全工作区回归和当前源码的全目标 Clippy 结果在本节记录时仍待重跑，不沿用前一源码基线。

本轮随后重跑得到终态：当前源码 `cargo test --workspace --quiet` 退出 0，全部默认运行的测试组通过；需显式原生工具或平台条件的忽略用例未计为通过。`cargo clippy --workspace --all-targets -- -D warnings`、`cargo fmt --all --check`、122 份 schema 的 Draft202012 静态校验、OpenSpec strict 与插件差异空白检查均退出 0。上述结果证明回归和协议静态有效，不把报告自填身份提升为可信来源，也不把 2.10/4.8 标为完成。

## 2026-09-28 RunReport 源码覆盖和独立字节复核

TDD 先复现报告漏洞：把源码 finding 的主定位、原生身份及白名单决策身份一同改为义务覆盖范围外的路径，旧 1.4 解析仍接受带例外结论。现每个源码目标必须属于其义务预期与实际覆盖集合，反例被拒。另为受信宿主提供 `compare_claimed_source_hashes`，由宿主独立指定工作区根并通过 `SourceSnapshot` 安全读取全部声明的源码目标，比较当前普通文件 SHA-256。目标测试先因接口缺失编译失败；实现后覆盖真实字节匹配、内容变化、文件删除、Unix 链接、旧报告及同文件冲突摘要。白名单合同 12 项、既有报告 14 项、SARIF 4 项通过。

当前源码完整 `cargo test --workspace --quiet` 退出 0：157 组、937 通过、0 失败、96 忽略；日志 `/tmp/codeguard-workspace-report-source-20260928.log`，SHA-256 `3b0bb42977983a8c2a05ba559ea5220f3afcf17f6beafb1a4681bb5e75b5c965`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件 diff 空白检查通过。该内容比较是当前时刻的局部证据，不证明报告来源、原生工具运行、批准与终局输入不变；正式门禁尚未调用，2.10/4.8/12.12 保持未完成。

## 2026-09-28 Ruff 本轮适配器摘要进入误报调查

真实 Ruff 0.16.8 用例先因误报提案没有 `adapter_sha256` 失败。Ruff 局部报告 0.9 现只在有原生 finding、未取消且预算仍有效时计算当前 CodeGuard 可执行制品摘要；工作台读取本轮已同步发现后再次比较当前二进制。反例同时改写本地报告与消费标记的报告摘要，仍因适配器字节不符拒绝候选；规则包保持 `candidate_unapproved`，提案仍 `candidate=null`、退出 3、无门禁效果。公开 lint 升 0.12、误报预览升 0.4、Ruff task verify 升 0.9，三份前版 schema 保存供历史读取；实际三种新输出均通过 Draft202012，其中 task verify 使用本地 schema 引用注册。见相邻 `codeguard-cli/tests/acceptance/ruff-adapter-identity.md`。

首次实现在原生探测前两次哈希整个二进制，引发短预算与 SIGINT 两项回归失败；改为 finding 返回后按需计算并在哈希后再次核对截止时间。最终当前源码全工作区测试退出 0：157 组、937 通过、0 失败、96 忽略，日志 `/tmp/codeguard-workspace-adapter-final-20260928.log`，SHA-256 `63a22f4bba2daf1a006ce0c4bcf917cdba192892712aceeed1f052ba3b18611e`。另外显式运行原生 Ruff 任务复检 8 项、白名单/纠错 2 项，全部通过；125 份 schema 静态校验、全目标 Clippy、格式、OpenSpec strict 和插件差异空白检查通过。二进制摘要仍不是可信发行签名，报告/消费标记仍由项目可写，批准 rulepack、人工裁定与正式门禁尚缺；4.8/4.9/12.12 不勾选。

## 2026-09-28 legacy-v1 逐入口协议映射

任务 2.6 已完成具名映射与参数验收，映射表见 [旧入口协议表](../../../docs/rust-cli/legacy-v1-protocol-map.zh-CN.md)，Rust 证据见相邻 `codeguard-cli/tests/acceptance/legacy-v1-protocol-map.md`。旧 check/CVE 对混合 FAIL 与 UNVERIFIED 返回 2，Dockerfile 返回 1 且保留已确认风险；CVE 参数错误为旧 3，PreToolUse 的 2 是宿主拦截。`fix` 的无语言、无改动、无适用文件分别登记；没有上下文的空结果不猜数字。旧 MCP 四个工具不具有逐请求进程退出码，五类 Hook 的生命周期成功不能当新版质量通过。所有 Rust 兼容投影固定 `not_evaluated`，C35 实际运行时和宿主迁移仍未完成。

真实旧插件相关测试在 PATH 前置已有 Python 3.13.5 后 164 项通过，MCP server 7 项通过；若由系统 Python 3.9 执行旧包装器，一项 `fix` 用例会因 `zip(..., strict=True)` 抛错，这一旧环境差异已保留为迁移缺口。当前 Rust workspace 全量测试 158 组、941 通过、0 失败、96 条件忽略，`legacy_v1_protocol_contract` 3/3，all-targets Clippy `-D warnings`、格式检查、OpenSpec strict 与插件差异空白检查均通过。此验收仅证明旧协议映射，不证明新版统一 CLI、MCP/Hook 或交付门禁完成。

## 2026-09-28 Rust 原生 cargo-audit 局部 CVE 观察

延续既有 OpenSpec 7.1，先新增原生 JSON 契约与公开命令目标测试，分别因解析入口和 `cve rust` 不存在失败，再实现 Rust 受控调用原生 `cargo-audit audit --no-fetch --no-yanked --json`。JSON 递归拒绝重复键，核对原生退出/计数/忽略配置，将每条 advisory 的包名、解析版本、来源与校验和绑定本轮 `Cargo.lock` 字节；报告无授权门禁或白名单效力。真实本机 `cargo-audit` 0.22.2 对当前 Rust 工程扫描 172 个锁定依赖、零漏洞，另对 `time 0.1.40` 样本检出 `RUSTSEC-2020-0071`；两份实际反馈均通过新 Draft202012 schema，均为 `database_freshness=unverified`、退出 3、`not_evaluated`。本机原生报告的数据库提交和更新时间均为 null，绝不据此称安全通过或签发误报例外。公开反馈只含依赖来源摘要；警告存在时仍保留已解析漏洞事实。

最终源码完整 `cargo test --workspace --offline -q` 退出 0：160 组、947 通过、0 失败、97 条件忽略；日志 `/tmp/codeguard-workspace-cargo-audit-final-state-20260928.log`，SHA-256 `a6872d6e2a888580533f5191ae035949e29601c09fe3d240aab1ace48ddca674`。新增 adapter 普通测试 5 项、CLI 普通测试 1 项；真实 cargo-audit 条件测试另显式执行 1 项并通过。全目标 Clippy `-D warnings`、`cargo fmt --all --check`、126 份 schema 静态校验、OpenSpec strict 与插件 diff 空白检查均通过；新报告对 false allow/coverage/database freshness 三种篡改被 schema 拒绝。验收详见相邻 `codeguard-cli/tests/acceptance/cargo-audit-native-observation.md`。

这只是局部原生观察：漏洞库可信身份和时效、已批准工具/策略、完整 workspace/features/targets、依赖治理和安全义务、任务同步与复检、`check all`、MCP/Hook/宿主和带例外门禁均未完成。7.1、4.8、12.12 及总体计划保持未完成。

## 2026-09-28 Rust CVE 统一检查与白名单边界

相邻 Rust CLI 将已有 cargo-audit 局部观察接入 `check all` 的独立 `rust.cve` 节点。显式工具与离线库提供的 advisory 保留在 JSON，对应脱敏发现进入 SARIF，human 显示漏洞和下一步；缺工具明确返回环境阻塞。反馈 0.29 和故障反馈 0.10 均加入 `rust_cve`，前一版本 schema 留存。CVE 类别即使观察到 `RUSTSEC-2020-0071`，仍因数据库时效和可信策略未核验保持 `incomplete`、退出 3；没有自写白名单放行路径。OpenSpec rulepack 场景和误报白名单设计补充了 Rust CVE 的待审边界，详见相邻 `codeguard-cli/tests/acceptance/check-all-cargo-audit.md`。

新增目标测试先因 `rust.cve` 缺失失败，接线后通过。完整回归初次揭示旧 Rust 文档测试仍断言三个节点，第二次揭示两项 CVE 测试临时目录并发重名；更新旧断言并给夹具加唯一序号后，最终 `cargo test --workspace --offline -q` 退出 0：161 组、949 通过、0 失败、97 条件忽略。日志 `/tmp/codeguard-workspace-rust-cve-all-20260928.log`，SHA-256 `e4ec3b345fa111ffa18bef11199a5b3f34ce1407aa43646082210844c6a2be0c`。额外显式运行真实 cargo-audit 条件用例 1 项，通过。全目标 Clippy `-D warnings`、格式、128 份 JSON Schema 静态校验、两份实际 `check all` JSON 的 Draft202012 验证、OpenSpec strict 和插件 `git diff --check` 均通过。

本轮没有可信漏洞库来源/时效、完整 Cargo 构建组合、受保护批准、稳定 CVE 任务/复检或正式宿主门禁；白名单当前仍是设计和局部纯领域/候选能力，不能实际替原生发现签发有效例外。7.1、4.8 和总体计划保持未完成。

## 2026-09-28 Rust CVE 工作台与复检增量

先以已初始化 Rust 项目重复原生审计仍无 `rust.cargo_audit` 稳定任务作为失败验收，再实现局部观察封套、持久同步、`next` 修复指引和 `task verify` 原工具复检。相同构建根重复扫描保留一张开放的 CVE 覆盖任务；原生 advisory 留在本地观察，数据库时效仍未核验。复检重新检查清单/锁身份并记录 `still_blocked` 事件，任务不会因勾选、零发现或本地白名单候选关闭。

目标 `check_all_cargo_audit` 3 项、受影响 `check_all_rust_native` 12 项通过，另 2 项条件性忽略。首次全量回归发现新 CVE 任务改变旧 Clippy 用例的 `next` 顺序及任务总数；现将待外部库核验的 CVE 任务排在可直接修复的源码问题之后，更新任务数量预期，受影响组复跑通过。完整 Rust 工作区离线测试最终 161 组、950 通过、0 失败、97 条件忽略，日志 `/tmp/codeguard-workspace-rust-cve-workbench-final-20260928.log` 的 SHA-256 为 `f14638de101e33499308d9ced02632eecd0ab8e032363c345a9ab3bad339a5d6`。全量开始后追加的缺工具阻塞断言另在目标组三项中复跑通过。130 份 schema 通过 Draft202012 静态校验，实际 CVE 封套与复检预览通过 Draft202012；全目标 Clippy `-D warnings`、格式、OpenSpec strict 和插件差异空白检查通过。验收详情见相邻 `codeguard-cli/tests/acceptance/rust-cve-workbench-task.md`。

本地报告及任务身份仍属 `local_unverified`；可信漏洞库身份/时效、批准工具/策略、精确白名单独立批准及正式交付门禁未实现，7.1、4.8 和总体计划保持未完成。

## 2026-09-28 Rust CVE 尝试历史、无进展预算与简报协议

以已初始化 CVE 任务走 claim→attempt ready-to-verify→同租约原生 `task verify` 的端到端回归。首次目标测试发现 `next` 虽能核验复检事件和历史，却没有展示 `still_blocked`；增加 Rust CVE 结果分支后，简报保留未核验库的具体下一步。`still_blocked` 计入同动作无进展预算；追加一次 `no-change` 后，`next` 返回 `needs_decision`，再次启动同动作明确返回 `no_progress_budget_exhausted`。目标 `check_all_cargo_audit` 4 项通过。

另用实际 `next` JSON 发现旧 `repair-brief-preview` 0.1 schema 只容纳 Ruff，现加入严格 Rust CVE blocker 分支，不放宽原 Ruff 约束。实际简报通过 Draft202012；检查器、复检结论、范围三种篡改均被拒。完整 Rust 工作区离线测试最终 161 组、951 通过、0 失败、97 条件忽略；日志 `/tmp/codeguard-workspace-rust-cve-attempt-20260928.log`，SHA-256 `4e172eedebc6e7f235425613f5126910860ebdf1eb403dba31259b6822572427`。新增 schema 在全量 Rust 运行后加入，另经 130 份 Draft202012 静态校验和实际输出验证；全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件差异空白检查通过。验收见相邻 `codeguard-cli/tests/acceptance/rust-cve-workbench-task.md`。

这仅证明本地工作台防重复动作，不具漏洞库来源/时效证明、精确白名单独立批准或最终门禁授权。其它语言的 `next` 严格 schema 覆盖仍缺，7.1/4.8/9.7 和总体计划保持未完成。

## 2026-09-28 尝试结束后的输入变化不得误归因复检

以 Rust CVE 稳定任务构造反例：claim 和 ready-to-verify 已结束，随后 `Cargo.lock` 发生字节变化，再运行原工具复检。旧代码把新输入的复检事件归到旧 attempt。现在通用尝试账本仅在当前任务输入摘要等于该次 finish 的 `after_sha256` 时允许绑定；输入变化时新复检仍可保存，但 `attempt_id=null`，旧尝试仅留在历史，不继续阻塞当前输入的动作或继承其无进展预算。目标集成测试先失败后通过，并确认新输入可登记新 attempt。

受影响普通测试：Rust CVE 5 项、Checkstyle 7 项、租约/尝试 16 项、复检 10 项，合计 38 项通过；Checkstyle 13 项与复检 8 项条件性忽略，不计通过。完整 Rust 工作区离线测试终态为 161 组、952 通过、0 失败、97 条件忽略；日志 `/tmp/codeguard-workspace-attempt-input-binding-20260928.log`，SHA-256 `48f8939abf9d724c00b99e9a1ce8213eca5009c283fbf893919889be8138113d`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件差异空白检查通过。此修正不证明外部工具/漏洞库字节或策略来源已冻结，也不签发白名单批准、任务关闭或交付许可。9.27/7.1/4.8 保持未完成，验收见相邻 `codeguard-cli/tests/acceptance/rust-cve-workbench-task.md`。

## 2026-09-28 白名单候选复用 finding ID 的冲突纠正

新增两条反例：同一稳定 finding ID 的候选分别指向两个源码目标。旧 `rules whitelist explain` 会选中其中一条并返回 `identity_matched`、退出 0；旧纯候选筛选器会返回 `ReadyForAuthorityCheck`。两项测试在修改实现前实际失败；现在查询将双方标为冲突、退出 3，筛选器返回 `ConflictingCandidates`。受影响的两个 Rust 测试组共 21 项通过；完整 Rust 工作区离线测试 161 组、954 通过、0 失败、97 条件忽略，日志 `/tmp/codeguard-whitelist-conflict-20260928.log`，SHA-256 `db31e7f66efbfbeb8bb35a2699c61bc959c3d3d2b257c3dcf6d4be16a966e45f`。全目标 Clippy `-D warnings`、`cargo fmt --all --check`、OpenSpec strict 与插件差异空白检查通过。候选查询仍为 `authority=unverified`、`gate_effect=none`；可信批准来源与真实交付门禁仍未接入，4.8/4.9 和总体计划保持未完成。

## 2026-09-28 公共检查请求与 RunReport 原始 JSON 重复键拒绝

增加检查请求嵌套 `jobs`、RunReport 顶层 `delivery_gate`、内层 `decision` 及内嵌请求 `jobs` 重复键反例。旧解析先覆盖重复值，这两项目标测试修改前均失败；现公共入口复用已有递归无重复键解析器与 16 MiB 字节预算，整份原始输入被拒绝，不生成经过结构校验的对话反馈。请求、报告、白名单报告三个受影响测试组共 33 项通过；完整 Rust 工作区离线测试 161 组、956 通过、0 失败、97 条件忽略，日志 `/tmp/codeguard-strict-public-json-20260928.log`，SHA-256 `cf278e412fb09f368636ae6a938187ae8538d78b16829630f084c9cb7a6e6197`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件差异空白检查通过。这仅加固协议消费；真实原生报告生产、可信来源及最终门禁仍缺，2.3/2.10/12.12 和总体计划未完成。

## 2026-09-28 `check all/java` 本轮项目范围复核

以真实伪 Ruff 子进程在初次项目发现后写入 `late.py`：旧 `check all` 没有标记范围变化，目标测试先失败。现在原生任务结束后重新静态发现，比较源码/清单集合、构建根、清单/锁/规则配置摘要及配置状态；源码新增或规则配置变化时公开 `unresolved_conditions` 记录 `project_scope_changed_during_check`，human 反馈要求重新发现和原工具复检。`codeguard/state` 自有受管记录写入不触发该项；已超过总截止时间则不做无预算末次发现，标记未复核。目标测试组 15 通过、1 条需原生 Ruff 的用例条件忽略；完整 Rust 工作区离线测试 161 组、958 通过、0 失败、97 条件忽略，日志 `/tmp/codeguard-check-scope-recheck-20260928.log`，SHA-256 `aada412ef433de5b3447ca339c2e05de48a77ef28f6147862d6e2cbf2875734b`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件差异空白检查通过。

该复核只比较发现范围和已静态观察到的配置身份，不冻结每个源码文件的全程字节、不检测改后又改回，也不能把本地候选转换为可信必需义务。因此 3.7/2.4 和总体计划保持未完成。

## 2026-09-28 `check all/java` 同路径源码字节复核

初次发现的源码路径在原生任务前建立有界快照；任务结束后从固定根目录描述符读取同路径文件并比较字节。先增加真实伪 Ruff 子进程把 `app.py` 的 `import os` 改为等长 `import io` 的反例，以及 runtime 的原路径字节复核契约；后者先因接口不存在而编译失败。现在 CLI 报 `project_source_changed_during_check`，human 提示核对并发编辑或检查器副作用，保留已有原生诊断和 incomplete 判定。单文件超过 16 MiB 的反例报 `project_source_snapshot_unavailable`；仅改 `codeguard/state` 不报源码变化。`ruff.toml` 同时是 TOML 源文件，配置变更触发源码变化提示符合当前发现分类。

目标 `check_all_partial_contract` 17 通过、1 条条件忽略，`source_snapshot_contract` 5 通过。首次并行全工作区运行在既有 `process_contract::argv_metacharacters_are_literal_and_cannot_spawn_a_shell` 的 `ReadFailure` 失败；第二次在既有 `eslint_probe_contract::interrupted_scan_preserves_cancel_and_deadline_reason_with_or_without_report` 的启动标记断言失败；两项单独复跑均通过，不将两次失败计为全量验收通过。随后 `cargo test --workspace --offline -q -- --test-threads=1` 退出 0：161 组、961 通过、0 失败、97 条件忽略；日志 `/tmp/codeguard-source-byte-recheck-serial-20260928.log`，SHA-256 `f1d7855414a4c1b0e7bfcd4bfa67eaf7e296660ee9d145c2acf94b38ec037772`。全目标 Clippy `-D warnings`、`cargo fmt --all --check`、OpenSpec strict 与插件 `git diff --check` 均通过。

当前快照仅覆盖初次静态发现的源码，捕获过程不是原子项目切面，改后又改回、末次复核之后的修改以及未发现的目标仍无法保证识别；完整沙箱、受保护义务账本和正式门禁亦未完成。因此 3.7/2.4 与总体计划保持未完成。

## 2026-09-28 原生进程读流排空与并行回归稳定性

上一轮同路径源码复核后的两次并行全量运行分别在 `process_contract` 的短命令读取和 `eslint_probe_contract` 的扫描启动前提上失败，单独复跑通过；这暴露了运行时固定 150ms 排空窗口及测试使用过紧整轮期限的时序边界。现成功退出的原生进程继续按原请求绝对期限排空 stdout/stderr，不另造固定短期限；期限耗尽仍不可返回完整。ESLint 反例把伪扫描时间维持长于总期限，并把准备阶段预算增大，使实际取消和期限行为仍被执行。

目标 `process_contract` 15 项通过，`eslint_probe_contract` 2 项通过、2 项条件忽略。当前源码 `cargo test --workspace --offline -q` 并行运行退出 0：161 组、961 通过、0 失败、97 条件忽略；日志 `/tmp/codeguard-runtime-drain-parallel-20260928.log`，SHA-256 `bbb5ee8768ed3baaa1d0337c4f932410c32cfcb631c14797c7641b09353abf4d`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 和插件差异空白检查均通过。先前并行失败记录不被抹除；单次并行通过不能证明所有负载和平台无时序问题。持久化 I/O 硬截止时间、Windows 对等行为及正式门禁仍缺，3.2/3.3 与总体计划继续未完成。

## 2026-09-28 Ruff D100 原生注释问题归类

先用本机 Ruff 0.16.8 和项目 `ruff.toml` 显式选择 D100，复现公共 Python 模块缺少顶层 docstring：原有 `check all` 已保留 D100 原生诊断，但 `comments` 候选仍显示未接入，目标验收先失败。现在仅在本轮原生 D100 实际检出时，将 Python 注释候选关联 `python.ruff`、显示 `observed_unverified` 并给出模块文档修复/同工具复检动作；D100 诊断摘要与修复任务提示也明确说明模块 docstring。补上准确 docstring 后再次运行原生 Ruff，D100 观察消失，注释候选不伪称完整通过，交付仍为 incomplete。规则包未映射的原生诊断保持未批准身份；没有从配置文本或零诊断推断全量注释覆盖。

真实 `native_ruff_d100_is_reported_as_python_comment_evidence` 用例显式执行并通过，普通受影响三个测试目标合计 38 项通过、9 项条件忽略。当前源码并行 `cargo test --workspace --offline -q` 退出 0：161 组、961 通过、0 失败、98 条件忽略；日志 `/tmp/codeguard-python-d100-parallel-20260928.log`，SHA-256 `93e1db0e071bcf6bec16c60916624d8ca4e2c6ba4fa8cbbc14444bdd3ceccbd9`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 与插件差异空白检查通过。D100 以外的注释规则、生效规则集证明、配置级 suppression、可信规则包和完整交付门禁仍缺，7.2 与总体计划不勾选。

## 2026-09-28 D100 稳定任务复检与生效规则交叉核对

实际初始化工作区后，以固定 Ruff 0.16.8 运行 `check all`：D100 原生诊断同步为一张稳定任务，`next` 给出同一任务和规则；`task verify` 在问题仍存在时记录 `still_present`，补充模块 docstring 后再次调用原工具记录 `candidate_absent_unverified_policy`。复检事件已持久化，finding 事实保持 open，没有把任务勾选或局部零诊断当作正式关闭与交付许可。该真实链的显式条件测试通过。

另构造伪 Ruff：JSON 报告声称 D100，但同轮 `--show-settings` 的启用规则集合为空。旧实现错误地返回本地扫描完整；反例先失败。解析器现内部保留精确原生启用集合，D100 与本轮设置矛盾时返回 `rule_settings_report_mismatch`、保留诊断并取消本地完整结论。内部集合不序列化，公开候选映射、规则包批准与既有 schema 形状均未扩大。`ruff_settings_contract` 3 项通过，目标伪报告反例通过；两条真实 Ruff D100 用例显式运行通过。

当前源码并行 `cargo test --workspace --offline -q` 退出 0：161 组、963 通过、0 失败、99 条件忽略；日志 `/tmp/codeguard-d100-workbench-settings-20260928.log`，SHA-256 `7327ce6eee24a47ef34e50fb3390b2a9a2a6c29065faa263445bab7fb9815787`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 与插件差异空白检查通过。配置级 suppression、全部注释规则及完整源集、可信工具/规则政策和正式任务关闭门禁仍未完成，7.2/9.7 与总体计划保持未完成。

## 2026-09-28 Ruff pydocstyle 规则族局部归类

将 Python 注释候选从仅识别 D100 扩为精确 D### 原生诊断，并逐项交叉核对同轮 Ruff 生效规则集合。真实 Ruff 0.16.8 的 D101 公共类缺文档测试先因未归类而失败，修正后通过；适配器格式边界 4 项测试通过，D1000/DOC201 等不会归入该类。伪原生报告 D100/D101 但启用集合为空的反例通过，均保留诊断、取消本地完整结论。真实 D100/D101 两项显式运行通过；全工作区离线测试 161 组、964 通过、0 失败、100 条件忽略，日志 `/tmp/codeguard-d-family-20260928.log`，SHA-256 `5c70119ce9172ee39688a0ef35dae8f38a15e0f58e48366409e1b614619bd98c`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 与插件差异空白检查退出 0。完整 D/DOC 覆盖、配置级 suppression、可信规则批准和交付门禁仍缺，7.2 保持未完成。

## 2026-09-28 D101 可执行修复与原生抑制对照

真实 Ruff D101 样本对“公共类缺少文档字符串”和明确的类 docstring 修复步骤先 RED 后通过。初始化工作区的稳定任务文件给出相同范围与原工具复检命令；在类声明加 `# noqa: D101` 时，`task verify` 的原生无抑制对照检出原问题并记录 `suppression_requires_review`，不能把绕过当修复。补充真实类文档后的复检仅记录 `candidate_absent_unverified_policy`，finding 仍 open。两项真实 Ruff 目标测试均通过；变更后全工作区离线测试 161 组、964 通过、0 失败、101 条件忽略，日志 `/tmp/codeguard-d101-guidance-20260928.log`，SHA-256 `b5d3fe1171c54f4cc85ca13c02c194c583867fa53f71a0f99af4ece2a7a70f26`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 和插件差异空白检查均退出 0。7.2/9.7 仍未完成。

## 2026-09-28 D101 项目自批白名单反例

在真实 Ruff D101 稳定任务已经存在后，向项目自有 `codeguard/decisions/forged.json` 写入同一 finding 和 `approved=true`。重跑原生 `check all` 仍返回 D101、同一唯一稳定任务和 incomplete；只读 `rules whitelist propose` 固定 candidate=null、authority=unverified、gate_effect=none。原逻辑只笼统报告批准规则包缺失，现将尚无核对映射的 D101 标记 `rulepack_mapping_unavailable`，分别列出 `reviewed_native_rule_mapping` 与 `approved_rulepack_identity`，human 输出也显示核对动作。该具体期望先 RED 后通过；已有 F401 候选映射的真实回归通过，仍不获批准。该证据只覆盖未接可信批准时的拒绝路径，不能证明未来独立签发、密钥来源与正式交付例外已接通；4.8/4.9 仍未完成。

分流改动后全工作区离线测试 161 组、964 通过、0 失败、101 条件忽略，日志 `/tmp/codeguard-rulepack-mapping-20260928.log`，SHA-256 `be05119f7a9fcc5cd7b9029b611f2975d54c1f06531dae81f7741376f8994663`；真实 D101 和 F401 白名单提案用例分别显式通过。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 和插件差异空白检查退出 0。完整可信签发及门禁仍未实现，保持原任务未完成状态。

## 2026-09-28 Python 依赖输入的逐构建根只读发现

相邻 Rust 工程新增 Python requirements 的保守行级分类和逐构建根 CVE 输入说明。先写的 `detect` 与 `check all` 目标回归分别因缺少 `python.pip_audit` 发现、类别反馈而失败；实施后，逐行固定版本、动态约束、uv 锁存在未解析、无依赖输入与根/子项目锁归属的正反例通过。包名大小写及 `-`/`_`/`.` 等价形式的重复声明也保持未解析。`plan cve python` 不生成已可执行扫描任务；`check all` human/JSON 报告配置未知、依赖图及原生工具待核验，交付固定 incomplete。源码/依赖输入变化的故障注入分支尚无独立测试，不能以这些回归代替原生漏洞验收。

`detect_cli` 27 项、`check_all_partial_contract` 17 项通过/3 条件忽略；adapter 分类定向测试通过。当前源码 `cargo test --workspace --offline -q` 退出 0：161 组、968 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-cve-input-20260928.log`，SHA-256 `87716b999b0a9a171c5d04dc76ab76176911b1bcbad0d293752c5a7b0cd17b17`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 与插件差异空白检查退出 0。未安装或调用 pip-audit，锁图、传递依赖、漏洞数据库身份与时效、真实 advisory、稳定 CVE 修复任务及正式门禁均未验收；5.10、7.2 与总体计划继续未完成。

## 2026-09-28 Python 标准锁与专用锁的原生入口边界

依据 [pip-audit 官方项目模式](https://github.com/pypa/pip-audit/blob/main/README.md?plain=1)及 [PyPA pylock 文件名规范](https://packaging.python.org/en/latest/specifications/pylock-toml/)，新增对 `pylock.toml` 和单段命名 `pylock.ci.toml` 的只读识别；它们仍标为标准锁模型未解析。`uv.lock`/`poetry.lock` 保留独立状态及需选原生工具或显式导出的动作；同根并存多锁时返回选择歧义，不默认让 pip-audit `--locked` 消费专用锁。公开 `detect` 真实文件样本先因标准锁未识别而 RED，实施后单标准锁、命名标准锁、多锁和仅 uv 锁四阶段回归通过。

`detect_cli` 28 项及 `check_all_partial_contract` 17 项通过/3 条件忽略。变更后 `cargo test --workspace --offline -q` 退出 0：161 组、969 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-pylock-20260928.log`，SHA-256 `598ccc575996826a30917de38b9f308a975ce5abdaf5bd8eeb46c970c19ecf03`。全目标 Clippy `-D warnings`、格式、OpenSpec strict 和插件差异空白检查退出 0。此轮没有调用 pip-audit，PEP 751 内容/环境、完整依赖图、真实 advisory 和漏洞数据库时效仍未核验；5.10/7.2 不勾选。

## 2026-09-28 pip-audit 项目锁命令计划与 JSON 协议观察

对照 [pip-audit 当前 JSON formatter 源码](https://github.com/pypa/pip-audit/blob/main/pip_audit/_format/json.py)与 [官方 CLI/退出码说明](https://github.com/pypa/pip-audit/blob/main/README.md?plain=1)，相邻 Rust adapter 新增标准锁项目模式的字面参数计划及 2.x JSON 保守解析。命令固定 strict、JSON、别名、关闭描述与进度、项目外缓存，不含修复或忽略参数；相对路径及项目内缓存拒绝。解析器只接当前对象结构，递归拒绝重复字段；跳过依赖、意外 fixes、重复组件、版本或退出矛盾和不符命令形状的原始描述都保持未完成。有效原生 advisory、组件解析版本及 CVE 别名仅为观察，空 JSON 仍固定 `advisory_coverage=not_evaluated`。

测试先因缺 `parse_pip_audit_json` 编译失败，解析实施后 4 项通过；再因缺 `PipAuditCommand` 编译失败，命令计划实施后 6 项全部通过。最终全工作区 `cargo test --workspace --offline -q` 退出 0：162 组、975 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-pip-audit-protocol-20260928.log`，SHA-256 `927b942584ebcb6a4a37b9dacaea6d8ca70c90186ad84ffff9cc13562398020f`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 与插件差异空白检查退出 0。测试 JSON 按上游源码构造；当前机器未安装/调用 pip-audit，本阶段没有真实原生输出、同轮锁身份、漏洞库时效、CLI/任务/门禁证据；7.2 和总体计划均不勾选。

## 2026-09-28 Python 标准锁局部 CVE 入口与归属门槛

公开 `cve python` 先因被旧 npm 分派接管而两项 RED。现使用显式工具/版本、共同截止时间和受控进程，在独占私有目录复放项目 pyproject 与唯一标准 pylock；工具版本、原清单/锁、私有副本与工具字节在执行前后核对。human/JSON 提供局部 advisory、缺锁及输入变化反馈，始终退出 3、`not_evaluated`、`coverage_proven=false`。本机模拟原生可执行文件测试证明：原生漏洞可见，原生零项不放行，私有锁改动使结果无效且原项目不变。macOS `/var` 到 `/private/var` 的祖先路径规范化曾使首次正例误判工具不可用；现拒绝工具自身符号链接，同时允许祖先目录规范化，目标测试通过。

复核又发现原生报告的组件若不在锁中仍会显示为项目局部 finding；缺包反例先 RED。现在只抽取 PEP 751 锁中的显式包名/版本，与原生报告整组解析组件作规范化精确对照；缺包、错版本、无版本源码包、损坏锁均不生成项目 finding。五项公开 CLI、七项 adapter 协议/绑定测试通过。试图构造非 UTF-8 文件名作 CLI 反例时，本机 APFS 在建文件阶段返回 `Illegal byte sequence`；该夹具移除，代码对不可解码目录项保持未完成，但没有声称此边界经真实文件系统验收。

独立 Draft 2020-12 校验通过原生零项与缺锁两份当前 CLI 报告，并拒绝 `coverage_proven=true`、`delivery_decision=allow`、已观察却 `native_report_valid=false` 三个伪授权变体；Python 只用于验收，不在 Rust 产品执行路径。最终当前源码 `cargo test --workspace --offline -q` 退出 0：163 组、981 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-cve-lock-binding-20260928.log`，SHA-256 `b9740ce886402146cd68a9ac30203d01dd580c7ff62731d01484f4bff7325b12`。全目标 Clippy `-D warnings`、Rust 格式、OpenSpec strict 与插件差异空白检查退出 0。模拟程序不是 pip-audit 本体；PEP 751 环境/依赖组及文件哈希、真实漏洞库身份与时效、完整原生运行、稳定修复任务和 check all/宿主门禁仍缺，7.2 与总体计划不勾选。

## 2026-09-28 Python 条件锁的错误归属防护

依据 [PyPA pylock 规范](https://packaging.python.org/en/latest/specifications/pylock-toml/)，`environments`、`requires-python`、extras、依赖组、default-groups 和包级 marker 会改变实际选用的包。原解析器把带环境条件的 `[[packages]]` 当成同一组显式包身份；先写的反例对此返回 `Ok`，RED 已复现。现在没有目标环境和组选择上下文时，Rust adapter 返回 `python_lock_selection_unresolved`；已配置工具时 `cve python` 与 `check all` 仍调用原生审计，公开版本、退出码和待归属 advisory 数量，但保留退出 3、零项目 finding 和具体核对动作。显式空 extras/组仍可用于局部观察。已初始化项目的实际 CLI 扫描仍创建一张稳定的 Python CVE 完整性任务，故该不确定性不会因无法归属而从修复工作台消失。

适配器 8 项协议测试和 Python CVE CLI 10 项测试通过；独立 Draft 2020-12 对实际条件锁报告验证通过（退出 3、零 finding、无 schema 错误）。全工作区 `cargo test --workspace --offline -q` 退出 0：163 组、987 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-lock-selection-20260928.log`，SHA-256 `0668b596522484e7a12455cc760323120830a00e73f955e556a64f2ef66ac1b4`。全目标 Clippy `-D warnings`、Rust fmt、OpenSpec strict 和插件 `git diff --check` 退出 0。模拟工具与静态格式核对不证明真实 pip-audit、环境选择、漏洞库及时效；7.2 与总体计划保持未完成。

后续检查发现首次条件锁保护把原生工具也提前跳过，不符合已配置检查器仍应反馈执行结果的设计。新 CLI 反例先显示 `native_version=null`（RED）；修正后同一模拟原生程序实际返回版本 `2.10.0`、退出 `1` 和一条待归属 advisory，公开结果仅反馈待归属数量、保留零项目 finding/退出 3，并自动同步同一稳定 CVE 完整性任务。真实 `cve python`、`check all` 和工作台报告的三份 JSON 均通过独立 Draft 2020-12 校验；脚本首次缺本地 schema registry 的错误已在验收脚本中修正，不属于产品。最终 `cargo test --workspace --offline -q` 退出 0：163 组、987 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-conditional-native-20260928.log`，SHA-256 `676bc207d7b9eb4e79e0045fc1ebc903ab475a9436b79dc04291182c94605ac7`。全目标 Clippy `-D warnings`、fmt、OpenSpec strict 和插件差异空白检查退出 0。未运行真实 pip-audit，环境/组精确选择、漏洞库身份与时效、全量义务及可信门禁仍缺，7.2 和总目标保持未完成。

## 2026-09-28 Rust CVE 原生异常后的部分发现

延续 F05、5.5 和 7.1。受控原生 `cargo-audit` 先输出与当前 `Cargo.lock` 匹配的完整 advisory JSON，再以异常码 2 退出；旧 CLI 把该有效 finding 丢弃，目标集成测试先 RED。修正后从完整报告独立解析并核对锁、清单及工具字节，公开一条待核验 RUSTSEC finding，`local_scan_complete=false`、`cargo_audit_execution_incomplete`、退出 3、交付 `not_evaluated`。保存的本地报告保留该发现，已初始化工作区同步唯一稳定 CVE 完整性任务；部分证据不升级为已批准漏洞或放行。截断 JSON/异常码 2 的负例仍为零 finding。独立 Draft 2020-12 核验实际局部与工作台 JSON，两份 schema 均通过；详见相邻 `codeguard-cli/tests/acceptance/rust-cve-partial-native.md`。

首轮全量回归在测试夹具建临时目录时因并发重名失败（`File exists`），未运行到产品断言。夹具增加进程内原子序号后，Rust CVE 测试文件 2 项普通测试通过、1 项显式真实工具测试默认忽略；最终 `cargo test --workspace --offline -q` 退出 0：163 组、988 通过、0 失败、101 条件忽略。日志 `/tmp/codeguard-rust-cve-f05-full-20260928.log`，SHA-256 `74b54089afe874b71cf1551f9453d13d5bf76b15dcf8de3ba2f6182183b3412f`。全目标 Clippy `-D warnings` 退出 0，日志 `/tmp/codeguard-rust-cve-f05-clippy-20260928.log`，SHA-256 `417b2ef0e9e174870bcbecb513216af0b5b02ef5e7c4e7271bc740d04b6c55b7`；Rust fmt、OpenSpec strict 和插件差异空白检查退出 0。原生程序为受控模拟器；真实 `cargo-audit` 崩溃、超时后部分输出、其它适配器及通用 F01–F10/F17 矩阵未验收，5.5/7.1 与总体计划均不勾选。

## 2026-09-28 Rust CVE 完整报告后超时的部分发现

延续 F05。模拟原生程序先输出完整且与本轮 `Cargo.lock` 匹配的 advisory，然后保持运行到超时；旧入口直接返回空 finding，目标测试先 RED。现对已捕获 stdout 做严格 JSON 与锁文件绑定，且复核工具、清单、锁字节；保留 advisory，但原生超时原因 `request_deadline_exceeded`、`local_scan_complete=false`、退出 3 和 `not_evaluated` 不变。已初始化工作区保存包含该部分 finding 的本地报告并同步稳定完整性任务，不能因此关闭漏洞义务或认定数据库时效。200ms 初始夹具在并行负载下无法稳定证明“报告已输出”，改为报告输出后停留 5s、2s 超时的明确顺序。独立 Draft 2020-12 对实际公开报告及保存的工作台报告均通过；首次验收脚本缺 URN 本地引用注册，修正脚本后两份 schema 零错误。详见相邻 `codeguard-cli/tests/acceptance/rust-cve-partial-native.md`。

最终 `cargo test --workspace --offline -q` 退出 0：163 组、988 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-rust-cve-f05-timeout-full-20260928.log`，SHA-256 `08e75244e07486cf28879a5c2d2b40e39834bddb314e5939cc3815dc3db3fbd4`。全目标 Clippy `-D warnings` 退出 0，日志 `/tmp/codeguard-rust-cve-f05-timeout-clippy-20260928.log`，SHA-256 `06deecc3c68c7e0b91ffbd05c208056b55458616edaf89af53d7e94c7a765e53`；fmt、OpenSpec strict 和插件差异空白检查退出 0。当前仍为模拟原生进程；实际 cargo-audit 卡死、输出超限/坏报告、其它语言适配器及通用 conformance 矩阵未完成，5.5/7.1 与总体计划保持未勾选。

## 2026-09-28 Rust CVE 输出超限的发现与故障分类

延续 F05。受控原生程序先向 stdout 输出完整、与本轮锁绑定的 advisory JSON，再向 stderr 写入超过共同 16 MiB 配额的数据；原 CLI 虽保留 finding，却把输出上限折叠为通用执行未完成，具体原因断言先 RED。现在明确反馈 `cargo_audit_output_limit`，仍为退出 3、`local_scan_complete=false`、`not_evaluated`，保留局部 advisory 并同步稳定 CVE 完整性任务。对照程序只输出残缺 stdout JSON 后触发同一上限，零 finding；没有从 JSON 前缀推断漏洞。独立 Draft 2020-12 对正反两组实际公开报告与各自保存的工作台报告均为零 schema 错误，见相邻 `codeguard-cli/tests/acceptance/rust-cve-partial-native.md`。

最终 `cargo test --workspace --offline -q` 退出 0：163 组、988 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-rust-cve-f05-output-limit-full-20260928.log`，SHA-256 `6e84ccc6450917fdece4ace379430543b8d72c9cc941821be5f59fad96eaa340`。全目标 Clippy `-D warnings` 退出 0，日志 `/tmp/codeguard-rust-cve-f05-output-limit-clippy-20260928.log`，SHA-256 `598bb85a445f943398014aad58e8f987aef829bd392bac6f17fbaa7339d267d3`；Rust fmt、OpenSpec strict 与插件差异空白检查退出 0。此处原生程序为受控模拟器，验证的是完整 stdout 报告后其它输出超限；cargo-audit 单体 JSON 自身截断不可据前缀恢复，真实工具故障、其它适配器和通用 F01–F10/F17 矩阵仍缺，5.5/7.1 与总体计划不勾选。

## 2026-09-28 Python CVE 原生故障后的部分发现

延续 F05、5.5 与 7.2。受控 `pip-audit` 先返回已独立核验的 2.10.0 版本，再输出与本轮 PEP 751 唯一锁整组组件匹配的 Flask advisory，最后异常码 2 退出；旧 CLI 丢弃 finding，目标测试先 RED。修正后严格解析完整 JSON，复核项目原清单/锁、私有副本与工具字节，并用既有锁归属比较保留局部 advisory。`native_report_valid=true` 只表示报告内容可核对；真实退出码 2、`pip_audit_execution_incomplete`、`local_scan_complete=false`、退出 3 和 `not_evaluated` 保留。工作台仍只生成稳定的 Python CVE 完整性任务，不将部分 advisory 认定为获批准的项目漏洞。残缺 JSON 或原生包不在锁中均保持零 finding。继续用同一目标测试验证完整报告后超时与其它输出超限：分别保留 `request_deadline_exceeded` 和 `pip_audit_output_limit`，无原生整数退出码，部分 finding 不放行；残缺 JSON 后超限仍零 finding。普通 Python CVE CLI 文件 11 项测试通过。

独立 Draft 2020-12 对异常退出、超时、输出超限、残缺报告四组实际公开报告及各自保存的工作台报告验证通过，finding 数依次为 1/1/1/0，四组均退出 3、未完成、零 schema 错误。第一次复跑时仓库默认 `target/` 在编译过程中消失，链接器报依赖 `.rlib` 缺失；核对时目录已不存在，磁盘尚余 37 GiB，未把此记作产品测试失败，也未重置源码。改用独立 `CARGO_TARGET_DIR=/tmp/codeguard-python-f05-target-20260928` 后目标和全量测试通过。最终 `cargo test --workspace --offline -q`：163 组、989 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-f05-full-20260928.log`，SHA-256 `eefa91a2e73154944bdd3881c18fbd9c8ec62e48bdf1d06ee3ec6b19ed2d820b`。全目标 Clippy `-D warnings` 退出 0，日志 `/tmp/codeguard-python-f05-clippy-20260928.log`，SHA-256 `465c3e723d436ef227a04a77e3404e82b7aad5eec3c1ff9080a6f3f7d0447e7f`；fmt、OpenSpec strict 和插件差异空白检查退出 0。验收详见相邻 `codeguard-cli/tests/acceptance/python-cve-partial-native.md`。真实 pip-audit 故障、PEP 751 条件环境/依赖组、数据库来源及时效、其它语言适配器和通用 F01–F10/F17 矩阵仍未证明，5.5/7.2 与总体计划保持未完成。

## 2026-09-28 `check all` 对 Python CVE 部分报告的状态修正

延续 2.3 和 7.2。局部报告在异常退出后 `native_report_valid=true` 是完整 JSON 与锁身份可核对，不等于原生命令按退出契约完成；旧总入口据此把执行节点和类别候选误标为已观察。新增已初始化工作区的 `check all` 反例，目标断言 `native_incomplete` 先 RED。修正后仅 `native_advisories_observed_unverified` 和 `native_zero_advisories_unverified` 这两种正常退出结果使 Python CVE 执行节点成功；异常码 2、输出超限保留本轮 finding，同时任务节点和类别候选为 `native_incomplete`，未解决条件含 `python_cve_task_incomplete`，工作台继续同步稳定完整性任务。11 项 Python CVE 目标文件测试通过。独立 Draft 2020-12 对异常退出及输出超限两份实际 `check all` JSON 验证通过：均退出 3、各一条 advisory、执行/候选未完成、零 schema 错误。详见相邻 `codeguard-cli/tests/acceptance/python-cve-partial-native.md`。

最终在独立构建目录中 `cargo test --workspace --offline -q` 退出 0：163 组、989 通过、0 失败、101 条件忽略；日志 `/tmp/codeguard-python-f05-check-all-full-20260928.log`，SHA-256 `be71ff67c3344e6a483c2c0d7c014a4bf2ce5d0d7cd00b12781d9747c43ac30a`。全目标 Clippy `-D warnings` 退出 0，日志 `/tmp/codeguard-python-f05-check-all-clippy-20260928.log`，SHA-256 `d0492b6f8a4a276e8cbe4f385278c6e748acbd88b449f60d9e35ee9707c6b123`；fmt、OpenSpec strict 和插件差异空白检查退出 0。只覆盖 Python CVE 局部到总入口的这一状态链；完整跨语言 findings/completion 聚合、真实 pip-audit/漏洞库、受批准策略与宿主门禁仍缺，2.3/7.2 与总体计划不勾选。

## 2026-09-28 npm CVE 异常退出后的证据与执行状态

受控 Node/npm 11.16.0 程序在输出与当前锁节点匹配的完整一条 advisory 后以 2 退出；旧 `cve typescript` 报告零 finding，目标断言先失败。修正后公开反馈保留一条脱敏局部发现及 `npm_audit_execution_incomplete`，工作台维持同一稳定 CVE 完整性任务。`check all` 原生结果仍显示该发现，但执行节点为 `native_incomplete`。截断 JSON 后以 2 退出的对照仍零 finding。局部报告可核对不等于原生命令完成，退出 3、覆盖和交付未评估不变。

该阶段 `npm_audit_cli` 和 `check_all_npm` 目标测试、`cargo test --workspace --offline -q`、`cargo clippy --workspace --all-targets --offline -- -D warnings`、`cargo fmt --all --check` 及 OpenSpec strict 均退出 0。此阶段只覆盖异常退出；超时与输出上限的后续进展见下段。受控替身未证明真实 npm 故障、数据库新鲜度与全部 F05 矩阵，2.3/5.5/7.3 和完整目标保持未完成。详见相邻 `codeguard-cli/tests/acceptance/npm-partial-native.md`。

后续补齐完整报告后超时和其它输出超限两种模拟故障：公开反馈均保留一条局部 advisory，原因分别为 `deadline` 与 `npm_audit_output_limit`，交付未评估；截断 JSON 的超限对照零 finding，工具文件变化也使结果失效。输出超限的实际 `check all` 反馈包含 finding，但执行节点 `native_incomplete`。已初始化工作区在超时后不给截止时间外的持久化成功，输出超限仍同步稳定任务。独立 Draft 2020-12 对异常退出的实际反馈、工作台和完整检查三个 JSON 验证通过。首次全量败于新增 npm 测试替身过早退出，第二次败于既有 Rust CVE 测试替身的同类时序；两者调整后目标回归及最终全工作区退出 0：163 组、989 通过、0 失败、101 条件忽略，日志 `/tmp/codeguard-npm-f05-full-final-20260928.log`，SHA-256 `a008b5049c919c7cc9fa43d968e0be936e43d5631d9c6f5acd2c35c080eaa5f5`。全目标 Clippy `-D warnings`、fmt 退出 0。真实 npm 故障、取消、全部原生优先级及跨语言 F05 矩阵仍缺，不勾选 2.3/5.5/7.3。
