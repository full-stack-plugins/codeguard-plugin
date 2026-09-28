# Tasks：统一 Rust Codeguard CLI

本文件跟踪**进行中的实现**；已完成的工程基线任务有独立代码与验收证据，其余项目保持未完成。规格事实源为本 change 的 `specs/`；设计展开在 [design](design.md)。每项完成需要关联代码、测试和实际证据，不以存在文件、编译或模拟报告替代。

当前范围与逐项依赖/验收导航见 [实施覆盖索引](implementation-coverage.md)：每个Requirement、命令和语言都有任务定位，每个task都有规格依据。阶段/汇总任务完成须满足其关联明细；不得重复创建第二份任务状态。

实施按红→绿→相关回归推进；每个批次先重新检查 Git/AGENTS/现有完成度。仓库创建、分支切换、工具安装、规则权威变更和发布按当时用户授权执行，不从本任务清单推断已经授权这些动作。不得修改本插件外部受管技能副本。

## 1. S01 契约与工程基线

依赖：无。覆盖：unified-cli-contract、native-tool-adapters、binary-distribution。

- [ ] 1.1 核对最新旧源码与 57 项清单差异，建立“保留正确行为 / 明确纠偏 / legacy 兼容”表；验收：每条差异关联 spec 和 fixture。
- [x] 1.2 在获准位置建立用户指定 `codeguard-cli/` 四 crate workspace，锁定 MSRV/依赖/Cargo.lock；验收：可运行 `codeguard --version`，无空适配器充数。证据：相邻 `codeguard-cli/tests/acceptance/engineering-baseline.md`；真实适配器能力仍为 gap。
- [x] 1.3 建立 crate 依赖方向检查；验收：core→runtime、adapters→runtime、宿主 SDK 入 core 等反例均被拒绝。证据：相邻 `codeguard-cli/crates/codeguard-cli/tests/crate_boundaries.rs` 与工程基线验收记录；检查器已改用 Rust 消费 Cargo metadata。
- [x] 1.4 创建真实语料登记、脱敏和 oracle 格式，收录当前误判/假通过最小样本；验收：源码/工具/规则身份可复现，争议样本独立标记。证据：相邻 `codeguard-cli/tests/acceptance/corpus-baseline.md`；Rust 语料验证与真实 Ruff/Maven 回放已替代新工程的 Python 辅助脚本，历史未复现样本不计入已接受 oracle。
- [x] 1.5 定义 language×category×platform 能力 schema 和生成文档入口；验收：54 stable/3 planned 全覆盖，formatter-only 不能伪装 lint。证据：相邻 `codeguard-cli/tests/acceptance/capability-inventory.md`；当前全部单元诚实标记为 gap。
- [ ] 1.6 固化应用服务与ports边界：观察/政策/计划/检查/交付/存储/租约/修复及schema所有权；交付：真实领域契约和依赖测试；验收：CLI/MCP共用服务、core无基础设施依赖，新CLI与验收工具为Rust实现，P3C/Maven等通过Rust runtime调用其原生命令，不以空stub计功能完成。

## 2. S02 CLI、结果模型与门禁

依赖：S01。覆盖：unified-cli-contract、verdict-integrity。

- [ ] 2.1 实现统一命令语法、canonical ID/别名及只读 plan；验收：错参无进程副作用、plan 不运行构建/扫描。
  进行中：相邻 Rust CLI 新增 C06 的只读 `plan_preview` 0.1，先校验类别/canonical 语言 ID，再静态观察配置；缺可信策略和工具锁时只列候选、不给执行 argv/正式义务、退出 3。目标集成测试验证伪造 Ruff 工具未运行及项目无新增文件，见 `codeguard-cli/tests/acceptance/plan-readonly-preview.md`。别名、可信政策、全量义务/DAG 和正式 CheckPlan 仍缺，不勾选。
- [x] 2.2 定义请求/计划/报告/工具锁 JSON schemas 与兼容版本策略，提供完整正反例；验收：未知 major/非法枚举不按 PASS 消费，运行报告区分项目检查器的 `configured/missing/invalid/unknown` 与本次原生结果。证据：相邻 `codeguard-cli/schemas/run-report.schema.json` 的 1.2 协议、`crates/codeguard-cli/src/run_report.rs` 与 `tests/run_report_contract.rs` 的正反例；1.0 历史报告仍可读取，1.1 起区分配置和运行，1.2 起 finding 要求定位且检查器状态按构建根区分。此项只完成协议，不代表项目配置探测或宿主对话接线已完成。
  公共协议输入加固：Rust 检查请求和 RunReport 现从原始字节递归拒绝重复 JSON 键，并复用 16 MiB 输入上限；`delivery_gate`/`decision` 和嵌套 `jobs` 重复键反例先失败后通过。此校验只保证结构消费，不验证报告来源或正式门禁。
- [ ] 2.3 实现 findings 与 completion 双维聚合及新退出码；验收：混合违规/缺工具返回 3 并保留全部发现，取消/内部异常优先级正确。
  Python CVE 部分结果增量：`check all` 对完整但原生异常退出或输出超限的 pip-audit 报告，保留已归属 advisory；执行节点与类别候选均为 `native_incomplete`，未解决条件保留 `python_cve_task_incomplete`。旧汇总层仅按 `native_report_valid=true` 将部分报告误记成功，反例先 RED 后修正；两份实际总报告通过 schema。完整 findings/completion 跨语言、取消与内部异常优先级仍缺，2.3 不勾选，见相邻 `codeguard-cli/tests/acceptance/python-cve-partial-native.md`。
  内部故障反馈进展：`check all/java` 的任务图若返回内部故障，现以退出 4 输出结构化 `check_aborted`，保留兄弟任务已取得的原生局部结果、发现及每项任务状态；交付为 incomplete/not_evaluated。同轮同时有取消时优先退出 130，仍保留故障任务 ID 与原生发现。它不是完整 RunReport，调度器自身失败和跨入口聚合尚未完成，2.3 仍不勾选。
  取消优先级进展：`check all/java` 的 `check_feedback` 升至 0.16，实际 SIGINT 并行回归证明一项 Ruff 原生任务取消后退出 130，同时保留另一项已完成的 Rust Clippy finding；状态明确为 cancelled，交付仍 incomplete/not_evaluated。`lint python` 对话反馈也升至 0.11，真实 SIGINT 原生探测退出 130，保留局部反馈与子孙清理证据。其它入口、调度器故障与完整义务聚合仍缺，2.3 不勾选。
  接线进展：公开 `check all` 可从项目发现列出已观察语言的六类候选，正式必需义务保持 unresolved/null；Python 源文件复用原生 Ruff lint、报告同步和 next，Rust 源文件有显式 Cargo 工具时运行局部原生 Clippy。混合项目中 Python 缺工具不吞掉 Rust 诊断，仍返回 3/incomplete。当前只是局部检查反馈，不是完整 RunReport 或全部检查族结果；见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`，2.3 不勾选。
  Java 接线进展：`check all` 0.7 增加独立 `java.p3c` 节点，按最近 Maven 构建根识别已配置的 P3C，只读项目配置与隔离原生单文件探针分别反馈。缺配置不启动 Maven；原生诊断含规则/位置进入 JSON/human。隔离探针提供十个 P3C 规则集，但项目检查只选择 POM 中可静态确认的子集；POM 无法对齐或变化时保留配置阻塞。Java lint 候选即使局部探针完成也保持 `native_incomplete/p3c_declared_rulesets_unverified_coverage`，不伪称完整 lint 或交付通过。真实 Maven/JDK 21 离线用例与未配置、嵌套构建根反例见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。完整义务聚合仍缺，2.3 不勾选。
  局部语言选择进展：公开 `check java` 复用同一 P3C 节点与任务同步，混合项目只调度 Java、只列 Java 候选，`check_feedback` 0.8 固定 `selection=java`/`delivery_decision=not_evaluated`/退出 3；真实 Maven 样本仅在 POM 同时声明 naming/comment 时返回命名和作者注释两条规则。完整义务集合、其它 Java 检查器及交付聚合仍缺，2.3 不勾选。
- [ ] 2.4 实现义务账本和交付决策；验收：类别命令、空目标、缺 adapter、未执行任务均不能签发项目 allow。
  `check all` 当前固定不完整，显式列出未接入的候选类别；只有受保护策略才可确定必需义务，候选目录不自动升级为账本，原 2.4 验收仍未完成。
  进行中：相邻 Rust 领域门禁现将独立冻结的应有义务 ID 与实际计划逐项对照；丢失、重复或额外 ID 使交付 incomplete，`conclude_check` 的请求退出 3，已发现问题仍保留。见 `codeguard-cli/tests/acceptance/frozen-obligation-ledger.md`。可信策略/完整发现如何生成和绑定冻结清单、正式 plan/check 的接线尚未实现，不勾选。
  追加 finding 身份冲突校验：即便义务 ID 和目标覆盖均完整，两条原生发现共用一个 finding ID 也使受影响账本无效，防止门禁按集合去重后误签例外；CLI 完整接线仍缺，2.4 不勾选。
- [ ] 2.5 实现统一 human/JSON/SARIF 渲染与私有证据引用；验收：结构化 stdout 纯净、SARIF 未完成可见、公开报告不泄露凭据。
  局部进展：相邻 Rust 工程已有结构有效 RunReport 的纯 SARIF 2.1.0 投影；未完成零发现仍显示失败通知，白名单 finding 保留且不自动 suppression，原生消息与路径留在私有证据。正式 CLI 格式入口、来源核验及全格式一致性仍缺，2.5 不勾选。
  命令接入进展：实际 `check all/java --format sarif` 已从同轮局部反馈投影已观察的原生 finding；无发现、内部故障及取消仍用失败执行通知表达，原生诊断文本和路径不公开。它尚非完整 RunReport，`lint`/其它检查类命令、`--output`、可信来源和全格式一致性仍缺，2.5 保持未完成。
- [x] 2.6 建立具名 legacy-v1 协议映射表和参数测试；验收：逐旧入口验证数字/混合优先级，不把兼容通过当新认证。证据：[逐入口映射表](../../../docs/rust-cli/legacy-v1-protocol-map.zh-CN.md) 与相邻 Rust 工程 `tests/acceptance/legacy-v1-protocol-map.md`；CLI 数字及 check/CVE/Dockerfile 混合优先级由 Rust 参数契约核验，MCP 无逐调用进程码、五类 Hook 宿主语义逐项登记，所有兼容投影固定 `not_evaluated`。旧插件 164 项相关回归及 7 项 MCP 实测通过。此项只完成协议映射，不声称 C35 兼容运行时、宿主接线或新版交付认证完成。
- [ ] 2.7 实现 C01–C36 命令注册、help/版本元数据、操作结果类型与参数支持矩阵；验收：文档/help/CLI/MCP映射无漂移，查询/计划/安装成功不能变为质量allow。
  进行中：相邻 `codeguard-cli` 已提供 C02 `--version --format human|json`，包含 CLI/目标平台/检查协议 major，并把尚无发布证明的构建身份、规则包兼容范围明确标为未验证；见 `schemas/version-report.schema.json` 和 `crates/codeguard-cli/tests/version_cli.rs`。其余命令注册、帮助生成、MCP 映射与版本化支持矩阵仍缺，暂不勾选。
- [ ] 2.8 固化每类命令timeout/jobs默认值、来源与总deadline；验收：子进程/重试不重置预算，非法预算执行前拒绝，清理未完成真实可见。
  进行中：相邻 Rust `check all` 局部入口现接受 1ms–24h 的 `--timeout`，默认 30m；非法预算在原生启动前返回 2，Ruff 版本探测与逐文件检查继承同一截止时间，超时给出 `request_deadline_exceeded` 而非本地完整。见 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。发现、持久化/清理硬预算、其它命令默认值来源、跨命令 jobs、重试和跨平台验收仍缺，不勾选。
  后续进展：`lint python` CLI 复用相同检查类预算解析与 30m 默认值，从解析后建立截止时间并传入原生 Ruff 链；无效预算和原生探测超时有 CLI 回归。见相邻 `codeguard-cli/tests/acceptance/lint-python-auto-brief.md`。任务复检、其它命令、来源报告及完整 I/O 预算仍待完成。
  复检进展：`task verify` 局部 Ruff 入口现复用同一预算解析和截止时间；非法预算在租约前拒绝，原生探测超时后复检观察为 incomplete、不写新事件、自有租约释放、任务仍 open。见相邻 `codeguard-cli/tests/acceptance/task-verify-native-observation.md`。租约和持久 I/O 的硬截止时间、来源报告、清理状态、jobs/重试及其它命令仍未完成。
  来源进展：三个已接入 CLI 反馈均已版本升级，公开 `execution_budget` 明确记录最终毫秒值、来源及 `native_execution_only` 的实际执行边界；本地 0.8 原始扫描报告不因对话协议升级而改写。见相邻 `codeguard-cli/tests/acceptance/{check-all-partial-native,lint-python-auto-brief,task-verify-native-observation}.md`。全部 I/O 截止时间与清理状态仍缺，2.8 不勾选。
  环境优先级进展：三个局部入口现登记 `CODEGUARD_TIMEOUT`，反馈来源枚举新增 `registered_environment`；非法环境值在原生执行/租约前返回 2，显式 CLI 可覆盖无效环境值。`CODEGUARD_JOBS` 目前只接 `check all`；完整 I/O 截止时间及清理状态仍缺。
  项目默认进展：可选 `codeguard/runtime.json` 1.0 仅允许 `timeout`，三个局部入口按 CLI > 登记环境 > 项目默认 > 内置默认选择并报告 `project_default`；坏协议、额外质量排除字段、超限/链接文件及非法预算在原生执行/租约前拒绝。`check all` 另支持 1.1 可选 `jobs`、`--jobs`、`CODEGUARD_JOBS` 与 1–64 边界，并向 DAG 传入实际并发上限；反馈区分上限、原生节点数与启动数。混合 Python/Rust 项目现有两个独立节点，旧入口尚未扩展 jobs，实际并发及跨进程资源互斥仍需验收。见相邻 `codeguard-cli/schemas/runtime-options{,-1.1}.schema.json` 和 `tests/acceptance/{check-all-partial-native,lint-python-auto-brief,task-verify-native-observation}.md`。全部 I/O 截止时间及清理状态仍缺，2.8 不勾选。
- [ ] 2.9 实现报告原子导出、可逆路径编码、多位置/包定位及来源保留；验收：output不可写为3且原finding保留，未知major拒绝，不按有损路径或相似文案跨工具抵消发现。
  局部进展：`check all/java` 的 JSON/SARIF 已支持 `--output PATH` 同目录暂存与原子写入；目标不可用时本轮报告仍在 stdout，已发现的原生问题不丢；已有非 CodeGuard 文件不可覆盖。human/其它检查类命令、可逆路径与多位置/包身份、完整 RunReport 导出及跨工具归并仍缺，2.9 不勾选。
  反馈补强：局部 JSON 0.18、故障报告 0.3 与局部 SARIF 现显式返回导出状态及受限失败原因码，使只消费结构化 stdout 的智能体也能看到保存失败；成功文件和 stdout 同报 `saved`。完整 2.9 仍未完成。
- [ ] 2.10 升级 RunReport 与所有公开消费者的白名单处置协议；验收：新版本明确 raw/active/whitelisted finding、批准引用和 allow_with_exceptions，旧消费者拒绝未知决策而非降级为普通 allow，human/JSON/SARIF/MCP/Hook 语义一致。
  进行中：相邻 `codeguard-cli` 已提供 RunReport 1.3 schema/严格消费和 conversation feedback 0.2 JSON/human，初期白名单协议与旧报告契约测试见 `tests/acceptance/run-report-allowlist-protocol.md`。后续已有保守 SARIF 投影，仍无真实报告生产、可信来源、MCP/Hook 消费者与端到端门禁，不勾选。
  协议身份接线：RunReport 1.4 要求每条 finding 的完整原生身份，并在误报处置中核对精确决策身份；规则、工具制品、检查器类别和主目标须与本轮报告一致，源码字节/指纹/适配器/rulepack、依赖图/advisory 变化拒绝处置。旧 1.3 schema 原件留存，未来未知版本拒绝；human/JSON/SARIF 继续明确来源及批准未核验，不能凭自写报告签发 allow。当前仅结构消费，真实原工具身份生成、可信来源、MCP/Hook 和正式门禁仍缺，2.10/4.8 不勾选。
  覆盖/字节复核增量：1.4 源码 finding 主目标必须同时属于本义务预期和实际覆盖集合；宿主可调用只读 `compare_claimed_source_hashes` 对其独立指定工作区内全部源码目标按真实字节比较 SHA-256，文件变化、缺失、链接或超预算均拒绝。该接口尚未由正式门禁调用，不能验证自称的原生结果或批准来源；2.10/4.8 不勾选。
  领域进展：`codeguard-core` 门禁现保留原始/已批准例外/活跃阻断三个集合；完整且唯一的例外形成 `allow_with_exceptions`，混合真实阻断为 deny、未完成与批准冲突为 incomplete，取消和内部故障不能留下交付 allow。同一批准 ID 跨 finding 复用被拒。仅是纯领域输入契约，受保护审批来源、可信时钟/策略、真实原生身份和公开消费者仍未接入，见相邻 `codeguard-cli/tests/acceptance/allowlist-delivery-domain.md`，2.10/4.8/12.12 仍不勾选。

## 3. S03 运行时、快照与缓存

依赖：S02。覆盖：execution-kernel、verdict-integrity。

- [x] 3.1 实现字面 argv/cwd/env/stdin 的受控进程执行；验收：空格/分号/命令替换字面值无额外执行，探测不消费 stdin。证据：相邻 `codeguard-cli/crates/codeguard-runtime/tests/process_contract.rs` 的 Unix 契约测试与 `codeguard-cli/crates/codeguard-cli/tests/ruff_probe_contract.rs` 的原生 Ruff 版本探测；Windows Job Object 与平台验收由 3.3/11.12 保持未完成。
- [ ] 3.2 实现并发流读取、总 deadline、输出预算和私有原子日志；验收：洪流/编码错误/日志 symlink 场景无假完整、无越界写。
  进行中：相邻 `codeguard-cli/crates/codeguard-runtime` 已覆盖 Unix 双流共享预算、短命令退出后才发现超限、直接子进程退出后读流跨过 deadline、超时部分输出和私有原子日志；日志目录逐级拒绝 symlink，Ruff 解析拒绝非 UTF-8 报告。Maven/Ruff 探测在身份和输入复核后再次检查同一截止时间。见 `codeguard-cli/tests/acceptance/runtime-stream-log-baseline.md`。持久化 I/O 的硬截止时间、Windows 对等实现和完整 CLI 门禁集成仍缺，暂不勾选。
  读流稳定性补强：子进程退出后的 stdout/stderr 排空改用原请求绝对期限，避免原固定 150ms 在并行负载下将已关闭短命令误判为 `ReadFailure`；到期仍为未完成。ESLint 取消/超时回归的伪工具保持扫描时间长于截止时间，但给准备阶段充分启动余量，避免把测试负载抖动误判为扫描行为失败。目标回归及全量证据见 verification；3.2 仍因持久化 I/O、Windows 和正式门禁缺口未完成。
- [ ] 3.3 实现 Unix 进程组与 Windows Job Object 的取消/终止/回收；验收：子孙进程、超时、Ctrl-C、排队取消有平台实测。
  Unix 局部进展：相邻 Rust runtime 新增 CLI SIGINT 原子取消桥接，原生执行循环在取消后终止并回收进程组；`process_contract` 通过超时/取消后子孙进程不得延迟写文件的真实副作用测试，`lint_python_cli` 从红测到绿测证明真实 Ctrl-C 返回 incomplete、`request_cancelled` 且无后台延迟写入。仅在当前 macOS Unix 环境验证；Windows Job Object、排队取消与其它宿主入口仍缺，故不勾选。
- [ ] 3.4 实现任务 DAG、资源锁及依赖失败传播；验收：独立任务继续、共享 build 目录互斥、失败依赖未完成可见。
  纯领域/运行时进展：相邻 Rust core 新增执行前校验的 `TaskGraph`，拒绝重复 ID、缺失/重复/自依赖、重复资源和依赖环；runtime 新增有界并发调度，按资源 ID 互斥，失败链逐层标记 `DependencyFailed`，独立任务继续，排队取消/超时不启动，回调 panic 不当成功。见 `codeguard-cli/tests/acceptance/task-dag-scheduler.md`。正式 CheckPlan/义务账本与 CLI 尚未接线，构建目录资源规范化和跨进程锁也未实现，故不勾选。
  CLI 局部接线：`check all` 将适用的 Python/Ruff 与 Rust/Cargo Clippy 节点送入调度器，共用取消标记和截止时间；公开 `check_feedback` 0.6 的 `execution_tasks` 把本地原生完成标为 `native_observed_unverified`，混合项目一个节点失败不丢另一个节点的诊断。真实并发、正式义务清单和构建目录资源规范化仍缺，见相邻 `codeguard-cli/tests/acceptance/check-all-partial-native.md`。
  Java 扩展：`check_feedback` 0.7 增加 `java.p3c` 独立节点，复用相同截止时间和取消标志，缺项目配置或工具前提仍保留文件级原因。原生 Maven 探针使用私有临时工作区；完整规则集、跨模块构建资源锁及工作区级义务仍缺，3.4 不勾选。
- [ ] 3.5 实现工作树/index/ref 快照与原始字节校验；验收：SHA-1/SHA-256、坏批响应、特殊文件、symlink/gitlink/LFS 均明确处理。进行中：相邻 Rust CLI 已按 NUL 协议读取真实 index、前后复核列表，并对有界普通 blob 独立核验 SHA-1/SHA-256 Git OID、记录脱敏字节摘要；symlink/gitlink/LFS、超预算和对象读取失败明确 unresolved，见 `codeguard-cli/tests/acceptance/git-index-safety-preview.md`。工作树/ref 快照、坏批响应注入测试、特殊类型完整语义及 Git 工具身份未完成。
- [ ] 3.6 实现 GIT_INDEX_FILE、初始提交、worktree、多 ref/non-HEAD/删除 ref push 输入；验收：真实临时 Git 仓检查准确且 index 不变。进行中：相邻 Rust 的真实 index 路径安全预览覆盖初始仓库、替代 `GIT_INDEX_FILE` 与默认 index 不变；worktree 和 pre-push 多 ref/删除 ref 尚未实现，不勾选。
- [ ] 3.7 实现执行前后内容身份复核和源码副作用检测；验收：并发编辑或检查器改源码导致 incomplete。
  进行中：相邻 Rust runtime 新增显式相对路径的有界 `SourceSnapshot`，拒绝静态可见的路径越界、重复、符号链接及预算超限；私有副本须写入新目录，运行后复核原件与副本字节。JDK Javadoc 单文件入口已使用此契约，真实 JDK 21 与链接/修改反例通过，见 `codeguard-cli/tests/acceptance/source-snapshot-boundary.md`。调用方源集完整性、并发目录替换的内核级隔离、其它 adapter 接线和项目级 Maven 副作用仍缺，3.7 不勾选。
  路径并发补强：Unix 读取和复核改为从固定根目录描述符逐级 `openat`/`O_NOFOLLOW`，目录在检查期间切换为范围外符号链接的真实并发反例只能返回原范围字节或错误。副本写入和整个原生进程仍无完整沙箱；源集完整性、其它 adapter 接线和项目级 Maven 副作用仍缺，3.7 不勾选。
  `check all/java` 局部范围复核：原生节点结束后再次静态发现，比较源码/清单集合、构建根、已观察清单/锁/检查器配置摘要及配置状态；新增源码或规则配置变化会加入 `project_scope_changed_during_check`，原诊断保留。截止时间已耗尽则报告范围复核未执行；自有 `codeguard/state` 记录不造成假变化。尚未逐字节冻结全部源码、捕获瞬时改回、实现完整内核隔离或受保护义务账本，3.7/2.4 不勾选。
  同路径内容复核增量：`check all/java` 在原生节点前对初次发现的源码集合建立有界 `SourceSnapshot`，节点后从固定根目录描述符复核原路径字节。同一路径内容变化加入 `project_source_changed_during_check`；文件数/单文件/总字节超限或安全读取失败显式标记快照或复核不可用，不产生 allow。静态配置文件若同时被归类为源码，其内容变化也可触发此项；仅写入 CodeGuard 自有记录不触发。快照非原子、无进程沙箱，改后又改回、末次复核之后的变化和未发现目标尚不能捕获，3.7/2.4 仍不勾选。
- [ ] 3.8 实现严格缓存及义务等价证明；验收：同 mtime/size 内容替换、规则/依赖/工具/库变化必失效，软缓存不可直接认证。
- [ ] 3.9 实现run/obligation/task/attempt关联轨迹与分阶段计时、缓存/终止原因；交付：脱敏结构化本地事件；验收：部分失败可追溯，公开轨迹不泄露原始argv/env，不默认上传遥测。
- [ ] 3.10 实现证据索引、私有权限、引用与保留策略及受管清理；验收：活动run/lease、被引用证据、用户源码和tracked历史不被清理，磁盘/权限/symlink失败不扩大删除或伪造完成。
- [ ] 3.11 实现离线与可信执行边界port及能力探测；验收：主动联网子进程被拒绝，无法保证时启动前incomplete；可信政策/签发身份不进入项目脚本执行域，真实平台证明由S11/S12补齐。

## 4. S04 规则与策略权威

依赖：S02。覆盖：rulepack-governance。

- [ ] 4.1 实现运行配置与批准质量策略的独立解析及 config explain；验收：CLI/env 无法弱化 required/threshold/exclude。
  进行中：相邻 Rust CLI 已有 `quality-policy-candidate` 1.0 严格解析，并在 `config validate/explain --policy-candidate` 只读显示必需检查、规则包/工具锁摘要、时效和精确内容绑定排除；重复、未知、自批和通配被拒。候选即使与本地工具锁字节匹配仍固定 `candidate_unverified`，不形成有效策略。运行参数与受保护批准策略的绑定及真实覆盖仍缺，见 `codeguard-cli/tests/acceptance/config-readonly-inspection.md`，4.1 不勾选。
- [ ] 4.2 实现旧 codeguard.json 显式迁移和原生 suppressions 差异解释；验收：未知/损坏字段不静默丢弃或按默认通过。
  追加进展：相邻 Rust CLI 的 `config validate/explain` 已只读识别旧 `extensions/exclude/gate_scope/java.commands`，拒绝未知/损坏字段、符号链接与坏工具锁；旧排除、delta 范围和命令均不自授策略权威，固定退出 3。尚未执行正式 schema 迁移或覆盖完整原生 suppressions，见 `codeguard-cli/tests/acceptance/config-readonly-inspection.md`。
  进行中：Ruff 0.16.8 局部扫描现以同轮原生 `--ignore-noqa` 对照记录源码注释抑制差额，原生结果未据此生成活动 finding 或质量通过；这尚不构成旧配置迁移、受批准 suppressions 差异解释或其它生态覆盖。见 `codeguard-cli/tests/acceptance/ruff-native-suppression-observation.md`。
- [ ] 4.3 实现 rulepack manifest、来源/许可、稳定规则 ID、摘要和兼容锁；验收：内容篡改/不兼容组合不能执行认证。
  进行中：相邻 Rust 工程新增仅用于 Ruff 0.16.8 F401/E501 的 `candidate_unapproved` 映射清单，严格解析来源、许可、精确版本、规则 ID 和字节摘要；完整本地报告记录已观察到的映射身份，同步时重算并拒绝篡改。它不设置原生规则覆盖，也不具备受保护批准，不能执行认证。见 `codeguard-cli/tests/acceptance/ruff-rulepack-observation.md`。
- [ ] 4.4 实现基线仅分类 new/existing；验收：未修改文件中的存量违规仍阻断，基线失败不消除 finding。
- [ ] 4.5 实现可信政策修订和例外输入校验；验收：agent 自写批准、无到期、过期、错内容或错范围凭据不生效，批准例外不显示普通 PASS。
  签名进展：Rust 已增加域分隔 Ed25519 原始载荷核验，绑定工作区、策略修订、受保护 Git 基线、序号、期限与快照字节；普通候选桥接还核对签名与快照内修订，再走精确字节/身份绑定。可信公钥、撤销、时间和最低序号仍须由宿主提供；未提供项目自批入口。签名四项及原快照十五项通过，见相邻 codeguard-cli/tests/acceptance/signed-approval-binding.md。宿主信任来源、完整签名修订链及真实门禁尚缺，4.5/4.8 不勾选。
- [ ] 4.6 保留点前缀默认策略及两项例外，生成汇总覆盖；验收：F18 全部成立，无未授权的新排除。进行中：相邻 Rust `detect` 0.3.0 已汇总普通发现的点前缀排除根、配置例外文件及未评估入库安全状态；`gate pre-commit` 路径安全预览能在真实 index 看到点前缀 `.env`，见 `codeguard-cli/tests/acceptance/{dot-prefix-scope-baseline,git-index-safety-preview}.md`。完整安全内容扫描与正式 Git 门禁未接线，不能勾选。
- [ ] 4.7 接入 rules list/config validate/explain 命令；验收：有效规则、原生suppression与批准来源可解释，静态验证不执行项目脚本，配置错误为未完成而非源码违规。
  追加进展：`config validate/explain` 0.1 只返回旧配置与工具锁的静态状态、未绑定的可信质量策略和无效白名单权威；不产生有效策略或质量门禁。`rules list`、规则/原生配置差异和批准来源解释仍缺，任务不勾选。
  2026-09-27入口进展：Rust rules list现复用静态发现及内置版本化Ruff候选映射，逐语言显示配置声明、来源/许可/摘要/兼容版本和六类目录缺口；Node生态显式映射到TypeScript，不靠语言前缀丢失ESLint配置。动态配置不执行、本地同名映射/自批不授权，报告0.1固定未完成且无门禁效果。新增schema及验收用例，结果见verification.md。完整有效规则、可信来源、suppression和批准例外仍缺，4.7不勾选。
- [ ] 4.8 实现精确误报白名单 schema、可信来源解析和 Rust 匹配器；验收：仅同一原生规则、目标/内容、工具/规则包/适配器及有效批准身份命中；通配、过期、冲突、自批和坏报告均不放行，原始 finding 保留。
  门禁碰撞反例：两个原生规则/义务共用 finding ID 时，旧纯领域门禁会把单条批准扩展到另一条；现将重复 ID 标为无效义务账本，白名单不匹配，原始阻断仍显示。可信批准接入、本轮原生身份和所有格式消费者仍缺，4.8 不勾选。
  原生身份加固：领域 finding 现可携本轮宿主冻结的完整身份，白名单处置必须同时与该独立身份匹配；缺字段的旧 finding、源码字节/指纹/工具/适配器/rulepack 摘要变化、依赖图或 advisory 变化均保留原始和活动阻断并返回 incomplete。该字段由谁从真实原工具和内容字节生成、如何验证宿主来源尚未接入；项目 JSON 自填同值不能取得信任，4.8 继续未完成。
  进行中：相邻 `codeguard-cli` 已实现不具授权效果的精确身份匹配、严格候选 schema/解析器、期限/策略修订/多候选冲突筛选，以及批准快照的字节摘要绑定；后者可拒绝不在先前固定快照中的候选，但预期摘要仍由调用方提供。见 `tests/acceptance/false-positive-identity-baseline.md` 与 `tests/acceptance/approval-snapshot-baseline.md`。可信策略/时钟和摘要来源、批准引用独立核验、同 PR 自批的受保护 CI 验证及门禁接线仍缺，不勾选。
- [ ] 4.9 接入 `rules whitelist list/explain/propose` 与 config validate/explain；验收：propose 只从本轮完整原生 finding、工具/适配器/rulepack 身份和内容复核生成候选；缺任何身份则报告未完成与补证据动作，不能填占位摘要；查询解释批准与失配原因，普通项目文件不能自授权，系统性误报走经批准的规则修订。进行中：相邻 Rust CLI 已提供显式候选文件的只读 `rules whitelist list/explain`；explain 可对显式提供的发现身份解释精确匹配或失配，观察身份与批准来源均未核验，始终标记 `authority=unverified`、`gate_effect=none`；坏文件、重复 ID、缺失目标均不能呈现为批准。`propose` 已能从本地稳定任务返回缺本轮身份的未完成预览，固定 candidate=null、无门禁效果，见 `codeguard-cli/tests/acceptance/whitelist-propose-incomplete-preview.md`。`config validate/explain` 已有只读候选解析但不能解释可信批准、期限或本轮 finding；自动发现与完整候选生成仍未完成。
  读取加固：`list/explain` 的候选与显式观察身份、纠错入口的旧决策与替代候选，现统一使用运行时有界普通文件读取，拒绝最终路径符号链接并避免文件类型检查后按路径重新打开；查询命中仍不取得批准。相关回归见相邻 `codeguard-cli/crates/codeguard-cli/tests/whitelist_command_contract.rs`；完整可信来源与门禁仍缺。
  冲突纠正：同一稳定 finding ID 的两条候选即使目标不同，`list/explain` 也将双方标为冲突，不输出任选一条的身份匹配。查询层改动不等于可信批准接入，4.9 不勾选。
  前置进展：Ruff 局部报告 0.5 已对完整文件记录本轮工具与配置摘要，未完成文件为空；`propose` 0.2 只从最新已同步报告读取仍存在的当前 finding 与这些摘要，未同步/源码变化/新扫描问题消失不回退旧观察。这仍是本地未验证身份，缺适配器、批准 rulepack、可信来源和完整候选生成，见 `codeguard-cli/tests/acceptance/ruff-observed-artifact-identity.md` 与 `codeguard-cli/tests/acceptance/whitelist-propose-incomplete-preview.md`，4.8/4.9 均不勾选。
  后续进展：局部报告 0.6 与 `propose` 0.3 额外展示 F401/E501 候选规则映射的 CodeGuard 规则 ID、原生工具版本、清单摘要和 `candidate_unapproved`，并将 `approved_rulepack_identity` 明列为缺失证据。该摘要只是本地观察，不会自批准或放行，见 `codeguard-cli/tests/acceptance/ruff-rulepack-observation.md`。
  适配器身份进展：Ruff 局部报告 0.9 在有原生 finding 且仍有检查预算时记录本次 CodeGuard 可执行制品摘要；`propose` 从已同步报告读取后再核对当前二进制，变更时拒绝旧观察，缺摘要时明确列为未完成。公开 lint 0.12、候选预览 0.4 和 Ruff task verify 0.9 按协议升级，旧 schema 留存；真实 Ruff 复检和篡改报告/同步标记反例通过。该摘要未证明签名发行、批准 rulepack、人工裁定或可信门禁，4.8/4.9 继续不勾选。
  工具身份复核进展：`propose` 可显式接收绝对 `--ruff-tool`，按当前普通文件字节复核扫描报告摘要；不同或不可读时隐去旧观察、保持 candidate=null/退出 3，不执行工具或签发批准。已增加参数边界及真实 Ruff 正反例；未指定工具时仍只能展示未获信任的历史摘要。可信工具来源、完整候选和独立审批未接通，4.9 不勾选。
- [ ] 4.10 实现白名单纠错闭环与规则级误报升级路径；验收：候选/驳回/批准/过期/撤销/失配关联稳定 finding 和任务，已批准例外不伪装为代码修复；误批或过宽条目采用旧决策撤销、新候选引用旧决策、独立批准的修订链，冲突或未批准期间不得放行，原任务重开；纠错提案含原决策/稳定 finding/结构化原因/本轮复检引用，替代候选有新 ID 与 replaces_decision_id；只撤销不制造替代、引用链无环、旧新原子切换、扩大范围拒绝；同规则多目标误报生成规则或适配器根因调查，须以正反例和受保护策略修订处理，不自动扩大白名单；评测保留原始发现和人工裁定误报率。进行中：相邻 Rust 快照协议 1.1 可固定撤销 ID，绑定时撤销优先于旧字节命中；可信发布、修订链事件、真实门禁和任务重开仍缺。
  本轮进展：相邻 Rust 增加替代候选 1.1 schema 与 `replaces_decision_id`，普通绑定不接受缺旧决策的替代结果；专用绑定校验旧决策引用、同一 finding/检查器/规则/类别/目标归属及同快照撤销旧 ID。旧决策来源可信性、完整修订链无环、纠错提案 CLI、任务投影和受保护发布仍缺，任务不勾选。
  后续进展：前序快照绑定再核对旧决策的字节摘要与原策略修订，拒绝旧字节篡改、前序已撤销、缺固定摘要与新旧同修订；摘要来源和修订先后顺序仍由受保护发布边界证明，多级链及真实门禁未完成。
  多跳进展：Rust 现可逐跳验证最多 32 个前序候选/快照直到普通根决策，拒绝链截断、乱序、多余节点、重复 ID/修订的环及前序候选超过当时有效期上限。可信发布来源与真实时间顺序、纠错提案/任务事件和真实门禁仍缺，4.10 保持未完成。
  纠错入口进展：`rules whitelist propose` 追加只读纠错参数，可从已核对的本轮 Ruff `task verify` 收据、稳定 finding 和旧候选预览撤销；仅撤销与替代草稿分别表达，错 run/错目标/复检后源码变化不生成提案。替代身份仍缺批准的适配器和 rulepack，候选/撤销事件、独立批准与门禁未接入，保持未完成。
  持久记录进展：纠错命令可选 `--record`，持任务锁重查复检证据，将同一提案按内容摘要幂等记录到稳定 finding 的事件目录；事件携带 task_id、原决策/新草稿和复检引用，固定未验证且无门禁效果。`next` 当前简报已可显示待审事件引用，但持久任务 Markdown 投影、独立批准、可信策略发布与真实门禁仍缺，4.10 不勾选。

  可读投影进展：纠错 --record 现从持锁重查的同一提案生成 tasks/corrections/<finding-id>/<event-sha256>.md 历史附件，保留七项任务信息、事件和复检引用。事件保存后附件失败单独反馈，编辑不覆盖、删除可重建；next 只展示与当前事件重建字节一致的附件，不从 Markdown 读取指令。完整任务协调、独立批准、可信发布及正式关闭仍缺，4.10/9.28 不勾选。

  复检配置进展：Ruff 当前简报与误报提案复核目标目前选择的配置路径及字节摘要，配置内容或优先级变化时旧观察不驱动纠错；缺配置身份的旧报告要求重新检查。真实 RED 复现 F401→E501 后旧纠错仍展示，以及新增同字节 .ruff.toml 后普通提案仍用旧配置；两者已接入同一只读发现复核。完整可信批准与自动候选仍缺，4.9/4.10 不勾选。

  签名链进展：Rust 多跳入口逐跳核验历史签名、快照修订、同工作区、严格序号与时间顺序、历史候选在受保护审核时刻有效；所有 pin 由验签推导，再沿用原精确替代/撤销/无环绑定。历史过期不抹去当时合法批准，公钥最新撤销仍阻止绑定；32 跳上限。三项签名链反例及单快照/旧快照/边界回归通过，见相邻 codeguard-cli/tests/acceptance/signed-approval-chain-binding.md。宿主信任来源、Git 基线祖先与真实发布/门禁仍缺，4.10 不勾选。

  Git 基线进展：runtime 原生只读祖先观察与 CLI 签名链联合入口已接通，完整提交、对象类型、非浅历史与每跳关系均须匹配；replace/graft 和 lazy fetch 禁用，同一预算/取消贯穿所有调用。真实 SHA-1/SHA-256、伪造关系、缺对象及本地传输正反对照四项，签名链五项通过，见 codeguard-cli/tests/acceptance/git-approval-baseline-binding.md。可信仓库/工具/公钥来源与真实策略发布、宿主门禁仍缺，4.5/4.10 不勾选。

  原生 finding 关联进展：领域门禁新增受保护宿主冻结的 checker/tool/category/obligation 映射，并核对原生主定位的源码路径或依赖组件及显式版本；缺定位、错工具/类别/义务、缺失或歧义映射不应用白名单。处置前预先识别重复 finding 引用及复用的批准决策 ID，冲突双方均保留活动阻断，顺序不影响结果。门禁 26 项、会话 8 项与反馈/报告/SARIF 回归通过，见 codeguard-cli/tests/acceptance/native-allowlist-disposition-binding.md。当前为领域/协议用例，可信来源、签名批准到真实原生报告的宿主接线仍缺，4.8/4.10 不勾选。

  最终期限进展：领域门禁新增宿主最终判定时钟，要求 observed_at <= gate_time_unix < expires_at 且时钟非零；检查结束到期、缺时钟或回退不沿用取证时刻放行。已验签结果暴露只读 expires_at，当前边界须取当前批准相关约束的最早期限，不用历史到期缩短合法替代条目。门禁增至 29 项，真实时钟来源与批准生产/宿主接线仍缺，见 codeguard-cli/tests/acceptance/final-gate-approval-clock.md，4.5/4.8 不勾选。

  签名处置接线进展：门禁新增宿主独立冻结的当前策略修订；旧/缺修订不能沿用白名单。普通及替代签名入口生成只读绑定预览，固定候选/快照摘要、范围、身份和最早期限；替代必须先核验完整签名/Git 链。独立批准标记始终 false，不能从项目 JSON 构造或自批。门禁 30 项、处置三项、实际 Git 链补充用例及受影响回归通过，见 codeguard-cli/tests/acceptance/signed-disposition-preview-binding.md。可信来源及真实批准生产/门禁仍缺，4.5/4.8 不勾选。
  范围接线进展：只读签名预览保留工作区及当前批准基线，领域门禁与独立冻结范围比较。跨工作区、错基线、非法/缺范围和旧输入均不能应用白名单；没有白名单的普通判定保留。可信宿主来源及正式门禁仍未接通，4.8 不勾选；验收见相邻 codeguard-cli/tests/acceptance/approval-scope-gate-binding.md。

## 5. S05 工具适配框架与准备

依赖：S03、S04。覆盖：native-tool-adapters、language-gate-commands。

- [ ] 5.1 实现 capability/discover/resolve/plan/parse/coverage/fix 协议与编译期注册；验收：adapter 不绕开运行时启动进程或联网。
- [ ] 5.2 实现工具解析、二进制身份、doctor 和 tool lock 验证；验收：wrapper/受管缓存/系统工具均匹配锁，缺工具返回恢复步骤。
  原生版本进展：统一 runtime 版本探测核对固定参数、工具前后字节、精确 stdout 与私有日志，共享截止时间；超时/取消/spawn/signal/超限/非零退出、版本/stderr/字节变化/日志失败分别保留诊断。现有 Ruff 启动阶段已复用，不完整时不扫描源码。真实 Ruff 0.16.8 版本调用验收与模拟故障分层；doctor CLI、可信锁、完整兼容/环境及准备报告仍缺，5.2/5.6 不勾选；见相邻 tests/acceptance/native-version-diagnostics.md。

  进行中：相邻 `codeguard-cli/crates/codeguard-cli/src/tool_identity.rs` 和 `crates/codeguard-cli/tests/tool_identity_contract.rs` 已对三种 origin 的入口、基础可执行位、独立运行时及有界目录树 bundle 摘要作只读核验；真实 Maven libexec 全树通过本地测试锁核对，委托 jar 篡改被拒绝；见 `codeguard-cli/tests/acceptance/tool-identity-baseline.md`。可信锁来源、完整动态依赖闭包、doctor 与恢复步骤仍缺，不能勾选 5.2。
  Ruff 局部原生报告另记录完成文件的工具/配置字节摘要并在整轮末复核，未完成文件不声称身份；尚未接受保护工具锁，见 `codeguard-cli/tests/acceptance/ruff-observed-artifact-identity.md`。
- [ ] 5.3 实现独立 tools install 流程、下载清单与校验；验收：普通 check/plan/doctor 不隐式安装；真实主动联网 wrapper 在离线隔离中被阻止，无法隔离则启动前 incomplete。
  网络编排进展：download_and_publish_signed_distribution 请求前核对签名/本机平台/精确工具/完整定位及宿主精确站点许可，下载后共享预算进入签名发布服务。拒绝无许可/通配等五类前置反例；另显式固定 Rust 官方仓库提交 LICENSE-MIT 的真实公共 HTTPS、摘要和临时发布 1 项通过（0.70 秒），不执行内容、测试 key 不是真实发行批准。真实宿主来源、正式 CLI apply/运行时/恢复/跨平台仍缺，5.3 不勾选，见相邻 tests/acceptance/signed-network-publication.md。
  签名发布编排进展：新增明确调用的离线包发布入口，按本机平台、精确工具绑定签名/原锁，raw 或完整布局关联后独立缓存发布；前/发布前/发布后时钟复核，拒绝回退，全部阶段共享预算取消。5 项目标契约通过，覆盖 raw/ZIP 原定位与复用、错误身份/包/签名/平台/工具/时钟、已有损坏目标保留，以及发布后时钟缺失失败再重验。尚无真实宿主信任/网络/正式 CLI 安装/运行时/恢复闭环，5.3 不勾选，见相邻 tests/acceptance/signed-package-publication.md。
  发行签名进展：新增独立 distribution.v1 Ed25519 域，绑定原始清单/锁、发行者/通道/平台、序号及有效期，严格清单/锁关联后返回只读结果。宿主公钥/撤销/时钟/最低序号真实性仍外置；无项目自批或签发命令。可信宿主和正式下载/install 编排尚缺，5.3 不勾选；见相邻 tests/acceptance/signed-distribution-binding.md。
  HTTPS 传输进展：Rust runtime 新增 TLS 验证、固定字节/摘要、有界手动重定向、共享绝对期限和取消的异步包下载 API；禁环境代理/自动重试/内容解压，状态/编码/长度/摘要不符无半成品。11 项本地 TLS 测试及 96 项相关回归通过；gzip, chunked 接受缺口先复现后修复。来源批准、正式清单到下载/发布接线、apply/运行时/恢复及跨平台仍缺，5.3 不勾选；见相邻 tests/acceptance/package-https-transport.md。
  下载/展开串联进展：download_verified_archive 请求前校验同一包摘要、格式/入口/预算/完整摘要，下载后以共享预算核对包、入口与完整树，不返回局部成功。新增本地 TLS ZIP/tar.gz→完整树→私有临时目录发布及 raw→字节发布，错误整树/包身份拒绝、声明冲突与无效输入不发请求。15 项 HTTPS 目标测试通过；正式授权、CLI 接线/运行时/恢复仍缺，5.3 不勾选，见相邻 tests/acceptance/downloaded-package-publication.md。
  完整树进展：新增保留空目录/父目录的 UnpackedArchive 入口，旧文件集合接口保留；内存树按既有 bundle-tree-v1 本机顺序计算/核验，公开构造对象重新检查形状/路径/总量和预期摘要。真实临时目录与原 CLI 算法精确相同，库篡改、空目录缺失、乱序/非法输入/取消/到期反例通过。本轮相关回归 54 项通过，1 项原生缓存 ignored 不计运行；bundle 根映射、批准及完整目录发布/下载/apply 尚缺，5.3 不勾选，见相邻 tests/acceptance/unpacked-bundle-tree.md。
  GNU/PAX 后续：支持下一成员的有界 GNU 路径/局部 PAX path、size 及无害全局描述；完整路径覆盖截断旧头，size 控制真实边界而非一律与旧头相等。17 项归档回归覆盖危险/重复/矛盾/孤立/损坏/超限扩展及标准 tar 解析交叉核对。全局 path/size、sparse/链接、bundle/目录发布、可信下载/批准及 apply 仍缺，不勾选；见相邻 tests/acceptance/tar-extension-verification.md。
  归档基础：runtime 新增 ZIP/tar.gz 内存展开，先核对包/入口摘要，全成员路径/类型/冲突、成员数及文件/容器预算检查，无文件系统解包或授权。11 项归档用例通过，两格式均串联包流→展开→临时缓存发布；首轮 tar GNU/PAX 等扩展明确拒绝，后续能力见上一条进展。完整 bundle 树、目录发布、可信下载/批准、CLI apply 与全平台仍缺，不勾选；见相邻 tests/acceptance/package-archive-expansion.md。
  输入修复：共享静态文件读取器采用 Unix 非阻塞打开，再按同一句柄拒绝特殊类型；修复无写入端 FIFO 在类型核验前卡住锁/发行清单观察的问题。先由独立测试子进程复现并回收，再验收读取器及 install 两个输入入口。仅为 Unix 特殊文件边界，网络/发行授权/归档/正式 apply 与跨平台仍未完成；见相邻 tests/acceptance/bounded-input-fifo.md。
  包流基础：runtime 新增精确长度/非零 SHA-256 校验的有界读取 API，128 MiB 上限，超长至多读取多一个字节，读取前后检查取消/期限；错误仅固定诊断，不返回半成品。9 项包流与 10 项缓存发布测试通过，1 项真实工具测试本轮 ignored 不计运行。临时缓存串联验证成功 raw 字节发布/复用及错误字节不进入发布。尚无网络读取超时、下载/展开/批准及正式 apply，5.3 不勾选，见相邻 tests/acceptance/package-stream-verification.md。
  清单 CLI 接线进展：install 显式 --distribution-manifest FILE，反馈 0.2 分层显示固定诊断和逐工具脱敏包声明。来源 URI 只给摘要，原锁失配/坏清单/符号链接拒绝，声明子集不消除其它工具或运行时缺口；apply 仍写前阻塞。22 项命令、11 项清单、4 项边界回归，7 份实际 schema 与 4 个伪造权限反例通过；可信下载/展开/正式 apply 未实现，5.3 不勾选，见相邻 tests/acceptance/tools-install-manifest-preview.md。
  发行清单进展：新增 1.0 严格解析与原始锁字节绑定 API/schema，精确工具/平台/版本/来源/二进制/bundle，限定 HTTPS 和包大小、相对归档入口；绑定时重验对象，拒绝重复字段、未知批准与错身份。11 项契约、4 项 crate 边界通过；schema 4 正例/16 反例通过。清单只是声明子集，不授予来源/安装权限；下载、展开、可信发布及 CLI 接入仍缺，5.3 不勾选，见相邻 tests/acceptance/distribution-manifest-binding.md。
  CLI 预览进展：tools install --lock FILE 默认 dry-run，共用库存/身份核验，绑定锁/二进制/来源引用摘要，分别解释平台与恢复动作。未绑定可信来源的 apply 在写入前明确阻塞，不调用发布 API。32 项回归、实际预览 schema、模式冲突及伪造完成反例通过；可信下载/发行包/正式 apply 未接通，不勾选，见相邻 tests/acceptance/tools-install-preview.md。
  缓存发布基础：runtime 已提供有界冻结字节/预期 SHA-256 的目录 FD 发布服务；私有独占暂存、写后校验、linkat 不覆盖发布及最终复核，拒绝链接/FIFO/错误权限/损坏目标，重复重验后复用，取消/超时不返回成功。53 项普通相关回归及 1 项显式真实 Ruff 临时发布/原生版本通过。收据不授予发行批准或准备状态；可信下载清单、CLI 预览/apply、压缩包和全平台尚缺，不勾选。见相邻 tests/acceptance/tool-cache-publication.md。
  5.3 补充进展：显式归档目录投影 API 先验证完整树，再按目录边界去前缀、保留空目录并匹配 bundle 摘要；未消费成员保留原路径和内容。59 项相关测试通过，包含实际临时目录摘要交叉核对；1 项原生缓存测试 ignored。正式清单映射、可信来源、下载/目录发布/apply 尚缺，5.3 不勾选；见相邻 tests/acceptance/bundle-root-projection.md。
  发行包关联进展：清单 1.1 显式 bundle_archive_root 与 1.0 兼容观察；新增冻结包关联 API，绑定同一锁、包大小/摘要、入口与子树，返回只读树及剩余成员，不写安装目录。清单 13、关联 3、命令 23 共 39 项测试及 schema 4 正例/10 反例通过；可信来源、实际缓存根映射/目录发布/apply 仍缺，5.3 不勾选，见相邻 tests/acceptance/distribution-bundle-binding.md。
  目录发布进展：macOS/Linux API 使用固定目录 FD、私有独占暂存、逐成员写后/完整集合重验和不覆盖原子目录重命名，取消清理本次暂存；坏已有目标保留并拒绝，并发同树只一方新发布。6 项目录发布、既有缓存 10、投影 4、CLI 57，共 77 项相关用例通过（1 项原生缓存 ignored）；正式缓存根映射、其它包成员/运行时、可信下载与 apply 仍缺，5.3 不勾选，见相邻 tests/acceptance/tool-bundle-publication.md。
  完整布局进展：清单 1.2 声明完整安装树摘要，精确绑定同一内容寻址目录下的锁入口/bundle 根；错路径拒绝，不重写锁。只读布局保留入口、空目录及 bundle 外全部普通成员，分别核验整树/子树。55 项相关测试及 schema 5 正例/7 反例通过；实际临时缓存发布后原锁入口和 bundle 核验匹配。正式 CLI 布局反馈、可信下载/批准、raw/运行时安装与恢复仍缺，5.3 不勾选，见相邻 tests/acceptance/distribution-layout-binding.md。
  CLI 布局反馈进展：install 预览 0.3 区分完整路径声明绑定/缺完整树/raw 不适用，显示内容寻址目录与定位摘要，内容核验固定 not_run；不读取包或调用发布，未批准 apply 仍写前阻塞。48 项相关测试、8 份实际 schema 输出、4 个伪造完成及 2 个格式/阶段矛盾反例通过；0.2 schema 单独保留，私有路径/地址不回显。批准/真实下载/apply 与恢复仍缺，5.3/5.6 不勾选，见相邻 tests/acceptance/tools-install-layout-preview.md。
  raw 定位/内容进展：1.2 原锁入口精确绑定二进制摘要.bin，错路径即使来源引用摘要匹配仍拒绝；有界分块核验返回无复制只读借用视图，预览正确区分新版定位已绑定/旧版需映射。53 项普通回归及 1 项显式真实 Ruff 0.16.8 关联/缓存发布/版本观察通过；4 份实际 raw schema 输出与伪造内容反例通过。可信下载/批准、运行时和正式 apply/恢复仍缺，5.3 不勾选；见相邻 tests/acceptance/distribution-raw-binding.md。
- [ ] 5.4 实现报告产物 freshness、scope/rule 执行覆盖核对；验收：陈旧或伪造空成功报告不能通过。
  进行中：Ruff 0.16.8 局部扫描已在同轮原生执行 `--show-settings`，记录 F401/E501 全局启用状态及逐文件忽略存在性；报告规则与设置矛盾即 incomplete，损坏设置亦不作为干净证明。设置仍不能证明 `noqa` 等源码内 suppression 或批准策略 required rules 覆盖，故 `coverage_proven=false`；见 `codeguard-cli/tests/acceptance/ruff-effective-settings-observation.md`。
  后续进展：同轮 `--ignore-noqa` 对照已使源码注释抑制成为独立观察；正常诊断不包含于对照即 incomplete。仅被抑制的文件标记 `suppressed` 而非 `passed`，旧任务加 `noqa` 后复检进入 `suppression_requires_review`。逐文件配置忽略、批准规则集合和完整门禁仍缺，见 `codeguard-cli/tests/acceptance/ruff-native-suppression-observation.md`。
  进行中：相邻 `codeguard-cli/crates/codeguard-runtime` 已实现只读新鲜报告槽位与原生执行/私有日志/报告读取的同轮组合，旧报告在 spawn 前拒绝，缺报告、链接、超限或日志失败均不返回完整结果；见 `tests/acceptance/fresh-native-report-baseline.md`。PMD 6 固定 `-r` 参数已接入局部 Rust 试运行服务，核对源码、启动器及整个工具目录树的前后摘要，并核对报告文件范围、退出码与诊断数量；见 `tests/acceptance/pmd6-runtime-probe-baseline.md`。已批准制品的锁定来源与规则实际生效证据、项目扫描范围、正式 `check` 接线及同用户并发篡改防护仍缺，不能勾选。
- [ ] 5.5 建立 adapter conformance harness；验收：F01–F10、F17 的有效与畸形报告可独立复用，mock 与真工具证据分层。
  F05 增量：相邻 Rust `cve rust` 对结构有效且绑定当前锁的 cargo-audit advisory，即使原生程序随后异常退出、输出完整报告后超时或在其它输出超限后，也保留局部 finding 和 `incomplete`；残缺 stdout JSON 不制造 finding，已初始化工作区仍能同步稳定完整性任务。模拟原生进程、真实工具与全适配器矩阵分层记录，见 `codeguard-cli/tests/acceptance/rust-cve-partial-native.md`。通用 conformance harness、单体 stdout 报告截断恢复、其它适配器及 F01–F10/F17 全矩阵仍缺，5.5 不勾选。
  Python CVE F05 增量：`pip-audit` 的完整 JSON 在异常退出、输出后超时或其它输出超限时，仍按本轮 PEP 751 锁归属保留局部 advisory 和具体未完成原因；残缺 JSON、锁外组件不生造项目 finding。已初始化工作区保存待核验证据并同步稳定完整性任务，见 `codeguard-cli/tests/acceptance/python-cve-partial-native.md`。模拟器不替代真实 pip-audit，通用 conformance harness 和全适配器矩阵仍缺，5.5 不勾选。
- [ ] 5.6 实现 tools list/verify/install 的库存、制品身份和默认预览/显式安装边界，以及doctor准备报告；验收：身份通过不等于可启动，安装部分失败可恢复，准备证据带run_id并可幂等同步。
  库存进展：tools list 已复用同一有界锁读取与制品核验，稳定列出所有声明平台、版本、适配器/规则来源及独立 runtime/bundle 缺口；跨平台为 not_inspected，不访问制品或虚构本机缺失。固定声明锁范围、必需库存未核验、required_by_policy=null 与 unknown/退出 3，不执行/安装/写工作区。28 项回归及实际 schema 验证通过；可信必需集合、正式库存与安装仍缺，5.6 不勾选，见相邻 tests/acceptance/tools-list-command.md。
  持久化进展：doctor 0.2 在已绑定工作区保存不可变 queued 报告并自动 sync；重复失败/原因变化沿用一个环境调查任务，next 给出受限恢复及复检路径。未选择不制造必需缺失；真实版本恢复不自动关闭或授予 ready。严格导入拒绝自写批准、未知字段、预算/工作区/消费摘要异常；保存失败向对话反馈。54 项回归、10 份实际 schema 与 6 项反例通过；可信必需项/全工具报告及 doctor 专用关闭未实现，5.6 不勾选，见相邻 tests/acceptance/doctor-workspace-sync.md。
  doctor 局部入口：默认反馈静态检查配置，仅显式绝对路径 Ruff 运行固定版本诊断，复用统一 runtime、私有临时 cwd/日志和共享预算；单探测上限 10s，脚本入口缺隔离时启动前拒绝。未选工具不冒充缺失；本地版本成功仅 observed_untrusted，策略/必需前置未核验，readiness unknown、交付 not_evaluated，报告明确 not_saved，不写工作区或扫描源码。其它工具、可信锁/必需前置映射、完整准备报告持久化及同步仍缺，5.2/5.6 不勾选；见相邻 tests/acceptance/doctor-local-ruff.md。
  CLI 进展：tools verify 以本地 codeguard.lock.json 或显式候选执行有界只读解析，复用三来源入口/运行时/目录包核验，反馈 issue 与恢复步骤；候选来源未核验，固定 incomplete/unknown、无门禁效力，匹配仅 matched_untrusted，版本仅锁声明，不启动 wrapper/联网/安装或写工作区。显式缓存与运行时参数可核对，跨平台条目不产生本机结论。工具库存/安装、可信锁来源、原生 doctor 与准备报告持久化/同步仍缺，5.2/5.6 不勾选；见相邻 tests/acceptance/tools-verify-command.md。
- [x] 5.7 实现C03 detect查询处理器与DiscoveryReport，复用观察port；验收：静态未知条件完整返回0，必要目录不可读返回3和部分观察，均不执行wrapper、不写画像/任务。证据：相邻 `codeguard-cli/crates/codeguard-cli/src/{main,discovery}.rs`、`schemas/discovery-report.schema.json`、`crates/codeguard-cli/tests/detect_cli.rs` 与 `tests/acceptance/discovery-baseline.md`；动态构建模型、其余清单语义及多语言源集属于 5.9/6.1/8.x，保留 unknown，不宣称检查通过。
- [x] 5.8 实现C04 capabilities查询、平台/类别筛选和发行元数据解释；验收：planned查询成功但不称可运行，未知语言2，损坏注册表4，不探测或安装工具。证据：相邻 `codeguard-cli/crates/codeguard-cli/src/main.rs`、`schemas/{capability-inventory,capability-selection}.schema.json`、`crates/codeguard-cli/tests/{capability_inventory,capability_selection}.rs`、`tests/acceptance/capability-inventory.md`；当前所有新能力仍为 gap，原生适配器验收属于 S06–S08。
- [ ] 5.9 实现动态构建模型解析任务与共享扫描义务映射；验收：detect/init/plan仅保留待解析条件，执行期经统一runtime留证据，多语言/多构建根不丢范围，adapter不私自I/O。
- [ ] 5.10 实现项目检查器配置探测；验收：按构建根识别 Javadoc、依赖/CVE、lint 与安全检查器的 `configured/missing/invalid/unknown`，说明配置位置与启用建议；28 个检测族只作候选目录，不自动生成全部必需义务。进行中：相邻 Rust `detect` 已只读解析 Maven POM 的六种检查器声明，保守处理父 POM、pluginManagement、profile 和 Gradle；另沿 Python 文件层级识别 Ruff TOML 的配置优先级、lint/format 区别及坏配置，见 `codeguard-cli/tests/acceptance/{maven-config-discovery,ruff-config-discovery}.md`。其他生态、Maven effective model、项目全量执行与宿主反馈接线仍未完成，故不勾选。
  后续进展：Maven 静态探测新增独立 P3C 项，仅在明确 P3C 2.1.1 插件依赖、已观察的规则路径和 `skipPmdError=false` 同时存在时标记已配置；普通 PMD、缺依赖/规则、动态版本与错误吞掉配置有正反例。`plan lint java` 仅显示候选，不认证规则执行。见相邻 `codeguard-cli/tests/acceptance/maven-config-discovery.md`。
  Javadoc 探测补强：明确关闭 `missing` 的 doclint、动态 doclint 与 `failOnError=false` 不再误报注释检查已配置；`check java` 也会反馈同一配置状态。Maven effective model、生命周期执行与其它生态仍缺，5.10 不勾选。
  Python CVE 输入进展：`detect` 按 Python 构建根区分 requirements 逐行精确版本、动态/未锁输入、uv/Poetry 锁文件未解析及缺输入；`plan cve python` 和 `check all` 保留 `python.pip_audit` 配置未知与原生工具/数据库待核验，不把固定版本或锁文件存在误报为漏洞扫描通过。真实多构建根归属和动态约束反例见相邻 `codeguard-cli/tests/acceptance/python-dependency-input-discovery.md`。项目生效配置、完整依赖图、原生漏洞结果与可信策略仍缺，5.10 不勾选。
  标准锁区分进展：发现器现识别 `pylock.toml` 与单段命名的 `pylock.<name>.toml`，单列 `python_standard_lock_model_unparsed`；同根并存标准锁与 uv/Poetry 锁时保持选择歧义，工具专用锁不再暗示可直接用于 pip-audit `--locked`。真实 CLI 反例见相邻验收文档。PEP 751 内容/环境、原生运行和漏洞库仍未核验，5.10 不勾选。

## 6. S06 Java 全链路

依赖：S05。覆盖：native-tool-adapters、language-gate-commands。

- [ ] 6.1 实现 Maven/Gradle/JDK/wrapper/profile/module/source-set 观察；验收：多模块、父 POM、动态未知范围与错误 JDK 有真实样本。
  探测诊断进展：Maven 版本阶段现区分运行时超时/启动前预算耗尽/无法启动/取消/输出及管道故障等原因。两个新反例先暴露通用错误提示，再通过具体原因返回；失败不启动 validate，不产生源码违规。原全量回归的 bundle mutation 偶发失败仍需具体原因复现才能归因，不能凭单独重跑推断解决。

  进行中：相邻 `codeguard-cli/crates/codeguard-cli/src/maven_probe.rs` 已通过统一 Rust runtime 调用 Maven 原生 `--version` 和离线 `validate`，复核启动脚本与 POM 内容，并对真实 POM 4.1 错误、无质量绑定 POM 的 validate 成功分别留局部证据；见 `codeguard-cli/tests/acceptance/maven-native-probe.md`。Maven 发行包/JDK 身份锁、Gradle、wrapper、profile、多模块、父 POM 与动态范围仍未完成，不能勾选 6.1 或把 validate 当质量通过。
- [ ] 6.2 确定并锁定官方 P3C/PMD/JDK 兼容组合，实现原生报告解析；验收：正反例证明规则实际加载，不能用 Checkstyle 名称替代。
  新进展：隔离单文件探针现在声明 P3C 2.1.1 JAR 中十个 `ali-*.xml` 规则集，本地反馈 0.2 记录清单与受控 POM 摘要；真实公开类同时命中命名和作者注释规则，包内可见类不命中作者注释。仅证实两条触发规则及该样本上下文，十个规则集的全规则生效、批准工具闭包和项目覆盖仍未核验，故不勾选。
  追加进展：公开 `lint java FILE` 现调用固定 Maven PMD 3.11.0/P3C 2.1.1/PMD 6.15.0 单文件探针，原生违规规则与位置可返回对话；本机 JDK 26 隔离离线仓的违规和干净样本均经 CLI 执行，后者仍标 `clean_scope_unproven`、退出 3。当前探针声明十个规则集，本机 JDK 21 的命名和作者注释规则有真实正例。该仓字节摘要仅为本地观察，未证明受批准工具锁、全规则实际生效或项目覆盖，见 `codeguard-cli/tests/acceptance/java-p3c-cli-native-local.md`，6.2 不勾选。
  进行中：相邻 `codeguard-cli/crates/codeguard-adapters/src/pmd_xml.rs` 已实现 Rust 对 PMD 6 XML 的有界纯解析，坏 XML/DTD/处理错误/版本不符及已报告的 suppression 不生成通过；`pmd6_command.rs` 的固定字面参数已交给局部 Rust runtime 试运行服务。可复跑的 Maven PMD/P3C 哨兵在本机 JDK 8/17/21/26 上均使违规样本报告真实 `ClassNamingShouldBeCamelRule`、干净样本无诊断、坏规则集失败；还以隔离 Maven 仓库、`-o` 和前后目录树摘要复跑，见相邻 `codeguard-cli/tests/acceptance/p3c-pmd-research.md` 与 `codeguard-cli/crates/codeguard-cli/tests/p3c_native_replay.rs`。但闭包摘要尚未接入受批准工具锁，干净 XML 不证明覆盖，正式 `check` 尚未接线，仍不能勾选或把该哨兵扩展为全部 P3C 规则的验收。
  规则归属补强：项目 POM 规则子集先绑定到隔离探针；本地 P3C 2.1.1 制品的十个规则集/56 个规则 ID 已整理为 Rust 目录，项目原生 XML 若报告未选择的规则集、错误 ID 归属或未知规则，标为 incomplete、不给源码 finding。伪 XML 反例与真实 Maven 正例见 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`；目录仍不是受保护 rulepack/工具锁，全规则执行覆盖和正式批准未证实，6.2 不勾选。
- [ ] 6.3 实现 Checkstyle/Javadoc 注释检查；验收：公共 API、参数返回、inheritDoc、record/Lombok/生成代码正反例。
  配置失败指引进展：固定 10.21.4 正常 254 + 官方非法属性/正则因果异常才细分 checkstyle_configuration_regex_invalid，公开对话和准备简报指向原配置正则，不回显自由文本。纯分类先 RED 后实现；缺报告且输入变化的反例再 RED，修正为输入/截止/取消优先。原生格式七轮回放通过（38.75 秒），见相邻 tests/acceptance/checkstyle-regex-failure-guidance.md。未知属性级错误/其它版本及完整批准覆盖仍缺，6.3 不勾选。
  作者/版本格式验收：补齐 JavadocType 指引中缺失的 @author/@version 与事实依据约束，目标指引测试先 RED 后通过。缺标签/格式不符/部分及完整补齐 2/2/1/0 原生诊断准确，原配置复检为局部候选；无效正则连续两轮保持 incomplete 并复用配置准备任务，不冒充源码违规。七轮通过（38.35 秒），见相邻 tests/acceptance/checkstyle-type-formats.md。全部正则/标签变体和完整项目/批准仍缺，6.3 不勾选。
  类型配置进展：MissingJavadocType/JavadocType 保留四级访问范围、五类类型 token、各自注解参数及类型标签/作者版本参数；跨模块借用反例先 RED 后通过，绑定/配置十三项通过。十组原生配置准确筛选公开/私有/注解/record 与参数/未知标签，恢复首次配置并真实补文档复检为局部候选，十一轮通过（58.02 秒），见相邻 tests/acceptance/checkstyle-type-options.md。作者/版本正则只有静态适配证据，其它 Scope/全部 token 语法与完整项目/批准覆盖仍缺，6.3 不勾选。
  方法标签配置进展：JavadocMethod 静态适配保留 accessModifiers、允许缺参数/返回标签、validateThrows、allowedAnnotations 及四种原生 token；合法参数先 RED 后修正，绑定/配置十二项通过。公开/私有与注解方法、异常标签六组原生配置及恢复首次配置的两次修复复检共八轮通过（57.23 秒），事实仍 open，见相邻 tests/acceptance/checkstyle-method-tag-options.md。完整配置、全部语法和批准覆盖仍缺，6.3 不勾选。
  方法 token 进展：MissingJavadocMethod 保留四种原生 token 的模块上下文；静态绑定先 RED 后通过，五组真实配置准确选择普通方法、构造器、注解成员及 record 紧凑构造器，稳定任务无重复；同配置两次复检验证紧凑构造器文档修复，事实仍 open。七轮原生验收通过（51.11 秒），见相邻 tests/acceptance/checkstyle-method-tokens.md。完整配置/语法及正式关闭仍缺，6.3 不勾选。
  注释变体进展：静态配置新增原 MissingJavadocMethod/JavadocType，实际 CLI 检查 record 参数文档正反例、继承文档/Override/Generated 默认例外，并保留同一行声明及单行方法体的原生差异，用多行方法验证缺文档。显式 Lombok 1.18.38 delombok 原源码/展开 getter 对照显示不同扫描范围，不将展开诊断指到原注解行。所有变体/版本/构造器及完整项目/来源/任务门禁仍缺，6.3 不勾选；见相邻 tests/acceptance/checkstyle-comment-variants.md。
  原生身份歧义纠偏：共享自定义 ID 的不同 Checkstyle 模块、重复默认检查来源或重复属性在局部配置识别中进入待解析，不挑先/后值、不制造源码违规。新增共享 ID 断言先失败；不同 ID 的相同检查类保持可用。真实 CLI 验证共享 ID 无活动 finding，独立 ID 后显示原生三条注释诊断。规则/义务与批准身份、完整配置/项目/任务门禁仍缺，6.3 不勾选，见相邻 tests/acceptance/checkstyle-rule-source-ambiguity.md。
  Checkstyle 正式局部命令进展：lint java --checker checkstyle 显式选择 Java/JAR/原配置，受支持静态注释配置进入私有快照与 runtime 服务，缺前置/未知上下文结构反馈；无默认规则替换，脚本缺隔离拒绝。公开反馈 0.1.0 保留原 source/位置/严重度，工具/覆盖/交付仍未核验。真实 binary 1 项通过，8 项命令/Javadoc/配置回归通过，两份实际 schema 正例及 4 个虚假权威反例通过；完整 check/project/任务门禁与其它配置仍缺，6.3 不勾选，见相邻 tests/acceptance/java-checkstyle-cli-local.md。
  Checkstyle 输入绑定进展：新增独立请求/结果与 Rust runtime 服务，精确四个不同物理输入摘要前后复核，缺失/额外/别名/变更不形成完整结果；新鲜报告、范围/退出与共同预算取消接线。模拟反例与真实 Checkstyle 10.21.4/Java 21 缺类型注释/修正两轮通过。完整 JDK/配置引用资源闭包、网络隔离/快照与项目归属及正式 CLI/任务门禁仍缺，6.3 不勾选；见相邻 tests/acceptance/checkstyle-input-bound-probe.md。
  Checkstyle 结果进展：Rust 结果判定绑定独立版本/冻结完整文件列表/正常退出，报告或范围异常不当源码违规；warning/info 退出零仍保留，Unix 错误计数低八位不抹去 256 条诊断。四项契约及真实 error/clean/warning 三轮通过；尚未绑定原项目身份/配置或正式 CLI/门禁，6.3 不勾选，见相邻 tests/acceptance/checkstyle-exit-scope-coherence.md。
  Checkstyle 真实验收进展：固定官方 10.21.4 自包含测试 JAR 与本机 Java 21，经统一 runtime 新鲜报告/私有日志/共同截止调用。配置缺 DOCTYPE 先导致无报告失败，纠正为制品内置映射的标准 DTD 后，公共类型、自定义方法 ID、缺 @param/@return 与补全文档两轮通过。制品摘要仅本地观察，真实项目原配置/范围/身份绑定、完整注释变体与生产任务门禁仍缺，不勾选；验收详见相邻 tests/acceptance/checkstyle-native-command.md。
  Checkstyle 参数进展：新增 CheckstyleCommand 固定 Java -jar/原配置/XML/独立报告/单文件参数，路径冲突与控制字符拒绝。显式 10.21.4 原生正反例测试入口有截止/回收/清理；核对该版本 XMLLogger 确认自定义 source 仅输出 ID，不能套新版类名#ID。命令 2 项、解析 6 项通过；因本机未发现 JAR，真实测试未执行。生产 runtime/配置及任务门禁仍缺，6.3 不勾选，见相邻 tests/acceptance/checkstyle-native-command.md。
  Checkstyle 解析进展：新增 Rust 有界 XML 纯解析，保留完整 source/自定义模块 ID、原生严重度与文件级零行/可选列；exception 和根级无文件事件不转换为源码规则违规。坏版本、未知结构、重复文件、DTD/编码/数值与规模异常均未完成；零诊断仍保留文件列表，不授予覆盖权威。测试为协议夹具，真实 Checkstyle 执行和正式配置/任务/白名单/门禁未接通，6.3 不勾选；见相邻 tests/acceptance/checkstyle-xml-observation.md。
  执行方式纠偏：明确 Maven 上下文时只调度原 POM 多文件探针，不再先运行孤立单文件 JDK；Maven 不适用/前置缺失保持具体未完成，不回退。真实 First 引用 Second 样本先复现无关单文件 native_execution_incomplete，再用同一 Maven 多文件警告/干净两轮验证；模拟缺前置时 JDK 哨兵不启动。反馈升级 0.23.0、Javadoc 0.3.0，区分模式/检查器；旧 0.22 schema 保留。两份实际原生报告及混合模式反例通过。生效模型/依赖类路径/生成源码/任务门禁仍缺，6.3 不勾选，见相邻 tests/acceptance/javadoc-project-mode-selection.md。
  进行中：相邻 Rust CLI 已增加 `lint java FILE --checker javadoc` 的 JDK 21 原生单文件局部诊断，已知 doclint 缺失注释/参数/返回规则可展示，未知输出和缺失类路径保留未完成；真实 JDK 正反例见 `codeguard-cli/tests/acceptance/java-javadoc-cli-native-local.md`。项目生效配置与完整源集绑定、Checkstyle 原生执行、生成代码范围验证、任务和门禁接线仍缺，6.3 保持未完成。
  追加进展：`check java` 现只在静态配置确认时调度 `java.javadoc`，把 JDK 21 单文件原生诊断显示到 JSON/human；无配置不自动变成必需检查。真实最小 Maven 项目有缺注释正例，见 `codeguard-cli/tests/acceptance/check-java-javadoc-partial.md`。它尚未执行 Maven Javadoc 插件生效生命周期、解析完整项目类路径、同步 Javadoc 任务或签发门禁，6.3 仍未完成。
  Maven 原生输出研究：Maven 3.9.16/JDK 21/Javadoc Plugin 3.12.0 的真实项目在 `failOnWarnings=false` 时 `BUILD SUCCESS` 仍含缺注释警告；设为 `true` 则失败且保留同样诊断。Rust 有界解析器已用两种原生结果和未知/额外错误反例验收，见 `codeguard-cli/tests/acceptance/maven-javadoc-native-output.md`。同一目录再次运行可能复用文档产物，正式项目执行器及本轮快照证明仍缺，6.3 不勾选。
  干净日志反例：完整注释项目的首轮与同目录重跑日志都可只显示 `BUILD SUCCESS`，无法从日志区分本轮生成或旧产物复用。Rust 解析器将这类输出标为 `CleanLogUnverified`，未知警告/失败仍为 `Incomplete`；真实 Maven 两轮和反例测试已通过。正式项目执行器必须另证隔离快照、产物及配置身份，6.3 继续未完成。
  多文件原生进展：`check java`/`check all` 在显式 Maven/JDK 21/离线仓库与树摘要下，对**简单静态 POM**使用私有源码及原 POM 快照运行 Javadoc Plugin 3.12.0；父 POM、profile、依赖、模块、扩展、其它插件或动态配置会在执行前返回不适用，不再以固定 POM 生成配置外诊断。真实两文件违规及修正后干净样本均经 CLI 复跑，原 POM 摘要已绑定；结果单列为局部多文件探针，固定 `project_checker_attribution=unverified`、`coverage_proven=false`、交付未评估。生效模型、类路径、生成源码及完整源集仍未证明，见 `codeguard-cli/tests/acceptance/maven-javadoc-multifile-probe.md`；6.3 不勾选。
  修复指引进展：Checkstyle 局部反馈 0.2 从原配置精确映射自定义 ID 到四类检查类，给出中文规则摘要、官方依据、修复方向和原输入复检参数；未知来源不发布 finding，重复映射不猜测。普通及真实 10.21.4 回放通过，旧 schema 保留；完整项目配置、任务关闭、批准来源和门禁仍缺，6.3 不勾选。验收见相邻 tests/acceptance/checkstyle-repair-feedback-binding.md。

  字段注释进展：原生 JavadocVariable 及其 scope/excludeScope/ignoreNamePattern 原参数进入精确绑定，复用反馈/稳定任务/原工具复检；17 项适配回归和真实三轮字段回放（24.99 秒）通过，实际字段记录及简报 schema 通过。仍缺完整 Java 规则/配置模型/覆盖与批准，6.3 不勾选，见相邻 tests/acceptance/checkstyle-field-javadoc.md。
  字段范围进展：增加 JavadocVariable 的静态原 tokens 参数，未知 token/其它模块借用被拒；四个绑定与四个配置回归通过。原工具已确认 public/protected/package/private、excludeScope 及字段 token 边界；仅枚举 token 不删除原生必需 VARIABLE_DEF，固定 JAR 字节码和回放据此修正规格/验收假设，不在 Rust 过滤诊断。完整项目模型与门禁仍缺，6.3 保持未勾选。
  模块名称进展：已支持注释模块接受官方完整名与 Check 后缀短名，使用固定映射保留原 XML/原生 source；未知包名不猜测，重复别名身份拒绝。28 项普通回归和字段四轮真实名称/稳定任务/复检回放（21.95 秒）通过。其它模块/资源/完整生效配置仍缺，6.3 不勾选，见相邻 tests/acceptance/checkstyle-official-module-names.md。
  方法原参数进展：MissingJavadocMethod 的范围、注解、属性方法、长度与名称排除按本版原参数执行；跨模块及无效静态值拒绝。19 项普通回归、真实四组配置回放（19.03 秒）通过，零诊断不关闭任务。单行非空方法行数边界由固定 JAR 核对并修正夹具假设，不修改原生判断；完整方法/构造器及项目模型仍缺，6.3 不勾选。见相邻 tests/acceptance/checkstyle-missing-method-properties.md。
- [ ] 6.4 实现 Java 安全静态检查及 CVE 依赖图适配；验收：真实安全/CVE 样本、坏报告、库过期与模糊匹配分开记录。
  解析器进展：相邻 Rust adapter 已按 OWASP Dependency-Check 官方 JSON 1.1 模板提取活动/原生抑制漏洞、来源、分数和包标识；缺必需数组、重复 JSON 键、分析异常或畸形漏洞拒绝。只得到局部报告事实，未调用原生 checker、核验库时效或绑定 Maven 图，6.4 保持未完成。见 `codeguard-cli/tests/acceptance/owasp-dependency-check-json-parser.md`。
  归属候选进展：相邻 Rust adapter 只在唯一 Maven PURL 与依赖图唯一非根节点的 group/artifact/version/type/classifier 完全一致时给出候选；缺失、冲突、未知限定符、私服 URL、版本不符或图中重复节点分别保留未归属。尚未核验真实制品摘要、原生扫描范围及数据库时效，也未接入 `check java`，6.4 不勾选。见 `codeguard-cli/tests/acceptance/owasp-maven-attribution.md`。
  字节身份补强：相邻 Rust adapter 增加 OWASP 报告 SHA-256 与 Maven 节点制品摘要的逐项比较，缺失、损坏和冲突各自保留；相同坐标不再足以构成制品相同的候选。CLI 的 Maven 离线图探针现为可定位的普通制品记录本轮 SHA-256。尚未认证 OWASP 与 Maven 同轮来源、仓库批准身份及漏洞库时效，6.4 保持未完成。见上述归属文档与 `codeguard-cli/tests/acceptance/maven-dependency-tree-check-java.md`。
  原生局部接线：`check java`/`check all` 已为静态配置的 OWASP Maven 插件建立 `java.cve` 任务，在固定版本的简单原 POM 与私有离线数据库副本中调用原生 goal 并解析 JSON 1.1；human/JSON 反馈展示脱敏 advisory、UNKNOWN 分数和原生 suppression。缺数据库、坏报告、POM 复杂、项目身份错配或数据库变化保持 incomplete。模拟 Maven 正反例通过；尚未以真实 OWASP/合格数据库验收，也缺可信时效、图/制品同轮绑定和正式门禁，6.4 不勾选。见 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`。
  同轮候选接线：同一 `check` 调用中的 OWASP 与 Maven 图报告现在按相同构建根、POM、Maven/JDK、仓库摘要交叉核对，再逐条复用坐标/制品摘要匹配器；结果写入 `attribution_probes` 并进入 human/JSON 反馈。模拟双插件原生报告的摘要一致、摘要不一致和私服 PURL 脱敏反例通过；这仍只是本地候选，数据库时效、真实原生工具和可信门禁未验收，6.4 不勾选。
  持久修复路径进展：已初始化项目中的 `check java` 现在保存 CVE 局部报告、自动同步，并把数据库时效未知或原生执行未完成写成稳定环境/证据 blocker；同一问题重复扫描只保留一张任务，内容被篡改的已消费报告不能重新导入。未经核验的 advisory 不伪装为已确认源码 finding，任务给出原工具复检和库核验步骤。真实库与可信门禁仍缺，6.4 不勾选。
- [ ] 6.5 实现 build 等级和测试执行声明；验收：默认静态构建不谎称测试通过，要求测试的策略不可自动跳过。
- [ ] 6.6 接入 Java 完整义务与影响闭包；验收：verify 未绑定质量任务、自定义 echo、50/51 文件、未修改调用方失败均不假通过。
- [ ] 6.7 用代表性 Java 项目完成 check java/check all/doctor/修复前后对照；验收：每条旧新差异人工裁定并有产物引用。
  进行中：`lint java FILE` 已把单文件原生 P3C 诊断接至 CLI；`check java/doctor`、真实多模块项目及修复前后全量人工裁定仍未完成。单文件证据见 `codeguard-cli/tests/acceptance/java-p3c-cli-native-local.md`，不勾选。
  后续进展：`check all` 已接隔离 P3C 单文件探针，并以最近 Maven 构建根限制配置归属；本机真实 Maven/JDK 21 离线扫描使违规规则进入统一反馈。局部稳定任务与原 Maven/P3C 复检已接通，十个声明规则集中的命名/作者注释两条有真实正例。`check java` 局部入口也已用真实 Maven 验证，但 doctor、全规则生效证明、其它 Java 静态检查与代表性项目修复前后差异裁定仍缺，6.7 不勾选。见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。
- [ ] 6.8 识别 Java 依赖治理及 CVE 检查配置并调用已配置的原生工具；验收：区分依赖图/版本/许可证/SBOM 与漏洞诊断，未配置时给智能体具体建议；动态版本、父 POM 或私服不可达不得伪造清洁结果。
  配置反馈进展：`check java`/`check all` 0.10 按 Java 源码最近构建根，把 Maven Dependency、OWASP Dependency-Check 与 FindSecBugs 的静态声明汇总为已声明但未执行、已识别插件缺失或配置未解析，并提供 checker ID 与下一步；多模块混合状态不概括为全项目已配置。Gradle 或 Maven/Gradle 混合根保持模型未解析且不附会 Maven checker ID。FindSecBugs 现在核对完整 groupId/artifactId，避免同名伪依赖误认。原生依赖图接线、CVE 报告解析、漏洞库 freshness、私服/动态版本及受批准义务仍缺，6.8 不勾选。见相邻 `codeguard-cli/tests/acceptance/java-dependency-cve-config-feedback.md`。
  依赖图解析进展：相邻 Rust 适配器已严格解析 Maven Dependency Plugin 3.7+ 的原生 JSON 树，保留传递边并拒绝坏报告；本机 Maven 3.9.16/插件 3.8.1 的离线 JUnit→Hamcrest 样本通过。原生 goal 尚未接入 CodeGuard 运行时或 `check java`，CVE/advisory 与库时效仍缺，不能从依赖图宣称无漏洞，6.8 仍不勾选。见相邻 `codeguard-cli/tests/acceptance/maven-dependency-tree-native-parser.md`。
  原生接线进展：相邻 Rust `check java`/`check all` 0.11 已将静态简单 Maven 构建根的 Dependency Plugin 3.8.1 作为独立 DAG 节点，在私有原 POM 副本中离线执行并反馈依赖图。父 POM、profile、动态版本、外部仓库等重放资格不足时保持未完成；原生 `BUILD SUCCESS` 伴随缺 POM 警告也拒绝当成完整图。真实 Maven/JDK 21 离线仓库的 JUnit→Hamcrest 端到端样本通过；全构建根/生效模型、私服、许可证/SBOM、CVE/advisory 和可信政策仍缺，6.8 不勾选。见相邻 `codeguard-cli/tests/acceptance/maven-dependency-tree-check-java.md`。
  无源码构建根补强：依赖图任务现在按每个静态已配置的 Maven 构建根调度，不因根目录暂无 `.java` 而省略；父根有源码、子根无源码时两者分别保留本轮探针结果。P3C/Javadoc 仍按源码条件执行。两个 CLI 回归样本证实旧遗漏及修复后的待检查范围；多模块生效模型与完整覆盖仍未证明，6.8 保持未完成。
  CVE 报告解析进展：新增有界 OWASP JSON 1.1 Rust 解析器，零漏洞报告与缺失依赖数组严格区分，原生 suppression 和无评分漏洞不丢失，数据源时间原样保留但不自证 freshness。原生调用、图归属、可信数据库与对话反馈尚未接线，6.8 不勾选。见 `codeguard-cli/tests/acceptance/owasp-dependency-check-json-parser.md`。
  图归属局部进展：OWASP Maven PURL 与原生 Maven 图已有独立精确坐标候选匹配器及反例测试；真实调用、制品与数据库身份验证和对话反馈仍缺，不能将候选升级为 CVE 判定，6.8 不勾选。见 `codeguard-cli/tests/acceptance/owasp-maven-attribution.md`。
  制品观察进展：依赖图局部原生反馈 0.2 在已核对的离线 Maven 仓库中读取能精确定位的制品并记录摘要，缺文件或不支持类型保持 null；仓库树在读取后再次核对。与 OWASP 报告摘要的匹配仍只是待认证候选，未执行真实 OWASP 扫描，也未检查数据库时效或关闭 CVE 义务，6.8 不勾选。
  OWASP 局部执行进展：已配置构建根现尝试原生 OWASP Maven goal，隔离复制原 POM 和离线数据库并将报告中的漏洞与失败原因反馈到对话；空报告明列 `empty_report_unverified`，数据库时效固定 unknown，未将坐标/摘要候选自动升级为漏洞门禁。当前仅模拟原生工具验收，真实插件、系统级网络隔离、数据库时效及项目全覆盖仍缺，6.8 不勾选。见 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`。
  同轮归属进展：严格静态 POM 现在允许并列声明固定 Maven Dependency Plugin 3.8.1 与已固定版本的 OWASP 插件，仍拒绝重复、第三方、动态及配置复杂插件。`check_feedback` 0.14 从本轮同根 POM/工具/JDK/离线仓库摘要相同的两份原生局部观察生成逐 advisory 坐标和制品摘要候选；失配与公开 PURL 脱敏均不能得到精确候选。模拟原生双插件、摘要冲突及私服限定符反例见 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`。漏洞库时效、可信来源、完整项目覆盖与真实 OWASP 数据库验收仍缺，不勾选 6.8。

## 7. S07 首批共享生态

依赖：S05；可与 S06 独立推进。覆盖：native-tool-adapters。

- [ ] 7.1 实现 Rust lint/rustdoc/build/依赖与安全义务；验收：workspace/features/targets 和所有 F01–F10 适用场景。
  2026-09-28 Rust CVE 局部进展：相邻 Rust 工程新增 `cve rust [path] --cargo-audit-tool ABS_PATH --db ABS_PATH --format json`，共享受控进程预算调用原生 cargo-audit 的 `audit --no-fetch --no-yanked --json --db ... --file Cargo.lock`。严格 JSON 解析拒绝重复字段、原生 ignore、计数/退出矛盾，逐 advisory 精确对照本轮 Cargo.lock 的包名、解析版本、来源与校验和；公开反馈仅输出来源 SHA-256，不回显私有仓库地址。实际零漏洞与已知 RUSTSEC-2020-0071 漏洞的原生执行均验证；本地数据库 JSON 的提交/更新时间为空，结果固定 `database_freshness=unverified`、退出 3、`delivery_decision=not_evaluated`。该阶段尚未接入 check all、稳定任务/复检、可信数据库及工具/策略、全部 workspace/features/targets，也未覆盖 yanked 治理；7.1 不勾选。见相邻 `codeguard-cli/tests/acceptance/cargo-audit-native-observation.md`。
  统一检查增量：`check all` 现以独立 `rust.cve` 节点调度同一 cargo-audit 局部观察，JSON/human/SARIF 保留原生 advisory 或缺工具/数据库原因。反馈协议 0.29 和中断协议 0.10 新增 `rust_cve`，旧协议原件留存；Rust CVE 类别即使有真实 advisory，数据库时效及可信策略未核验仍为 `observed_unverified`、交付 `incomplete`。这不生成可信白名单批准，也不宣称 Rust 依赖安全通过。稳定任务/复检、可信数据库和全构建组合仍缺；7.1/4.8 不勾选。验收见相邻 `codeguard-cli/tests/acceptance/check-all-cargo-audit.md`。
  工作台增量：已初始化工作区的 `cve rust` 与 `check all` 将局部 cargo-audit 观察绑定本轮清单/锁、工作区和运行 ID 后同步为每构建根一张稳定 CVE 覆盖任务。`next` 给出原工具和漏洞库核验指引；`task verify` 重跑原生工具、保存摘要绑定事件，数据库身份及时效未获可信核验时仍返回 `still_blocked`，任务保持 open。缺工具也生成环境阻塞；该待核验任务排序在可直接修复的源码问题之后，避免挤掉 Clippy 修复。目标普通回归 `check_all_cargo_audit` 3 项及 `check_all_rust_native` 12 项通过，2 项条件忽略；实际复检预览和封套通过 Draft202012 schema。可信漏洞库/工具/规则包、白名单批准及正式门禁仍缺，7.1/4.8 不勾选。验收见相邻 `codeguard-cli/tests/acceptance/rust-cve-workbench-task.md`。
  尝试历史增量：同一 CVE 任务的 claim→attempt ready-to-verify→原工具复检现经目标集成测试；`next` 显示 `still_blocked` 并将无进展计入预算，再一次无改动后要求具体决策，拒绝第三次同动作启动。修复了先前复检已保存但 `next` 不显示 CVE 结论的问题。该链证明局部重复动作抑制，不证明漏洞库合格、漏洞修复、批准例外或正式关闭，7.1/9.7/4.8 保持未完成。
  协议增量：`repair-brief-preview` 0.1 在保留严格 Ruff 分支的同时新增精确 Rust CVE blocker 分支；真实 `next` 复检输出通过 Draft202012，错检查器、伪称 resolved、错范围三类反例拒绝。其它语言简报尚未纳入同一严格 schema，2.2/9.7 的全命令范围不能据此宣称完成。
  2026-09-27 rustdoc适配进展：增加独立Cargo/rustdoc JSON流解析，missing_docs与broken_intra_doc_links保留原生规则/级别/唯一主定位和package/manifest/target归属；重复键、异常结束、歧义定位、未知警告和编译错误保持未完成，不复用只认Clippy的过滤器。7项协议契约、6项依赖边界通过；显式本机Rust1.98.1的原生重放1项实际覆盖缺文档/正常/坏链接/编译错/allow抑制五种输入，通过；相关Clippy -D warnings及fmt通过。公开comments rust、任务/复检、原配置与可信规则来源、完整workspace/features/targets仍未接通，7.1不勾选；详见verification.md及相邻tests/acceptance/rustdoc-native-observation.md。
  公开入口追加：comments rust现经共享runtime执行显式Cargo的锁定离线库目标探针，复用共享预算、私有target目录、SourceSnapshot与独立解析；前后复核清单/锁/已发现源码/工具及源码集合，失配/变化不能标完整观察。human/JSON给出规则/位置、原工具复检和not_evaluated；无工具/坏输入明确未完成，任务接入标not_integrated。4项普通CLI反例、5项入口回归及1项真实Cargo补文档前后复查通过；两份实际反馈通过schema、四种伪造授权/覆盖/关闭被拒；相关Clippy通过。完整配置闭包、可信规则/工具、持久任务/原工具verify及check all接线仍缺，7.1保持未完成。
  文档身份前置：原生范围字段必填并校验真实UTF8切片及行列对应；候选指纹绑定规则/相对目标/原生范围字节，不用行号或列表顺序。同一原生记录可去重，重复声明身份碰撞保留两项歧义观察并置正式ID为空，运行未完成。反馈升级0.2并保留0.1 schema。3项身份契约、6项CLI普通及7项解析回归通过；真实补充与最新静态终态见verification.md。尚非完整符号身份或持久任务接线，7.1/9.7不勾选。
  局部进展：`check all` 在显式提供绝对 Cargo 工具时，经 Rust runtime 离线执行原生 Cargo Clippy 默认 features/all-targets，并从机器报告保留 Clippy 规则与位置；缺工具、坏报告、编译错误和异源路径保持未完成。配置文件存在与 Cargo manifest 分开报告；真实 Cargo Clippy 临时项目已验证。已初始化工作区可将当前 Clippy finding 或缺工具 blocker 同步到稳定任务并在对话反馈返回下一步，项目可写的伪批准文件不隐藏发现。`task verify --cargo-tool` 可再跑原生 Clippy 并写本地复检事件；真实 `#[allow(clippy::needless_return)]` 导致零诊断时，同工具原生 `--force-warn` 对照重新检出并返回抑制待核查；对照损坏或输入身份变化保持 incomplete，两轮均无发现也仅为待策略核验候选，任务不关闭。工具/规则批准、workspace/features 全组合、rustdoc/build/依赖/安全和 Rust 跨组合覆盖完整核验仍缺，7.1 不勾选。
  构建接线进展：`check all` 在同一执行图和共享预算内调用原生 Cargo check，单独保留编译错误与环境阻塞并同步稳定任务；Clippy 修复任务仍优先展示，构建任务可单独读取与原工具复检。反馈 0.28 严格增加 rust_build 和 rust.build 节点，历史 0.27 独立保留；实际报告通过 Draft202012。类型检查不执行测试、不证明 workspace/features/targets 及受批准工具/策略全覆盖，白名单候选不能替代编译修复或门禁，7.1/9.7 仍不勾选。
  Rust CVE F05 增量：`cargo-audit` 在完整匹配的 advisory JSON 后异常退出、超时或其它输出超限时，公开局部报告保留 advisory 及各自未完成原因，并将报告同步到稳定 CVE 完整性任务；损坏 JSON 仍不生造 finding。见 `codeguard-cli/tests/acceptance/rust-cve-partial-native.md`。真实崩溃/超时、单体 stdout 截断恢复、workspace/features/targets 和完整策略仍缺，7.1 不勾选。
- [ ] 7.2 实现 Python（python）Ruff/注释/依赖与安全义务；验收：目标 Python/配置继承/锁缺失解析有真实样本。进行中：Ruff 已有项目 TOML 发现、逐文件原生扫描和公开 `lint python` 局部反馈命令；真实 E501/干净文件共存、排除文件不假通过、根/子目录不同配置各自生效，以及 CLI F401 回报通过；异源 JSON 诊断被过滤且本次标未完成。扫描后源码或配置变化也使受影响文件转为未完成，旧诊断只作待复查证据。命令因尚无完整策略固定返回3，见相邻 `codeguard-cli/tests/acceptance/{ruff-config-discovery,python-lint-scan}.md`。项目全量源集、规则/锁/政策及注释、依赖、安全适配仍缺，不勾选。
  F05 进展：原生 pip-audit 完整报告与本轮唯一 pylock 整组组件匹配后，即使退出异常、随后超时或其它输出超限，也保留 advisory 与故障原因；残缺 JSON 和锁外组件不生成项目 finding。局部报告/工作台仍为未完成和 `not_evaluated`；`check all` 同样保留发现，但异常退出和输出超限的执行节点与类别候选为 `native_incomplete`，见 `codeguard-cli/tests/acceptance/python-cve-partial-native.md`。真实工具、条件环境/依赖组、漏洞库来源及时效和完整门禁仍缺，7.2 不勾选。
  后续进展：局部反馈 0.8 与本地报告 0.7 增加原生逐文件设置观察，真实逐文件 ignore 与伪造规则启用矛盾反例通过；设置观察不证明源码内抑制缺席，不改变退出 3 或 `not_evaluated`，见 `codeguard-cli/tests/acceptance/ruff-effective-settings-observation.md`。
  最新进展：局部反馈 0.9 与本地报告 0.8 增加源码注释抑制原生对照及 `suppressed` 文件状态；真实 `# noqa`、复检与任务持久化反例通过。配置级 suppressions 与其它 Python 检查族仍缺，不能勾选。
  注释类别增量：Ruff 0.16.8 在项目显式启用 D100 时，`check all` 将本轮原生 D100 诊断关联 Python `comments` 候选并给出模块 docstring 修复/原工具复检动作；真实缺文档与补文档两轮证明只有实际诊断才列为已观察，仍为未验证覆盖和 incomplete 交付。未建立全部 pydocstyle/DOC 规则的生效集合、配置级抑制、可信规则包或完整注释义务，7.2 不勾选。
  依赖/CVE 输入进展：新增只读 Python requirements 行级分类与逐构建根锁归属，`detect`/`plan cve python`/`check all` 向智能体说明缺少真实依赖闭包、原生检查器和漏洞库验证；有锁或版本 pin 都不当作漏洞扫描结果。验收见相邻 `codeguard-cli/tests/acceptance/python-dependency-input-discovery.md`。原生 pip-audit 调用、漏洞报告解析/归属、数据库身份及时效、稳定任务与正式门禁仍未完成，7.2 不勾选。
  PEP 751 标准锁进展：`pylock.toml`/单段命名锁作为候选输入被观察，uv/Poetry 专用锁保留独立转换或原生工具选择动作；两类同根并存不任意选一份。该区分只减少错误命令建议，尚无 pylock 语义解析或 pip-audit 原生执行证据，7.2 不勾选。
  pip-audit 协议进展：相邻 Rust adapter 加入标准锁项目模式的固定只读 argv 与当前 2.x JSON 保守解析；跳过的组件、重复字段、版本/退出矛盾、意外修复结果和未关闭的别名/描述输出均拒绝。有效包版本和 advisory 仅形成局部观察，`advisory_coverage=not_evaluated`。六项协议测试通过，见 `codeguard-cli/tests/acceptance/pip-audit-protocol.md`。尚未有本机 pip-audit 原生调用、同轮锁/工具身份绑定、数据库时效或 CLI/工作台接线，7.2 不勾选。
  公开局部探针进展：`cve python` 现可显式选择原生工具/版本，在私有项目副本中复放一份标准 pylock 与 pyproject，使用共享受控进程执行并前后核对原输入、私有副本和工具字节。human/JSON 反馈原生 advisory 或具体准备阻塞，固定 3/`not_evaluated`/覆盖未证明；工具修改私有锁、原生零项与缺锁反例均有 CLI 测试。协议 0.1 见相邻 `codeguard-cli/tests/acceptance/python-cve-cli.md`。使用的是真实进程内核和模拟原生程序，本机 pip-audit、数据库时效、完整 PEP 751 环境/包图、check all 与稳定任务仍未验收，7.2 不勾选。
  锁身份补强：原生报告的整组组件名/版本现在必须与本轮 PEP 751 标准锁显式版本集合一致；锁中无版本包、原生包不在锁中或版本不符均不能成为项目 finding。等价 Python 包名规范化及缺包/错版本反例通过，见同一验收文档。环境 marker、extras、dependency groups、文件哈希及完整有效包图仍未解析，7.2 不勾选。
  锁选择防误报增量：标准锁的顶层环境/解释器约束、非空 extras/依赖组/default-groups 及包级 marker/解释器约束现被识别为未解析选择；已配置工具时仍执行原生审计、反馈原生版本/退出和待归属 advisory 数量，但不把 `[[packages]]` 并集或本轮 advisory 当作实际依赖漏洞。适配器 RED→GREEN 和 CLI 原生进程正例见相邻 `codeguard-cli/tests/acceptance/python-cve-cli.md`。这是拒绝错误归属且保留原工具检查的保护，尚未实现各环境的精确选择与全量扫描，7.2 仍未完成。
  统一检查接线：`check all` 现在按具有可识别 pyproject 的 Python 构建根创建独立 `python.cve.N` 执行节点，复用私有快照原生探针和共享截止时间/取消；显式提供 pip-audit 工具及版本时，human/JSON 逐根显示 advisory，缺工具或缺锁反馈具体准备阻塞。反馈协议 0.30 与中断协议 0.11 新增 `python_cve`，旧协议留存；纯源码无清单继续保留配置缺口。多构建根、缺原生上下文与旧 Python/Rust 混合回归通过；该阶段仍无稳定 CVE 修复任务、复检、漏洞库时效和可信门禁，本机未运行真实 pip-audit，7.2/2.3 不勾选。见相邻 `codeguard-cli/tests/acceptance/python-cve-cli.md`。
  工作台增量：已初始化工作区现把 `cve python` 和 `check all` 的逐构建根观察同步为稳定 CVE 完整性任务；导入前重读工作区、清单与整组标准锁。`task verify` 对任务原构建根再次调用显式 pip-audit，复检事件经 `next` 的摘要和输入身份核对；重复扫描一张任务、双构建根两张任务、同一任务的 advisory→零项复检仍 open 的普通 CLI 回归通过。独立 Draft 2020-12 对实际工作台报告与复检预览通过。仍仅模拟原生程序，缺真实 pip-audit、PEP 751 完整环境/依赖组、可信漏洞源、精确漏洞修复任务和正式关闭/门禁；7.2/9.7 保持未完成。验收见相邻 `codeguard-cli/tests/acceptance/python-cve-workbench-task.md`。
  D100 修复闭环与误报边界：已初始化工作区的真实 `check all` 将 D100 同步为稳定任务，`next` 给出修复指引；原工具复检仍存在与补文档后候选消失均写事件，任务不因勾选或零诊断自动关闭。伪原生报告若声称 D100、但同轮生效设置未启用，则保留诊断并标记 `rule_settings_report_mismatch`，不能变成可执行注释结论。解析器内部保留精确原生启用集合，公开映射与 schema 不变。仍缺正式全量注释覆盖和可信规则来源，7.2/9.7 不勾选。
  pydocstyle 规则族增量：仅将精确 D### 格式且同轮 Ruff 原生设置确认启用并实际检出的诊断归入 Python `comments`；真实 D101 公共类缺文档样本通过。伪报告 D100/D101 若与启用集合矛盾则保留诊断、标记 `rule_settings_report_mismatch` 并取消本地完整结论；D1000 等非精确代码不归类。此分类不宣称完整 D/DOC 规则覆盖、规则包批准或交付通过，7.2 不勾选。
  D101 指引与复检：对话反馈及稳定任务给出公共类 docstring 的限定范围修复步骤；真实 `# noqa: D101` 只产生 `suppression_requires_review`，真正补文档后仍仅 `candidate_absent_unverified_policy`，任务保持 open。全部注释义务与可信策略仍缺，7.2/9.7 不勾选。
  D101 白名单自批反例：工作区自写 `codeguard/decisions/forged.json` 的 `approved=true` 后，真实 Ruff D101 仍保留同一 finding 和唯一 open 任务；`rules whitelist propose` 不生成候选，并将未核对的原生规则映射与批准规则包身份分别列为缺口，human 输出指引核对原规则/工具版本。已有映射的 F401 回归仍保持原待批准状态。当前只有拒绝路径，可信批准来源及真实例外门禁仍缺，4.8/4.9 不勾选。
- [ ] 7.3 实现 Node/TypeScript/JavaScript（typescript）adapter 基础与依赖审计；验收：parser/tsconfig/本地插件和 monorepo 范围正确。
  稳定任务前置：Rust投影绑定相对路径/规则/源码锚点/出现序号，排序去重；行号/原生措辞变化不造新ID，任一定位异常拒绝整组输入。UTF16、CRLF与Unicode行终止符经真实ESLint位置用例核对（0.23秒），四项身份契约及CLI/probe回归通过。报告入队/同步/next尚未接通，不能声称已创建持久任务；7.3/9.7仍未完成，见相邻tests/acceptance/eslint-stable-task-input.md。
  公开入口进展：`lint typescript FILE`显式Node/ESLint入口/版本/原配置/原cwd调用原生probe，human/JSON保留规则/位置/严重度及准备原因；局部反馈0.1.0固定coverage=false、门禁未判定、工作台未接入。23项普通回归与真实ESLint原发现/同配置修复后零诊断两轮35.44秒通过。目录/完整源集、持久任务、TS/parser/plugin/monorepo及依赖仍缺，7.3不勾选；见相邻tests/acceptance/eslint-public-lint-feedback.md。
  原生核心规则验收：发现本机既有ESLint10.11.0缓存，无安装/升级，通过显式Node24.18.0和Rust runtime运行真实clean/warning/error/parser failure/inline suppression/同配置修复复检六轮，104.56秒通过。原生抑制保持待核查，零诊断仅局部一致；不是TS/parser/plugin/monorepo/完整CLI与门禁验收，7.3不勾选。见相邻 `codeguard-cli/tests/acceptance/eslint-native-core-rules.md`。
  发现补充：独立JS/TS无清单也返回配置准备；清单复核变更/不可读（有无flat config四反例）使发现不完整，不能隐藏为未知配置并标画像新鲜。先RED后修正，发现/初始化/端口66项通过。
  配置发现进展：detect/init 接入六种 flat config、旧 eslintrc 和 package.json eslintConfig 的只读线索，保留嵌套配置根及配置字节身份；动态规则、多候选选择、TS loader、旧版本上下文和未观察到配置均明确 unknown，不执行JS或套默认规则。67项发现/初始化/发现端口回归通过，见相邻 `codeguard-cli/tests/acceptance/eslint-static-configuration-discovery.md`；真实逐文件配置、插件/导入闭包、CLI执行和依赖审计仍缺，7.3不勾选。
  受控执行进展：Rust 统一 runtime 接入显式 Node/ESLint 入口、原配置和完整显式输入摘要；版本、私有新鲜报告及执行前后输入校验不一致均未完成。普通启动前反例与实际 Node 受控 JSON 夹具见相邻 `codeguard-cli/tests/acceptance/eslint-input-bound-probe.md`；该夹具不是原生 ESLint，项目有效配置、导入/插件闭包、TS/monorepo、CLI/依赖审计仍缺，7.3 不勾选。
  中断诊断进展：扫描启动后取消/超时分别覆盖已写有效报告与无报告四种受控反例；缺报告加取消曾 RED，现优先保留请求中断，不降级为报告损坏。其它失败分流为报告预检、执行留证和报告读取；不把退出2/无报告解释为源码违规。仍为执行层局部验收，完整7.3不勾选。
  原生命令计划进展：新增 EslintCommand 显式 Node/JS/原配置/源集/JSON 槽位/阈值，以固定字面参数规划，不 Shell/npx/fix/cache/quiet/no-ignore；路径/重复/覆盖及参数预算启动前拒绝。缺 API 先 RED 后实现；四项参数契约通过，真实 Node 24.18.0 经统一 runtime 转发 argv 实测通过（0.05 秒），此为观察脚本，不是 ESLint 原生执行。闭包/物理别名/生效配置/实际 ESLint/CLI/依赖及门禁仍缺，7.3 不勾选；见相邻 tests/acceptance/eslint-native-command-plan.md。
  报告协议进展：新增 Rust ESLint 10 JSON 有界观察，按具体版本/冻结文件与计数解释 0/1/2、max-warnings、fatal/无 ruleId 和 suppression；合法 warning 与部分规则保留，坏范围/版本/重复/计数不自成干净结果。缺 API 先 RED，dot 路径因自动折叠再 RED 后修正；本轮只做协议夹具，不安装或执行 ESLint。CLI/Node 闭包/有效 parser/config/monorepo/依赖和任务门禁仍缺，7.3 不勾选；见相邻 tests/acceptance/eslint-json-observation.md。
- [ ] 7.4 实现 Shell（shell）方言与 Dockerfile（dockerfile）/IaC 基础；验收：zsh 不静默丢弃、Hadolint 与配置安全报告不互相掩盖故障。
- [ ] 7.5 实现 CVE 共享生态映射、依赖归并和数据库 freshness；验收：UNKNOWN/离线/原生缺失/重复依赖均符合规格。
- [ ] 7.6 实现跨生态静态检查配置识别与原生结果归类；验收：注释/API 文档、依赖治理、SAST/秘密/IaC/容器等检查器在已配置时运行并反馈，未配置/无效/不可用分开解释，修复后按原工具复检。

## 8. S08 全语言补齐

依赖：S05，复用 S06/S07 已验收基础。覆盖：native-tool-adapters、language-gate-commands。

每组以 [57 项清单](../../../docs/rust-cli/coverage-and-acceptance.zh-CN.md) 为边界；每个语言必须有六槽位、工具锁、正反例、故障样本、平台与真实验收产物。每个语言分别拆为能力判定、lint/comments、其余类别与验收三项；每项内部有多工具时按实际 adapter 再细拆，不将未完成工具藏在汇总完成状态中。

- [x] 8.1 为 go 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。证据：相邻 Rust `rulepacks/go_static_candidate_v1.json`、`schemas/go-static-candidate.schema.json`、`codeguard-adapters::parse_go_candidate_profile` 和 `tests/acceptance/go-candidate-baseline.md`；六槽均 `applicable/gap`，五平台未验收，旧 Go stable 不升级为新能力；缺槽/重复/虚报实现、格式化器冒充注释、CVE 漏数据库时效及错类别工具反例通过。真实原生适配与验收仍属 8.2/8.3。
- [ ] 8.2 实现 go 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
  原生文件范围进展：Go 普通反馈 0.6 / 源码复检 0.7 / 统一反馈 0.22 增加整组源码摘要；源码复检沿用受控 Go 环境获取 go list JSON，目标 excluded/not_selected 不作为已修复候选，清单失败保持 incomplete；next 和同步在整组源码变化后要求复扫或仅记历史。标签、CGO、平台排除真实反例与普通导入回归通过；完整平台/规则覆盖、注释检测与可信关闭仍缺，8.2 不勾选。
  原工具任务复检进展：`task verify --go-tool ABS_PATH` 现沿用共享预算、租约、尝试绑定和报告事件；Go 0.5 绑定目标源码，反馈 0.4 区分仍存在、同规则身份变化待核对、未发现候选和未完成。next/尝试历史消费同一 Go 事件，模块配置或源码变化后不沿用候选。普通环境复检、真实 still_present/身份变化/修复/编译失败及实际 schema 验证通过；正式关闭/复发重开、完整平台/规则覆盖和可信策略仍缺，8.2 不勾选。
  持久任务进展：Go 子反馈 0.4 / 统一反馈 0.21 绑定 workspace/run 及各模块 manifest/go.sum 字节摘要，lint go/check all 自动保存并幂等同步；next 与 Markdown 任务给出 Go 原工具复扫及环境/策略修复指引。错工作区、位置/模块/计数矛盾或越界拒绝源码任务，源码或模块摘要变化保留历史而非活动发现。真实重复扫描只保留一个任务，修复后同步不自动关闭；Go task verify、完整策略/平台覆盖仍缺，8.2/9.13 不勾选。
  稳定身份前置进展：Go 子反馈 0.3 / 统一反馈 0.20 绑定发现 ID、完整指纹与本轮源码摘要；前置空行保持 ID、不同原生证据/重复锚点分离，模块内位置越界拒绝全部部分发现。原生顺序先排序、同位置同诊断去重。该阶段尚无 Go 持久报告归属、work sync/next/task verify 接线，8.2 仍未完成。
  进行中：相邻 Rust `codeguard-adapters::parse_go_vet_json` 已针对本机 Go 1.23.4 的原生 `go vet -json` 做保守局部解析，真实违规/干净/编译错误样本与坏版本、坏 JSON、越界位置、多包坏块反例通过；`-json` 违规样本退出 0 但 stderr 有诊断，不能以退出码判干净。macOS `/var` 与 `/private/var` 根别名经真实反例修正。解析器本身不证明工具/规则身份、完整源集/build tags/多平台覆盖或 Staticcheck 注释检测；见相邻 `codeguard-cli/tests/acceptance/go-vet-json-local-probe.md`。
  CLI 进展：`codeguard lint go [path] --go-tool ABS_PATH --format json` 已经由 Rust 运行时执行原生版本探测和 vet，离线私有 Go 环境、源码/清单/工具前后摘要及 stderr JSON 解析进入公开局部反馈；真实违规、干净、编译失败和错误工具正反例通过。仍固定退出 3、`not_evaluated`，没有任务同步、受批准策略/工具锁、完整 build tags/平台覆盖或 Staticcheck 注释适配，故 8.2 不勾选。
  范围加固：早期仅执行根模块时曾对嵌套 `go.mod` 返回明确未完成；现已由下一项逐模块执行替代。原生诊断的相对文件若不在本轮已发现和摘要复核的 Go 源码集合中，不产生该诊断对应的 finding。对应 CLI 反例与本机原生正反例通过；完整源集仍未证明，8.2 不勾选。
  多模块进展：局部 CLI 现按发现的 Go Module 根逐一运行原生 vet，记录每模块状态并保留前一完整模块的 finding；双模块真实违规与后续编译失败样本通过。逐模块输入摘要和发现归属复核仍只构成局部观察；build tags/平台矩阵、可信工具与规则策略、注释适配和完整验收仍缺，8.2 不勾选。
  统一检查进展：`check all --go-tool` 复用同一观察服务并纳入共享调度/执行预算、候选类别及 JSON/human/SARIF 局部反馈。缺工具与预算耗尽有明确状态，真实 Go finding 可见但不签发完整通过；持久任务与正式义务、规则/平台证明仍缺，8.2 不勾选。
- [ ] 8.3 完成 go 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.4 为 csharp 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.5 实现 csharp 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.6 完成 csharp 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.7 为 kotlin 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.8 实现 kotlin 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.9 完成 kotlin 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.10 为 swift 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.11 实现 swift 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.12 完成 swift 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.13 为 php 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.14 实现 php 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.15 完成 php 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.16 为 ruby 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.17 实现 ruby 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.18 完成 ruby 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.19 为 scala 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.20 实现 scala 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.21 完成 scala 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.22 为 elixir 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.23 实现 elixir 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.24 完成 elixir 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.25 为 c 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.26 实现 c 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.27 完成 c 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.28 为 cpp 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.29 实现 cpp 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.30 完成 cpp 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.31 为 objc 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.32 实现 objc 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.33 完成 objc 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.34 为 dart 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.35 实现 dart 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.36 完成 dart 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.37 为 vue 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.38 实现 vue 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.39 完成 vue 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.40 为 svelte 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.41 实现 svelte 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.42 完成 svelte 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.43 为 astro 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.44 实现 astro 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.45 完成 astro 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.46 为 css 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.47 实现 css 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.48 完成 css 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.49 为 html 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.50 实现 html 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.51 完成 html 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.52 为 graphql 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.53 实现 graphql 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.54 完成 graphql 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.55 为 solidity 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.56 实现 solidity 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.57 完成 solidity 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.58 为 terraform 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.59 实现 terraform 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.60 完成 terraform 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.61 为 nix 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.62 实现 nix 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.63 完成 nix 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.64 为 sql 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.65 实现 sql 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.66 完成 sql 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.67 为 protobuf 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.68 实现 protobuf 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.69 完成 protobuf 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.70 为 yaml 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.71 实现 yaml 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.72 完成 yaml 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.73 为 markdown 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.74 实现 markdown 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.75 完成 markdown 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.76 为 toml 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.77 实现 toml 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.78 完成 toml 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.79 为 haskell 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.80 实现 haskell 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.81 完成 haskell 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.82 为 ocaml 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.83 实现 ocaml 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.84 完成 ocaml 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.85 为 fsharp 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.86 实现 fsharp 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.87 完成 fsharp 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.88 为 perl 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.89 实现 perl 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.90 完成 perl 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.91 为 groovy 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.92 实现 groovy 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.93 完成 groovy 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.94 为 clojure 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.95 实现 clojure 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.96 完成 clojure 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.97 为 powershell 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.98 实现 powershell 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.99 完成 powershell 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.100 为 zig 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.101 实现 zig 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.102 完成 zig 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.103 为 nim 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.104 实现 nim 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.105 完成 nim 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.106 为 crystal 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.107 实现 crystal 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.108 完成 crystal 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.109 为 julia 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.110 实现 julia 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.111 完成 julia 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.112 为 elm 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.113 实现 elm 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.114 完成 elm 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.115 为 lua 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.116 实现 lua 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.117 完成 lua 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.118 为 luau 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.119 实现 luau 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.120 完成 luau 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.121 为 pascal 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.122 实现 pascal 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.123 完成 pascal 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.124 为 r 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.125 实现 r 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.126 完成 r 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.127 为 cfml 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.128 实现 cfml 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.129 完成 cfml 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.130 为 vbnet 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.131 实现 vbnet 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.132 完成 vbnet 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.133 为 erlang 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.134 实现 erlang 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.135 完成 erlang 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.136 为 liquid 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.137 实现 liquid 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.138 完成 liquid 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.139 为 cuda 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.140 实现 cuda 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.141 完成 cuda 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [ ] 8.142 为 ansible 固化六类别适用性、候选工具/方言/版本及缺口；验收：每个槽位有实际依据，not_applicable 不得用缺工具解释。
- [ ] 8.143 实现 ansible 的 lint/comments 适配与规则；验收：真实工具正确样本和违规样本、错误配置/版本/报告反例通过，格式化不能冒充注释检查。
- [ ] 8.144 完成 ansible 的 dependencies/CVE/security/build 适用能力及整体验收；验收：依赖生态映射和逐类别真实证据齐备，缺口未解决不升级 stable。
- [x] 8.145 为 cobol 保留显式 planned/gap；验收：项目要求该能力时返回未完成，不能用空实现充数。证据：相邻 Rust `planned_language_gaps` 集成测试以 `.cbl` 项目检查六类别、capabilities planned/gap、退出 3 和不生成空义务；见 `tests/acceptance/planned-language-gaps.md`。
- [x] 8.146 为 arkts 保留显式 planned/gap；验收：项目要求该能力时返回未完成，不能用空实现充数。证据：同一测试的 `.ets` 正反例和六类别未集成反馈。
- [x] 8.147 为 metal 保留显式 planned/gap；验收：项目要求该能力时返回未完成，不能用空实现充数。证据：同一测试的 `.metal` 正反例和六类别未集成反馈。
- [ ] 8.148 机器核对最新注册表与全部验收条目；验收：54 个原 stable 六槽位与真实证据完整，3 planned 如实披露，无丢项/重复/别名漂移。

## 9. S09 持久问题与修复工作流

依赖：S02、S03、S04、S05；与后续修复和宿主接入共享本协议。覆盖：remediation-workflow、scan-scope-policy、project-initialization。

- [ ] 9.1 实现 init dry-run/apply 与工作区 schema/.gitignore/受管路径；验收：不覆盖用户文件，不重复建立质量配置，未初始化只用私有用户缓存存原始报告。进行中：相邻 Rust CLI 已提供默认只读预览、精确受管目标预检查和局部 apply，含根 AGENTS 受管摘要；当前 apply 固定 partial/退出3，不虚构完整初始化。准备任务、刷新及私有原始报告缓存尚未接线；见 `codeguard-cli/tests/acceptance/init-workspace-preview.md`。
- [ ] 9.2 实现自有产物精确范围规则与工作区校验；验收：运行副本不递归扫描，codeguard/src 用户源码正常检查，入库 secret 仍阻断。进行中：相邻 Rust discover 已精确跳过自有文件及记录目录，保留 `codeguard/src`；真实 Git index 路径安全预览独立运行，但自有记录内容安全与正式 gate 仍缺。见 `codeguard-cli/tests/acceptance/init-workspace-preview.md`。
- [ ] 9.3 实现 finding/blocker 的稳定身份与重命名匹配；验收：十次相同扫描只有一个问题，行号变化不生成无意义重复，不确定匹配不误关闭。进行中：相邻 Rust CLI 的 Ruff 局部反馈 0.3 产生不依赖行号的 ID/指纹；真实双轮扫描加本地 sync 验证同一发现仅一份 finding/task。重复 finding 的每轮证据现写入忽略入库的 `state/observations/`，避免改动首次事实与无意义审计事件，崩溃重试幂等。局部 Ruff 环境 blocker 以 checker、构建根、原因和范围生成稳定 ID，重复扫描复用任务。Rust Clippy 局部 finding 现按原生规则、目标与源码行内容形成稳定身份；重复扫描只保留一张任务，缺 Cargo blocker 同样稳定。重命名关联、跨工具身份和不确定匹配协调仍缺，不勾选。
  Java/P3C 命名子集现也按原生规则、目标和源码锚点形成稳定 finding，缺 P3C 配置按 Maven 构建根/原因形成 blocker；初始化工作区两次扫描只保留一张任务。仍无重命名关联或不确定匹配协调。
  CVE/Java/Ruff 等现有 blocker 的重复报告逐轮保存到忽略入库的 `state/observations/`，只有首次或复检后再现追加 tracked 事件；重复扫描任务及 tracked 事件均稳定。跨模块公共前置依赖和完整事件状态机仍缺，不勾选。
- [ ] 9.4 实现 run_id 游标、全量未消费报告幂等 sync；验收：先 lint 后 CVE 不丢问题，部分/过时报告不能跨范围关闭旧问题；事件写入后游标写入前崩溃可恢复且不重复，一份坏报告不阻止其它有效报告持久化，整体仍返回3。进行中：Rust `lint python` 在已初始化工作区按 workspace_id 保存脱敏本地报告并自动调用 `work sync`；后者遍历全部未消费 Ruff 报告，先落 finding/event/task 后落 `(workspace_id,run_id,摘要)` 消费标记，重复导入和标记丢失重试不重复任务；旧源码只计历史，坏报告不阻止有效报告，同键不同摘要拒绝。跨类别 RunReport、准备诊断、严格事务和并发协调仍缺，见 `codeguard-cli/tests/acceptance/work-sync-ruff-baseline.md`，不勾选。
  新增 Java/CVE 局部报告 0.3 的自动保存与幂等导入：数据库时效未知和缺工具/库分别生成稳定 blocker，同根重复扫描不创建多张任务；消费后改报告再次同步会显示摘要冲突。CVE advisory 仍只是未核验原生观察，尚不生成源码 finding。跨类别完整 RunReport、崩溃矩阵与可信来源仍未完成，9.4 不勾选。见 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`。
  跨类别恢复验收补充：同一工作区的 Ruff 与 CVE 两份已保存报告在自动同步失败后可由一次 `work sync` 同时导入；一份坏报告不阻止这两份报告，删除两份消费标记后重试也不新增任务/事件。见相邻 `codeguard-cli/tests/acceptance/work-sync-lint-cve-cross-category.md`。任意崩溃点事务、并发及全类别 RunReport 尚未验收，9.4 不勾选。
  坏报告现在按当前字节摘要保存脱敏本地失败收据；`next` 对未改输入返回具体失败原因而非反复建议同步，报告变更后旧收据不适用。收据不构成 finding 或白名单批准。回归仍仅覆盖局部报告队列，9.4 不勾选。
  同工作区 `work sync` 现复用原有跨进程非阻塞文件锁，将本轮报告遍历、fact/事件和消费标记置于同一临界区；锁被占用时返回版本一致的未完成协议，释放后可重试。此测试验证互斥与恢复，不证明完整多进程随机交错、跨平台锁或任意崩溃点事务，9.4 仍不勾选。
  持久边界补充验收：Ruff finding 的任务、fact、本地观察、事件四阶段及 Ruff 环境 blocker 的 fact 阶段均用独立工作区恢复；重放后缺失记录恢复、原字节不变、事件仅一条、消费标记最后出现。此阶段是磁盘中间态重建，实际进程退出验收见下条；磁盘故障和完整多类别事务矩阵仍缺，9.4 不勾选。
  实际进程退出补充：仅单元测试编译的子进程在 Ruff finding 的事件已持久化、消费标记未写时直接退出，父进程复查磁盘并重试，事件不重复且游标恢复；生产构建无故障注入入口。其它阶段、磁盘故障、跨类别多记录强杀与完整 RunReport 仍缺，9.4 不勾选。
  临时写入恢复补充：旧 PID/计数命名的 staging 文件残留曾使 `write_once` 直接失败；现有界换用新的 `create_new` 名字，残留文件原字节不变，目标记录完成。仍未证明磁盘错误/断电和完整事务，9.4 不勾选。
- [ ] 9.5 实现 append-only 事件、父关系、状态机与可重建 Markdown 投影；验收：手改勾选无复检不关闭，缺父/分支冲突触发协调。进行中：Ruff 与 Rust Clippy 初见 finding 写固定 `observed` 事件和任务投影，重复报告不改 tracked 文件；其余事件、父关系校验、完整状态机及投影重建尚未实现，不勾选。
- [ ] 9.6 实现任务依赖与 blocker 归并；验收：多个模块共缺 JDK 形成一个前置任务，各义务仍完整可见。进行中：Rust `work sync` 已将同一 Ruff 构建根、同一不完整原因的多个受影响文件归并成一个 `kind=blocker` 任务，分别保留原路径与观察事件；不同构建根不误合并，见 `codeguard-cli/tests/acceptance/work-sync-ruff-blockers.md`。JDK 跨模块公共前置任务、义务依赖边及跨检查器归并尚缺，不勾选。
- [ ] 9.7 实现 status/next/show 与 RepairBrief/版本化 recipe；验收：给出修复目标、范围、步骤和复检条件，诊断中的指令不可执行。进行中：Python Ruff 局部反馈给出有界修复提示；初版 sync 生成脱敏 Markdown 任务。Rust `next` 已从本地结构化 Ruff fact 生成只读简报，含范围、静态步骤、复检与关闭条件；任务 Markdown 指令不进入简报，缺工具/配置优先指向准备工作。尚无完整 status/show、真实尝试历史、版本化 recipe、租约与复检关闭，因此不勾选，见 `codeguard-cli/tests/acceptance/next-local-brief-preview.md`。
  doctor 复检进展：task verify 已重用原版本诊断和任务租约/尝试一致性，持久化摘要绑定收据；next 与尝试账本识别 doctor 身份。失败仍受阻、未选择未完成，真实 Ruff 恢复仅 environment_restored_unverified_policy，next 指向批准前置及原受阻质量检查，任务仍 open。65 项相关回归及实际协议验收通过；可信义务/正式关闭未实现，不勾选，见相邻 tests/acceptance/doctor-task-verification.md。
  Java/CVE blocker 现也有本地 Markdown 任务和 `java_cve.next` 只读简报，给出构建根、漏洞库/工具检查步骤及带占位参数的复检命令；原生 advisory 未被当作已确认漏洞或白名单批准。`task verify` 可重跑原生 OWASP 并保留局部观察，但正式关闭/重开尚未实现，9.7 不勾选。
  新增局部 `status` 与 `task show` 只读视图：前者从当前受限事实汇总开放任务、待同步报告和下一步，后者复用事实/事件核对展示指定任务的证据、范围、约束、历史和复检，不读取 Markdown 指令。画像/检查 freshness 固定未核验，空任务不称通过；缺完整事件父关系、历史 gate 收据、依赖、关闭状态与版本化 recipe，9.7 仍不勾选。见相邻 `codeguard-cli/tests/acceptance/status-show-local-preview.md`。
  Checkstyle 工作台连接进展：显式 --workspace 现保存摘要绑定的本轮局部观察，复用既有 work sync 稳定任务与事件，next 从最新报告给出规则依据、修复步骤和原输入复检参数；源码/配置变化要求复扫，手工勾选不关闭任务。历史消费按精确字节收据复用，陈旧新报告不导入。task verify、环境阻塞持久化、check all 配置发现与正式闭环仍缺，9.7/6.3 不勾选；验收见相邻 tests/acceptance/checkstyle-local-workbench.md。

  Checkstyle 复检进展：task verify 现接受显式 Java/JAR/原配置，在统一预算和租约中重跑原工具，记录仍存在/暂未检出/规则覆盖待审/未完成，next 与尝试读者识别对应收据。工具身份固定首次观察，连续更换工具不能滚动认可；失败观察记录具体原因，全部保持 open。正式关闭、批准策略、完整配置/覆盖、环境任务与取消端到端仍缺，9.7/6.3 不勾选；验收见相邻 tests/acceptance/checkstyle-task-recheck.md。

  Checkstyle 前置任务进展：显式工作台遇到缺工具/配置/报告问题现保存准备观察并同步稳定 CG-B 任务，next 读取最新具体诊断和受影响范围；不会生成源码 finding，备注/勾选不关闭。后续同范围已消费原生观察只转向核对原选择与批准覆盖，不重复恢复工具；输入变化使线索失效。模块粒度、准备 task verify、完整关闭与宿主 Hook 仍缺，9.7/6.3 不勾选；验收见相邻 tests/acceptance/checkstyle-preparation-tasks.md。

  Checkstyle 准备复检进展：task verify 现支持显式原工具的准备任务复检，保存具体 still_blocked/incomplete 或局部恢复观察，并同步源码 finding；租约失败不执行或落事件，任务保持 open。53 项受影响普通回归、真实 Java/Checkstyle 恢复及实际产物 schema 通过，见相邻 tests/acceptance/checkstyle-preparation-recheck.md。完整义务/批准与关闭仍缺，9.7 不勾选。
  准备尝试预算进展：新增 claim/ready-to-verify/失败复检/事件关联/两轮预算耗尽全链用例。修正失败复检后简报不可修复导致 task_not_actionable 的卡点；当前输入有效时允许前置修复，输入变化仍先复检，预算耗尽返回 needs_decision。29 项相关普通回归及真实 Checkstyle 恢复通过，9.7 保持未勾选。
  恢复交接进展：真实准备尝试的恢复事件关联 attempt，解除 awaiting_verification，环境任务保持 open。复检后 Java/JAR 身份变化现令 next/task show 的旧恢复或缺失观察失效；真实复制 JAR 改动反例先失败后通过（10.28 秒）。批准与正式关闭仍缺，9.7 不勾选。
  反馈原因进展：next/task show 将当前工具/源码/配置失效原因与原复检原因分开；status 摘要不再丢失具体前置诊断。专用简报与状态 schema 更新，17 项普通回归、JAR 改动/删除真实回放（9.77 秒）及实际产物 schema 通过。正式批准与全义务仍缺，9.7 不勾选。
  当前输入优先进展：真实 still_present 反例暴露配置失效被后续旧诊断覆盖为 actionable；next/task show 现先核对工具、配置、已绑定源码变化，再解释旧结果，准备与源码任务共享失效优先级。旧收据保留，当前失效不推荐旧修复方向；相关完整覆盖和关闭仍缺，9.7 不勾选。
  原始配置连续性进展：复检简报从首次摘要绑定报告保留配置身份；同检查类/规则 ID 下增加名称排除后零诊断，连续复检须为 rule_coverage_requires_review，不成为修复候选。原配置恢复并添加文档后仅给局部候选，事实仍 open；真实反例先 RED、修正后四轮通过（40.99 秒），见相邻 tests/acceptance/checkstyle-recheck-config-continuity.md。配置字节变化均需复核，语义等价及受批准策略/正式关闭仍缺，9.7 不勾选。
- [ ] 9.8 实现 claim/heartbeat/release 跨进程租约；验收：同工作区只有一个有效领取者，过期和中断可恢复，不声称跨机器全局锁。进行中：相邻 Rust CLI 已有 Unix 本地跨进程锁、随机 token 摘要、generation、5 分钟期限及基本过期接管；并发四领取者只有一人成功，旧 token 和同名 owner 不能修改新租约；未结束 attempt 阻止 release，过期接管先落唯一 abandoned 事件。verify/fix 绑定、完整崩溃事务与 Windows 实现未完成，不勾选。
- [ ] 9.9 实现 attempt start/finish、动作与 patch 身份、无进展预算；验收：复检前失败/no-change/abandoned 均计数，耗尽后不重复推荐同一动作。进行中：Unix Rust CLI 已有受控 action-id、租约绑定、前后受影响路径摘要、不可覆盖 start/finish 事件、同结果幂等重放和同输入两次无进展预算；`ready-to-verify` 必须有绑定该 attempt-id 的原工具复检才可再次 start，复检仍显示问题/未完成时计入预算，私有报告丢失须重新复检。`next` 展示最近历史并停止推荐耗尽的动作。缺完整 patch/环境身份、跨平台实现、正式 fix 自动登记、可信策略和任务关闭，不勾选。
- [ ] 9.10 实现 task verify 的证据关闭与重开；验收：工具超时、加 ignore、移动到排除目录不自动 resolved，真修复有完整身份绑定；环境任务先确认恢复再重跑原受阻义务，自有验证租约收尾释放、调用方租约保留、错token不启动检查器。进行中：Rust `task verify` 已复用原生 Ruff 路径，对本地 finding/blocker 保存新报告、同步新问题并追加 `verification_observed`；问题消失只给待策略核验候选，fact 保持 open，`next` 对照报告复核候选；Unix 本地版本新增复检自有/借用租约、扫描前错误 token 拒绝、提交前再次核验及结束后自有租约释放，真实 Ruff 0.16.8 样本已覆盖借用场景。Rust Clippy finding/blocker 现复用租约、原生复检、同步与观察事件；真实抑制后原生 `--force-warn` 对照重新检出旧规则并要求抑制核查；对照无效或输入变化不生成修复候选。见 `codeguard-cli/tests/acceptance/task-verify-native-observation.md`、`task-verify-lease-binding.md` 与 `check-all-partial-native.md`。可信策略/覆盖、长操作自动续租、Windows 等价实现、正式关闭和重开仍缺，不勾选。
  Java/P3C 命名子集也能复用原生 Maven 探针、任务租约、局部报告同步及验证事件；原问题仍在为 `still_present`，零诊断仅为 `rule_coverage_requires_review`，配置恢复为 `environment_restored_unverified_policy`。任务仍 open，源码身份变化不产生有效关闭证据。见相邻 `codeguard-cli/tests/acceptance/check-all-java-p3c-partial.md`。
  后续进展：原任务被 `# noqa` 遮蔽时，复检 0.2 返回 `suppression_requires_review`，`next` 指向抑制核查且 fact 保持 open；真实删除违规仍仅是待策略核验候选，见 `codeguard-cli/tests/acceptance/ruff-native-suppression-observation.md`。
  再次补充：真实 Ruff 复检中，原 F401 被配置禁用时返回 `rule_coverage_requires_review`，新增逐文件 ignore 时返回 `suppression_requires_review`；两者均不关闭任务，也不把零诊断伪装成修复。逐文件匹配范围和受批准策略来源仍待验收。
  CVE blocker 复检进展：`task verify` 已按任务检查器重跑原生 OWASP Maven，接受与 `check java` 一致的离线 Maven/JDK/仓库/漏洞库参数；报告经 sync 保留新阻塞，事件和尝试历史核对原报告摘要。缺前置条件或漏洞库时效未核验均保持 `still_blocked` 和 open，POM 变更后要求重跑。模拟报告与缺数据库正例见相邻 `codeguard-cli/tests/acceptance/owasp-maven-check-java.md`；真实数据库、可信政策和正式关闭/重开仍缺，不勾选。
- [ ] 9.11 实现 code/dependency/environment/target/policy 的处置归因与例外标签；验收：policy_resolved 不计代码修复，例外保留未解决事实和期限。
- [ ] 9.12 提供受控 fix 的 attempt 与验证事件接口；验收：noop、部分修改失败及并发编辑的事件样本分别记录且不生成假修复；真实 formatter 接线在 S10 完成。
- [ ] 9.13 为插件提供启用后的 scan→sync→brief API；验收：新问题给下一步，重复无 Git 噪声，同步失败保留原 gate 并说明 backlog_update_failed。进行中：初始化项目的公开 Rust `lint python` 已自动保存、同步并在同一 CLI 对话反馈中返回局部 Ruff 简报；重复原生扫描不改 task。`check all` 的局部 Rust Clippy finding/blocker 也能保存、同步并在 JSON/human 对话反馈返回下一步。同步或简报失败仍显示原生结果并分别标明状态，见 `codeguard-cli/tests/acceptance/lint-python-auto-brief.md` 与 `check-all-partial-native.md`。插件 Hook/MCP 接线、正式 RepairBrief/门禁及其它检测族尚缺，不勾选。
  Java/P3C 命名子集现也自动保存、同步并显示稳定 finding/blocker 的下一步；仍为局部观察，不能替代完整 Java 义务或白名单批准。
- [ ] 9.14 验证持久记录隐私、篡改和删除边界；验收：日志默认不入 Git，删除所有任务不影响真实 gate，跨机器无原始日志可重新复检。进行中：Ruff 本地报告/消费标记默认 Git 忽略，tracked finding/task 不含原生消息，所有同步结果固定 `not_evaluated`；跨机器、删除记录和入库内容安全验收仍缺，不勾选。
- [ ] 9.15 实现项目边界与多构建根画像；验收：monorepo、多仓、worktree 和混合语言不会互相覆盖或越界观察。
- [ ] 9.16 定义 project.json/module-graph.json schema 与来源身份；验收：产品/目标/解析/本机版本分别记录，未知值不由其它字段猜测。进行中：相邻 Rust CLI 已产出画像 0.2.0 与模块图 0.1.0 局部 schema、manifest/锁/已识别规则配置摘要及 workspace 内容摘要；`package.json` 包版本另列，语言目标与未探测本机版本保持 unknown，解析版本与完整输入清单仍缺。
  语言目标进展：project profile 0.3 按 Maven/Cargo 清单保留 Java compiler release/source/target 与 Rust rust-version/edition 的 declared_only 值、构建根、清单字节摘要；不生成全局语言版本，不拿包版本或本机版本替代。变量/继承/重复或非法字段显式 unresolved，刷新保留人工备注。旧 profile 0.2 schema 单独保留；有效模型、其它生态与安装版本仍缺，9.16/9.17 不勾选；见相邻 tests/acceptance/declared-language-target-profile.md。
- [ ] 9.17 接入各已实现 adapter 的 manifest/锁/wrapper 静态观察；验收：init 不执行项目脚本，声明版本和已解析版本分别有依据。
  包版本进展：Maven/Cargo 的直接包版本进入已有 package_declared_versions，与初始清单字节 SHA-256 绑定；Maven 不依赖完整 GAV，Cargo 校验直接 SemVer。继承、变量、重复/错类型/非法版本保持 unknown，不冒充语言或本机版本；刷新保留人工备注且幂等，不执行构建器。有效模型、解析版本及其它生态仍缺，9.16/9.17 不勾选；验收见相邻 tests/acceptance/declared-package-version-profile.md。
- [ ] 9.18 实现分类型、带条件和完整性的模块图；验收：聚合不当依赖，动态未知边不支撑缩小检查范围，过期 CodeGraph 不作为当前证据。进行中：相邻 Rust CLI 仅生成有 manifest 依据的 contains 边并将依赖关系标 unresolved；构建依赖、源码引用、条件及 CodeGraph 身份仍缺。
  Maven 图进展：相邻 Rust adapter 在同次清单字节上观察直接模块/依赖声明，init 图 0.2 区分 contains、aggregation 与 declared build_dependency，附清单摘要、scope/条件。完整唯一直接坐标才连本地依赖；变量、父模型、profile、重复坐标、特殊属性和越界/未知模块保留 unresolved。刷新依赖版本会更新图并保留人工任务备注，旧图 schema 单独保留。完整有效模型、其它生态、源码引用和条件解析仍缺，9.18 不勾选；见相邻 tests/acceptance/maven-static-module-graph.md。
  Cargo 图进展：新增同次清单字节绑定的直接成员/path 依赖观察。图 0.3 保留 normal/build/dev 范围，package 重命名核对目标包身份；workspace/optional/target、通配/排除、外部/缺失/逃逸目标保留 unresolved，不执行 Cargo/build.rs。依赖名称变化后刷新移除旧边并保留人工备注。旧 0.1/0.2 schema 单独保留；有效 Cargo 模型/条件解析及源码引用仍缺，9.18 不勾选；见相邻 tests/acceptance/cargo-static-module-graph.md。
- [ ] 9.19 实现多维架构画像与确认任务；验收：domain/controller 命名不自动认定 DDD，文档/源码冲突保留，推断不能激活阻断规则。
- [ ] 9.20 生成 architecture.md 与 AGENTS 精简受管区块；验收：事实/推断可追溯、详情链接有效，不泄露本机路径或凭据，文本指令不被升级为政策。进行中：相邻 Rust CLI 已生成 unknown 架构投影和仅含结构化画像身份/相对链接的根 AGENTS 区块；完整多维架构与来源归属仍缺。
- [ ] 9.21 实现 AGENTS 区块合并和文件身份保护；验收：人工内容、其它工具区块、子目录指令保留，人工修改/重复 marker/并发写入返回冲突。进行中：相邻 Rust CLI 已保留区块外原字节，并验证初始化后新加的人工前后文在刷新时仍保留；拒绝重复/缺失 marker、人工改写及规划后字节变化。外部编辑器不协作时最终比对与替换之间仍有竞态，子目录指令作用域尚未完整验收。
- [ ] 9.22 实现 init 默认 dry-run 与受控 apply 的可恢复事务；验收：无隐式安装/构建/服务启动/Hook接管，第二文件失败不伪称全成功或覆盖用户更改。进行中：相邻 Rust CLI 已预检受管目标、逐文件记录已创建文件/目录并对 AGENTS 再次核对；模拟画像先写而 workspace 标记未更新的中断后可重试完成且重复运行幂等。跨文件恢复日志及完整并发保护仍缺，故 apply 固定 partial/退出3。
- [ ] 9.23 实现输入清单与增删感知的幂等画像刷新；验收：新增模块、锁/规则变化均失效，刷新保留 findings/events/备注。
  进行中：相邻 Rust CLI 已将 manifest、锁文件字节摘要、旧清单精确登记的单文件检查器配置摘要和各语言源码路径集合摘要纳入局部画像；新增/删除构建根、同数量路径替换或上述配置变化可触发受管投影刷新，输入不完整不声称 fresh。点前缀例外仅匹配精确配置名，不扫描其它隐藏源码；配置存在不当作检查器已配置。旧受管摘要与 AGENTS 区块摘要防止覆盖人工修改，workspace 最后更新，findings/tasks 保留。`package.json` 包版本另列，不冒充语言目标版本。24 项 init 契约测试通过。未登记/嵌套规则配置、源码关系完整性、跨进程编辑器锁及中断恢复的更深验收未完成，不勾选。
- [ ] 9.24 生成质量配置映射、测试/环境前置清单及准备任务；验收：缺工具或未知架构不虚构代码违规，不自动增加排除或存量豁免；dry-run 仅返回计划，apply 才持久化任务。
  配置反馈进展：init_plan 0.5 按构建根反馈原生检查器 configured/missing/invalid/unknown、来源、原因和下一步。每条固定 execution=not_run、required_by_policy=null、gate_effect=none，清单明确 partial。JSON/human 同语义，不把缺配置转为代码违规或自动启用工具；旧 0.4 schema 单独保留。批准义务、前置任务持久化与完整 readiness 仍缺，9.24/9.25 不勾选；见相邻 tests/acceptance/init-checker-configuration-feedback.md。
- [ ] 9.25 实现 init_status/readiness/next_actions；验收：仅按适用必需前置条件及有效证据汇总 ready/incomplete/unknown，可选工具不误阻塞；初始化成功不等于 check/gate 通过，给出可继续执行的 doctor/check/sync/next 动作。
  准备任务进展：核心 plan_preparation 将同一 readiness 当前结论投影为稳定准备任务；有效缺失/不兼容/冲突提供不同动作，未知只要求重新核验，不沿用旧诊断。来源未核验、非法/重复要求不产生行动任务；可选/不适用/满足条件不生成修复任务。工作区内任务逻辑键不随绑定变化，步骤/关闭条件固定且无执行或交付授权。可信生产、持久化及 CLI/doctor/next 接线仍缺，9.25 不勾选；见相邻 tests/acceptance/preparation-task-planning.md。
  readiness 领域进展：新增可信要求/观察输入契约与纯判定；当前有效的必需缺失/不兼容/冲突为 incomplete，未探测/未解析/过期/错绑定为 unknown，可选条件不影响结果。集合未完整、无适用必需条件、重复或歧义不能 ready；ready 不替代原生检查。当前只是领域模型，批准义务/原生来源/时钟及 CLI/准备任务仍未接通，9.25 不勾选；见相邻 tests/acceptance/preparation-readiness-domain.md。
  对话摘要进展：init_plan 0.4 在 dry-run/apply 返回同语义 profile_summary（语言/源码清单数量、构建根、逐清单目标与未知状态），human 从相同结构投影并转义路径/字段，避免伪造终端行；不暴露原始清单、本机根路径，不执行工具或生成质量通过。旧 0.3 schema 单独保留。完整 readiness/准备任务/宿主接线仍缺，9.25 不勾选；见相邻 tests/acceptance/init-profile-conversation-feedback.md。
- [ ] 9.26 固化 status历史freshness、next五类disposition及工作区缺失行为；验收：无任务不等于通过，过期结果不显示当前allow，待租用/待决策/待验证各有具体下一步。进行中：Rust `next` 局部查询区分未初始化、待同步、缺配置需决策、缺工具可准备、源码变化需重检和空任务需全量验证；尚无 status 历史新鲜度、租约 waiting、预算耗尽决策及完整五类覆盖，不勾选。
  `status` 现对未初始化、空任务、待同步及开放任务给只读结构化概况，证据 freshness 明示 `unverified`；历史 allow 收据与可信当前性仍未实现，不能据此升级该项完成。
- [ ] 9.27 落实token/generation、action-id、attempt-id、幂等finish及释放恢复；验收：旧owner/token不能写新租约，重复finish不重复预算，未结束attempt正常release被拒绝，报告同键不同摘要拒绝；接管前abandoned/预算写入失败不授予新租约，恢复重放不重复计数。进行中：Unix CLI 已实现同一任务锁下的受控 action-id、随机 attempt-id、generation/token 核对、不可覆盖 start/finish、重复 finish 同结果返回原收据、release 拒绝 open attempt、过期接管先写 abandoned；跨进程崩溃矩阵、写入失败注入、verify/fix 共享租约和 Windows 等价实现仍缺，见相邻 `codeguard-cli/tests/acceptance/task-attempt-local-ledger.md`。
  输入变更加固：ready-to-verify 尝试只在当前任务输入摘要仍等于 finish 时摘要时可认领原工具复检；输入改变则新复检事件无旧 attempt_id，旧尝试不再锁住当前输入的动作或继承旧预算。Rust CVE 锁文件变化反例已由目标集成测试覆盖，相关任务/租约回归通过；真实跨进程竞态、外部工具/漏洞库身份及 Windows 等价实现仍缺，9.27 不勾选。
- [ ] 9.28 实现误报调查任务和 `whitelisted_false_positive` 事件/投影；验收：任务包含原生证据、最小复现、裁定、范围、复检与尝试历史；候选/失效/撤销后重新待处理，决策引用不能自行授权。

## 10. S10 修复能力

依赖：S03、S05、S09 的事件/attempt 接口及对应已验收 adapter。覆盖：execution-kernel、rulepack-governance。

- [ ] 10.1 实现 dry-run 计划与隔离副本修复、变化清单；验收：只读请求不改源码，计划包含内容身份与副作用范围。
- [ ] 10.2 实现前置哈希核对和受控 patch 应用；验收：用户并发编辑不被覆盖，路径逃逸不执行。
- [ ] 10.3 实现同策略复检和修复归因；验收：noop/失败后部分修改/复检器副作用分别呈现，不虚报 fixed。
- [ ] 10.4 将依赖升级和规则调整分开；验收：修 CVE 不自动放松阈值，修 lint 不关闭规则或更改测试真值。
- [ ] 10.5 实现fix的task/owner/token接入及租约所有权；验收：复用已领取任务不重复attempt，批量租约冲突在应用前失败，dry-run不消耗预算，verify关闭原问题时仍保留新发现。

## 11. S11 宿主与分发接入

依赖：S02、S03、S09，至少 S06/S07 已可真实运行。覆盖：hook-protocol、binary-distribution。

- [ ] 11.1 构建候选平台二进制，固化 ABI/MSRV/签名身份/校验清单；验收：各 target 运行 smoke，未测平台不标 stable。
- [ ] 11.2 实现插件 runtime lock 和原子下载/切换；验收：摘要不符、缺二进制、离线均无静默 Python fallback。
- [ ] 11.3 实现 MCP 相同核心 API 与版本化兼容工具；验收：F22、凭据脱敏与超时/取消正确。
- [ ] 11.4 更新五类宿主入口及 hooks/__protocol__.md 的旧新模式表；验收：保存反馈与严格交付区分，skipGate/env 不能降级新模式。
- [ ] 11.5 实现真实 Git pre-commit/pre-push 与 CI 入口；验收：alternate index、多 ref、非 HEAD、未知 Shell 边界正确，remote参数/stdin及ci input schema显式验证，不默认HEAD或由input自授策略权威。进行中：Rust CLI 暴露 `gate pre-commit` 的真实 index 路径安全预览，固定 3/incomplete，不是可放行的完整 Git Hook；见 `codeguard-cli/tests/acceptance/git-index-safety-preview.md`。
- [ ] 11.6 在独立 codeguard-skills 源仓更新调用与修复指引，再按 vendor 流程同步；验收：不直接编辑受管副本，不建议规避门禁。
- [ ] 11.7 明确 legacy 弃用与安全回滚路径；验收：旧数字保持，但旧通过不能被新 CI 认证。
- [ ] 11.8 完成macOS arm64候选制品和平台适配验收；依赖11.1/11.2；证据：真实启动、进程树/取消、路径/私有权限、原子写入、离线能力和代表性工具，未支持项明确gap。
- [ ] 11.9 完成macOS x86_64候选制品和同一平台验收清单；依赖11.1/11.2；验收：不能用arm64或仅交叉编译结果替代目标平台运行证据。
- [ ] 11.10 完成Linux x86_64候选制品、libc/最低系统约束和平台清单；依赖11.1/11.2；验收：固定实际目标环境，不把一种libc通过泛化为全部Linux。
- [ ] 11.11 完成Linux aarch64候选制品、libc/最低系统约束和平台清单；依赖11.1/11.2；验收：本平台真实工具/取消/隔离证明，不复用x86_64成功声明。
- [ ] 11.12 完成Windows x86_64候选制品与平台清单；依赖11.1/11.2；验收：Job Object、特殊路径、文件共享/权限和取消真实运行，不用Unix测试替代。
- [ ] 11.13 完成Codex宿主命令/MCP/保存反馈/Git阻断及恢复验收；依赖11.2–11.5与S09/S10；证据：实际绑定版本、原始请求及返回、scan→sync→brief链，不以安装缓存替代运行。
- [ ] 11.14 完成ZCode宿主同一接入清单；依赖11.2–11.5与S09/S10；验收：按其真实协议映射、不透传新CLI退出码，无法阻断的入口如实披露并验证真实Git/CI接入。
- [ ] 11.15 完成Kimi宿主同一接入清单；依赖11.2–11.5与S09/S10；验收：实际调用二进制、失败可恢复、任务链闭合，不以其他宿主通过代替。
- [ ] 11.16 将配置探测与原生检查结果反馈到 Codex/ZCode/Kimi 智能体对话；验收：已配置检查器、未配置项、有效诊断、工具故障、修复建议和复检命令清楚可见；backlog 同步失败仍显示本次结果，原始工具文本不能作为智能体指令。进行中：相邻 Rust `conversation_feedback` 已从结构校验后的 RunReport 生成 JSON/human 状态、规则 ID、可用的位置、未完成原因与复检 argv；`lint python` 把真实 Ruff 扫描配置、诊断、故障及 backlog 同步状态渲染成 CLI human/JSON，存储失败仍显示原生 finding，均排除原始工具文案；见 `codeguard-cli/tests/acceptance/{conversation-feedback-baseline,python-lint-scan,work-sync-ruff-baseline}.md`。可信来源绑定、完整规则解释与三宿主自动对话接线未完成，故不勾选。

## 12. S12 质量评测与验收

依赖：S08、S09、S10、S11。覆盖：全部十一个规格能力。

- [ ] 12.1 全量执行 F01–F26 适用矩阵与 schema/协议 golden 测试；验收：必备场景零假通过、零工具故障误判。
- [ ] 12.2 冻结分层语料、oracle和统计门槛，划分独立holdout；验收：样本/来源/裁定与批准阈值可追溯，不为提高结果改动holdout；计算器由12.10实现，实际评测由12.11执行。
- [ ] 12.3 完成真实旧新对照及人工差异裁定；验收：历史错误不作为新 oracle，兼容回归与意图纠偏分开。
- [ ] 12.4 测量冷/热启动、p50/p95、内存和并发；验收：覆盖与 findings 等价后再比较性能，不以跳检提速。
- [ ] 12.5 执行策略弱化、缓存污染、错误快照、报告缺项和修复越界测试；验收：本地边界如实记录，受保护 CI 不接受未批准策略；项目脚本无法改写可信政策、工具锁或签发收据。
- [ ] 12.6 Codex/ZCode/Kimi 各做真实命令、MCP、保存与 Git 阻断流程；验收：绑定预期二进制，失效场景不能假通过。
- [ ] 12.7 完整运行发现→同步→next→attempt→修复→verify→关闭/重开→全量 gate；验收：跨类别报告不丢失、失败可恢复、耗尽重试不逃逸、任务勾选或清空不改变真实门禁。
- [ ] 12.8 完整运行项目 init→AGENTS 读取→准备任务→检查→修改构建输入→画像刷新；验收：混合语言、版本冲突、架构未知与人工内容均处理正确，初始化不签发交付认证。
- [ ] 12.9 按 C01–C36 建立逐命令验收矩阵；验收：合法/非法参数、格式、操作退出码、副作用、未初始化、取消/重放/恢复及核心服务复用均有证据，MCP请求失败与服务生命周期分离。
- [ ] 12.10 实现分层评测计算与证据不足判定；依赖1.4、12.2的语料/阈值冻结产物；验收：TP/FP/FN、Wilson区间、零分母、争议样本和覆盖差异有已知期望值，不能以零finding报100%准确。进行中：相邻 Rust Core 已实现纯分层计算与相关正反例，见 `codeguard-cli/tests/acceptance/quality-evaluation-baseline.md`；尚未接入经批准冻结的 oracle/阈值与真实回放，不能勾选。
- [ ] 12.11 建立并执行确定性离线回归、独立holdout与真实工具/漏洞库评测的分离入口和报告归档；依赖12.2、12.10；验收：按语言/类别公布n/TP/FP/FN/区间及库身份/freshness/日期，网络波动不污染离线oracle，性能比较先证明发现/覆盖等价，不自动创建云定时任务。
- [ ] 12.12 完成误报白名单正反例与全格式门禁验收；验收：用户指出误判后能沿同一稳定 finding 完成原工具复核、候选、独立批准、再次检查与对话反馈；精确命中为 allow_with_exceptions、真实阻断为 deny、工具/覆盖未完成为 incomplete；过期/错文件/错内容/错版本/自批/原生 suppression 均不放行，原始 finding、审批引用及到期提示在 CLI/MCP/Hook/SARIF 一致。

## 13. S13 发布、文档与规格收敛

依赖：S12 通过且获得相应发布授权。覆盖：binary-distribution、全部规格。

- [ ] 13.1 对照全部 requirement/scenario/tasks 建立最终证据索引；验收：缺证据的项目仍未完成，不为发布删除要求。
- [ ] 13.2 完成 Rust fmt/clippy/tests、工具链回归、插件既有适用测试、vendor 离线与在线检查、OpenSpec strict；记录真实结果。
  2026-09-27终态补证：依赖边界修复后的同一轮Rust全工作区测试退出0，149组、880通过/0失败/91忽略；fmt及all-targets Clippy在同一源码状态此前通过。旧插件unittest运行632项（621通过、11跳过），独立协议集142通过/0失败/1跳过，旧注册表/架构/Ruff及OpenSpec strict均退出0，vendor离线/在线已有终态。详细证据见verification.md及相邻Rust工程tests/acceptance/workspace-regression-20260927.md；忽略/跳过不算通过，旧协议模拟不证明新Rust宿主接线，MSRV与跨平台/完整工具链矩阵仍未验收，暂不勾选。
- [ ] 13.3 形成 release notes、CLI/策略迁移指南和实际能力矩阵；验收：候选、stable、planned 与未验证平台表述一致。
- [ ] 13.4 发布并逐层核对源码/tag/制品/插件 lock/market/installed runtime；验收：版本及摘要闭环，不以本地成功替代安装证据。
- [ ] 13.5 完成受保护 CI 与已安装三宿主的最终运行复核；验收：实际检查链全部可追溯且未发生自动降级。
- [ ] 13.6 只有全部实施验收完成后 sync/verify/archive 本 change；保留本次设计验证与后续运行验证的独立记录。
- [ ] 13.7 对照实施覆盖索引验证规格、命令、语言、平台、宿主和任务的双向追踪；验收：没有无任务需求或无依据任务，新增设计同步索引，证据缺失仍保留未完成。

### 2026-09-27 ESLint 工作台连接进展（7.3 / 9.7 未完成）

显式 lint typescript --workspace 已通过Rust保存脱敏观察、严格同步并生成稳定finding/七项Markdown任务，对话反馈返回next及next_error。重复扫描保留同一开放任务和用户备注；status/task show可读该任务。已消费历史按原报告摘要收据确认，修复源码后不会重演历史输入导致误报。最新报告、当前输入与首次工具/配置不连续、抑制、未完成或局部零诊断都要求复检；任务文字不改变状态。

配置变化备用指引误选Python的问题由回归先RED确认，现保留ESLint命令和待核验上下文。33项普通相关回归与补充查询联通测试通过，当前feedback0.2及两类简报schema通过；真实原生与最终检查记录见verification。Node环境任务、原生证据完整保留、正式关闭/重开、完整项目/TS插件/配置闭包和门禁仍缺，7.3/9.7不勾选。验收见相邻codeguard-cli/tests/acceptance/eslint-workbench-sync.md。

### 2026-09-27 ESLint 环境任务进展（7.3 / 9.7 未完成）

缺调用上下文、工具/输入不可读及版本/配置/报告未完成现产生独立准备观察和开放环境任务，不伪造源码finding。身份按工作区/当前源码范围固定，重复诊断或原因变化复用任务；外部目标拒绝。next核对最新已消费观察、当前源码及收据，较新同范围扫描恢复后转verification_required，不继续沿用旧故障；human/JSON采用任务步骤。

缺上下文入队测试先RED后通过，相关35项回归及反馈/准备简报schema通过。实际既有ESLint10.11.0拒绝不存在规则的公开CLI测试13.71秒通过：环境任务1、源码finding0、门禁未判定。完整关闭/重开、原生证据、构建模型/跨文件环境归并和宿主门禁仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-preparation-workbench.md。

### 2026-09-27 ESLint task verify 进展（7.3 / 9.7 未完成）

ESLint源码/准备任务现可按显式Node、入口、版本、原配置和cwd运行原工具复检；沿用租约、统一执行截止时间、报告同步和失败尝试预算。缺上下文也保存明确未完成开放事件，不改用其它语言检查器。复检绑定首次工具/配置连续性，仍存在、局部消失、抑制、环境恢复和上下文变化分别处理，始终不关闭任务。next/status/attempt已适配ESLint报告和时间顺序。

入口缺口先RED，57项相关回归加1分类用例通过；既有真实Node/ESLint通过公开发现、任务复检仍存在、同配置修复复扫及任务局部消失四轮194.36秒验收，事件保存，门禁未判定。公开输出schema实测发现统一schema缺ESLint分支并修正，两种task verify反馈通过。完整配置/插件/源集覆盖、可信策略及正式关闭重开仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-task-verification.md。


### 2026-09-27 ESLint 原规则有效配置核查

Rust task verify 增加同轮原生 --print-config 查询，绑定显式源码/主配置/Node/入口前后字节与统一截止时间；只保存规则级别、原因和摘要。复检协议0.2新增effective_rule，历史0.1仍只读识别。规则关闭或缺失时零诊断必须rule_coverage_requires_review，查询损坏/输入变化为未完成，next指向配置核查；不批准白名单或关闭任务。

44项普通相关回归及分类单元用例通过，最终9项规则解析/公开CLI普通测试、目标Clippy -D warnings和fmt通过。既有Node24.18.0/ESLint10.11.0原生启用/off/缺规则三轮38.50秒通过；实际公开CLI只改导入mode.cjs关规则、主配置和源码不变的反例108.38秒通过，仍要求覆盖核查且保存事件，无安装升级。受控CLI实际产物通过统一复检、ESLint复检及简报三份Draft202012 schema；简报lint-only复检ID正则先失败后补入eslint-task前缀。schema产物使用受控协议夹具，不冒充原生工具验收。

完整导入/插件闭包、TS/全项目源集、required规则批准覆盖、可信宿主门禁和正式关闭重开仍缺，7.3/9.7保持未完成。验收见相邻codeguard-cli/tests/acceptance/eslint-effective-settings.md。


### 2026-09-27 ESLint 有效配置查询取消

公开task verify受控进程反例先RED：查询收到SIGINT后，原因丢失并保存成still_present。Rust查询与任务复检现优先保留取消/期限；共享任务入口取消后不保存正常复检事件，并释放自有租约。真实进程组延迟写副作用未出现，再次复检能获取租约。目标用例3.84秒通过，36项相关普通回归、目标Clippy -D warnings和fmt通过。脚本仅为受控协议夹具，不冒充原生ESLint；Windows、跨宿主、中断历史协议及完整I/O预算仍缺，3.3/7.3/9.7不勾选。见相邻tests/acceptance/eslint-effective-interruption.md。


### 2026-09-27 ESLint 项目本地插件原生验收

使用既有Node24.18.0/ESLint10.11.0及项目原flat config加载guard.cjs本地规则。公开lint保留完整workspace/no-debugger ID并生成稳定任务；只修源码后，task verify通过原扫描及原生print-config确认规则仍启用，保存局部消失候选，插件与主配置不改，status门禁未评估。真实测试91.56秒通过，没有安装/升级。

此证据补齐局部本地插件规则穿过公开CLI/任务复检的真实样本，不证明完整插件闭包或可信批准。TS parser/tsconfig、monorepo完整范围、依赖审计、required规则/正式关闭及宿主门禁仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-local-plugin.md。取消路径及本地插件两项增量在同一change跟踪，不同步或归档未完成计划。


### 2026-09-27 ESLint 显式目录调度

lint typescript PATH现支持有界目录清单及逐文件原工具执行，保留排序相对路径、局部反馈、跳过项和未执行清单；共享deadline，前后清单/显式输入变化、单文件失败及工作台保存失败均未完成。codeguard内用户源码照常扫描，点条目/node_modules/链接未选择原因显式反馈。仍使用调用者指定的单一原配置/cwd，不声称自动选择monorepo子配置。

目录入口先RED，配置源码又复现输入冲突及同步路径重复拒绝；现只允许原配置与源码共享同一只读字节身份，报告覆盖/其它输入别名及重复源码仍拒绝。受控样本首次4稳定任务、重复0新增，单文件退出2保留其它发现，链接跳过、100ms共同预算3文件未执行及画像缺失工作台失败反例通过。48项普通相关回归通过，最终目标Clippy -D warnings/fmt通过，公开目录JSON通过Draft202012 schema。实际既有Node24.18.0/ESLint10.11.0公开目录三文件（违规、干净、配置源码）62.34秒验收通过，无安装升级；schema样本是受控夹具，与原生证据分开。

完整TS/tsconfig、monorepo原生源集及配置归属、插件闭包、依赖/CVE、聚合硬I/O预算、原生证据及可信正式关闭/宿主门禁仍缺，7.3/9.7不勾选。见相邻tests/acceptance/eslint-directory-feedback.md。


### 2026-09-27 ESLint 显式子项目配置映射

目录入口新增--config-map绝对路径，1.0有界协议逐项声明项目根/原配置/cwd，组件边界及最深显式根匹配，未命中沿用原参数。不从目录名推断原cwd，不批准规则。重复根/字段、未知字段、越界/链接或不可读配置启动前拒绝，映射与全配置摘要纳入前后及子任务前检查。反馈0.2保留逐文件配置范围和来源及映射摘要，schema仍接受历史0.1。

未知选项先RED；受控a/ab边界、根`.`选择、重复/越界/approved字段及首轮改写映射后停止余下三文件反例通过。45项普通相关回归通过，最终补充根`.`用例及目标Clippy/fmt通过；映射及当前公开反馈Draft202012 schema通过受控实际产物，越界schema反例被拒绝。既有Node24.18.0/ESLint10.11.0真实双项目四文件80.78秒通过，根规则没有强加子项目，保留配置源码检查，无安装升级。

自动配置归属、完整TS/插件闭包/源集、依赖审计、批准覆盖、聚合硬I/O与正式关闭/宿主门禁仍缺；7.3/9.7不勾选，不归档change。验收见相邻tests/acceptance/eslint-config-map.md。


### 2026-09-27 npm原生审计基础

Rust新增npm11/auditReportVersion2有界观察及离线原生命令计划，保留组件、严重度、范围、节点、原生advisory source和间接关系；版本/计数/定位/退出/重复JSON键或error对象不自成干净结果。原生source不是CVE编号，range不是解析版本；依赖类别有重叠，不简单相加。只读package脚本配置API区分明确声明、未观察到、复杂调用和损坏，不执行清单脚本，也不能证明外部CI未配置。

缺API先RED；组件低危但直接advisory高危反例再RED后修正。5项协议/参数/配置用例及9项既有ESLint回归通过，共14项普通测试；CLI目标、adapter库Clippy -D warnings及fmt通过。既有Node24.18.0/npm11.16.0经统一runtime验证版本、空锁JSON及缺锁error，0.68秒通过，包/锁字节不变，无node_modules或脚本副作用，无安装升级。合成advisory是协议夹具，不冒充真实漏洞数据库检出。

配置API尚未接detect/init，公开CVE/依赖命令、非空依赖/真实漏洞、解析版本/图绑定、漏洞库时效、稳定任务/原工具复检及可信门禁仍缺；7.3/7.5不勾选。见相邻tests/acceptance/npm-audit-observation.md。

## 2026-09-27 npm锁文件节点关联进展

新增 Rust v3 普通安装节点解析与原生审计精确位置/名称/版本关联；两项锁文件契约及五项 npm 审计回归通过。链接、别名、缺版本、重复字段和身份不匹配保持未完成。仅协议夹具，不是实际非空依赖审计；依赖边、范围求值、库新鲜度、公开命令及工作台闭环仍缺，7.3/7.5 保持未勾选。验收见相邻 `codeguard-cli/tests/acceptance/npm-lock-binding.md`。

## 2026-09-27 npm离线非空依赖反例

扩展实际 Node 24.18.0/npm 11.16.0 原生验收为私有空缓存的空锁、一个普通依赖节点的非空锁、缺锁三种情况。实验发现非空离线审计也能退出0并返回零漏洞，不能把零发现当成库覆盖或CVE通过。Rust观察新增固定 `advisory_coverage=not_evaluated`，节点关联保持局部身份观察。测试检查清单/锁不变、无安装及脚本副作用；尚缺在线/可信缓存的真实漏洞正例及库新鲜度、完整命令/工作台，因此7.3/7.5不勾选。

## 2026-09-27 npm原生advisory与复检

显式无凭据registry命令API已提供HTTPS根源及验收loopback HTTP源，固定audit-registry、不安装/不执行脚本；受控原生npm执行证实1.2.3被advisory命中、修订2.0.0后同工具复检无发现，503源失败为npm_native_error。两项原生测试通过（0.58秒），六项审计契约、Clippy/格式通过。受控源不是可信库，coverage固定not_evaluated；早期一次原生正例出现未分类错误，已增加诊断而不能宣称稳定性完全证明。真实库/时效、公开命令及完整工作台仍缺，7.3/7.5不勾选。见相邻`codeguard-cli/tests/acceptance/npm-native-advisory.md`。

## 2026-09-27 npm审计配置发现与预览接线

node.npm.audit已按原package.json摘要逐根进入共享发现、init数据来源及detect/plan/check all的配置反馈；manifest重读变更/不可读保留unknown与观察未完成。修复plan按语言筛选遗漏node检查器的问题，typescript/all预览均保留四态；check all人类反馈显示根、原因与下一步。新binary流程与发现/计划/初始化70项不同用例通过，Clippy/格式通过。仍未自动执行npm审计、覆盖其它包管理器/CI声明、库时效、稳定任务和门禁，7.3/7.5保持未完成。见相邻`codeguard-cli/tests/acceptance/npm-audit-discovery.md`。

## 2026-09-27 npm输入绑定runtime服务

新增独立请求/结果及Rust原生版本-audit-报告-锁节点关联服务，冻结精确输入SHA及npmrc存在性；缺身份、版本错配、输入修改/配置新增、取消与超时均未完成、不提供可用于关闭任务的解析结论。三模式反例与八项审计/锁回归通过；真实npm局部服务首轮通过，最终版本参数修改后复验。完整工具/配置/环境闭包、可信库时效、公开命令与任务闭环仍缺，7.3/7.5保持未完成。见相邻`codeguard-cli/tests/acceptance/npm-input-bound-probe.md`。

## 2026-09-27 npm公开CVE局部反馈

Unix `cve typescript` 已接显式Node/npm/版本/用户与全局配置/可选审计源，冻结输入并以human/JSON返回脱敏原生组件、锁版本、严重度、advisory source及下一步。缺上下文给准备状态，局部零发现仍not_evaluated；未接工作台，不假称关闭。10项普通契约、真实binary npm空锁（21.75秒）、两份实际schema报告及四个伪造权威反例通过，Clippy/格式及OpenSpec严格校验通过。真实库、自动check all、完整预算默认来源及持久任务闭环仍缺，7.3/7.5不勾选；验收见相邻`codeguard-cli/tests/acceptance/npm-public-cve-feedback.md`。

## 2026-09-27 npm共享预算默认值接线

公开npm CVE入口复用CLI/登记环境/项目runtime/内置默认值选择器，坏候选项目文件或符号链接在原生执行前返回准备未完成，显式高优先级值不受低优先级坏配置影响。反馈0.2记录预算/来源及native_execution_only，保留严格旧0.1schema。预算、公开命令、发现与输入绑定四项普通测试通过，哨兵未启动；Clippy/格式及OpenSpec严格校验通过。真实命令及实际schema结果后补。硬I/O预算、可信库与工作台仍缺，7.3/7.5不勾选；验收见相邻`codeguard-cli/tests/acceptance/npm-runtime-defaults.md`。

## 2026-09-27 npm稳定工作台与next接线

初始化根中的公开npm审计自动保存脱敏原生组件/advisory/锁版本观察，严格复核输入与字段，经现有同步器创建按根稳定的CVE完整性任务；执行原因作为诊断历史，不伪装源码漏洞或关闭。next识别检查器并给原工具复检步骤。重复扫描一张任务、坏节点/重复字段不产生新任务；反馈0.3及持久观察schema已提供，旧0.1/0.2反馈保留。24项不同普通回归与真实npm公开命令持久化（21.50秒）、实际schema通过，Clippy/格式及OpenSpec严格校验通过。自动check all、早期准备阻塞全覆盖、父工作区映射、npm task verify与可信库/门禁仍缺，7.3/7.5不勾选。验收见相邻`codeguard-cli/tests/acceptance/npm-workbench.md`。


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

## 2026-09-27 Rustdoc强制对照导入身份修正

反例先RED：普通观察合法时，强制对照的伪造指纹及重复输入归属均被旧同步器消费，failed_reports=0。现把复检导入交给独立Rustdoc封套解析：严格检查顶层键与唯一输入路径归属，稳定输入绑定源/目标及清单/锁；普通和强制观察分别进入同一严格原生范围/指纹解析。强制argv及原始证据保留在封套，只在内部核验投影规范化参数，不修改原始报告或将抑制当修复。输入不稳定/当前失配时只导入准备阻塞，不生成源码任务。

同一反例验收三种变体：伪造强制指纹和重复输入被拒，不稳定封套只生成一项重扫阻塞；没有新增源码任务。相关普通回归13项文档CLI、15项同步、6项next，共34项通过；3项默认忽略不算通过。真实Cargo CLI独立1项通过（14.49秒），覆盖正常文档发现/修复复检、原生allow/force-warn和中文链接；相关Clippy -D warnings退出0（7.18秒）。真实报告协议验收另记；schema增加重复行拒绝，唯一字段归属仍由Rust核验。

这是任务复检证据的完整性修正，不是正式批准或关闭；7.1/9.7保持未完成。全工作区未重跑，完整目标仍需持续推进。验收见相邻tests/acceptance/rustdoc-forced-evidence-binding.md。


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

## 2026-09-28 Rust 构建任务的原工具复检与白名单边界

延续既有7.1/9.7/9.4，不新建OpenSpec change。先以已同步编译任务的 `task verify` 返回 `task_checker_unsupported` 作RED；现将 `rust.cargo_check` 接入任务租约、统一截止时间、原生Cargo check、全部已发现Rust源/根清单/锁快照和本轮工具摘要。复检封套 `rust_build_task_recheck` 0.1 与任务、运行和输入绑定；`task_verification_preview` 0.8 保留旧0.7 schema。有效相同错误为still_present，局部零诊断仅candidate_absent_unverified_policy，环境任务仅恢复候选；事件与本地报告持久化并供next/尝试历史核验。保存前重抓输入且拒绝源集变化，报告导入严格复核原生诊断身份。next复检命令指向同一task verify，不自行关闭或批准白名单。

白名单仍按已有规则体系处理：候选/本地决策无门禁效力；原生工具故障、配置或覆盖未完成不能转成误报放行。Rust构建任务的局部复检只提供纠错证据，不证明可信白名单批准、完整构建组合、测试执行或最终交付。受影响普通测试41项（build10、work sync15、next6、task verify10）通过，12项条件性忽略；真实既有Cargo任务复检1项通过。Clippy受影响包all-targets -D warnings退出0；119份schema静态合法性与引用存在性通过。此前910项全量基线早于此新代码，不能作为当前全量证明。7.1/9.7/9.4/4.8/12.12均保持未完成，待可信策略、白名单批准/正式门禁、完整构建目标、任务关闭复发和跨宿主验收。详见相邻codeguard-cli/tests/acceptance/rust-build-task-verification.md。

## 2026-09-28 npm 审计异常退出的局部证据

延续 F05、2.3、5.5 和 7.3；未新建 change。受控 npm 11.16.0 命令输出完整且与锁节点绑定的 advisory 后异常码 2 退出，旧公开反馈丢弃 finding；目标测试先 RED。现严格解析与再次核对输入后保留脱敏证据，原因仍为 npm_audit_execution_incomplete、交付未评估；check all 执行节点为 native_incomplete，不因报告有效而显示任务成功。截断 JSON 反例仍零 finding。同一工作台只维持稳定的 npm CVE 完整性任务，不把局部观察改成漏洞确认或放行。

该阶段目标 npm_audit_cli/check_all_npm、全工作区 cargo test --workspace --offline -q、全目标 Clippy -D warnings、fmt 和 OpenSpec strict 均退出 0。详见相邻 codeguard-cli/tests/acceptance/npm-partial-native.md。此阶段仅覆盖异常退出后的完整报告；超时与输出上限的后续进展见下段。真实 npm 故障、数据库来源及时效及跨语言 F05 矩阵未验收，2.3/5.5/7.3 与总计划继续未勾选。

后续 F05 增量：同一 npm 原生观察现对完整 stdout 报告后超时、其它输出超出共享上限继续执行严格 JSON/锁节点/输入摘要核对；分别保留 `deadline` 和 `npm_audit_output_limit` 及局部 finding，不将零漏洞报告当作未完成执行的干净证明。超时后不跨截止时间持久化；输出超限仍可同步稳定完整性任务，`check all` 节点保持 `native_incomplete`。工具运行中变更或 JSON 截断都不产生 finding。完整 5.5/7.3 与 F05 跨适配器验收仍未完成。
