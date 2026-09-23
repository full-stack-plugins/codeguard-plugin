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

## 第十七批实际验证：显式 Git 目标与调用目录

- v0.14.2 已经插件 PR #48、市场 PR #5 合并到双仓 `main`；插件 PR/main 的 `skills-check` 通过，不可变 tag/Release 指向合并提交 `2cdf816d3a5924155480dd24a535d61ebab47e01`，市场 Codex/ZCode/Kimi ref 与双语导航为 0.14.2。该远端证据只覆盖第十六批及此前源码，本批仍需独立发布。
- 临时 CodeGraph 快照同步后追踪 `evaluate_git_command → resolve_project_roots → repository_root` 与 `staging_intent`。发现显式 `cd` 到非 Git 目录后执行 commit/push 会回退调用者仓；显式 `git -C` 无效目标会落到 workspace 兜底；应用传入 cwd 仅用于仓库定位，拟暂存解析却读取进程全局 cwd。分别用真实临时 Git 仓和独立调用目录复现：前两类错误放行/泛化诊断，第三类遗漏新增 Python 文件。
- 当前 `GitTargetError` 将显式目标不可绑定与无显式目标的 workspace 兜底区分；前者在应用边界返回 exit 2 和具体路径，不再检查错误仓。Git 根观察的 `SnapshotError` 同样不交给顶层 fail-open。拟暂存解析接受可选显式 cwd，并由应用传入同一调用目录；旧无参导入/调用仍可使用进程 cwd。真实 PreToolUse 子进程证明无效目标阻断，`git -C` 有效目标仍覆盖非 Git cd。
- TDD RED 包含错误放行、错误兜底、遗漏 pathspec 与根观察异常；GREEN 后完整单测 **470/470、0 skipped**，真实 Hook 回归 **143/0/0**。ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 通过；受管技能与 lock 未改。
- 这不是 Shell 求值器：条件链、动态拼接、命令替换、复杂引用和链内环境变化仍是明确边界。三宿主现场、Windows、联网漏洞库与全部语言工具链未因此获得验收。本批在此记录时尚未 bump/提交/发布。

## 第十八批实际验证：多仓操作与豁免归属

- v0.14.3 已经插件 PR #49、市场 PR #6 合并到双仓 `main`；插件 PR 及合并后 `main` 的 `skills-check` 成功，不可变注释 tag 与 GitHub Release 解引用到 `f646f031bf35d269da82d4f70c0a4666991eb175`，市场三宿主版本为 0.14.3。该发布只覆盖第十七批及此前源码，不覆盖本批修改。
- 临时 CodeGraph 快照从最新 main 同步并追踪 `evaluate_git_command → resolve_git_operations → validation_tree/proposed_paths`。原实现按整链 `push` 和 `pending_commit` 选面：A 仓 commit、B 仓纯 push 时，B 暂存的 `.env` 被错误纳入本次推送并阻断。真实双 Git 仓测试先 RED；现在 `GitOperation` 保留每个副作用的仓、模式与有序豁免状态，B 只检查 HEAD，同仓 commit→push 仍检查已有待推送内容与拟提交内容。
- 仓库级 `skipGate` 原先以 `any(...)` 令 A 仓配置豁免 B 仓；内联 `-c` 和链式 `git config` 也会全链放行。新增测试分别先 RED，再证明只豁免所属仓与操作；同仓后续无豁免提交仍受检，后置设置不追溯前面的提交。已有仓库配置为 true 但命令先 unset 再提交也曾被预读配置误放行，现按命令序列覆盖旧配置。旧 `resolve_project_roots` 与语法布尔 helper 导入面保留。
- 追加 RED：`git config --file=其它文件` 错被当成本仓豁免；`git config ... || git commit` 错把仅在设置失败时才会执行的提交放行。现在前者不构成豁免，后者及 `;`/换行连接的配置状态报告 UNVERIFIED 并要求拆分命令。未把完整 Shell 求值器伪装成已实现。
- 完整单测 **479/479、0 skipped**；真实 Hook 回归 **143/0/0**。Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线及在线、本 change strict、diff whitespace 均通过；受管技能及 lock 未改。测试覆盖真实 Git/快照与应用层故障，但静态 Shell 解析仍非完整求值器，三宿主现场、Windows、在线漏洞库和全部语言工具链仍未独立验收。本批发布闭环待执行。
- 后续 RED 发现：`echo "docs; git config codeguard.skipGate true" && git commit` 会把引号内分号当真实分隔符，错误放行含 `.env` 的提交。语法/仓库/间接脚本/拟暂存改用同一个引号及转义感知切分函数；真实 Git 提交安全用例与纯语法用例转绿。复核后完整单测 **481/481、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线及在线、本 change strict、diff whitespace 均通过。本批发布证据仍待补齐。
- 第十八批随后发布为 v0.14.4：插件 PR #50、市场 PR #7 已合并双仓 `main`；插件合并后 `skills-check` 成功，注释 tag 解引用到 `be619cd4b769495280c7d0d7405f9b01a8ca4dc9`，GitHub Release 正式发布；市场 Codex/ZCode/Kimi 清单及双语导航均为 0.14.4。此证据仅覆盖第十八批及此前代码，不覆盖以下新工作树。

## 第十九批实际验证：一层 Shell 间接 Git 操作归属

- 将最新 v0.14.4 `main` 同步至已有临时 CodeGraph 索引（136 文件；源码仓不建索引），沿 `PreToolUse → evaluate_git_command → _guarded_mode/resolve_git_operations → staging_intent` 追出检测与归属分叉。真实临时 Git 仓先 RED：`bash -c 'git commit'` 在调用仓报“无仓”；内层 `git add .env` 不进拟暂存面；外层已有 commit 时忽略后续 Shell 脚本对另一仓的 commit；`cd` 后相对脚本找不到。上述都可能让宿主得到错误仓库或错误范围的结论。
- 一层 bash/sh/zsh `-c`（含 `-lc`）或可读脚本现在按解释器实际参数位置、调用目录解析；内层 Git 操作携带来源正文与 cwd，和外层操作按仓聚合。拟暂存分析合并外层与内层来源，真实 Hook 子进程证明未实际执行 `git add` 就拦截 `.env` 且 index 字节不变。纯 push 不纳入未提交 index；外层 skipGate 设置只传递给所属仓的内层操作。
- 不能可靠建模的 Python/Node 间接命中、脚本内 skipGate 配置变化、交互暂存与后续提交跨解释器边界时，明确返回 Git 意图 UNVERIFIED 并阻断；仅在纯 push 之后的独立暂存不误扩该 push 面。脚本的普通 `-c` 参数不再被误认成解释器代码。动态脚本与任意 subprocess 构造仍是未覆盖边界。
- RED→GREEN 的目标用例及最终完整单测 **495/495、0 skipped**；真实 Hook 回归 **143/0/0**。Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。受管技能及 lock 未改；这些是本地契约证据，不是三宿主安装、在线漏洞库、Windows 或第十九批发布证据。本批已准备 v0.14.5 元数据；远端发布须另行核对 PR、CI、tag、Release 与市场主线。

- 第十九批随后发布为 v0.14.5：源码 PR #51 合并为 `3f1266d8b57625e282989a51b20c528d578a01e1`，市场 PR #8 合并为 `a910cde2f6bfd5ebc6ca88d11fbb834687fb9084`；PR/main `skills-check` 成功，远端注释 tag 解引用到源码 main 合并提交，GitHub Release 为非 draft、非 prerelease，市场 Codex/ZCode/Kimi 及双语导航为 0.14.5。此证据不覆盖以下新工作树。

## 第二十批实际验证：裸前缀不遮蔽 Shell Git 副作用

- 将最新 v0.14.5 `main` 同步至已有临时 CodeGraph 索引（136 文件；源码仓未初始化索引），追踪 `git_syntax._analyze_segment`、`git_context._indirect_body`、`_guarded_mode`、`resolve_git_operations` 与 `staging_intent`。真实临时 Git 仓和纯函数探测先 RED：裸 `bash -c 'git commit'` 进入门禁，而 `FOO=1`、`env FOO=1`、`command`、`sudo` 前缀令同一 Shell 正文完全不命中；带敏感 `.env` 的暂存内容可被错误放行。
- 直接 Git 与解释器入口现共用 `git_syntax` 的裸前缀归一化；一层脚本仍由同一个调用目录与正文进入仓库归属和拟暂存分析。RED→GREEN 用例覆盖五类前缀、内层 add/index 不变、`cd` 后相对脚本、真实 PreToolUse 子进程；带值 wrapper 参数、动态命令及任意控制流仍不在静态保证范围内。
- `/opt/anaconda3/bin/python3` 3.13.5 完整执行 **498 unittest、0 skipped**；真实 Hook 回归 **143/0/0**。Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。CodeGraph 的 `affected` 对本次核心文件返回空，但真实目标测试存在且已运行，故不把空图谱结果当无影响证明。受管技能和 lock 未改；本批尚未版本升级、提交或发布，三宿主现场/Windows/在线漏洞库仍未验收。
- 同步最新 CodeGraph 后继续追踪 `git_syntax` 发现：`inline_skip_gate` 和 `skip_gate_config_change` 仍用原始空白分词，与已共用的直接 Git/解释器前缀语义分叉。真实仓库 RED 证明已有持久 `skipGate=true` 时，`env FOO=1 git config codeguard.skipGate false && git commit` 被错误放行；带前缀的 `git -c` 单次豁免则被错误阻断且失去审计。二者现复用同一 `_segment_tokens`，目标测试转绿；此证据补充前述批内回归，不将早先 498 项计数当最终全量结果。
- 最终本地完整回归：`/opt/anaconda3/bin/python3` 3.13.5 执行 **500 unittest、0 skipped**，真实 Hook **143/0/0**；Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。两项新 RED 场景及既有豁免/引号边界均转绿。本批已准备 v0.14.6 元数据；在 PR/CI/tag/Release/市场主线核对前，不能用 v0.14.5 的证据证明新改动已发布。

- 第二十批随后发布为 v0.14.6：源码 PR #52 合并为 `e32b10648b2d3e048b30ee6fc04f7945affa44fc`，市场 PR #9 合并为 `9430df2e24095dbb50eb65dde3e9df670853c9e8`；源码 PR 和合并后 main 的 `skills-check` 成功，远端注释 tag 解引用到源码 main 合并提交，GitHub Release 非 draft、非 prerelease。市场三宿主清单与 README 导航同步到 0.14.6，合并后远端 tag/Release 校验通过；市场 PR 没有报告 CI 检查，不能声称市场 CI 已通过。此发布不覆盖以下第二十一批工作树。

## 第二十一批实际验证：逐命令执行证据不在应用层丢失

- 将 v0.14.6 的当前源码同步到临时 CodeGraph 索引（136 文件；源仓未初始化索引），沿 `execute_plan → language_check.run_check/run_fix → check_application.result_envelope` 追踪。内核 `PlanExecution` 保留全部已执行命令，但应用只读取 `terminal`；Java 第一条命令通过并输出诊断、第二条失败时，前者从结果和失败日志消失。真实 Python 子进程测试先 RED（缺少 `execution_trace`），不是模拟返回值。
- 语言检查现保留检查、修复和复检各阶段的实际命令、目录、退出码、故障标识及有界 stdout/stderr 尾部；MCP 的既有字段不变，附加逐命令安全元数据。失败日志记录所有已执行检查的完整输出，未执行的第三条命令不进入证据。Java 选定的 `JAVA_HOME` 进入子进程但不出现在公开 trace，宿主环境不变；`.zsh` 仍跳过 formatter，但修复后的复检保持原范围。
- 真实 MCP stdio RED 复现：`codeguard.json` 权威命令中的哨兵 token 经原始 argv 和检查器输出进入新增轨迹，扩大了公开面。`check_application` 现将 `check_code_style` 与 `auto_fix` 的新增轨迹压成阶段/序号/程序名/退出与故障/输出长度，不回显 argv、环境覆盖或输出文本；原始证据仍由内部执行结果和本地失败日志保留。后者可能含敏感内容，文档明确要求排除版本控制，不宣称日志已脱敏。
- 新目标测试经真实 `mcp_tool_payload` 路径转绿；进一步通过官方 MCP SDK 的 stdio 客户端从 `check_code_style` 收到两条实际命令状态与完整失败日志路径，token 未出现在 JSON 响应。加入 `auto_fix` 轨迹收敛测试后完整本地单测 **503/503、0 skipped**，Hook 回归 **143/0/0**，Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线/在线、本 change strict 与 diff whitespace 通过。受管技能与 lock 未改；这仍是本地证据，当前发布的 v0.14.6 不含本批修改，三宿主安装现场、真实 Maven/Gradle、在线漏洞库及 Windows 未验收。
- 宿主安装登记只读抽查：本机 ZCode 的 `installed_plugins.json` 将 `codeguard@full-stack-plugins` 指向 `v0.12.1` 与其缓存目录；它不能证明 v0.14.6 或本批在 ZCode 的加载/触发。当前抽查的 Codex/Kimi 缓存路径未提供当前版证据，但不能据路径缺失推断所有宿主环境均未安装。宿主安装和真实加载需在后续有权限的独立验收中验证，不由源码测试、市场 ref 或旧缓存替代。

- 第二十一批随后发布为 v0.14.7：源码 PR #53 合并到 `1543a93ae893040633ced2818b6dd7fb30752c40`，市场 PR #10 合并到 `e5816b097006f65db24a7ac2c5d00080faae9ee1`；源码 PR 与合并后 main 的 `skills-check` 均通过。远端注释 tag 解引用到源码合并提交，正式 GitHub Release 非 draft、非 prerelease；市场 Codex/ZCode/Kimi 生成清单校验及导航版本为 0.14.7。市场 PR 没有报告 CI 检查，不声称市场 CI 通过。此发布只覆盖第二十一批及此前代码，不覆盖以下新工作树。

## 第二十二批实际验证：诊断日志私有原子落盘

- 继续做 CLI 能力矩阵黑盒审计：真实 Git 仓同时修改 `.zsh` 和 `.sh`，假 shfmt 确实被调用并退出 2；原 `fix.py` 按 `zip(results, languages)` 只打印第一条 zsh 跳过，错误返回 0。新测试 RED 后改为按每条结果的语言呈现和聚合，目标测试连同 `detect`/`init` 入口及日志测试 9/9 GREEN。

- 临时 CodeGraph 索引同步到最新源码（源仓未初始化索引），沿 `language_check.run_check → 项目 out 日志` 与 `reporting._truncate_detail → 临时门禁日志` 两条链定位到普通 `Path.write_text`。两处均写原始检查器输出；文档虽提示可能含敏感文本，但项目日志在默认 022 umask 下为 0644。预置日志路径符号链接会覆盖目标文件，项目 `out` 目录链接会把日志写到外部；`out` 是普通文件时，`mkdir` 异常会掩盖已有检查结论。
- 真实文件系统新增 5 项 RED：项目日志权限、项目日志文件链接、输出目录链接、不可用输出目录、门禁截断日志链接。统一由 `storage.write_private_text` 在同目录创建私有临时文件并原子替换，拒绝直接链接的日志目录；两类应用只决定路径与内容。日志不可用时不返回虚假的路径，检查状态保持原判；保留既有日志内容格式与可见路径。另加原子替换失败的故障注入，证明旧日志不被截断、临时文件清理、既有判定保留。目标 6/6 通过，POSIX 创建权限为 0600，链接目标保持原样。
- 完整本地单测 **512/512、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 通过，受管技能及 lock 未改。CodeGraph `affected` 对本次文件返回空，但实际新增测试和原有调用链覆盖存在，不将该空结果当无影响证据。
- 本批仅证明静态预置链接、POSIX 权限和原子替换语义；不承诺抵御并发替换父目录的完整文件系统竞态，也没有 Windows 实机、三宿主现场、在线 CVE 或大型 Maven/Gradle 验收。v0.14.7 的 CI/Release 不能证明此新代码；v0.14.8 发布证据须单独记录。

- 第二十二批随后发布为 v0.14.8：源码 PR #54 合并到 `ef6ace131f5922a652f88bcf320a0edcd69e1c92`，市场 PR #12 合并到 `32d717d25498160617f326c4b0c192513d8c511a`；源码 PR 与合并后 main 的 `skills-check` 成功。远端注释 tag 解引用到源码合并提交，正式 GitHub Release 非 draft、非 prerelease。Codex/ZCode/Kimi 生成市场清单全量校验通过且版本均为 0.14.8；市场 PR 无 CI 检查，不称其 CI 已通过。本地两仓 main 已快进且干净。此发布不覆盖以下第二十三批工作树。

## 第二十三批实际验证：Git 门禁故障隔离与已知结论保留

- 当前 main 的临时 CodeGraph 索引同步后，沿 `gate.run_batch → gate_checks.check_language` 和 `git_guard_application.evaluate_git_command → repository_policy.check_commit_safety → git_snapshot.proposed_paths` 追出两处未隔离故障。前者的 `ThreadPoolExecutor.map` 会把一个 worker 异常抛出到整批门禁；后者的 `SnapshotError` 越过应用层进入 Hook 顶层 fail-open，连先前已确认的 lint 拦截都可能丢失。CodeGraph `affected` 对这两处返回空，不作为无测试影响的证据。
- 三项故障注入先 RED：一种语言抛内部异常、另一语言真实执行违规命令时整批抛错；安全路径读取失败时，无论是否已有 lint 失败，应用均抛错；Hook 无法交付结构化未知上下文。现 `gate` 在单语言任务边界返回不可变 `GateOutcome` 的 UNVERIFIED 备注，不泄漏异常原文，继续保留其它语言的失败和原仓审计；`git_guard_application` 将预期的安全路径快照故障转为 JSON additionalContext，已有拦截仍 exit 2，未有已知失败则保持现行 fail-open exit 0。三项目标测试转绿，真实 Hook 协议入口的 JSON 也实测。
- 沿 `mcp_tool_payload → auto_fix → run_fix` 审查发现，修复结果的公开投影原本只收敛 `execution_trace`，却把同一结果字典的原始 `command` 与 `stderr_tail` 复制进 MCP JSON。凭据注入测试先 RED；现按允许字段投影修复状态，将 formatter 诊断尾部写入私有 `out/.codeguard-fix.log`，仅在成功落盘后返回路径。真实失败 formatter 的进程输出、POSIX 0600 权限及输出目录链接不可用时不退回公开原文均已测试。CLI 的原始本地诊断未改变。
- 本地完整单测 **517/517、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 通过。临时 CodeGraph 索引已同步本批 3 个变更源码文件，当前 138 files / 2138 nodes / 4816 edges；源仓未初始化索引。受管技能及 lock 未改；当前发布的 v0.14.8 不含本批代码。三个宿主的已安装运行、Windows、在线 CVE、真实大型 Maven/Gradle 与进程池基础设施级故障仍未验收。

- 第二十三批随后发布为 v0.14.9：源码 PR #55 合并到 `a7cff4e8548b2f496f4572c8a9b951a404b6a0d8`，市场 PR #13 合并到 `46a2fc6571d44163f71d626c672930351c052010`；源码 PR 与合并后 main 的 `skills-check` 均成功。远端注释 tag 解引用到源码合并提交，正式 GitHub Release 非 draft、非 prerelease。Codex/ZCode/Kimi 生成市场清单全量校验通过且版本均为 0.14.9；市场 PR 无 CI 检查，不称其 CI 已通过。两仓本地 main 已快进且干净。此发布不覆盖以下第二十四批工作树。

## 第二十四批实际验证：按 Git 操作时间投影拟暂存面

- 最新源码同步临时 CodeGraph 索引后，沿 `evaluate_git_command → staging_intent → proposed_paths/validation_tree` 追出整条命令链暂存并集的时间归属缺口：安全文件已暂存，`git commit -m safe && git add .env` 或后接 push 会把后置 `.env` 倒算进此前提交并错误拦截。真实 PreToolUse Hook 的两个场景先 RED，index 字节保持不变；`commit && add .env && commit` 的阻断对照仍为 RED 测试中的通过项。
- `git_staging` 先记录绑定目标仓的不可变 add/commit 事件，再在无间接脚本的硬门禁中投影到该仓最后一次 commit；旧独立 `staging_intent` 默认完整暂存面不变。一层间接脚本缺跨层事件时钟，继续保守并集，不能用本次局部排序削弱可能提交的敏感内容。三个真实 Hook 场景转绿；含 `git add -p` 的后置交互暂存不回溯污染此前提交。
- 首轮全量发现 workspace 子仓兜底回归：合成子仓目标的暂存观察仍以非 Git workspace cwd 解析，原有脏子仓拦截变成 exit 0。保留原回归用例为 RED 证据，改为兜底时绑定已选子仓根；原测试与目标测试转绿。另增 A 仓先 commit 后 add、B 仓随后 commit 的真实 Hook 用例，证明截止点按仓计算且两个 index 字节均未改变。
- 继续沿 CodeGraph 的 `_flatten_substitutions → resolve_git_operations/staging_intent` 审查时发现安全反例：`$(git add .env)` 与反引号在外层 commit 前执行，但静态展开把内层文本附到末尾。真实 Hook 测试先 RED（敏感文件被错误放行）；现含命令替换的链保守并集，不启用文本顺序截止。两种带有效提交消息的形式均转绿，原始 index 不改写。单引号中的字面替换可能保守误拦，这一历史解析边界未宣称解决。
- 本地完整单测 **521/521、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 通过。受管技能及 lock 未改；已发布的 v0.14.9 不含本批工作树。当前只证明无脚本/命令替换的直接静态链顺序归属，跨一层脚本与命令替换仍保守合并；Windows、三宿主已安装运行、在线 CVE、大型 Maven/Gradle 与完整 Shell 控制流仍未验收。
- 宿主只读复核：本机 ZCode `installed_plugins.json` 的 `codeguard@full-stack-plugins` 仍登记 `0.14.7`，不能拿 v0.14.9 的 Release 或市场 ref 当作该宿主的当前加载/触发证据。未修改任何宿主安装。

- 第二十四批随后发布为 v0.14.10：源码 PR #56 合并到 `aa7a04aec9f5dbe220acfcc411a9fa10a3784367`，市场 PR #14 合并到 `a649eaf88673225d3dba54e1fb1a090d1a97daa3`；源码 PR 的 `vendor-check` 与合并后 main 的 `skills-check` 均成功。远端注释 tag `v0.14.10` 解引用到源码合并提交，正式 Release 非 draft、非 prerelease。市场 Codex/ZCode/Kimi 清单全量校验通过；市场 PR 无 CI 检查，不称其 CI 已通过。此发布不覆盖以下第二十五批隔离 worktree。

## 第二十五批实际验证：Git blob 批量传输的对象身份

- 最新 main 的隔离临时 CodeGraph 索引沿 `validation_tree → cat-file --batch-check/--batch → gate.run_gate` 追到准确快照的信任边界：旧实现只汇总大小，再以 `--batch` 头部长度切片，未逐项核对 ID、类型、数量、大小、尾部边界或 payload 哈希。独立故障注入证明错误对象 ID 的内容仍被接受；新增测试中 9 类协议错位/截断及门禁 UNVERIFIED 场景先 RED，真实二进制 blob 对照保持通过。
- `git_snapshot` 的字节型 Git 入口统一执行错误归一化；批量大小响应和内容响应按 index/HEAD 的同一对象顺序验证。每段 blob 按 SHA-1 或 SHA-256 Git 对象格式重新计算哈希，因此同长度替换也不能通过伪造响应头被接受；有效包含换行/NUL 的内容仍原样重建。错误响应转 `SnapshotError`，准确门禁返回 `git UNVERIFIED`，真实 index 字节不变。进一步用应用层集成用例确认：同批已经暂存的 `.env` 仍被安全规则 exit 2 拦截，未知快照不会抹掉已知违规；既有未知项 fail-open/可见告警政策未改。
- 隔离 worktree 本地完整单测 **526/526、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。当前只证明本地静态/故障注入契约与真实 SHA-1/SHA-256 仓库，不等于三宿主已安装现场、Windows、在线 CVE、大型 Maven/Gradle 或恶意 Git 进程沙箱验收。第二十五批尚未 bump、提交、推送或发布。

- 第二十五批随后发布为 v0.14.11：源码 PR #57 合并到 `e3b4262f1b5b5ef8d1c8ad2952a3012f47e42fbd`，市场 PR #15 合并到 `799c0369121c794bbb99fbdcd29fedf6e048aec0`；源码 PR 与合并后 main 的 `vendor-check` 成功。远端注释 tag `v0.14.11` 解引用到源码合并提交，正式 Release 非 draft、非 prerelease，市场 Codex/ZCode/Kimi 清单全量与远端 tag/Release 校验通过。市场 PR 无 CI 检查，不称其 CI 已通过。宿主安装/运行仍未验收。

## 第二十六批本地验证：Git 对象列表完整性

- 最新 v0.14.11 main 的隔离 CodeGraph 索引追踪 `validation_tree → git` 及准确门禁调用者：blob 哈希已验证，但 `ls-files --stage` / `ls-tree -r` 的对象列举仍以宽松 `split(NUL)` 读取，缺少终止符、重复/空记录或在完整记录边界漏项时可交付不完整树；畸形头会抛裸 `ValueError`。故障注入先 RED：10 个部分树错误接受，1 个异常类型不符。
- 当前实现把 `-z` 帧解析集中为 `_nul_records`，对象列表另验证模式、类型/阶段、对象格式长度和十六进制 ID、非空唯一安全路径，并与独立 Git 路径列举交叉核对。两种列表不一致或 index 并发变化均转 `SnapshotError`；准确门禁可见 `git UNVERIFIED`，不改真实 index。包含制表符/换行的合法文件名仍逐字节物化。CodeGraph `affected` 对本次文件返回无测试，但真实新增故障注入与既有集成测试覆盖较广，故不把图谱空结果当作无影响证明。
- 隔离 worktree 本地完整单测 **533/533、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。还正向覆盖空 index、有效 SHA-1/SHA-256、push HEAD 与脏工作树分离。临时 CodeGraph 索引同步后为 139 文件、2,181 节点、4,931 边；源仓仍未初始化索引。本批尚未 bump、推送或发布；宿主现场、Windows、在线 CVE、大型仓库与恶意 Git 进程仍不在已验证范围。

- 同批跨入口 CodeGraph 审查沿 `mcp_tool_payload → auto_fix → run_fix/run_check` 发现，旧 `auto_fix` 在作用域校验前对 Git 改动路径 `read_bytes`：父目录符号链接可先读仓外文件，大文件无内存预算，读取故障直接越过 MCP 结果边界。新增三种故障注入先 RED（仓外读取、超预算缺 UNVERIFIED、修复后身份故障缺 UNVERIFIED），另覆盖循环链接。应用服务现复用 `fingerprint.file_content` 的流式身份与 64 MiB/10,000 文件预算，修复前不可靠则不运行 formatter；修复后不可靠仍保留修复/复检证据，但顶层 `fixed=false` 且明确 UNVERIFIED。架构白名单只增加应用到 fingerprint 基础设施的有向依赖，反向导入与环仍受检。
- 补充后全量单测 **537/537、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构检查、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。MCP `auto_fix` 的私有日志/公开投影及真实 formatter 回归仍通过；这不等于三宿主实际安装或恶意并发文件系统的完整沙箱证明。

- 第二十六批随后发布为 v0.14.12：源码 PR #58 合并到 `fd0f771360c5ea27dbfc0ae5ab54ffdb5a0598ca`，市场 PR #16 合并到 `a648cdc704ab10d31dd2c3d8acb24b9b84af1ae1`；源码 PR 和合并后 main 的 `vendor-check` 成功。受保护注释 tag `v0.14.12` 解引用到源码 main 合并提交，正式 GitHub Release 非 draft、非 prerelease；市场 Codex/ZCode/Kimi 清单与中英文导航为 0.14.12。市场 PR 无 CI 检查，不称其 CI 已通过。源码本地 main 已快进且干净；市场原工作区保留已有未提交修改，远端 main 单独核对。本次发布不等于三宿主已安装运行，也不覆盖以下新候选。

## 第二十七批本地验证：MCP 修复归因与复检副作用

- 从 v0.14.12 的同树临时 CodeGraph 索引追踪 `mcp_tool_payload → auto_fix → run_fix/run_check → fingerprint.file_content`。旧实现仅在修复与复检都完成后取第二份身份；检查器自己改写文件时，顶层 `fixed` 会错误归因给 formatter。目标测试先 RED（缺 `UNVERIFIED`），改为修复前、formatter 后、复检后三次有界身份观察。
- formatter 后或复检后身份不可验证，以及检查器在复检期间改动目标文件时，保留实际修复和检查执行证据，顶层 `fixed=false` 且 `UNVERIFIED`。正向覆盖 formatter 真正改变文件而只读复检；反向覆盖检查器单独改写、把 formatter 变化还原、第三次观察故障，并由真实检查器子进程复现副作用。目标 9 项通过。
- `/opt/anaconda3/bin/python3` 3.13.5（MCP SDK 可用）完整执行 **542 unittest、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构依赖/循环、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。Homebrew Python 3.14.3 执行同套测试有 4 项依赖条件跳过，不能替代完整证明。受管技能及 lock 未改；本项已在隔离 worktree 本地提交为 `73873d5`，未 bump、推送或发布，三宿主已安装运行、Windows、在线 CVE 与大型 Maven/Gradle 项目仍无本批证据。
- 继续沿 `fix.py → language_check.run_fix → run_check(fix=True)` 审计：`run_fix.fixed` 历史上等于 formatter 退出码 0，供兼容调用方决定是否复检，却被 CLI 直接打印成 `✅ fixed`。真实临时 Git 仓的已规范 Python 改动文件经 Ruff 无改动返回 0，新增黑盒测试先 RED（CLI 虚称 fixed），现 CLI 仅报告 formatter 执行成功且文件变化未验证，旧字段与自动复检策略保持不变。MCP 顶层 `fixed` 仍使用独立身份比较；内层兼容字段的语义迁移需另行审计。最终本地完整单测 **543/543、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 均通过。本项已在隔离 worktree 本地提交为 `e1406de`，未 bump、推送或发布。
- 再沿同一 CodeGraph 路径审查 `run_fix → auto_fix → _public_fix_results`：内部 `fixed=rc==0` 被直接拷进 MCP 逐项结果，导致 no-op formatter、多个 formatter 或失败后部分改写的公开修复结论不可信。新增三个身份/归因测试先 RED；公开结果保留 `formatter_succeeded` 命令事实，并且仅唯一成功执行且复检后身份稳定时才声明逐项 `fixed`。多 formatter 不猜归属；失败且内容变化则整体 UNVERIFIED。完整单测 **546/546、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构检查、语言 schema **57 项/11 规则**、vendor 离线与在线、OpenSpec strict、diff whitespace 通过。内部兼容字段与复检策略未变；此处仍仅是隔离 worktree 的本地证据，未证明三宿主安装运行或版本发布。

- 第二十七批随后发布为 v0.14.13：源码 PR #60 合并到 `f683bc7b9888da97277eadce853774adf5fcaa15`，市场 PR #17 合并到 `947fc7d65b9a7f31360c1eeb96a02e62d1e8b196`。源码 PR 的 `vendor-check` 和合并后 main 的 `skills-check` 均成功；市场 PR 无 CI 检查，不称其 CI 已通过。受保护注释 tag `v0.14.13` 解引用到源码 main 合并提交，正式 GitHub Release 非 draft、非 prerelease，Codex/ZCode/Kimi 市场元数据及中英文导航均为 0.14.13。此发布不等于三宿主已安装运行、Windows、联网 CVE 或大型 Maven/Gradle 的现场验收；task 5.6 全目标审计、规格同步与归档仍未完成。

## 第二十八批本地验证：外部进程输出资源边界

- 在最新 v0.14.13 main 的隔离工作树建立临时 CodeGraph 索引（141 文件、2,226 节点、5,017 边）；`execute` 影响分析覆盖 77 个符号，沿语言检查、Git 门禁、CVE、Dockerfile 与 Hook 路径追出公共执行器的无界 `capture_output=True`。应用层虽截断报告，仍在收集阶段承担无限输出的内存风险。目标真实子进程用例先因缺少捕获预算参数 RED。
- 统一执行器现并发读取 stdout/stderr，默认共享 16 MiB 捕获预算；超限停止进程，保留预算内两流诊断，返回 `output_limit`/125 并由语言判定显式转 UNVERIFIED。退出码 125 由工具自己返回时不伪造执行器故障。POSIX 独立进程组有助于停止子孙进程；Windows 子孙进程回收尚未实机证明。已有 argv 字面值、工作目录、非法 UTF-8、超时部分诊断、非零双流和旧 tuple 协议继续通过。
- 首轮全量发现旧 SkipGate 重试用例 mock `subprocess.run`，执行器改用 `Popen` 后该 mock 不再触及业务边界；改为在 `repository_policy.execute` 注入相同的首次超时/两次超时证据，两项断言仍核验重试和审计。最终隔离工作树本地完整单测 **549/549、0 skipped**，真实 Hook 回归 **143/0/0**；Ruff、架构门禁、语言 schema **57 项/11 规则**、vendor 离线与在线、本 change strict、diff whitespace 通过。
- 该护栏只约束文本检查执行器；Git 二进制快照使用独立 `git_snapshot.git()`，其 `cat-file` 传输、覆盖层累计磁盘预算与恶意 Git 输出仍需另行审计。本批未 bump、推送或发布；三宿主现场、Windows、在线 CVE 与大型 Maven/Gradle 项目没有获得新证据。

- 第二十八批随后发布为 v0.14.14：源码 PR #62 合并到 `479d87815be8478d409e598ab473412dc6997383`，市场 PR #18 合并到 `9bea1d06a07d1c111c93f597b5cc0da7e89720ae`。源码 PR 的 `vendor-check` 与合并后 main 的 `skills-check` 均成功；市场 PR 无 CI 检查，不称其 CI 已通过。受保护注释 tag `v0.14.14` 解引用到源码 main 合并提交，正式 Release 非 draft、非 prerelease，Codex/ZCode/Kimi 市场元数据和中英文导航均为 0.14.14。本次发布不证明三宿主已安装运行、Windows、在线 CVE、大型 Maven/Gradle 或 Git 二进制快照的资源上限；task 5.6 全目标审计、规格同步与归档保持未完成。

## 第二十九批本地验证：Git 二进制输出有界捕获

- 从 v0.14.14 main 的隔离工作树重新建立临时 CodeGraph 索引（141 文件、2,240 节点、5,047 边），沿 `git_snapshot.git → _snapshot_entries/validation_tree → gate` 确认：Git `capture_output=True` 在解析 20,000 文件/256 MiB blob 预算之前无界收集输出。此前的预算只能拒绝已装入内存的过量结果，无法保护执行进程。
- 同一执行器现在提供原始字节结果，不解码 Git NUL 列表或 blob；Git 路径响应限 16 MiB，batch-check 按对象数限额，blob 响应在已验证大小总量后按内容与头部限额捕获。两流共享预算，超限终止并抛 `SnapshotError`，不交付截断的成功前缀。真实进程验证了 NUL/非法 UTF-8 原样保留、stdin 字节传递、双流洪泛早停；真实 Git 仓以 8 字节预算触发拒绝且 index 字节不变，既有 SHA-1/SHA-256、截断/错位/同长度替换和门禁可见性测试继续通过。
- 首轮目标测试暴露 macOS 上已结束进程的 `killpg` 权限竞态；清理逻辑现只在进程或读取线程仍存活时尝试终止，并在权限故障下保守回退。首轮目标 27/27、全量 552/552；以下覆盖层审计沿同一尚未发布的工作树继续，不把该中间计数称为最终结果。
- CodeGraph 沿 `validation_tree → overlays → read_bytes/write_bytes` 发现：旧实现虽限单文件 32 MiB，却未限覆盖层累计字节或文件数，且整文件载入内存；特殊 FIFO 可被静默当作删除，文件↔目录转换依赖 set 迭代顺序。五项真实 Git 目标场景先 RED（含总量、数量、FIFO 和双向转换），修复后以 64 KiB 块流式复制，最多 20,000 项/单文件 32 MiB/累计 256 MiB；源描述符前后核验大小与 mtime，异常不交付临时树。旧目录只在自动清理的一次性快照中被普通文件替换，原仓及 index 未改。
- 随后在直接调用覆盖层复制器的隔离子进程中复现 FIFO 打开阻塞（超时 2 秒 RED）；在支持的平台上使用非阻塞打开，并以 `fstat` 拒绝特殊文件后，目标用例 0.06 秒通过。最终本地完整单测 **558/558、0 skipped**，真实 Hook **143/0/0**；Ruff、架构检查、语言 schema **57 项/11 规则**、vendor 离线及在线、本 change strict、diff whitespace 均通过。此处尚未记入新版本发布证据；Windows 子进程树、异常大的真实仓库性能、敌对并发文件系统、在线 CVE 与三宿主现场仍待独立验收。
- 同日只读分层审计：插件远端 `main` 仍为 `95b793f`（v0.14.14 后文档合并），市场远端 `main` 新增其它插件 `processon-design 0.2.8` 的提交 `db08d83`，其 `catalog.json` 内 Codeguard 仍为 0.14.14；本机 ZCode 的 `installed_plugins.json` 将 Codeguard 指向 0.14.7 且对应缓存目录存在。Codex/Kimi 的本次默认缓存路径搜索未取得当前版本证据，不据此断言未安装。故源、市场和已安装宿主仍是不同证明层，本批未改宿主配置或触发更新。原始插件检出位于另一条带未提交改动的分支，隔离工作树没有覆盖它。
- 再沿 `validation_tree → proposed_paths/overlays → gate` 审计发现，同一快照会先为 `changed` 列举一次覆盖层，物化时再列举一次；若结果不同，就可能报告已检查第一组文件、实际只复制第二组。真实 Git 仓中对两次路径列举注入不同结果先 RED（`first.txt` 在 changed 中但不在快照），现一次列举并将同一集合传给路径计算和物化，原 `proposed_paths` 外部调用仍自行观察。该修复不等于 Git index 与工作树之间的原子事务；内容读取期间仍以已有大小/mtime/预算校验拒绝可见变化。
- 最终本地完整单测 **559/559、0 skipped**，真实 Hook **143/0/0**；Ruff、架构检查、语言 schema **57 项/11 规则**、vendor 离线及在线、本 change strict、diff whitespace 均通过。仍是隔离工作树未发布代码，不能用 v0.14.14 的远端 CI、Release 或旧宿主安装证明它已经交付。
