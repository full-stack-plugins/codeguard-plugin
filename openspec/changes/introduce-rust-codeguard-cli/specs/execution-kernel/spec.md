## MODIFIED Requirements

### Requirement: Existing entry points SHALL remain compatible

显式 legacy-v1 兼容入口 MUST 保留原 CLI 子命令、四个 MCP 工具、五类 Hook 路径/JSON/退出约定及旧 Python 导入接口，除非另有弃用发布。用户配置 MUST 经显式转换，语言注册与外部受管技能所有权不变。

本规范中原有 Python 模块路径、顺序遇错终止、软缓存不供硬门禁、基线豁免、Java 轻量版本检查、fail-open 和旧退出码要求 MUST 限于 legacy-v1。Rust 新入口 MUST 遵守本 change 的统一义务、缓存证明、基线仅分类、独立任务继续及严格交付契约。其余原始证据、字节校验、内容身份、隐私与不修改用户 index 等正确性要求 MUST 延续。执行内核不得导入宿主 SDK。

#### Scenario: Legacy script invocation
- **WHEN** 旧 manifest 从原路径执行兼容脚本
- **THEN** 使用显式旧协议，不静默改写数字语义，也不能签发新交付认证

#### Scenario: Rust execution encounters an independent failed task
- **WHEN** 一个任务失败且其它任务不依赖它
- **THEN** 仍收集其它任务证据，失败依赖项保留未完成，不继承旧顺序短路作为全批通过依据

## ADDED Requirements

### Requirement: Static input inspection SHALL reject special files without waiting for peers

配置、工具锁、发行清单及其它静态协议输入 MUST 在同一已打开文件句柄上确认普通文件类型与大小边界，不得以可读路径或文件名证明输入有效。Unix 打开 MUST 拒绝目标符号链接并采用非阻塞模式，FIFO 无写入端时不得在类型判断之前无限等待；类型或大小无效返回未完成诊断，不执行输入、不修改源码或签发准备成功。此机制 MUST NOT 被描述为任意文件系统调用的硬超时保证，其它平台必须独立验收同等约束。

#### Scenario: A manifest or lock path points to a FIFO without a writer
- **WHEN** 静态工具库存/安装预览读取的输入是无写入端 FIFO
- **THEN** 不等待写入端，拒绝特殊文件并反馈 unreadable/未完成；不写入工作区、不将其计为源码违规或工具就绪

### Requirement: Rust execution SHALL bound and close process lifecycles

执行 MUST 使用字面 argv、明确 cwd/env/stdin、总预算及有界输出，记录真实终止原因。超时/取消/超限 MUST 停止并回收受控进程树，保留部分证据；同一构建目录的冲突任务 MUST 互斥。工具规则解释 MUST 不属于通用进程执行层。

#### Scenario: Child process outlives its parent
- **WHEN** 工具创建子孙进程后发生取消
- **THEN** 在声明的平台保证内终止并回收整棵受控进程树，不能仅丢弃句柄

#### Scenario: Clean child exits before reader threads are scheduled
- **WHEN** 原生工具成功退出且 stdout/stderr 已关闭，但并行负载推迟了读线程调度
- **THEN** 在请求剩余总期限内继续排空并取得真实 EOF；不得因固定短排空窗口把完整结果误判为读取失败，超过总期限仍返回未完成

### Requirement: Rust snapshots SHALL bind the actual delivery input

真实 pre-commit MUST 尊重 GIT_INDEX_FILE；pre-push MUST 读取每条 ref/OID 元组，不能假定 HEAD；CI MUST 绑定明确不可变内容。字节完整性、类型、哈希、路径和执行前后身份 MUST 校验。快照失败或源内容被检查器修改 MUST 未完成，不改真实 index；宿主预测 MUST 不冒充完整 Shell 语义。

#### Scenario: Push targets a non HEAD ref
- **WHEN** 用户推送的 local OID 与当前 HEAD 不同
- **THEN** 检查实际 local OID 及指定推送范围，不能用 HEAD 通过替代

#### Scenario: Partial commit uses an alternate index
- **WHEN** Git hook 环境含 GIT_INDEX_FILE
- **THEN** 检查该 index，保留真实工作树及 index 内容

### Requirement: Managed artifact publication SHALL preserve identity and ownership

受管工具安装的缓存发布 MUST 与质量结果缓存分开。安装字节须有上限并核对预期 SHA-256，缓存根须归当前用户且不可被其它用户写入；使用固定目录描述符和不覆盖的原子发布，拒绝缓存根/目标链接、损坏或权限不符的已有制品。取消、到期或校验失败不得发布未完成文件；正常退出清理暂存，重复相同字节只能在再次核验后复用。缓存写入收据只说明字节发布，不证明锁/发行来源批准、平台兼容、可启动或质量通过；CLI 安装仍须独立核验批准来源。

#### Scenario: Another file already occupies the content-addressed tool destination
- **WHEN** 安装发布目标已存在但内容、文件类型、所有权或权限不匹配
- **THEN** 保留原目标，安装未完成并给出冲突；不得覆盖或跟随链接，也不能用文件名中的摘要自证完整

### Requirement: Distribution package streams SHALL be bounded and verified before extraction

发行包读取 MUST 绑定预期非零 SHA-256、精确传输大小和共享截止时间，传输长度上限为 128 MiB；超出声明长度最多探测一个字节即拒绝。读取中断重试 MUST 继承剩余预算，取消、期限、短流、长流、摘要失配、分配或传输失败 MUST NOT 返回可展开/发布的成功字节。传输诊断 MUST 脱敏。读取器每次读取前后 MUST 核对截止时间和取消；实际网络层 MUST 独立实施单次连接/读取超时，不能以流层预算检查声称可中断任意阻塞读取。验证只证明包字节与输入声明匹配，MUST NOT 自授发行来源批准、平台就绪或门禁通过。

#### Scenario: Stream exceeds or differs from the declared package
- **WHEN** 包字节短缺、超长、摘要失配或读取失败
- **THEN** 返回固定未完成诊断，不向展开/发布阶段交付成功字节；无穷流不能按声明长度之外继续累积内存

#### Scenario: Cancellation or deadline changes during a package read
- **WHEN** 单次 read 返回时已经取消或超过共享截止时间
- **THEN** 拒绝本次字节，不重置预算、不返回校验成功；网络读取超时义务仍由传输层完成

### Requirement: Archive expansion SHALL validate all members before publication

ZIP/tar.gz 展开 MUST 先核对包摘要，绑定明确入口及其二进制摘要，并核验包内所有成员，不得只检查入口而忽略其它路径。路径穿越、绝对/平台歧义路径、重复及大小写碰撞、文件/目录与祖先冲突、链接/设备/特殊类型 MUST 拒绝。普通文件展开总量不得超过请求预算及 512 MiB，全包成员最多 10000；压缩容器及头信息亦须有独立有界预算。损坏压缩数据、CRC、隐藏尾随数据、缺入口、错摘要、取消或到期 MUST NOT 返回局部成功。展开结果只是冻结文件集合，MUST NOT 自授发行批准、bundle 校验、安装或准备通过；落盘仍须受管发布层重新核验路径归属和权限。未实现的扩展、压缩算法或归档类型 MUST 明确未完成，不静默跳过。

#### Scenario: Valid entrypoint coexists with a dangerous archive member
- **WHEN** 入口及其摘要正确，但其它成员路径穿越、重复、为链接/设备或发生文件目录冲突
- **THEN** 拒绝整个展开结果，不向发布层交付部分成功文件，不生成源码违规

GNU 长路径与局部 PAX MUST 作为下一条普通文件/目录的有界扩展处理，消费后清空；GNU 数据最多 1025 字节并有明确 NUL 终止，单条 PAX 数据最多 64 KiB，记录长度必须精确且全部消费。重复键、重复局部扩展、矛盾路径、孤立扩展和 malformed 记录 MUST 拒绝。生效路径仍须遵守所有原路径约束；完整扩展路径可覆盖被截断的旧头字节，不得将旧头 UTF-8 断裂误判为有效路径非法。局部 PAX size MUST 控制真实文件数据边界并参与总量/溢出检查，不得一律要求与旧头相等或按旧头推进。权限、所有者、时间及 xattr 描述字段 MUST NOT 从归档恢复；未实现的全局路径/大小、linkpath、sparse 或字符集变换须明确未完成。

#### Scenario: Local extension changes the effective path or size
- **WHEN** 合法 GNU/PAX 给下一文件提供完整路径或 PAX size 与旧头不同
- **THEN** 使用经验证的生效路径及大小，按生效大小核对内容和后续块边界；下一文件不沿用局部扩展，原摘要、路径、类型及资源检查不降低

#### Scenario: Extension is malformed, ambiguous or orphaned
- **WHEN** 路径穿越、重复键、矛盾扩展、大小溢出/超限、长度错误或扩展无后续成员
- **THEN** 返回固定未完成诊断，无局部成功或文件写入；不从后续文件或旧头猜测缺失的扩展语义

#### Scenario: Archive fails integrity, resource or format validation
- **WHEN** ZIP/gzip 数据损坏、展开超限、入口缺失/摘要错误、附加隐藏数据或未支持的扩展存在
- **THEN** 返回固定脱敏未完成原因，不写工作区；取消和期限沿用包读取/发布的同一剩余预算

### Requirement: Complete archive trees SHALL bind all bundle contents

完整归档树 MUST 保留显式空目录及所有隐式父目录，文件集合与完整树入口 MUST 明确区分；旧文件集合消费者不得被静默改成新返回类型。完整树使用现有本机 `codeguard-bundle-tree-v1` 的目录/文件记录、路径长度、内容大小/摘要及本机排序/目录遍历顺序核验，不得以入口匹配或文件总数代替 bundle 内容身份。公开结构被外部构造或改写后 MUST 重新校验路径、父目录、类型/大小写冲突、总量和预期非零精确摘要；最多 100000 树条目、512 MiB 总文件字节和 128 MiB 单文件。摘要计算 MUST 继承共享截止时间/取消并检查内容块。匹配只证明声明树内容，不得授予发行来源、目录发布、完整依赖闭包、准备或质量通过。

#### Scenario: An empty directory or delegated library differs from the locked bundle
- **WHEN** 入口字节相同，但归档中空目录被删除或委托库被修改
- **THEN** 完整树摘要不匹配，包不能按该 bundle 身份进入正式发布；保留具体未完成原因，不生成源码违规

#### Scenario: A caller provides a forged or incomplete in-memory tree
- **WHEN** 树含穿越/重复/大小写冲突、缺父目录、超限或无效预期摘要
- **THEN** 拒绝树核验，不按路径文本推断条目已验证；取消和到期无成功摘要或批准

### Requirement: Rust cache reuse SHALL prove obligation equivalence

缓存 MUST 绑定内容、依赖闭包、工具/运行时、adapter、规则、配置、平台、来源和 CVE 库身份/时效。只有完整有效结果可复用；硬门禁不得直接消费软反馈缓存，必须核验严格身份和可信来源并重算 gate。缺少依赖隔离证明 MUST 扩大扫描或未完成。

#### Scenario: Configuration changes with identical size and time
- **WHEN** 配置等长替换且 mtime 未变
- **THEN** 缓存不命中，不能按元数据复用旧 PASS

### Requirement: Rust fixes SHALL preserve ownership and verify outcomes

fix MUST 区分 dry-run 与 apply，检查目标身份及范围；应用前置条件不符 MUST 不覆盖用户编辑。执行成功、观察到变化、复检确认修复 MUST 分开报告。修复 MUST NOT 自动降低规则、阈值、忽略或修改测试期待以消除违规。

#### Scenario: User edits during fix planning
- **WHEN** 修复计划生成后原文件发生变化
- **THEN** 不覆盖用户内容，重新规划或报告未完成

#### Scenario: Formatter succeeds without changes
- **WHEN** 原生 formatter exit 0 且内容未变
- **THEN** 只声明执行成功，不声称 fixed=true

### Requirement: Offline and trusted CI execution SHALL enforce their declared boundaries

离线执行 MUST 在可验证的不联网条件下运行，包括被调工具的子进程；无法提供条件时 MUST 在执行前报告未完成。可信 CI 的策略、工具锁、验证器和状态签发凭据 MUST 与被测脚本执行区隔离；项目产物 MUST 经可信端核验，不得让项目脚本直接签发或篡改认证。普通快照目录 MUST NOT 被宣传为满足该隔离。

#### Scenario: Wrapper attempts network access in offline mode
- **WHEN** 被调 wrapper 主动发起网络访问
- **THEN** 声明支持的离线环境阻止访问；无法保证的平台拒绝开始并报告能力不足

#### Scenario: Project script tries to rewrite policy or receipts
- **WHEN** 被测项目脚本尝试改写可信策略、工具或最终状态
- **THEN** 受保护执行边界拒绝写入，脚本生成的收据不能直接作为 gate 认证

### Requirement: Execution observability SHALL correlate evidence without changing verdicts

执行链 MUST 关联request/run/obligation/task/attempt ID，记录快照、启动、执行、解析、缓存及总耗时、终止原因、缓存理由和完整性。原始argv/env/诊断 MUST 仅进入受控私有证据，公开轨迹脱敏。默认遥测 MUST 留在本地，不自动上传源码、凭据或诊断。度量采集不可把incomplete改成PASS，日志/证据写入故障须独立呈现。

#### Scenario: A failed execution has partial useful evidence
- **WHEN** 原生工具在产出finding后超时
- **THEN** 从run和obligation可追溯已保留证据与真实终止原因，公开轨迹不泄漏原始敏感参数

#### Scenario: Metrics storage is unavailable
- **WHEN** 指标存储失败但原检查已形成结论
- **THEN** 保留原质量结论并明确观测故障；必要证据无法保存时报告操作未完成，不伪造检查成功

### Requirement: Evidence storage SHALL preserve ownership and active references

日志、报告、快照与缓存 MUST 使用精确受管路径、适合平台的私有权限与原子写入，拒绝symlink路径逃逸。证据索引 MUST 记录摘要、保留策略和有效引用；清理 MUST 不删除用户源码、tracked问题历史、活动run/lease或仍被保留收据引用的必要证据。损坏/丢失证据不得支持当前认证，允许重新复检恢复；磁盘或权限失败不得触发无限重试或扩大删除范围。

#### Scenario: Cleanup encounters an active run and a user file
- **WHEN** 到期本地缓存与活动run、同名用户源码同时存在
- **THEN** 只清理有所有权和到期依据的非活动产物，其余保持，不能按整个codeguard目录删除

#### Scenario: A private log path redirects through a symlink
- **WHEN** 日志或报告目标指向受管范围以外
- **THEN** 拒绝越界写入并保留真实失败状态，不覆盖目标或把缺日志当检查通过
