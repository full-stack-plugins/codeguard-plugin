# Codeguard Rust CLI 技术方案

状态：待实现；命令、字段与文件布局是目标协议，不代表当前 Python CLI 已支持。规范性事实源为 [本次 OpenSpec](../../openspec/changes/introduce-rust-codeguard-cli/proposal.md)。

## 1. 命令模型

逐项职责、价值、结果类型、副作用、失败恢复与典型调用旅程见 [命令架构](command-architecture.zh-CN.md)，检测族与验收边界见 [静态检测目录](static-check-catalog.zh-CN.md)。以下是同一目标协议的语法汇总；执行预算参数省略处遵循该文档 2.4 的支持矩阵和默认值，并在实现时从同一命令 schema 生成完整帮助。

```text
codeguard <lint|comments|dependencies|cve|security|build|check> <language|all> [path]
          [--format human|json|sarif] [--output PATH]
          [--jobs N] [--timeout DURATION] [--offline]
codeguard help [command...]
codeguard --version [--format human|json]
codeguard plan <lint|comments|dependencies|cve|security|build|check> <language|all> [path]
          [--format human|json]
codeguard detect [path] [--format human|json]
codeguard capabilities [language] [--format human|json]
codeguard doctor [language|all] [path] [--format human|json]
codeguard rules list <language|all> [path] [--format human|json]
codeguard config <validate|explain> [path] [--format human|json]
codeguard fix <language|all> [path] --category <lint|comments|dependencies|security|cve>
          <--dry-run|--apply> [--task TASK_ID] [--owner ID --lease-token TOKEN]
          [--format human|json]
codeguard gate pre-commit [path] [--format human|json]
codeguard gate pre-push [path] --remote-name NAME --remote-url URL [--format human|json]
codeguard gate ci [path] --input PATH [--format human|json]
codeguard tools <list|verify> [path] [--format human|json]
codeguard tools install --lock PATH [--dry-run|--apply] [--format human|json]
codeguard init [path] [--dry-run|--apply] [--format human|json]
codeguard work sync [path] [--format human|json]
codeguard status [path] [--format human|json]
codeguard next [path] [--format human|json]
codeguard task show <task-id> [path] [--format human|json]
codeguard task verify <task-id> [path] [--owner ID --lease-token TOKEN] [--format human|json]
codeguard task claim <task-id> [path] --owner ID [--format human|json]
codeguard task <heartbeat|release> <task-id> [path] --owner ID --lease-token TOKEN [--format human|json]
codeguard task attempt start <task-id> [path] --owner ID --lease-token TOKEN
          --action-id ID [--format human|json]
codeguard task attempt finish <task-id> [path] --owner ID --lease-token TOKEN
          --attempt-id ID --outcome VALUE [--format human|json]
codeguard mcp serve
codeguard compat legacy-v1 <旧子命令与参数>
```

检查命令的 language 必填，path 默认当前目录。canonical ID 沿用现有注册表，别名由同一注册表解析；`all` 是发现所有适用语言及类别，不是对所有注册语言强制安装工具。未知语言在执行前返回用法错误。

`gate pre-push` 通过 remote-name/remote-url 接受 Git hook 参数，通过 stdin 接受 ref/OID 元组；`gate ci --input` 接收版本化请求文件，其中明确仓库身份、不可变 commit OID 集合与预期内容来源。符号 ref 只作描述，输入文件不授予政策权威。禁止通过默认 HEAD 推测推送/CI目标；完整输入 schema 和验证样本在 S02 落实。

```bash
codeguard lint java . --format json
codeguard comments java .
codeguard cve all . --offline
codeguard check all . --format json --output codeguard-report.json
codeguard plan check all .
codeguard doctor java .
codeguard fix java . --category lint --dry-run
```

检查命令默认不修改源码、配置、Git index，也不自动修复；构建产物和工具缓存写入隔离运行区。`plan` 不执行构建、扫描、下载或安装，只读取计划所需信息；无法静态确定的部分记为待解析。`doctor` 可执行有界版本探测，但不执行安装。`tools install` 是独立显式动作，默认只预览锁定的安装计划，`--apply` 才安装，不由扫描隐式触发。

`check` 的类别是 lint、comments、dependencies、cve、security、build；先识别项目实际检查器配置，再运行已配置且可用的原生工具。未配置项反馈给智能体，只有批准策略要求的缺项影响交付门禁。build 的测试执行等级独立记录，由批准策略和明确的项目构建命令确定：沿用现有 Java 静态构建默认不运行测试；报告必须写明 test_execution=false，不能声称测试通过。若批准策略要求测试，必须运行，CLI 不提供自动跳过路径。

持久修复工作区及新增命令的写入边界见 [修复工作流](remediation-workflow.zh-CN.md)。check 写本地报告，work sync 显式更新脱敏问题/任务；next 只读并返回 RepairBrief，task verify 依据复检追加状态事件，不能手工强制关闭。

init 默认 dry-run，静态建立项目画像、模块图、检查准备清单及 AGENTS 受管摘要；apply 写入计划内产物，实际探测仍交给 doctor。版本来源、架构推断、增量刷新和 AGENTS 合并契约见 [初始化设计](project-initialization.zh-CN.md)。init 操作成功只表示计划/产物完成，不签发质量通过；其 readiness 独立记录前置条件。

## 2. 退出码、请求通过与交付通过

下表首先定义检查类的含义。信息/计划/管理命令的 0 表示该操作完整完成：例如 plan 可以完整返回含阻塞的计划，next 可以正常返回待决策，而 doctor/config validate/tools verify 对必需验证条件未满足返回 3。任何非交付命令不能因 exit 0 签发质量 allow；详见命令架构的退出语义表。

| 新 CLI 退出码 | 条件 |
|---|---|
| 0 | 请求选中的全部适用义务已完成且无阻断违规 |
| 1 | 请求已完成，存在阻断违规 |
| 2 | 参数语法、未知子命令/语言等用法错误；未启动检查 |
| 3 | 必需义务未完成：缺工具、无能力、坏配置、超时、无效报告、覆盖不全等 |
| 4 | Codeguard 内部故障或无法建立可信结果 |
| 130 | 用户取消；已有结果保留为部分结果 |

聚合优先级：取消 > 内部故障 > 未完成 > 违规 > 请求通过；用法错误只在执行前产生。单检查执行故障不等于进程原生 exit=3；`raw_exit_code` 单独保存，进程未启动或由 signal 终止时可为 null，并有 `termination_reason`。

`lint java` 可以 exit 0，但报告 `delivery_gate.decision=not_evaluated`、`eligible=false`。只有 `check all` 或交付入口完成整份质量 contract，且内容与可信策略匹配时才可 `allow`。完整扫描无适用对象时可以 exit 0，但结果为 `not_applicable`，不能显示“全部已验证”，也不能用空输入签发交付认证。显式 `lint java` 找不到任何 Java 目标则 exit 3，避免目录选错变绿。

`check java` 完成全部 Java 义务；除非计划已证明该项目整份 contract 只含 Java 且所有跨语言依赖义务也覆盖，否则不签发全项目通过。实现初版可统一限制为 `check all`/`gate` 才计算交付 allow。

## 3. 数据模型与协议

`schema_version` 使用 major.minor 字符串，初始目标为 `1.0`；二进制版本、adapter 版本、rulepack 版本分别记录。消费者必须拒绝未知 major，允许兼容 minor 的可选扩展；禁止宽松读取未知枚举后按通过处理。

命令结果共用 report_type/operation/request_id/command_status/exit_code/warnings/next_actions。检查继续使用下述 RunReport，查询、计划、准备、修复和状态操作采用各自 schema；不把所有结果强制变成空 findings 报告。command_status 描述操作完成性，独立于检查 completion、finding、readiness 和 delivery_gate。mcp serve 的服务生命周期与各请求结果分离。

| 对象 | 关键字段 | 不变量 |
|---|---|---|
| CheckRequest | command、selection、root、content_source、operational_options | 用户选择与批准策略分开 |
| PolicyIdentity | source、revision、digest、authority | digest 证明一致性，不单独证明授权 |
| ContentIdentity | source_kind、repository/worktree identity、commit/index/tree digest、manifest digest | 不能仅用路径/mtime/size |
| CheckObligation | id、module、language、category、required、targets、rule_ids | 先有义务，再选择工具，缺工具不能删除义务 |
| CheckPlan | obligations、tasks、dependency_edges、resource_keys、scope_digest | DAG 无环；未执行任务有解释 |
| ToolExecution | executable identity、argv、cwd、env fingerprint、times、raw rc、artifacts | 原始敏感参数只进私有证据 |
| CheckResult | obligation_id、completion、reason、findings、execution_refs、coverage | findings 与 completion 正交 |
| Finding | id、native_rule_id、category、severity、gate_impact、message、location、evidence_refs、baseline_state | 原生严重度与批准策略判定的 blocking/non_blocking/undetermined 分开；不能由自然语言反推规则 |
| Coverage | expected、observed、unresolved、excluded_policy_digest、proof_kind | 数量相等不等于集合相等 |
| GateDecision | decision、eligible、blocking_finding_ids、incomplete_obligation_ids、coverage_mismatch_ids、invalid_ledger_ids、policy_digest | 未完成不能 allow；义务与实际目标精确比对 |
| RunReport | version、run_id、request、policy/content identity、results、gate、summary | human/json/sarif 派生自同一对象 |

当前 Rust 结构消费协议已升至 1.3，并兼容读取 1.0–1.2；`completion=complete|incomplete|not_applicable`，`delivery_gate.decision` 增加 `allow_with_exceptions` 及原始/已处置/活跃发现集合。当前仅有 schema、严格解析与 JSON/human 对话摘要切片，真实报告生产、可信审批和其它格式/宿主消费尚未接通，不能把解析成功的带例外声明作为可信交付。内部故障另置 `run_status=internal_error`，交付决策保持 incomplete。详见[误报白名单设计](false-positive-allowlist.zh-CN.md)。

输出示意（**字段节选，不是可直接通过 schema 的完整样本**）：

```json
{
  "schema_version": "1.0",
  "request": {"command": "check", "selection": "all"},
  "results": [
    {
      "obligation_id": "java:app:lint:p3c",
      "completion": "complete",
      "findings": [{"id": "f-1", "native_rule_id": "native-rule-id", "severity": "error", "gate_impact": "blocking"}]
    },
    {
      "obligation_id": "maven:app:cve",
      "completion": "incomplete",
      "reason": "advisory_database_unavailable",
      "findings": []
    }
  ],
  "delivery_gate": {
    "decision": "incomplete",
    "eligible": false,
    "blocking_finding_ids": ["f-1"],
    "incomplete_obligation_ids": ["maven:app:cve"]
  },
  "exit_code": 3
}
```

`gate_impact` 缺失或非法时拒绝消费报告；`undetermined` 保留发现，并使对应请求未完成。非阻断发现保留在报告中，但本身不产生违规退出码。当前 Rust 领域聚合与四类协议 schema/严格消费边界已实现相关结构判定；原生适配器、批准策略映射、完整报告生成与可信来源核验仍属后续任务，不得把人工构造的字段当作已验证原生证据。

结构化 stdout 只能有一个 JSON 文档；进度、下载提示、工具输出写 stderr 或私有日志。`--output` 成功时将相同序列化报告原子写入目标文件，stdout 仍遵守所选格式；写入失败返回 3，保留已有结果。SARIF 转换保留 tool/rule/location，并用运行通知与 invocation 成功状态表达 incomplete，禁止导出零 findings 就隐去未完成；标准 JSON 始终是完整协议。

源位置使用仓库相对路径；文件名含非 UTF-8 字节时保留可逆编码标识和展示名，不用有损字符串进行身份比较。多位置、跨文件数据流或依赖发现允许 primary location 缺省，但必须存在包/模块定位。归并只对同工具或经过显式规则映射的等价发现进行，保留原始记录和次数；不同工具不能只按文案去重。

## 4. 核心类型、接口与依赖

建议技术栈为 clap、Tokio、serde/serde_json、thiserror；Git 初版使用受控 argv 调用已安装 Git 并校验字节协议。依赖版本与 MSRV 在建仓时实测固定到 Cargo.lock，不在设计文档引用浮动 latest 作为构建锁。

领域类型放 `codeguard-core/src/model/`，每个主要类型单文件；计划、门禁、策略为纯逻辑。核心协调器通过 ports 请求 I/O。接口设计示意：

```text
Adapter.descriptor()                         -> CapabilityDescriptor
Adapter.discover(observations)               -> ApplicabilityEvidence
Adapter.resolve(context, policy, toolchain)  -> ResolvedCheck
Adapter.plan(resolved_check)                 -> AdapterPlan
Adapter.parse(raw_artifacts, termination)   -> ParsedEvidence
Adapter.verify_coverage(plan, evidence)      -> CoverageAssessment
Adapter.plan_fix(finding_set, context)       -> FixPlan

ExecutionPort.run(process_spec, cancellation) -> ToolExecution
SnapshotPort.capture(content_request)         -> SnapshotLease
EvidenceStore.persist(raw_evidence)           -> EvidenceRef
CachePort.lookup(validated_identity)          -> VerifiedCacheEntry | Miss
```

这些是逻辑签名，不是待拷贝编译的 Rust stub。Codeguard 自有的观察、编排、解析、策略判定、门禁和新工程验收均以 Rust 实现，不通过 Python 辅助脚本承载新入口逻辑。runtime 做观察和受控执行；P3C、Maven 等外部原生检查器仍运行官方命令，Rust adapter 只解释注入的数据、提出命令，不私下 `spawn`、联网或修改文件。core 根据计划协调任务，CLI 负责依赖注入。MCP 放在 cli 的入口模块，复用同一核心 API；不得通过调用自身命令拼另一套 verdict。

## 5. 工具适配器协议

每个适配器发布描述包含：adapter ID/version、语言及方言、检查类别、平台/运行时版本范围、所需配置、输入单位、报告格式版本、原生退出语义、缓存前提、修复能力、网络要求和资源锁。

稳定 ID 如 `java.p3c`、`java.checkstyle`、`java.javadoc`、`rust.clippy`、`python.ruff`、`typescript.eslint`。Node 工具可复用实现，但 Vue/Svelte/Astro/GraphQL 的 parser/plugin/context 必须分别验证，不能靠同一个 eslint 二进制宣布所有能力可用。

优先 JSON/XML/SARIF 等结构化报告。只提供文本的工具必须固定兼容版本、locale、语法及 golden fixtures；解析失败保留原文和未完成状态。禁止通用“包含 error 就失败”或“exit 1 就违规”的策略。比如 ESLint 的退出 1 与退出 2 表达不同类别结果，适配器必须按它的契约解释。[ESLint CLI](https://eslint.org/docs/latest/use/command-line-interface#exit-codes)

有效 findings 与环境故障可能同时存在：保留已验证 findings，completion=incomplete。工具 exit 0 也必须核对报告、执行义务、被扫描对象与 freshness；有副作用的检查器不得把改写后的通过当作原始内容通过。

注册表只登记有证据的能力。`format` 存在但没有只读检查能力时，不能自动算作 lint；有原生 check/diff 模式时需证明无修改且报告可解释。无成熟注释检查器的语言可实现确定性 AST 规则，但需独立 capability/正反例验收；否则明确缺口。

## 6. Java 专项

Java 是第一条端到端实现线，不代表只支持 Java。适配计划必须区分以下义务：

| 类别 | 工具/机制候选 | 验证要点 |
|---|---|---|
| 阿里规范 | 官方 P3C PMD 规则实现 | P3C/PMD/JDK 的兼容组合和实际规则加载 |
| 格式与通用规范 | Checkstyle；项目已有格式检查目标 | XML 结构、规则版本、源码级别、只读模式 |
| 注释规范 | Checkstyle Javadoc 规则、Javadoc/doclint | 公共 API 范围、参数返回、继承文档、Lombok/record/生成代码 |
| 安全静态分析 | 项目已接入并经验证的安全分析器，例如 SpotBugs 安全规则或规则扫描器 | 所需字节码、classpath、规则清单与报告完整性 |
| CVE | 经验证的 Maven 依赖扫描适配器 | 解析实际依赖图与版本，漏洞库身份和匹配证据 |
| 构建 | Maven/Gradle 的批准生命周期和目标 | 编译及必要质量任务是否真的执行；测试执行单独声明 |

官方 P3C 包含 PMD 实现；本仓 Checkstyle XML 不应被重命名或包装成“官方 P3C 已通过”。具体兼容版本在真实样本矩阵中确定。[P3C 官方仓库](https://github.com/alibaba/p3c)

Java 解析顺序：项目 wrapper 与声明运行时 → effective model/启用 profile → 模块图/源集/依赖 → 已绑定质量任务 → 缺失义务的受控适配计划。读取 effective model 可能执行构建扩展，因此不是纯静态 `plan` 的隐式行为，需进入执行阶段并留证据。

当前 Maven Javadoc 多文件局部探针只对无继承、依赖、profile、模块、扩展、其它插件和动态配置的简单 POM 重放原文件，并把原 POM 与显式源码一起复制到私有快照。其它 POM 返回未完成，不能用固定模板 POM 产生项目归属的注释问题。此局部执行仍未证明完整生效模型、生成源码和源集覆盖，不签发项目门禁结果。

对于未配置质量工具的项目，返回 `missing` 与具体配置建议；不自动构造或写入 POM/Gradle 质量插件。配置无效返回 `invalid`，无法判定返回 `unknown`。用户或批准策略明确选择启用后再按原生命令运行，不以“缺配置”报告源码违规。`java.commands` 只能提供实际命令，不能以 `echo ok` 满足 P3C。

Maven 父子模块、dependencyManagement、profile、toolchains、annotation processor、测试源集和 Gradle 动态脚本都影响结论。静态模型不完整时保守扩大范围；扩大后仍不能证明规则执行，则未完成。已有 Java 影响闭包可迁移，但版本变动不得自动以 validate/help 替代未证明等价的 lint/CVE 义务。

## 7. CVE、注释、安全类别

CVE 的单位是依赖生态和解析后的组件图，不是源码后缀。Maven/Node/Python/Rust/Go 与通用扫描器按清单能力选择；原生缺失不得偷偷 fallback 成不同覆盖的通过。多个语言共享同一依赖图可以共享证据，但每份义务必须可追溯。

漏洞记录保留 CVE/GHSA/OSV 等原标识、别名、包坐标或 purl、版本、传递依赖路径、匹配方式、受影响区间、修复版本、严重度来源和漏洞库时间/摘要。只有模糊 CPE 匹配时，不伪装成精确包证据；待复核项仍可导致完整性不足，不静默丢弃。

缺 lockfile 不必一律失败：适配器若能解析并固化实际依赖图可继续，否则未完成。漏洞库过期、网络断开或数据库未验证不能产生安全 PASS；离线只使用满足批准 freshness 的本地库。未知严重度不能映射为 LOW 或删除：若策略无法比较则未完成；批准“所有已知漏洞阻断”时可直接判违规。

当前 `check java` 按每份 Java 源码的最近构建根展示 Maven Dependency、OWASP Dependency-Check 与 FindSecBugs 的静态声明状态。静态简单 POM 中已配置的 Maven Dependency Plugin 现可用私有原 POM 副本离线运行原生依赖树，反馈组件和传递边；原生日志即使 `BUILD SUCCESS`，只要有缺 POM 等警告便标未完成。其余 checker 仍未接入原生执行；缺失、跳过、未知或多模块混合配置分别给出原因与下一步。局部依赖图不代表全模块、版本治理、许可证、SBOM、CVE 数据库或安全检查覆盖。

注释规则绑定语言语法及 API 范围。规则包应明确是否允许继承文档、接口/实现重复说明、生成代码排除和 test fixture 的专用规则；这些是预先确认的语义，不是扫描失败后的临时豁免。

安全分为源代码规则、配置/IaC、敏感内容及入库路径策略。`.env`/`*.pem` 等命中现行禁止入库模式时报告 `repository_policy_violation`，不得仅凭文件名宣称发现私钥；内容扫描的 secret finding 另有规则和脱敏证据。公共证书等例外需要正式策略变更，AI 不可自动放行。

## 8. 配置、规则包和工具链锁

保留 `codeguard.json` 作为项目入口，通过显式 schema migration 导入新协议。新增 `codeguard.lock.json` 绑定工具、适配器与规则摘要；不读取旧字段后静默丢弃。

| 配置平面 | 内容 | 覆盖规则 |
|---|---|---|
| 运行参数 | jobs、终端格式、日志位置、预算 | CLI > 环境变量 > 项目默认；不足只产生未完成 |
| 质量策略 | required、rulepack、severity、源集、批准排除、freshness、测试要求 | 可信组织策略及已批准项目修订；运行参数不可弱化 |
| 工具锁 | 工具版本/摘要、JDK、adapter、rulepack、下载来源 | 按 lock 验证；不使用 latest 自动升级 |
| 项目原生配置 | eslint/ruff/checkstyle 等 | 作为实际规则输入；必须与批准策略要求对齐 |

当前 Rust `config validate/explain --policy-candidate FILE` 只实现质量策略**候选**的静态协议检查。候选 1.0 固定 `policy_id/revision`、工具锁原始字节摘要、非空必需检测集合、逐项语言/类别/检测族、规则包摘要、具体规则、源集与阻断严重度、CVE 库时效、测试要求；候选源码排除必须是单个仓库相对文件路径、文件字节摘要、结构化原因及有限到期字段。重复义务、通配排除、未知语言和自写 `approved` 被拒绝。精确源码排除与**发现后的误报白名单**是两种不同处置：前者影响扫描范围，后者保留扫描与原始 finding。两者均只能由独立批准策略赋权。

此候选协议不包含受保护批准来源；CLI 即使核对了本地工具锁摘要，也固定返回 `candidate_unverified`、`effective_policy=null` 和未完成。它还不能证明原生规则实际启用、排除内容/期限在本轮有效、策略修订在 CI 基线中，或形成冻结义务清单。后续可信策略加载必须从受保护宿主/CI 取得基线身份，拒绝同次 PR 用自身策略文件授权自身变更；不能把 `--policy-candidate` 当成批准开关。

`config explain` 显示每一有效值的来源与覆盖原因。原生配置中已有 disable/suppressions 必须列入策略解释和数量/摘要审计；不能把原生配置当作不可审查的隐藏降级入口。PR 同时修改代码与检查配置时，CI 使用可信基线策略评估政策差异；未经批准的新策略不能给本 PR 自行签发通过。

规则包目录设计：

```text
rulepacks/<pack-id>/<version>/
  manifest.json
  rules.json
  tool-configs/
  compatibility.json
  fixtures/
```

manifest 记录来源、许可、分类、规则严重度、工具兼容约束、内容摘要和变更说明。每个 native rule ID 映射稳定的 Codeguard rule ID；删除、改义或改变默认阻断级别属于可审查规则迁移，不靠扫描时随机选择。

默认选择“已存在且匹配锁的项目工具 → 已验证的受管缓存 → 匹配锁的系统工具”；版本不匹配即未完成。安装需要独立 `tools install`，提供下载清单、校验和与安装范围；扫描期间不能用 npx/pip/curl 偷偷安装。可能下载依赖的构建命令须在计划中说明网络模式与锁约束，`--offline` 不得联网；在线模式也不得自动升级规则或工具。

`--offline` 是执行约束，不能只转发工具的 offline flag。adapter 声明可验证的离线条件，运行时使用经平台验证的网络禁止环境执行可能联网的 wrapper/扩展；无法保证时在启动前返回 `offline_isolation_unavailable`，不声称已离线。安装沙箱或容器工具仍是独立准备动作，扫描不得隐式安装。验收必须包含会主动联网的真实子进程。

## 9. 执行器与资源控制

`ProcessSpec` 包含 executable、argv、cwd、受控 env overlay、stdin 模式、deadline、输出预算、资源键、网络策略声明和预期产物。默认 stdin=null；pre-push 输入先由 CLI 读取为结构化请求，不把宿主 stdin 交给扫描器。

Rust 并发读取 stdout/stderr，有界缓冲加私有文件记录；超限必须标识不完整。取消或超时需终止受控进程树并 wait/reap；只丢弃 Child 不等于可靠结束进程。当前 Unix 原型使用 `std::process::Command`、非阻塞管道和独立进程组，并提供拒绝 symlink/覆盖的私有原子原始日志接口；证据索引、脱离进程组的子孙进程及 Windows Job Object 尚待实现，不能用原型验收完整进程树控制。[Rust Command 文档](https://doc.rust-lang.org/std/process/struct.Command.html)

任务 DAG 中相互独立的检查继续收集证据；同一模块构建目录、数据库更新或非并发扫描器通过 resource key 互斥。deadline 是整次请求预算，包含排队/探测/执行/解析/清理；子进程不能各自重置全部预算。

检查计划只读源码：准确内容物化到隔离目录，生成产物写独立区域；执行前后检查源码身份，意外变更导致未完成。禁止跟随路径逃逸 symlink；Git symlink/gitlink/LFS 对象按类型记录，无法获得所需真实源码时不当作普通文件通过。日志私有、原子写，证据索引保留摘要与保留期限；MCP/终端不默认输出密钥或原始环境。

受保护 CI 的可信协调/验证进程、策略、工具锁和最终状态凭据与被测脚本执行域隔离，采用只读挂载、独立身份或等效平台机制，不把签发凭据传入构建进程。执行区仅可写临时构建输出及待核验产物；可信端重新校验内容、报告来源、执行范围和规则覆盖后生成最终结果。单纯不同目录不能满足这个保证；不具备隔离能力时报告能力限制，不宣传抗任意脚本篡改。该要求不会将普通本地模式虚构成安全沙箱。

重试只限可识别的瞬时 I/O 故障，固定次数并保留全部尝试；不重试真实违规以期待随机变绿，不在重试中换规则、目录或工具版本。工具内部编程错误不无限重试。

## 10. 内容快照、缓存及增量证明

| 入口 | 权威内容 |
|---|---|
| 显式 check | 本次请求冻结的工作树清单和内容，检查后复核身份 |
| Git pre-commit | Git 实际传入环境下的 index，尊重 GIT_INDEX_FILE，包括部分提交 |
| Git pre-push | stdin 各 local ref/OID 与 remote ref/OID，支持多 ref、删除 ref、非 HEAD ref |
| CI | 调用方明示且解析为不可变 OID 的待交付内容；合并结果与分支头不能混用 |
| 宿主 PreToolUse | 有边界的预测内容；不声称等价于完整 Shell 执行 |

Git 原始路径使用 NUL 协议，校验对象数量、类型、长度、模式和哈希；SHA-1/SHA-256 按仓库对象格式处理。index 冲突、多仓、初始提交、worktree、submodule、删除/重命名以及输入并发变化均有 fixtures。预测失败阻止认证并提示真实 Git 接入或拆分动作，不扫描另一个仓库充数。

缓存键至少包含：协议/adapter 版本、工具二进制与运行时、规则包、有效配置、目标内容与完整依赖输入集合、模块图、content_source、任务参数、平台、locale、CVE 库身份和 freshness。字节相同但 source kind/授权上下文不同也不得直接复用交付收据。

只缓存完整可验证结果，PASS 和真实违规都可缓存；incomplete/取消/内部故障不提供完成证据。完整缓存记录包含报告摘要和覆盖证明；缓存损坏视为 miss。交付入口不得消费软反馈缓存，可复用满足相同严格身份和可信来源的检查结果，再独立重算交付 gate。本地可写缓存不能作为受保护 CI 的可信外部证据。

增量算法先生成全量义务，再为每项选择执行或复用。无依赖隔离证明的 AST/类型/构建检查扩大到模块或项目；改变规则、编译选项、锁文件或父配置使相关闭包失效。不能以“文件未变”证明依赖它的检查结果未变。

## 11. 修复协议

```mermaid
sequenceDiagram
    participant U as 调用方
    participant C as Codeguard
    participant F as 原生修复器
    U->>C: fix --dry-run
    C-->>U: 精确目标 / 内容身份 / 补丁或计划 / 副作用说明
    U->>C: fix --apply，既有修复授权
    C->>C: 核对目标身份与授权范围
    C->>F: 在隔离副本执行支持的修复
    F-->>C: 退出状态及变化
    C->>C: 校验范围，安全应用，再按相同策略复检
    C-->>U: 执行成功 / 实际变化 / 复检结果分别报告
```

`fixed=true` 需要证明目标变化与该修复有关并完成复检；formatter exit 0 不够。应用 patch 前比较前置内容哈希；并发编辑时停止应用，不能覆盖用户修改。失败有部分变化时保留补丁及真实状态；只回滚自己可证明拥有且未被后续改动的部分。

不自动修改 lint 配置、阈值、忽略、测试或基线来修复 finding；CVE 升级引入行为变化时将依赖变更作为独立修复计划，完整复扫和受影响验证后才声明解决。

## 12. 插件、MCP 与分发

插件 lock 绑定 CLI version、target triple、artifact digest、协议 major、rulepack lock；安装时和运行前验证绑定。原生二进制是统一入口，但 Java/Node/Python 等扫描工具仍需要各自运行时，`doctor` 必须说明。

初始发布候选目标：macOS arm64/x86_64、Linux x86_64/aarch64、Windows x86_64；Linux libc/最低系统版本和每工具平台能力在 S10 实测固化。未验证组合不标稳定。下载原子落盘后切换；校验失败不得使用随机 PATH 版本或静默回退 Python，报告未完成。

MCP 工具参数映射到相同 CheckRequest，保留旧工具名时通过显式协议适配。宿主 Hook exit=2 可能表示阻断，而新 CLI exit=2 是用法错误，必须按报告语义映射，不透传数字。取消、超时、二进制不可用也要有宿主特定测试。

旧通道 `compat legacy-v1` 保持各旧子命令自己的退出协议：常见 check/CVE 为通过0、未验证1、违规2、用法3；混合优先级按旧入口原约定，不把 Dockerfile/CVE/check 的历史差异硬套成一张表。新报告与旧字段同时出现时以明确 protocol 标签解释，保留所有发现。兼容通道不能被新交付 CI 当作等价认证。

切换流程：协议与适配器测试 → 真实仓对照 → 显式指定新二进制 → 宿主/CI 按语义接入 → 全语言与平台验收 → 旧入口弃用。回滚只能回到满足相同严格契约的已验证 Rust 版本；若只能运行旧 fail-open 通道，则交付状态保持未认证，不能为恢复可用性伪造通过。

## 13. 可观测性与度量

每次 run/obligation/task/attempt 使用关联 ID，记录工具耗时、启动/解析/快照耗时、扫描范围、缓存原因、原始退出和未完成原因。日志默认本地，不收集源码遥测；如需远程统计需单独明确采集内容。

证据索引同时记录摘要、受管所有权、引用和保留策略；到期清理不删除活动run/lease、仍被保留收据引用的必要证据、用户源码或tracked问题历史。证据缺失不能继续支持当前认证，可通过重新复检恢复。关联追踪、证据存储和评测门槛已分别进入execution-kernel与binary-distribution规格，具体任务见 [实施覆盖索引](../../openspec/changes/introduce-rust-codeguard-cli/implementation-coverage.md)。

低误报评价至少同时展示：finding precision、漏报率、工具故障误判率、必需义务完成率、被排除/豁免比例、各类别覆盖、p50/p95 耗时及样本数。把规则关闭后 precision 变高视为覆盖退化。指标定义和真实验收见 [coverage-and-acceptance](coverage-and-acceptance.zh-CN.md)。

本技术方案没有声称已达到某个误报率或性能增益；这些必须由任务中的固定语料、人工裁定与真实工具运行证明。

## 批准签名核验接入

局部实现使用 ring 0.17.14 的 Ed25519，精确签载荷原始 UTF-8 文本，不做签后 JSON 重新序列化。签名消息按固定协议域、NUL、精确密钥 ID、NUL、载荷原文组成；载荷及封装 schema 分别为 signed-approval-payload/envelope 1.0。工作区、修订、基线、序号、期限及快照字节摘要都参与签名。普通候选桥接拒绝签名载荷修订与快照内修订不一致，并继续验证候选的精确字节和原生身份。

```mermaid
flowchart LR
    A[项目误报候选] --> B[独立评审与签发环境]
    B --> C[签名载荷与批准快照]
    H[受保护宿主：公钥 撤销 时钟 基线 最小序号] --> V[Rust 签名与上下文核验]
    C --> V
    V --> S[严格快照解析及精确候选绑定]
    S -->|替代链| L[逐跳 Git 提交祖先核验]
    L -. 尚待接通 .-> G[原生完整性与最终门禁]
    S -. 普通批准尚待接通 .-> G
    N[本轮原生发现] --> G
```

当前签名 API 不加载项目公钥，不提供签发 CLI，也不产生交付结论。宿主的公钥来源、轮换/撤销及最低序号状态尚未接线；测试 seed 不属于发行信任锚。局部多跳入口现逐跳核验签名、快照、工作区、序号和签发/历史审核时间，并继续执行精确替代、撤销、无环与 32 跳限制；不能凭一个当前签名认可未核验的历史摘要。前序代码基线的 Git 祖先关系仍待受保护宿主核验。所有宿主输入仍须来自独立信任边界，同权限本地进程不可宣称不可绕过。

局部 Git 联合入口现补齐原生逐跳祖先观察：先完成签名与精确替代绑定，再核对前序基线属于子基线历史；只接受完整同格式提交 ID，拒绝浅历史、缺对象、非提交、噪音或失败报告。禁用 replace/graft、commit-graph 加速和 lazy fetch，各跳共享截止时间与取消标记。原签名 API 单独成功仍不证明祖先关系；宿主还须认证 Git 工具、隔离仓库、可信公钥及本轮原生检查，联合 API 的 BoundToPinnedSnapshot 也不等于交付 allow。

## 工具安装缓存发布的当前基础

相邻 Rust runtime 已提供 `publish_tool_bytes`：调用方先冻结有界字节和预期 SHA-256；在已有、当前用户拥有且非共享可写的目录中，以固定目录 FD 创建私有暂存，写后核验，原子新增内容寻址文件，再核验最终文件。重复条目必须复核，损坏、链接、FIFO 或权限异常不覆盖；取消/到期/写入失败不返回成功，暂存正常清理。收据只描述缓存发布，不能充当可信锁、发行批准、平台兼容或质量通过。

正式 `tools install` 还须先接入批准来源、下载清单、平台/包格式与预览/apply 服务，再调用该基础层。当前不开放未批准候选的 CLI apply。不可中断的文件系统调用及同用户恶意改写不提供强隔离保证；发布后失败可能保留完整制品，后续须重新核验恢复。验收见相邻 tests/acceptance/tool-cache-publication.md。


### HTTPS 发行包传输局部实现

相邻 Rust runtime 的 download_verified_package 只接收冻结 URL/大小/摘要及显式重定向 authority，TLS 验证与响应校验后返回有界字节。连接、重定向和包流继承同一绝对期限/取消；不使用环境代理、自动重试或内容解压，不写缓存、不授予发行批准。11 项本地 TLS 及相关回归见相邻 codeguard-cli/tests/acceptance/package-https-transport.md。正式 tools install 尚未调用此入口，可信来源/网络授权、下载至发布编排、运行时安装、恢复和跨平台仍须完成；check/plan/doctor 不会自动联网安装。


### Javadoc 项目检查模式

明确提供 Maven 上下文时，项目检查只运行原 POM 多文件探针，避免同项目类型互相引用造成孤立单文件假阻塞。前置/生效范围不确定时保留具体原因，不回退；未选择 Maven 时 JDK 单文件局部观察保持可用。反馈 0.23.0 与 Javadoc 0.3.0 标明 probe_mode，Maven 模式不嵌入单文件诊断。局部观察数不证明完整源集、有效配置或交付通过。验收见相邻 codeguard-cli/tests/acceptance/javadoc-project-mode-selection.md。

### Checkstyle 局部 CLI 实施进展

相邻 Rust 工程现在提供 `codeguard lint java FILE --checker checkstyle --java-tool PATH --checkstyle-jar PATH --config PATH --format json`，使用显式原配置和私有源码/配置快照调用统一 runtime，反馈原生规则身份、位置与严重度。当前静态注释配置限定已验证内置模块；未知配置/资源保留待解析，不改写为默认规则。JSON 0.1.0 与真实工具局部验收详见相邻 `tests/acceptance/java-checkstyle-cli-local.md`。项目级 check、完整工具/配置/规则范围及任务/白名单/交付接线仍未完成；局部观察不变成普通通过。
