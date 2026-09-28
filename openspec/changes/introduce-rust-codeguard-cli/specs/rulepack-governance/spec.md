## Purpose

定义质量策略、原生配置、工具链和规则包的权威及变更流程，确保降低误报依靠准确证据而不是智能体自行关闭检查，并保留可复核的例外与历史问题记录。

## ADDED Requirements

### Requirement: Quality policy SHALL be independent from operational options

必需检查、规则、阈值、排除、测试要求及漏洞库时效 MUST 来源于批准策略。CLI/env 运行参数 MUST NOT 弱化它们；同一 PR 的策略修改 MUST NOT 在未经批准时为自身代码签发通过。config explain MUST 显示原生配置及 suppression 的有效来源和差异。

项目可写的质量策略候选 MAY 经严格 schema 与内部引用校验，但即使其工具锁字节摘要匹配，也 MUST 仅作为未获信任的待审输入；候选的必需检查、阈值或排除 MUST NOT 变成有效门禁。候选源码排除至少绑定精确仓库相对文件路径、文件内容摘要、原因和期限，不得以通配、目录或本地 `approved` 字段扩大范围。正式批准来源与基线修订须由独立信任边界核验。

#### Scenario: Agent raises the severity threshold
- **WHEN** 智能体通过参数、环境或本地配置把批准阈值提高
- **THEN** 新交付门禁不接受该弱化，记录策略差异而非通过

#### Scenario: A checker disables all native rules
- **WHEN** 原生配置改为禁用必需规则或以自定义空命令替代
- **THEN** 覆盖校验不能满足义务，不以命令成功通过

#### Scenario: A local policy candidate matches a local tool lock
- **WHEN** 项目提供结构正确的策略候选，且其摘要恰好匹配同一工作树的工具锁
- **THEN** config 只能报告本地引用相符及批准来源未核验，不生成有效策略、白名单授权或交付通过

### Requirement: Rulepacks and toolchains SHALL be versioned and locked

rulepack MUST 有版本、规则来源/许可、稳定规则映射、内容摘要及工具兼容范围。检查 MUST 验证工具/运行时/配置/规则锁；扫描 MUST NOT 隐式安装、升级或改写项目配置。安装 MUST 是单独显式动作，离线检查 MUST 不联网。

`rules list <language|all> [path]` MUST 复用当前项目发现和版本化规则映射，分别展示检查器静态配置状态、已知候选映射及尚缺的规则目录。候选映射 MUST 保留来源、许可、内容摘要与兼容版本，不得因为项目存在配置文件就声称具体规则已启用、已执行或获批准。目录尚不完整时 MUST 返回未完成和下一步，不把空规则列表解释为项目无需检查。命令 MUST 只读，不执行项目脚本或原生检查；项目可写的同名规则包、白名单或批准字段不得替换内置清单或取得授权。

#### Scenario: A configured checker has only candidate rule mappings
- **WHEN** Python 项目具有静态可识别 Ruff 配置，规则目录只有未批准 F401/E501 映射
- **THEN** rules list 分别展示配置声明及带来源/摘要的候选映射，逐规则启用和执行状态仍未核验，返回未完成而不是生效规则集合或质量通过

#### Scenario: Project rule files claim approval or contain executable configuration
- **WHEN** 项目写入同名规则包或自批字段，并在动态配置中放入副作用脚本
- **THEN** rules list 只复用静态发现，不运行脚本，不用项目文件替换内置规则映射，不生成批准或门禁效果

#### Scenario: A requested language has no complete native rule catalog
- **WHEN** rules list 请求已登记但尚无完整规则目录的语言，或 all 中包含该语言
- **THEN** 返回该语言及各检测类别的目录缺口和准备动作，不把没有映射视为没有规则或已经通过

#### Scenario: Tool version differs from the lock
- **WHEN** PATH 工具与锁不匹配
- **THEN** 未完成并给出准备动作，不自动下载 latest

### Requirement: Historical findings SHALL remain findings

基线 MUST 只用于 new/existing 分类和趋势，不得默认豁免存量违规。所有阻断规则 MUST 对新旧发现一致生效。基线不可读或无法比较 MUST 不删除当前发现。

#### Scenario: A harmless edit leaves an old violation
- **WHEN** 完整检查在未修改源码中检出已有的阻断违规
- **THEN** 可标 existing，但仍阻断，不因历史身份或 diff 位置豁免

### Requirement: Exceptions SHALL require independently verifiable authority

例外 MUST 同时绑定规则、范围、内容身份、到期时间、原因和可核验的批准身份，不能采用永久无期限例外。agent 声称获批、skipGate、可写 JSON 或普通 Git config MUST NOT 本身构成授权。例外 MUST 保留原始发现及非通过检查状态；外部批准交付必须与普通 PASS 区分。文档 MUST 明示同权限本地进程不可提供不可绕过保证。

#### Scenario: Agent writes a local approval flag
- **WHEN** 智能体写 `approved=true` 或 `codeguard.skipGate=true`
- **THEN** 新交付门禁不接受为授权，不改变违规或未完成状态

#### Scenario: A real exception expires
- **WHEN** 经批准例外超过有效期或不匹配当前范围
- **THEN** 不应用该例外，保留完整门禁要求

#### Scenario: An old approval is reused after the frozen policy changes
- **WHEN** 白名单处置引用旧策略修订，但宿主冻结的当前修订不同、缺失或无效
- **THEN** 不应用该处置，保留活动阻断及未完成；不能以处置中自写的修订作为当前策略来源

#### Scenario: Approval expires while a check is running
- **WHEN** 发现取证时批准仍有效，但最终门禁的可信时刻已达到到期边界，或最终时钟缺失/为零/早于取证时刻
- **THEN** 不应用白名单，保留活动阻断并返回未完成；MUST 使用最终门禁时刻而非扫描开始时刻，不能重放旧 observed_at 维持过期豁免

#### Scenario: Expiry is absent or content changes
- **WHEN** 例外没有到期时间或当前内容不匹配获批身份
- **THEN** 拒绝应用例外，不能沿用此前批准关闭问题

### Requirement: Existing dot-prefix scope SHALL remain explicit

本变更 MUST 保留普通检查面点前缀默认忽略、不逐路径告警，以及入库安全和配置发现两项例外。覆盖报告 MUST 记录有效策略与汇总范围，不能宣称排除内容已检查。新增扫描或放宽禁止入库策略 MUST 经独立策略变更。

#### Scenario: Dot configuration and secret coexist
- **WHEN** 项目含点前缀 linter 配置、普通点前缀源码和拟入库 `.env`
- **THEN** 配置仍发现、普通源码按策略忽略、入库安全照常运行，三者不混为同一排除

### Requirement: False-positive allowlists SHALL be exact, authorized dispositions

误报白名单 MUST 仅处置经原生工具复现、人工裁定的精确 finding；MUST 保留原始 finding、规则依据、复检命令和批准引用。条目 MUST 绑定原生检查器/规则/类别、目标和内容身份、finding 指纹、工具/适配器/rulepack 身份、误报依据、可信策略修订及有限期限。源码目标按仓库相对路径与本次文件字节摘要匹配；依赖目标按组件、解析版本、依赖图及 advisory 身份匹配。首版 MUST NOT 允许通配符、正则、整目录或整条规则豁免。重复性规则误报应通过经批准的 rulepack 或项目策略修订及正反例解决。

匹配 MUST 发生在原生结果解析、路径归属、内容和覆盖复核之后。缺字段、失配、过期、冲突或未获独立批准的条目 MUST NOT 放行；可信来源不可验证时相关策略义务为 incomplete。`false_positive` MUST 与仍然真实存在但被批准接受的 `accepted_risk` 分开。工具故障、坏报告、原生 suppression、未配置必需检查和覆盖不足 MUST NOT 被白名单处置。

白名单 MUST 作为 finding 的处置层实现，不得作为扫描排除、原生命令 suppression 或“无发现”的证明。对系统性误报，MUST 优先定位原生规则、适配器或项目策略的根因，并通过受保护 rulepack/策略修订及正反例回归纠正；不得自动把多个精确条目提升成规则级白名单。误判纠正、驳回、批准、过期、撤销和身份失配 MUST 保留历史事件并关联原稳定 finding/任务；手动修改任务状态不改变门禁。评测 MUST 保留白名单前的原始发现及人工裁定，不得用增加白名单掩盖误报率或漏报率。

配置外扫描属于适配器/配置归属错误，MUST 在 finding 生成前纠正；例如项目只启用 P3C naming 规则，却因隔离探针模板额外加载 comment 规则，额外诊断不得进入该项目 finding/白名单申请。若项目生效规则集尚不能确认，义务保持 incomplete，不得把多扫的诊断交由白名单逐条抵消。

#### Scenario: A Rust CVE observation has an unverified advisory database
- **WHEN** cargo-audit 的 advisory 与本轮 Cargo.lock 包身份一致，但 RustSec 数据库来源或时效未经可信边界核验，且项目提供自写的精确白名单条目
- **THEN** 原始 advisory 和未完成原因仍反馈到对话，条目只作为待审线索，不命中有效例外、不关闭任务或给出交付通过

`rules whitelist propose` MUST 从本次原生报告及内容复核取得完整 finding、工具制品、适配器和 rulepack 身份，再生成可评审候选；不得用历史任务的首次观察、版本字符串、当前文件名或占位摘要补造缺失身份。若这些证据不全，MUST 返回未完成及逐项补证据/原工具复检动作，不写可批准候选，不改变现有门禁。

当调用者显式指定当前原生工具路径时，候选预览 MUST 只读核对该普通文件的字节摘要与扫描报告所记工具摘要；无法读取或不一致时 MUST 隐去旧观察并要求原工具复扫。该复核本身不证明工具获批准，也不把尚缺的规则包、策略或独立裁定身份补齐。

白名单纠错 MUST 关联原稳定 finding、原决策与修订链。已批准决策不可原地改写；更正时 MUST 保留撤销事件，生成引用旧决策的新候选，并由独立批准边界在同一可信策略修订中固定撤销与新增集合。新候选未获批准、旧决策已撤销或修订链冲突时 MUST NOT 凭任一条目放行。`rules whitelist explain` MUST 说明脱敏的匹配/失配字段、批准状态和下一步；智能体提出误报或修订候选不等于批准，不能把改任务文本或本地决策文件当成纠错完成。

纠错输入 MUST 指明原决策 ID、同一稳定 finding ID、结构化纠错原因（误批、范围过宽、证据失效、根因已修复之一）及本轮原工具复检引用；替代候选还 MUST 具有新的决策 ID、`replaces_decision_id` 和完整精确身份。只撤销而不替代时不得虚构新候选。CLI MUST 返回可审阅的撤销/替代提案和受影响 finding 列表，但提案写入 `codeguard/decisions/` 不得自行生效。受保护发布边界 MUST 校验旧决策存在、引用链无环、撤销与新增集合原子发布，并拒绝旧新条目同时命中或替代候选扩大到其它目标。无法完成复检或权威校验时 MUST 保留原任务为待处理/未完成，不得将白名单修订写成代码修复。

#### Scenario: Exact approved false positive is found again
- **WHEN** 同一原生工具、规则、目标内容及策略身份产生同一 finding，且误报裁定仍有效
- **THEN** 仅该 finding 标记 whitelisted_false_positive，保留原始证据和批准引用，同文件其它 finding 照常判定

#### Scenario: A similar finding has different identity
- **WHEN** 相同规则发生在另一文件、文件字节变化、依赖版本/图/advisory 改变或工具语义版本变化
- **THEN** 原条目不匹配，新 finding 继续接受正常门禁

#### Scenario: Disposition identity disagrees with its native finding
- **WHEN** 待应用白名单的完整观察身份与裁定一致，但原生 finding 来自不同工具、不同主目标或依赖版本，或缺少可核对的主定位
- **THEN** 门禁保留原始阻断并返回未完成；可信宿主必须显式固定 checker/tool/category/obligation 映射，缺映射、冲突映射或未知映射不得按名称后缀猜测。源码/项目主定位核对精确路径，依赖主定位核对精确组件及非缺省版本；不能借次要位置放过主目标不同的发现

#### Scenario: A matching approval is paired with a stale native finding identity
- **WHEN** 裁定与其附带的观察身份相同，但本轮原生 finding 缺少独立冻结的完整身份，或该身份中的源码字节、发现指纹、工具/适配器/rulepack 摘要、依赖图或 advisory 与裁定不同
- **THEN** 保留原始及活动阻断并返回未完成；历史报告缺该字段也不得借旧批准放行。宿主仍须从本轮原工具与内容复核取得该身份，项目可写字段本身不能证明来源可信

#### Scenario: Conflicting dispositions arrive in a different order
- **WHEN** 同一 finding 有多条处置，或同一批准决策 ID 被复用于不同 finding，且输入顺序改变
- **THEN** 门禁在应用前识别全部冲突，保留相关活动阻断，不将任一条先到处置标为 whitelisted；两种顺序产生相同未完成结论与发现集合

#### Scenario: Candidate decisions reuse a finding ID with different targets
- **WHEN** 两条白名单候选使用同一稳定 finding ID，但指向不同源码路径、内容或依赖目标
- **THEN** `rules whitelist list/explain` 将两条都标记为冲突，`explain` 不返回单条身份匹配结论；最终门禁也不得从冲突候选中选择有利于放行的一条

#### Scenario: An approved identity is attached to an invalid obligation ledger
- **WHEN** 原生发现的义务归属与所在结果不一致、所在义务未知/无效，或该义务覆盖集合失配
- **THEN** 不应用该发现的白名单处置，即使观察与裁定身份及检查器映射一致；保留原始/活动阻断并返回未完成

#### Scenario: Ruff configuration changes after original checker verification
- **WHEN** 复检后的 Ruff 配置内容变化、配置优先级变化，或旧报告缺少可核对的当前配置身份
- **THEN** next 要求重新运行原工具，不沿用旧纠错事件或附件；纠错提案返回 verification_required 而不记录新提案，普通误报提案不展示旧观察为当前证据。源码不变、旧配置字节不变也不能抵消高优先级配置切换

#### Scenario: The Rust adapter binary changes after a Ruff finding
- **WHEN** 本轮 Ruff finding 的局部报告记录了 CodeGuard 适配器二进制摘要，但工作台读取候选时当前二进制字节已不同，或取证时无法安全取得摘要
- **THEN** `propose` 不沿用旧观察或补造摘要，返回具体缺口与原工具重扫动作；匹配的二进制摘要只补齐适配器观察身份，未经批准的 rulepack 和人工误报裁定仍不得转成有效候选或门禁例外

#### Scenario: A recorded correction has a missing or edited readable projection
- **WHEN** 已保留纠错事件，但可读附件缺失、写入失败或被用户编辑
- **THEN** 保留事件引用，单独反馈附件恢复动作；重复记录可重建缺失附件，但不得覆盖用户编辑。next 仅展示与当前复检和事件重建字节一致的附件，附件文字不得取得批准、执行或关闭权威

#### Scenario: A signed approval binds a snapshot to protected host context
- **WHEN** 宿主选择签名批准来源，并在扫描前固定公钥、撤销状态、可信时钟、工作区、策略修订、受保护代码基线与最小修订序号
- **THEN** 按域分隔和原始签名载荷核验签名、范围、期限、防回滚与快照字节；快照内部修订也须与签名修订一致。项目自选公钥、签名成功或同次 PR 自写 approved 均不得替代宿主来源与原生检查完整性核验；坏签名、撤销、过期、范围/字节/修订错配及无可信时钟不放行

#### Scenario: A signed replacement chain contains an unverified predecessor
- **WHEN** 当前替代条目签名有效，但前序签名损坏/撤销、历史审核上下文无法核验、工作区不符或序号/时间乱序
- **THEN** 不绑定完整批准链，当前签名不得覆盖前序缺口；每个历史摘要须由该跳签名核验取得，禁止项目自行提供历史 pin。历史候选在受保护审核时刻无效、链截断/多余/成环或超限也不放行

#### Scenario: A disposition is reused outside its approved workspace or baseline
- **WHEN** 白名单处置的工作区或当前批准代码基线与宿主独立冻结的范围不一致，或任一范围缺失/无效
- **THEN** 最终门禁不应用该例外，保留原始及活动阻断并返回未完成；签名预览须携带已核验的范围，不能在投影时丢失。仅接受完整非零 SHA-1/SHA-256 基线，不将 HEAD 等可变引用当作身份；该基线属于当前批准上下文，不能从工作树或处置字段反向生成宿主信任

#### Scenario: Historical review occurs after its replacement was issued
- **WHEN** a predecessor signature is valid at its supplied protected review time but that review time is later than the child approval issuance
- **THEN** Codeguard SHALL reject the revision chain rather than treating valid signatures alone as valid chronology

#### Scenario: Signed predecessor refers to an unrelated code baseline
- **WHEN** 签名修订链有效，但前序代码基线不是后续基线的 Git 祖先（允许同一提交）
- **THEN** 宿主批准绑定入口拒绝该链；完整对象缺失、浅历史、Git 失败或预算耗尽均返回未完成而非认可关系。仅接受完整 SHA-1/SHA-256 提交 ID，禁用 replace/graft 与按需远程取对象，不将本地 Git 观察本身当作可信宿主来源

#### Scenario: A valid signature binds an all-zero code baseline
- **WHEN** 签名和宿主上下文一致，但基线是 SHA-1 或 SHA-256 全零 ID
- **THEN** 普通与替代批准入口均拒绝该上下文；全零值不得代表受保护提交或缺省基线

#### Scenario: A legitimate historical approval has expired today
- **WHEN** 当前替代条目有效，前序批准在其受保护历史审核时刻合法，但今天已经过期
- **THEN** 可以核验历史关系，不能因此自动接受当前条目；当前签名与候选仍按本次可信时钟核验，历史密钥最新撤销状态仍须检查

#### Scenario: Agent proposes or self-approves a whitelist entry
- **WHEN** agent 写本地候选、`approved=true`，或同一 PR 提交尚未进入可信基线的批准条目
- **THEN** 候选不改变门禁，受保护 CI 只使用此前可信策略修订；批准、期限和来源均可解释

#### Scenario: A local finding lacks exact checker artifact identity
- **WHEN** 持久任务仅记录规则、路径和指纹，但本轮报告缺少工具制品、适配器或 rulepack 摘要
- **THEN** `rules whitelist propose` 返回未完成和缺失身份列表，不猜测摘要、不产生可批准候选，原 finding 继续阻断

#### Scenario: Native finding has no reviewed rule mapping
- **WHEN** 本轮原生检查检出真实规则，但该规则在适配版本下尚无核对过的 CodeGuard 规则映射
- **THEN** 白名单提案明确区分“规则映射待核对”与“已有映射但尚未批准”，指出原生规则和工具版本核对动作，不制造候选或授权；项目自写 `approved=true` 也不能改变原 finding 或稳定任务

#### Scenario: Required checker fails despite an old whitelist match
- **WHEN** 必需原生检查器本次崩溃、报告归属无效或必需规则被未经批准的 suppression 隐藏
- **THEN** 结果保持 incomplete，不以历史白名单条目推断本次检查通过

#### Scenario: An import failure is mislabeled as a false positive
- **WHEN** 本地报告无法解析或归属，智能体为其写误报白名单候选
- **THEN** 失败收据只指引修复报告或原生检查环境，不生成可白名单处置的 finding；候选不能改变未完成状态

#### Scenario: Two native findings collide on one stable ID
- **WHEN** 同一轮的不同原生规则或义务给出相同 finding ID，其中一条带有精确误报批准
- **THEN** 保留两条原始发现，拒绝将该 ID 的批准扩展到另一条；受影响义务与交付结果保持 incomplete，要求修正身份冲突后重跑

#### Scenario: Similar false positives recur across a project type
- **WHEN** 同一原生规则在多个独立目标上反复被人工裁定为误报
- **THEN** 生成规则/适配器根因调查并提供正反例；不自动创建通配白名单或修改原生排除

#### Scenario: User corrects an unreasonable finding
- **WHEN** 用户指出某条 finding 是误判，并提供反例或复现线索
- **THEN** 智能体先复核原工具结果、有效规则和目标身份，保留原 finding 与任务，提出精确误报候选或规则/适配器修复建议；只有独立批准的精确候选在下一次完整检查中匹配，才对该 finding 标记 `whitelisted_false_positive`，并向对话展示批准引用、到期时间及 `allow_with_exceptions` 或剩余阻断原因

#### Scenario: Approved decision is revoked or task text changes
- **WHEN** 已批准条目被撤销，或有人手动勾选、改写其修复任务
- **THEN** 保留原始 finding 与历史裁定；撤销后本轮原生 finding 重新按正常门禁判定，任务文字不能赋予批准

#### Scenario: User edits an approved whitelist entry
- **WHEN** 用户或智能体修改已批准条目的理由、目标、工具身份或期限
- **THEN** 修改后的字节必须重新批准；不得沿用旧批准、自动续期或扩大范围。对话说明失配字段和复核动作，纠正记录关联同一稳定问题；有效误报处置不标记为源码修复完成

#### Scenario: An approved false-positive decision needs correction
- **WHEN** 人工复核发现已批准条目过宽、误批或其证据已失效，并提出替代候选
- **THEN** 旧决策及撤销原因保持可追溯，新候选引用旧决策且在独立批准前不生效；本轮原生 finding 重新阻断或保持未完成，不能同时消费冲突的旧、新决策

#### Scenario: A corrected decision has no replacement or attempts to broaden scope
- **WHEN** 评审只撤销误批条目，或替代候选试图覆盖另一文件、依赖节点、原生规则或内容版本
- **THEN** 只撤销时原 finding 恢复正常门禁；扩大范围的替代候选被拒绝并单独调查，不因引用旧决策而取得授权
