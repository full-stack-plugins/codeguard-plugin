# 重构证据与能力保留矩阵

日期：2026-09-23。基线 `61e2592`（v0.12.1）。这是**进行中的证据台账**，不是整项目完成报告，也不是新版本发布说明。

## 第一批实际验证

- 改前：275 unittest，4 skipped；ruff 通过。
- RED：CLI/PostToolUse/CVE 的非法 UTF-8、权限故障、超时诊断保留分别失败；Git 门禁与 Dockerfile 执行面追加同类场景也观察到失败。
- GREEN：284 unittest，4 skipped；`tests/run_all.py` 141 通过 / 0 失败 / 0 跳过；ruff、语言 schema（57 项/11 规则）、vendor 离线与在线、本 change strict、diff whitespace 均通过。在线锁仍为 v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`。
- 核心进口隔离：独立 `python -I` 进程载入纯判定与报告，不需要 hooks/MCP/注册表；报告生成不加载 subprocess。
- 旧 `scripts/verdict.py` 与 `gate_lib` 报告符号继续兼容导出。主要检查执行面只调用 `codeguard.execution`，不同入口仍保持各自 timeout 默认值及判定策略。
- 移除了不可达的第二条 Java 执行分支；真实 Java 规划/门禁/MCP 测试仍通过。去掉了未跟踪文件指纹的重复 stat。
- 测试调整不是放宽断言：两个依赖 `run_per_language.subprocess` 私有属性的假进程测试改为真实缺失命令/exit 2；一个只搜索 `_run_one` 源码的超时测试改为真实睡眠超时和主动 exit 124，保留未验证且不拦截的行为断言。

本批尚未 bump/提交/发布。受管技能、lock 和插件专属技能清单无改动。版本与市场发布在整体收敛后执行，不能把尚未完工的源码宣称为已发布新版本。

## 第二批实际验证：计划、环境和架构边界

- RED：Java 规划选择的 JAVA_HOME 没有进入子进程（实际读到 host-jdk）；混合 shell/zsh 的 formatter 已修复文件但没有触发复检（仍返回旧 FAIL）；51 个文件回退全量时把单文件占位符替换成空路径并真正执行工具。三者均由临时项目里的真实 Python 子进程复现，没有 mock 检查器结果。
- GREEN：新增共享 `scoped_plan`、不可变模型和 `execute_plan`。Java 多命令保留 env，第二条失败阻止第三条副作用，父进程环境不变。CLI 与保存 Hook 的修复复检保持原范围，未涉及文件保持原文。空计划、空 delta、无文件列表的单文件命令被拒绝，不产生假 PASS。
- 架构门禁先因缺失失败，再由真实临时源码树证明：内核反向导入 hooks/MCP、纯模型导入 subprocess、函数内隐藏导入、相对/包导入环、新内核模块未声明政策均返回非零；合法依赖和当前仓库返回零。纯模型另用 `python -I` 证明不加载进程或宿主模块。
- 全量：299 unittest，4 个历史 skipped；`tests/run_all.py` 141 通过 / 0 失败 / 0 跳过；ruff、独立架构门禁、本 change strict 通过。语言 schema 57 项/11 规则，vendor 离线/在线及 diff whitespace 通过，受管技能与 lock 保持不变。
- CI 配置增加架构检查；尚无这批代码的远端 CI 结果。CodeGraph 索引仍待授权，未初始化。未 bump、提交、推送或发布；全项目目标保持进行中。

## 第三批实际验证：Git 语法、仓库观察与路径政策

- 先通过隔离 `python -I` 进程观察独立边界缺失，再分离 `git_syntax`、`git_context`、`path_policy`；同一批测试现证明语法和路径政策不加载 hooks、Git 执行器或宿主模块，仓库观察无需 hooks 加入 sys.path。
- 真实临时 Git 仓验证多仓边界、一层解释器间接推送与 `git add -u` 的跟踪文件范围；全量既有测试继续覆盖快照、拟暂存、敏感路径、逃生门和命令替换。`scripts/vendor` 与嵌套 fixture 的例外保持，路径策略只返回诊断，不执行移除建议。
- 消除两份一层脚本读取实现，主 Hook 只判定一次模式；仓库探测复用统一执行器。原 pre_tool_git_guard 和 gate_lib/scope 的 helper/规则常量继续兼容导出。非 Git cd 后回退 cwd 的历史行为尚未修正，已删除错误的 Shell 等价性说明，未将其声称为完整语法支持。
- 历史内联豁免提示测试先解除装饰器在独立进程实际执行并通过，再正式移除 skip；其余三项 pathspec 的旧测试仍待核对，没有为了绿色数量删除用例。
- 最终全量：302 unittest，3 skipped，其余通过；`tests/run_all.py` 141/0/0；ruff、架构依赖/循环检查、语言 schema、vendor 离线、本 change strict、diff whitespace 通过。受管技能/lock 未改。在线 vendor 的最新证明仍为第二批，本批尚未提交，不把它冒充新执行结果。
- `gate_lib` 中的检查应用编排与状态存储尚待分离，task 3.2/4.x 未勾选。未创建 CodeGraph 索引、分支、提交或发布，目标继续进行。

## 第四批实际验证：原子状态、会话归属与已完成事件

- RED：真实 6 进程各写 35 次统计，旧裸读改写只留下 5 次而非 210；同文件在第二个会话被第一会话去重；一个 Stop 消费其它会话统计。初次 UNVERIFIED 后立即保存重试只执行检查器一次；相同硬门禁事件第一次拒绝为 2，第二次却放行为 0。均已用当前测试覆盖并转为 GREEN。
- 本轮复核的 RED：UPS 的损坏 Ruff 配置第一次明确未验证，第二次为空；观察操作抛异常后没有完成式重试接口。先修正测试夹具以只检查 Python（避免 TOML 检查器的正常违规遮盖目标），确认第二次输出被吞，再修改实现。
- `storage` 的稳定旁路进程锁覆盖整个读改写，临时文件 fsync 后原子替换；事务回调或 replace 失败不覆盖旧数据且无临时文件残留。`hook_state` 统一统计、冷却、绕过明细、审计及归属，五个 Hook 进入会话/worktree 作用域。新作用域不猜测旧全局数据归属；无 ID 时兼容共享状态。
- 真实多进程证明 210 次统计/绕过和 210 条唯一审计保留；3 个 writer 与消费方交错时总计 240 次不丢失。真实 Git linked worktree 及两个 session 分别 Stop 各得自己的 1 次。保存未知后立即重跑，第二次执行得到 PASS。
- 硬门禁只重放已完成拒绝，不复用放行；同事件从干净文件变为暂存 F821 后仍得到 2。SessionStart/Stop 只在观察正常返回后登记；异常可重试。UPS 存在 skipped/未知时不登记完成。并发未完成副本可重复运行，不宣称 exactly-once。
- 最终全量：312 unittest，3 个历史 skipped，其余通过；状态专项 10/10；`tests/run_all.py` 141/0/0。ruff、架构依赖/循环检查、语言 schema 57 项/11 规则、vendor 离线和在线、本 change strict、diff whitespace 通过。在线仍为 v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`；受管技能和 lock 未改。
- 验证环境为 macOS/Python 3.13.5。Windows 锁分支尚未实机测试。软缓存内容/配置身份、保存检查期间文件变化、准确快照审计的原仓归属仍待后续任务；本批不宣称全项目或全平台完成。未建立 CodeGraph 索引、创建分支、提交、bump 或发布。

## 第五批实际验证：缓存身份与失效规则

- RED：8 项首批测试中 7 项失败，分别为等长同 mtime 修改继续复用旧 PASS、未来时间戳复用、linked worktree 暂存内容不进键、进程内配置永不过期、保存检查期间新内容被登记为已查、工具恢复后仍返回旧未知、用户配置变化不重跑。追加 UPS 同提示词但源码变化的真实检查也先失败（只执行一次）再修复。
- `fingerprint` 独立采集 Git 内容条目和有预算的文件内容身份，`cache` 校验版本/字段/时间并原子保存完整结果；gate_lib 保留兼容调用点但不实现存储细节。项目配置改为实时小文件读取。UPS 去重纳入输入身份；保存检查前后校验，formatter 后重新捕获输入再复检。
- 缓存专项 16/16：除上述 RED 外，还实测忽略的 Ruff 配置变化、换行文件名、push upstream 变动、无变化软复用/准确门禁重跑、坏缓存格式、预算降级以及外部符号链接/缺失目录不生成身份。工具执行使用真实进程；预算测试只缩小身份采集预算，不伪造检查结果。
- 全量回归曾因旧缓存夹具缓存了“无涉及改动”的 skipped 而失败；将其明确改为实际检查 shell，新增断言无 skipped，保留缓存命中/变化重跑两条原断言。不是允许未知结果缓存来迎合旧测试，也未删失败用例。
- 最终全量：328 unittest，3 个历史 skipped，其余通过；`tests/run_all.py` 142/0/0；ruff、架构依赖/循环、语言 schema 57 项/11 规则、vendor 离线、本 change strict、diff whitespace 通过。在线 vendor 最新实测为第四批，本批受管技能/lock 未改，尚未提交。
- 本机对当前仓库实际采集一次输入身份可用，耗时 0.155 秒；不是性能分位数或大型仓库承诺。预算 10,000 文件名/64 MiB，超限/非 Git/特殊文件时禁用缓存但继续检查。任意外部动态配置、远程依赖和未声明环境仍不是该软缓存的完整建模对象；硬门禁始终独立准确快照。
- 未初始化 CodeGraph、未创建分支、未 bump/提交/发布。task 3.2 门禁应用编排、3.3 注册表/探活、Java/CVE 适配器、协议入口及最终文档发布仍未完成。

## 第六批实际验证：门禁应用、独立结果与原仓审计

- RED：4 项新增测试先失败：隔离解释器无法导入独立 gate 应用；准确快照审计 worktree 为临时目录；基线 exit 2 但输出相似文本仍获豁免；当前检查 exit 2 被基线 exit 1 的相同文本掩盖为存量跳过。均已修复并转 GREEN。
- `gate` 选择检查内容面和汇总；`gate_checks` 返回不可变 GateOutcome/GateDecision；`repository_policy` 管路径安全与显式豁免，`baseline` 管基线复跑，`spec_validation` 管可选 OpenSpec 集成。gate_lib 保留旧导入入口而无重复检查实现。Git blob 快照的二进制协议未改。
- worker 不共享可变备注，不直接写审计；调用线程保序落盘，worktree 为原仓、execution_root 为实际临时目录、session_scope 保留调用归属、cmd 为实际 argv。追加两种不同耗时真实进程证明失败与审计顺序仍按请求顺序。Java 继续复用原项目计划，尚未宣称解析/影响/规划已完成拆分。
- 既有私有 monkeypatch 的迁移明确失败过：7 项 AttributeError/缓存路径错误修复为对实际所有者或低层进程边界注入。没有为测试保留无意义的 shutil/subprocess 业务依赖；公开导入函数仍兼容。run_all 原来未恢复语言检测 monkeypatch，现用显式语言参数与有作用域覆盖，避免污染后续测试。
- 将旧假进程的 rc=2 场景改为真实 Python 后，发现 scope 对包含 `find ` 的任意 argv 注入排除表达式，实际 exit=1 SyntaxError；已限定为 Shell 的 -c 命令体。该真实回归现保持 exit 2 未验证；已有 find 型扫描排除测试全部保留并通过。
- 最终全量：333 unittest，3 个历史 skipped，其余通过；应用专项 5/5；`tests/run_all.py` 142/0/0。ruff、架构门禁、语言 schema、vendor 离线、本 change strict 和 diff whitespace 通过。在线 vendor 最新证据仍为第四批；本批未提交，受管技能/lock 未改。
- 未初始化 CodeGraph、未创建分支、未 bump/提交/推送/发布。注册表/探活、Java/CVE 分层、协议入口整体收敛与最终文档发布仍待完成；原有粗粒度 finding_signatures 的边界仍需最终审计，不将本批未知状态修复夸大为语义等价的完整基线比较。

## 能力保留矩阵（持续更新）

“已有测试”表示可复跑的证据入口，不代表该能力全部边界均已覆盖。

| 能力 | 必须保留的合同 | 已有测试/证据入口 | 后续审计重点 |
|---|---|---|---|
| CLI check | 路径、语言过滤、fix/dry-run、timeout、日志和聚合退出码 | test_mcp_server / test_verdict_integrity / run_all | 每种参数组合黑盒清单 |
| CLI fix | delta/repo、显式全量、项目 formatter 不扩范围 | test_verdict_integrity / test_hardening_fixes | fixed 的真实变更证据一致性 |
| CLI detect / init | 语言发现；init 仅引导不静默安装 | run_all / bin/codeguard | init 帮助与退出码独立 smoke |
| CLI dockerfile | hadolint + Trivy、JSON/文本、安全风险与未验证 | run_all / test_execution_kernel | 原有坏报告/超时疑似假通过，需单独复现并修复 |
| CVE | 五种适配器、别名、阈值、优先级、复扫、JSON | test_cve_boundaries / test_verdict_integrity / run_all | 纯报告/判定与扫描/应用已拆分；30 项边界测试覆盖异常与副作用，在线扫描、实际工具版本与完整依赖覆盖未验收 |
| 四个 MCP 工具 | 官方 stdio SDK、名称/schema、结果信封、实际修复标识 | test_mcp_server（真实 stdio） | 协议和应用服务分离，不引入必须安装的新依赖 |
| SessionStart | PATH、语言/配置/工具盘点、双副本去重 | test_hardening_fixes / run_all | 导入无副作用，版本消息不漂移 |
| PostToolUse | 单文件反馈、EJS/产物过滤、同范围修复与复检、通知 | test_verdict_integrity / test_artifact_awareness / run_all | 原子统计/冷却/去重，真实修改计数 |
| UserPromptSubmit | 意图软提醒、语言子集、非 Git 不扫、逃生门 | test_gate_trigger / test_hardening_fixes / run_all | 软硬策略一致但不同执行权限 |
| PreToolUse | 已支持命令归一化、多仓、拟暂存、HEAD 推送、敏感路径 | test_session_fixes_20260922 / test_verdict_integrity / run_all | 命令意图与仓库绑定类型化，保留能力边界 |
| Stop | 统计/绕过提醒/清理/副本去重 | test_hardening_fixes / run_all | 并发会话互不清空、旧状态迁移 |
| 判定 | 五状态、pylint 退出位、环境错误、方言、基线对比 | test_gate_hardening_usage / test_gate_hardening_batch2 | 签名粒度与基线证据可靠性；不删整项能力 |
| Git 快照 | index/HEAD、overlay、删除/重命名、不更改 index/工作树 | test_verdict_integrity / test_git_staging / test_gate_hardening_batch2 | pathspec 按仓解析、字面路径及真实 index 保持已验证；复杂 Shell、特殊索引环境、批量/子模块/超限边界仍需最终审计 |
| Java | Maven/Gradle wrapper、多模块反向闭包、动态回退、显式命令、默认 skipTests | test_java_project_impact / test_java_boundaries / test_session_pain_fixes / test_mcp_server | parser/graph/planner 与环境/版本观察已分离；真实大型项目、任意动态构建与跨平台未验收 |
| 语言注册表 | 54 stable + 3 planned，配置与文档由单一来源生成 | test_validate_languages_json / test_full_scan_excludes / run_all | 注册表类型和探活职责收敛，不宣称 57 工具链全测 |
| 项目/用户配置 | 原路径、enabled_languages、扩展映射、exclude、scope、timeout | test_session_fixes / run_all | 更新失效、坏配置边界、跨宿主一致性 |
| 审计/去重/缓存 | CODEGUARD_HOME、绕过明细、软缓存、硬快照不复用 | test_cache_identity / test_state_storage / test_hardening_fixes / test_gate_hardening_batch2 | 原子状态与软缓存显式输入身份已实测；任意外部动态输入不在保证内，Windows/大型仓库仍需独立验证 |
| 分发与技能 | 三宿主 manifest、68 个外部受管技能、不可变 lock、模板与文档 | test_plugin_manifests / test_skill_vendor / test_readme_parity | CI/Release/市场/宿主运行分别证明 |

## 第七批实际验证：语言服务与探活生命周期

- RED：旧进程级缓存吞掉工具恢复、保留工具失效前的成功、跨 cwd 复用探测；隐式 `--version` 消费宿主 stdin；非法 UTF-8 导致异常；嵌套构建标记丢失根配置、超过十层找不到项目根。坏 JSON 被当默认配置，坏字段崩溃或静默通过；显式语言 check/fix 可绕过坏配置。真实子进程和临时文件夹复现后修复。
- `registry_schema` 与运行时共用纯校验，重复 ID/非法形状产生诊断；`registry` 单一加载/派生，MCP 不重复读表；`config`、`discovery`、`toolchain` 分离。隔离 Python 进程证明项目发现不加载 subprocess、执行器、hooks 或宿主 SDK。原公开导入和命令路径保留，私有全局探活缓存删除。
- 单轮 `ToolchainProbe` 绑定目标 cwd、stdin=DEVNULL；成功才去重，失败可立即重试，下一轮重新执行。真实计数文件证明两个并行语言共享工具一次执行且下一轮再次执行。新增双进程会合用例先揭示全局锁串行问题，再改为按命令锁：不同工具可并行，相同工具不重复启动。
- 配置覆盖和排除规则热更新、未知 Java 扩展字段保留；坏配置返回 UNVERIFIED，实际 formatter 副作用未发生。真实 MCP stdio 中 check/auto_fix 的坏配置请求明确未验证，修复配置后同一服务继续工作，不需要重启。
- 最终全量 **354 unittest：351 通过、3 个历史 pathspec skipped**；语言服务专项 19/19；`tests/run_all.py` **142 通过 / 0 失败 / 0 跳过**。ruff、架构依赖/循环、语言 schema 57 项/11 规则、vendor 离线和在线、本 change strict、diff whitespace 通过。在线锁仍为 v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`，68 个受管技能及 lock 未改。
- 首轮全量暴露校验器提前返回漏掉已有 severity 诊断、回归脚本遗留变量名；保持原行为断言并修复后重跑，最终结果以上述末次为准。测试没有证明全部 57 种真实工具链、Windows 或已安装宿主运行。未初始化 CodeGraph、创建分支、提交、bump 或发布；下一项是 Java parser/graph/planner 分离，整项目目标仍进行中。

## 第八批实际验证：Java 观察与纯策略分离

- RED：只改依赖版本、compiler/release、Gradle sourceCompatibility 或嵌套插件 version 都被旧实现误判成纯版本升级；单行 POM 中仅顶层版本变化反而无法降级。`api/../service` 被词法前缀错误归到 api。Java `1.8` 被识别成 JDK 1，普通属性引用被忽略。先通过真实 Git/文件与可执行 JDK 定位夹具复现，再修改实现。
- `java_build` 只读构建描述，`java_impact` 用反向邻接表计算闭包，`java_planning` 只选择命令；`java_changes` 与 `java_environment` 通过统一执行器观察 Git/JDK；`java_analysis` 装配兼容计划。隔离 Python 进程证明纯策略不加载 subprocess/解析器/宿主，循环图有限终止且输入不变。CLI/MCP 入口、默认 skipTests/check -x test、显式命令、wrapper 与逐命令 JAVA_HOME 保留。
- 重构期间真实回归发现 macOS `/var` 路径别名误报仓外，已统一根路径规范化并恢复旧测试；新增嵌套项目 Git 夹具又暴露 HEAD:path 读取父仓同名 POM 的问题，改为 cwd 相对 HEAD:./path。插件脚本文本空白与 revision 属性引用同样经过先红后绿，不能混入纯版本豁免。
- 完整描述比较仅剥离可证明的项目版本；未知语法、无法取基线、依赖/插件/编译配置或复杂关联版本修改不降低级别。真实 Git index 内容前后相同；规划不执行 wrapper、不安装工具。保留轻量优化不等于承诺完整构建语义等价。
- 最终全量 **375 unittest：372 通过、3 个历史 pathspec skipped**；新增 Java 边界 21/21，既有 Java 影响 15/15；`tests/run_all.py` **142/0/0**。ruff、架构依赖/循环、语言 schema 57 项/11 规则、vendor 离线和在线、本 change strict、diff whitespace 通过。在线 lock v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`，受管技能与 lock 未改。
- 当前只证明本地契约与真实进程/Git 行为，不代表真实大型 Maven/Gradle 构建、任意 effective POM/DSL、Windows 或三个宿主已验收。未初始化 CodeGraph、创建分支、提交、bump 或发布。下一项为 CVE 编排与五个扫描器报告适配，整体目标保持进行中。

## 第九批实际验证：CVE 报告与编排边界

- 第一组 RED 通过真实子进程夹具复现：Trivy 非列表 Results/未知严重度/非零空报告被误判通过；npm 残缺统计、错误信封、非零零发现误判；Maven 非法数值/缺标识/缺分数丢失；Cargo 探活失败仍继续及统计冲突；pip skipped 依赖被当作已审计；坏配置导致 traceback 或由显式生态绕过。21 项测试最初产生 26 个失败及 1 个缺失修复证据字段错误，完成实现后转绿。
- `cve_reports` 与 `cve_policy` 纯解析/判定；`cve_scanners` 负责命令、项目依赖输入和本次 Maven 报告；`cve` 负责唯一生态目录、选择、修复/复扫；`cve_check` 是兼容导出与呈现。隔离进程证明纯解析器不加载 subprocess/执行器/扫描器/CLI，架构依赖白名单与循环门禁通过。没有引入新运行时依赖。
- 补充 RED 又验证并修复可选 scanInfo 非法形状泄漏异常、npm 明细与计数冲突、pip 部分失败被已知发现遮盖，以及 Maven/Trivy 非零但仅有低阈值发现被错误套用 npm 规则。npm 的有效低级别发现仍允许高阈值 PASS；其余已带阈值的工具不能据此推断成功。UNKNOWN 不在 Trivy 调用阶段被过滤。
- 真实进程夹具检查 5 个扫描器的有效干净报告与 exit 124/126/127 矩阵、pip 项目输入、不消费宿主 stdin、npm 显式修复副作用/失败修复后的成功复扫/失败复扫、文本与 JSON 一致、缺结构化判定的 exit 0 不放行。Maven 不读取项目旧报告；原 argv/cwd/exit/stdout/stderr 与发现保持可见。测试不联网扫描、不安装工具、不修改宿主或用户项目。
- 旧测试私有 monkeypatch 迁到实际 `cve_scanners.run`/`cve.scan_maven` 所有者；单档 `{high: 0}` 假报告改为完整 npm 档位，派发 fixture 显式给出 PASS，避免为测试保留“exit 0 自动安全通过”。原行为断言、阈值映射与别名回归保留。
- 最终全量 **405 unittest：402 通过、3 个历史 pathspec skipped**；新增 CVE 边界 30 项全过；`tests/run_all.py` **142 通过 / 0 失败 / 0 跳过**。ruff、架构依赖/循环、本 change strict、diff whitespace 通过；语言 schema 为 57 项/11 规则。vendor 离线与在线通过，锁仍为 v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`；受管技能、lock 和白名单未改。
- 核对五个工具官方报告实现，参考链接见 design 第 11 节；未宣称实际在线漏洞库、完整依赖覆盖、CVSS 向量求值、Windows 或三宿主生产运行已验收。未初始化 CodeGraph、创建分支、提交、bump 或发布。下一项是 task 4.3 CLI/MCP/五 Hook 协议边界与剩余历史 pathspec，整体优化仍未完成。

## 第十批实际验证：拟暂存范围与历史 pathspec

- 三项历史 skipped 不再调用从未实现的 match_pathspec，改为现有 staging_intent → 真实 validation_tree 的范围与字节断言；glob、目录与无匹配三种行为均实际运行，未删除测试或伪造 helper。原来单测中的空 src 字面路径改用真实 src 文件和兄弟文件，断言“不扩范围”。
- 新增真实 Git 场景先红后绿：exclude 与 include 被逐条并集；子目录 add . 扩到兄弟；-u pkg 带入未跟踪；-f 忽略路径漏选；git -C/空格路径/相对 cd 上下文错误；另一仓 add -A 污染本仓纯 commit；真实 Hook 从仓外执行 -C + 敏感 glob 静默放行。随后补测子目录被当作仓根导致敏感文件漏检，并修复到真实 worktree 根。
- `git_staging` 负责只读 Git 解析与逐仓绑定，`git_context` 保留旧导入兼容；Hook 为每个目标仓独立取得 lanes/extra。成组 pathspec 交 Git，输出字面路径，快照读取不重新解释星号。测试前后 index 字节一致，目录/空格/删除/排除与 force 的快照内容和范围相符，没有实际 add 用户文件。
- 旧全量回归曾出现 4 项失败：bash -c 引号识别两项、多仓兜底一项及空 src 假路径一项。改为正确解包一层解释器文本、纯 commit 不做无谓路径查询、真实范围 fixture 后重新验证；未忽略兼容性失败。交互暂存/外部 pathspec 文件保持能力边界，走 JSON additionalContext 的 git UNVERIFIED，而非普通内部异常或静默通过。
- 最终全量 **416 unittest 全部通过，0 skipped**；新增暂存边界 11 项、第二批回归 18 项均通过；`tests/run_all.py` **142/0/0**。ruff、架构依赖/循环、语言 schema 57 项/11 规则、本 change strict 与 diff whitespace 通过。受管技能/lock/白名单未改；在线 vendor 最近证据为第九批，本批未提交。
- 不将只读路径观察称为完整 Shell 执行模拟：复杂控制流、未引用的 Shell glob 展开、引号中的分隔符、链内任意写入、特殊索引环境、非 HEAD refspec 和并发编辑仍有边界。下一项继续 CLI/MCP/五 Hook 协议分层，以及 Dockerfile/基线证据遗留差距；整项目尚未完成，未初始化 CodeGraph、创建分支、bump、提交或发布。

## 第十一批实际验证：CodeGraph、Dockerfile 协议和基线豁免

- 对当前工作树的临时副本执行 `codegraph init -i -y`：123 文件、1,795 节点、4,069 边；查询 CLI/MCP→语言检查→执行器、PreToolUse→Git 暂存/门禁/基线，以及 Dockerfile 解析调用链。CodeGraph 指出 `run_check.py` 仍持有 MCP 自动修复策略，`execute` 被多个应用入口共享；这两点分别列为后续协议收敛和已落地执行边界的证据。临时副本不包含受管技能和资产，原仓没有新建索引。
- 初次全量运行 430 项出现 28 失败、4 错误：`dockerfile_security.py` 仍使用旧扫描分支，未接入已写出的 `codeguard.dockerfile`/`dockerfile_reports`。改为只负责参数、文本/JSON 呈现，旧 Python 导入显式再导出；14 项真实进程边界全部通过。当前 JSON 和文本共用同一状态与退出码，丢报告/坏结构/超时为 UNVERIFIED，已知发现仍保留。
- 基线误豁免新增三项 RED：同规则第二处违规、规则相同但描述不同、基线命令成功却打印错误文本。将实际豁免改为带次数的诊断比较，并要求基线自身判定 FAIL；旧 `finding_signatures` 导入保留。三项转 GREEN，原有存量/新增/无基线用例仍通过。
- 修复架构检查中新 Dockerfile 模块尚未登记的白名单；所有内核模块继续受依赖方向和导入环门禁约束。最终完整单测 **433/433，0 skipped**；`tests/run_all.py` **142/0/0**；ruff、架构门禁、语言 schema 57 项/11 规则、vendor 离线与在线、本 change strict、diff whitespace 通过。受管技能和 lock 未改。
- 这些结果证明本地契约及离线真实进程/Git 场景，不证明真实联网漏洞扫描、三个宿主现场加载、全部 57 个语言工具链或跨平台运行。尚未 bump、提交、推送或发布；目标继续推进。

## 第十二批实际验证：语言服务与 CLI/MCP 边界

- 将 `run_per_language.py` 的唯一实现移入 `codeguard.language_check`，旧路径只再导出；`gate_checks` 改为直接依赖应用服务。`check_application` 接管语言选择、MCP 四工具请求、改动范围自动修复与历史结果字段；`run_check.py` 继续只承担 argparse、文本呈现和 MCP SDK stdio 接线。
- 迁移后 CLI/MCP/语言计划/执行专项 62 项通过；新 CodeGraph 快照同步后为 125 文件、1,819 节点、4,108 边，`mcp_tool_payload` 的调用者已落在 `run_check.py`。静态架构门禁通过，core 不导入 SDK 或 hooks。五个 hook 仍有入口内编排，4.3 尚未完成。
- 报告不再硬编码旧 `0.12.0`，读取当前插件 manifest；新增独立 Python 进程核对显示版本。双语 README 移除硬编码“当前开发版本”，指向当前架构和本 change 证据；历史文档标明适用范围。增加本地链接存在性测试，目标专项 16 项通过。
- 本批完整全量单测 **435/435，0 skipped**；`tests/run_all.py` **142/0/0**。ruff、架构门禁、语言 schema 57 项/11 规则、vendor 离线与在线、本 change strict 及 diff whitespace 均通过。此处仅是本地验证；尚无本次改动的远端 CI、发布或三宿主现场运行证据。五个 Hook 的入口分层仍未完成，4.3 与整体目标保持进行中。

## 不能遗忘的剩余项

1. CodeGraph 已对本轮工作树的临时副本建索引并查询，目标仓本身仍无 `.codegraph/`；修改后的文件需同步临时索引后才可视为新的图谱证据。
2. 基线四项历史 skip 已全部实跑恢复；Dockerfile 坏报告/超时与基线诊断粒度已补测试并修复。仍需逐项复核其它能力边界，不能以零跳过推断全功能验收。
3. 现有未归档 `gate-toolchain-unverified` change 与其它会话修改保持原状，不能把它们的勾选当本次验收。
4. 报告版本及双语当前架构文档已收敛；仍需审计 CLI/Hook 其它版本文字，并完成发布链及宿主验收。
5. 通用执行器仅处理文本检查命令；Git blob 的二进制协议必须保留字节，不得为了“一致”强制 UTF-8 解码。
6. 第一期不解决任意命令进程树管理、完整 shell 解释、沙箱及所有动态 Java 构建；这些边界不能在文档中消失。
7. 只审阅了 pre-commit 官方的通用语言协议与 Python 适配器作边界参考，未声称移植或达到同等成熟度。

## 第十三批实际验证：v0.13.0 阶段发布与会话 Hook 应用层

- 上一批源码作为阶段版本 v0.13.0 经插件 PR #45、市场 PR #1 合并到两个 `main`；插件 PR 与 main 的 `skills-check` 均通过。不可变 `v0.13.0` 注释 tag 解引用到插件 main 合并提交 `fb95bbad6a6748e081918b79e58d7d1bb85a7d40`，GitHub Release 已发布；市场 Codex/ZCode/Kimi 清单为 0.13.0，生成器只读校验通过。三宿主已安装副本和运行现场仍未验证，不以发布代替宿主验收。
- 本批新改动先有 RED：SessionStart/Stop 应用服务不存在，3+3 项新契约测试失败。`startup_application` 接管语言发现、配置盘点、探活、双副本/版本提醒报告；`session_application` 接管原子状态消费、总结与残留 skipGate 观察。两个 Hook 保留原路径、旧 Python 导入与会话去重，仅做宿主配置、通知、stdout 和 fail-open。
- 真实 Git 和会话测试确认 Stop 只消费当前作用域一次、残留 skipGate 单列提醒；独立解释器证明两个应用服务导入不加载 Hook 或宿主 SDK。修改后的临时 CodeGraph 快照同步了 8 个文件，调用链显示 `build_startup_report` 与 `consume_summary` 均由对应 Hook 调用，未在源仓初始化图谱。
- 本地本批全量 **441 unittest 全部通过、0 skipped**；`tests/run_all.py` **142/0/0**；ruff、架构依赖门禁、语言 schema 57 项/11 规则、vendor 离线与在线、本 change strict、diff whitespace 均通过。PostToolUse、UserPromptSubmit、PreToolUse 仍持有应用编排，4.3 和整体目标继续进行；本批代码尚未 bump、提交、推送或发布。

## 第十四批实际验证：五类 Hook 协议入口收敛

- UserPromptSubmit 的意图/语言策略与软门禁编排分别进入 `prompt_policy`/`prompt_application`；PreToolUse 的 Git 命令判定进入 `git_guard_application`，并显式传入调用者 cwd；PostToolUse 的保存检查、修复复检与反馈进入 `save_application`。SessionStart/Stop 沿用上一批应用服务。五个 Hook 保留原路径、协议输出、通知、fail-open 与兼容导入。
- RED 后 GREEN：五个应用服务的独立导入与行为测试；软提示/保存的完成确认只在宿主输出后发生。PreToolUse 故障注入曾证明拦截事件在 stdout 写入前被记为完成，现改为输出后再记；宿主输出异常时不会错误缓存已交付拦截。既有 `run_all.py` 的异常注入改打实际 `prompt_application.run_gate` 所有者，并保持 fail-open 断言。
- 临时 CodeGraph 快照重新同步了本批改动并追踪三个新应用服务的 Hook 调用点；源仓未初始化索引。`scripts/check_architecture.py` 声明并约束新内核模块，隔离导入测试阻止其反向加载宿主 Hook/MCP。
- 使用本机已有、带 MCP SDK 的 `/opt/anaconda3/bin/python3` 3.13.5 完整执行 **454 unittest，全部通过、0 skipped**；`tests/run_all.py` **142/0/0**。Homebrew Python 3.14 缺 MCP SDK 时同一套测试仅执行 451 项、跳过 3 项，故不将该运行作为完整证明。ruff、架构门禁、语言 schema 57 项/11 规则、vendor 离线与在线、本 change strict、diff whitespace 通过；技能 lock 和受管技能未改。
- 本地入口边界已满足 task 4.3。Stop 会先消费会话状态再输出，若 stdout 故障可能丢失该次总结；三宿主安装现场、Windows、联网漏洞库及所有语言真实工具链仍待独立验收。本批源码在本记录时仍未 bump/提交/推送/发布，不把 v0.13.0 的远端证据套用到新改动。

## 第十五批实际验证：诊断归属与 Stop 交付确认

- v0.14.0 已经插件 PR #46、市场 PR #2/#3 合并到两个 `main`；插件 PR 和合并后 `main` 的 `skills-check` 通过，不可变 tag/Release 指向插件合并提交 `0e699b85b0cb3abaf6a248e04121ecae152ba508`，市场三宿主清单及中英文导航均为 0.14.0。该发布证据只覆盖上一批代码，本批源码尚未发布。
- 临时 CodeGraph 索引同步后追出 `check_language → baseline_stale_finding → finding_instances`；原提取器剥掉文件位置。两项真实 Git/检查器测试先 RED：其它文件的同文本 `F401` 与 ShellCheck `In <file> line N` 诊断均被误豁免。现在比较文件归属、描述、出现次数，把基线临时路径映射回原仓相对路径；同文件只移动行号仍允许有证据的豁免。CodeGraph 的受影响测试映射返回空，故以实际源码调用和目标测试作为覆盖证据，不将空映射当无测试。
- Stop 原逻辑在输出前 `take_json`，故故障注入先 RED：stdout 写入失败时会话记录已被删除。现新增准备结果和输出后确认；写入或刷新失败时记录保留可重试。若准备后有并发新写入，锁内快照不一致就不消费，允许下一次重复展示旧统计而不删除新记录。旧 `consume_summary` 兼容接口保留，Hook 改用 `prepare_summary`。两种输出故障和并发写入均有目标测试。
- 本机现有 `/opt/anaconda3/bin/python3` 3.13.5 完整执行 **460 unittest，全部通过、0 skipped**；`tests/run_all.py` **142/0/0**。ruff、架构门禁、语言 schema 57 项/11 规则、vendor 离线与在线、本 change strict、diff whitespace 均通过；受管技能及 lock 未改。上述为本地证据，远端 CI/版本/市场需在本批发布后另验。
- 这两处消除了已复现的假豁免与输出前丢总结；仍不声称完整 Shell 解释、三宿主现场、Windows、在线漏洞库、全部工具链或 OpenSpec 5.4/5.6 的全目标审计完成。stdout 刷新成功不等于宿主最终消费确认，因此异常重试可出现重复总结；该取舍优先保证不丢统计。

## 第十六批实际验证：跨 Hook 输出交付边界

- 已发布的 v0.14.1 源码经插件 PR #47、市场 PR #4 合并到双仓 `main`；插件 `skills-check` 通过，注释 tag 与 GitHub Release 指向合并提交 `b8fa3850c877eae454845326fc167103d406b7d3`，三宿主市场清单均为 0.14.1。该证据只覆盖此前源码，不覆盖本批工作树。
- 临时 CodeGraph 快照同步最新源码后，追踪 `PromptResult`/`SaveResult`/PreToolUse 的交付调用链：Stop 已刷新 stdout 再确认，而其余两个软 Hook 及 Git 硬门在刷新前就登记完成或缓存。当前项目的真实测试文件覆盖范围比 CodeGraph 的受影响测试提示更广，故以源码链和实际测试为准。
- 新增 RED：UserPromptSubmit 与 PostToolUse 在 stdout 刷新失败时，旧入口仍登记完成；Git 已知拦截的输出写入失败向外抛异常，若由入口顶层 fail-open 捕获则可能放行；刷新失败还会缓存未交付拦截。现在所有确认都在刷新后；已知拦截输出故障保留 exit 2、不缓存，含无 tool_use_id 路径和缓存重放。对普通软反馈仍保持原 fail-open 协议。
- 定向测试 **26/26**，完整单测 **465/465、0 skipped**，真实 Hook 回归 **142/0/0**；ruff、架构依赖/循环、本 change strict、语言 schema **57 项/11 规则**、vendor 离线和在线以及 diff whitespace 通过。vendor lock 仍为 v0.1.2 → `2c0c8071f96de48dc53e11de2499c083c100e44c`，受管技能与 lock 未修改。
- 本批只证明本地输出时序与故障注入；stdout 刷新不等于宿主最终消费，可能在重试时重复反馈。三宿主已安装运行、Windows、联网漏洞库和全部语言工具链仍需独立验收；本批在此记录时尚未 bump/提交/发布。
