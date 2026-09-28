## Purpose

定义统一 Rust 二进制与宿主插件的制品绑定、兼容入口、迁移和发布证据，使源码、发布版本、实际安装和运行能力能够分别验证，避免未验证回退产生假通过。

## ADDED Requirements

### Requirement: Network installation SHALL verify signed selection and exact host permission before downloading

签名网络安装编排 MUST 在任何下载请求前核验原签名/清单/锁、独立宿主范围/时钟/最低序号、本机平台及精确工具，并要求完整定位清单。宿主网络许可 MUST 为有界规范主机:端口集合，包含初始站点，禁止通配、环境代理推导或项目自批；重定向仅沿同一明确许可范围，传输 MUST 复用受控 runtime 的 TLS/字节/预算契约。签名/目标/平台/许可失配 MUST 在请求前拒绝且不写缓存。

下载后的制品发布 MUST 复用签名包发布编排，重新核验下载前固定范围和时间、包/完整树及原锁定位，沿用绝对期限/取消，不执行包内入口。只有完成的制品收据可返回；网络成功或测试签名不得替代真实宿主信任来源、运行时齐备、原生可运行性或质量门禁。真实网络测试 MUST 单独明确站点/固定内容，使用测试信任密钥时不得声称真实发行批准。

#### Scenario: A site is missing from the independent host grant
- **WHEN** 签名与精确目标相符，但初始下载 authority 不在宿主许可中或许可含通配
- **THEN** 返回固定未批准/范围无效诊断，不发起下载请求，不写缓存

#### Scenario: A public HTTPS fixture traverses the complete service
- **WHEN** 明确授权测试站点及固定提交内容，以专属测试密钥绑定声明调用网络编排
- **THEN** 生产 TLS 客户端核验精确字节并按原锁发布临时缓存，不执行制品；该证据不升级为真实发行信任根或宿主验收


### Requirement: Signed package publication SHALL bind source, content, clock and original locator

明确调用的离线包发布编排 MUST 在文件系统写入前验证发行签名和原清单/锁、选择精确工具及本机平台，仅使用具有完整定位协议的清单。raw MUST 使用精确长度/摘要/原锁定位关联，归档 MUST 关联完整树和可选 bundle，再调用受控发布层重新核验内容及文件系统。编排 MUST NOT 重写工具锁、下载网络资源或执行包内入口；制品收据不得证明运行时齐备、原生可运行性或质量通过。

签名和受保护时钟 MUST 在内容核验前、发布前及发布后核对，时钟不得早于初始固定上下文或本轮前次观察；取消和绝对期限共享全部阶段。签名/目标/包/期限失配或发布前取消 MUST NOT 写入制品。发布后时钟/期限/预算失败可能保留完整内容，但 MUST 返回失败，重试仅在重新核验来源/内容/文件系统后复用；不得删除既有损坏目标或回退旧清单猜测定位。宿主信任/撤销/防回滚真实性及网络安装许可仍须独立建立，项目 JSON 不能自行授予权限。

#### Scenario: A signed raw or archive package is published at the original lock locator
- **WHEN** 明确调用编排，独立宿主输入下签名有效、原始包/布局相符且缓存安全
- **THEN** 发布入口与原工具锁精确相同；重复调用重新核验后复用，不执行制品或声称完整工具准备

#### Scenario: The final clock becomes unavailable after publication
- **WHEN** 完整制品已发布但最终时钟不可核验
- **THEN** 不返回成功，完整内容可保留；后续新调用必须重新验证全部绑定和时间后才能复用

#### Scenario: Existing published bytes are tampered
- **WHEN** 同一内容寻址目标已存在但字节损坏
- **THEN** 返回失败并保留损坏目标，不覆盖或删除它来制造安装成功


### Requirement: Distribution signatures SHALL bind original manifest and lock bytes under independent host constraints

发行来源绑定 MUST 使用独立 `codeguard.distribution.v1` Ed25519 协议域，签名覆盖精确密钥 ID 与原始 release_json UTF-8 文本，不复用白名单批准域或签后重序列化载荷。版本化封装/载荷 MUST 拒绝未知及重复字段，限制输入长度。载荷 MUST 固定发行者、通道、平台、递增序号、签发/失效时间、原始清单及锁字节 SHA-256。

可信公钥、其发行者/期限/撤销状态，以及预期通道/平台、可信时钟、最低序号和最长有效期 MUST 由受保护宿主独立提供，不从被检查项目或同次候选变更自证。核验 MUST 拒绝范围失配、过期/未来签发、撤销、回滚与缺时钟；核验后仍 MUST 严格解析清单、绑定全部制品至同一原锁，并要求所选平台确实存在。只读结果 MUST NOT 可由 JSON 构造或直接声明安装/网络/质量权威；签名相符仅证明在给定宿主输入下的字节/范围绑定，正式执行仍须验证真实宿主来源、网络授权、最终时钟/撤销及安装计划。

#### Scenario: A valid release signature binds exact manifest bytes
- **WHEN** 宿主范围及有效密钥下签名相符，原清单/锁摘要精确一致且全部制品绑定成功
- **THEN** 返回只读清单/锁摘要、平台、序号与期限，不联网安装或授予门禁权威

#### Scenario: Another protocol or changed bytes are replayed
- **WHEN** 提供白名单域签名，或已签 release_json、清单、锁字节被修改
- **THEN** 签名或精确字节绑定拒绝，即使 JSON 的业务内容看似相同

#### Scenario: A signed manifest disagrees with the locked artifact
- **WHEN** 清单摘要/签名相符但制品身份与原工具锁不同，或所选平台无制品
- **THEN** 拒绝来源绑定，不以签名替代严格制品核验


### Requirement: Package HTTPS transport SHALL preserve frozen bytes under the shared budget

已授权调用方使用的包下载运行时 MUST 核对冻结 URL、非零摘要与 1..128 MiB 长度，验证 TLS，不采用环境代理、自动重试或内容解压。初始 URL MUST 为无凭据、查询或片段的 HTTPS；重定向 MUST 手动检查，最多五跳，禁止降级或凭据，跨 authority 仅允许显式规范 host:port 集合。重定向查询可承载 CDN 签名，但 MUST NOT 在反馈中输出原 URL、查询或底层错误。下载 MUST 继承原绝对截止时刻和取消信号，在等待连接、响应和读取期间响应取消，不得逐跳重置预算。

最终响应 MUST 为 200，仅接受未编码或 identity 内容；传输编码只允许单个 chunked，不得与 Content-Length 混用。声明长度及实际解码框架后的包长度、SHA-256 MUST 与冻结输入精确一致；超长最多多读一个字节，截断、编码歧义、超时、取消或失配不得返回半成品。成功值只证明字节传输，不授予发行来源、安装、准备或门禁权威，也不写缓存。生产入口不得提供禁用 TLS 或由项目指定信任根的选项。

#### Scenario: A valid TLS stream returns the frozen package
- **WHEN** TLS 验证成功且响应为固定长度、chunked 或关闭分隔的精确声明字节
- **THEN** 返回经过长度/摘要核验的有界包；不写文件、不授予来源或安装权威

#### Scenario: A transport coding changes byte semantics
- **WHEN** 响应声明 gzip 内容或 gzip, chunked 传输编码、坏长度、截断或错误摘要
- **THEN** 返回固定诊断，不向后续展开或发布返回字节

#### Scenario: An unapproved redirect or cancellation occurs
- **WHEN** 发生跨未批准 authority、HTTP 降级、凭据、歧义 Location 或共享预算取消/到期
- **THEN** 不继续目标请求或返回成功，不重置预算，也不回显敏感原 URL


### Requirement: Downloaded archives SHALL bind the complete tree before publication

完整归档下载入口 MUST 在发请求前核对下载与展开声明使用同一包 SHA-256，并拒绝未知格式、非法入口、零摘要、无效展开上限或非法完整树摘要。下载、展开、入口及完整树核验 MUST 使用同一绝对期限/取消，不得把网络成功直接当作可发布树。返回结果 MUST 保留所有普通成员及空目录；后续发布 MUST 重新核对树摘要和文件系统，不授予发行来源/运行时/安装权限。raw 下载亦只能在精确包摘要相符后提交独立发布层。测试 CA MUST 只用于局部测试，不能成为生产默认信任。

#### Scenario: HTTPS carries a complete ZIP or tar.gz package
- **WHEN** 包、入口与完整树声明均相符，后续调用方明确使用私有临时缓存
- **THEN** 普通文件、入口和空目录完整保留，独立发布后磁盘内容相符；没有发行批准或原生工具执行结论

#### Scenario: The package hash is consistent but the declared tree differs
- **WHEN** 下载成功而展开树与完整声明摘要不一致
- **THEN** 返回树摘要失配，不返回可发布的局部成功

#### Scenario: Download and archive declarations disagree
- **WHEN** 展开声明的包摘要不同或入口/格式/预算/完整摘要无效
- **THEN** 请求前拒绝，不发送网络请求也不写缓存

### Requirement: Archive bundle roots SHALL be projected explicitly without discarding other members

归档安装 MUST 在选择子目录前验证完整归档树。bundle 根 MUST 是显式声明的规范目录；空根仅表示明确选择整树，不得根据包名或首个目录猜测。投影 MUST 按完整目录边界去除前缀，保留选中空目录，并按既有 bundle 树协议核对预期摘要。未消费成员 MUST 保留原路径与内容供安装计划单独处理，不得无声丢弃。非法根、失配、取消或预算耗尽 MUST NOT 返回成功。内容匹配 MUST NOT 自行授予来源批准、工具准备或安装完成状态；正式落盘仍须核验文件系统与制品身份。

发行清单 1.1 MUST 在声明 bundle 树摘要时显式提供 `bundle_archive_root`，无 bundle 时不得声明映射，raw 包不得携带映射。1.0 清单 MUST 保持可读，但不能凭旧声明猜测 bundle 根。内容关联 MUST 绑定清单原字节与同一锁原字节、精确工具/平台、包大小/摘要、入口摘要和 bundle 摘要；关联成功仅证明内容，不授予下载、安装或可信来源权威。

发行清单 1.2 的归档制品 MUST 声明完整 `install_tree_sha256`，覆盖入口、bundle 及其余普通成员，raw 包不得声明完整树。内容寻址安装目录 MUST 为 `<install_tree_sha256>.bundle`；锁入口 MUST 精确为该目录加归档入口，锁 bundle 根 MUST 精确为该目录加显式包内根，空包内根指向安装目录自身。绑定 MUST 拒绝路径不一致而非重写锁。完整布局 MUST 保留原包相对路径、空目录和所有普通成员，并分别核验完整安装树和可选 bundle 子树；不存在 bundle 时仍核验完整树。旧清单缺少完整安装树声明时不得猜测或自动升级为安装计划。

清单 1.2 的 raw 制品 MUST 将锁入口精确绑定为 `<binary_sha256>.bin`；即使来源引用摘要相符，非规范入口也必须拒绝，不得重写锁或发布到另一名字。raw 内容关联 MUST 核对同一原清单/锁、精确工具/平台、包长度及分块二进制摘要，采用共享期限/取消信号，不返回半成品。借用结果 MUST 保持输入不可变且不复制制品内容；诊断不得转储原始字节。旧清单可观察，但不能据此自动推导新版 raw 安装定位。内容相符和本机版本观察 MUST NOT 授予发行批准或质量门禁权威。

#### Scenario: A raw reference hash matches an incorrect lock path
- **WHEN** 清单来源引用摘要与锁一致，但锁入口不是对应二进制摘要的 `.bin` 文件
- **THEN** 新版绑定返回 raw 定位失配，预览不推进到包内容核验或安装，不重写锁

#### Scenario: Frozen raw content is verified and published locally
- **WHEN** 明确新版定位、包长度/摘要相符，底层发布层被已授权调用方使用
- **THEN** 发布返回的相对入口与原锁一致，原锁可重新核验；借用字节不复制，不从内容匹配或原生版本观察推导批准/门禁通过

#### Scenario: A wrapper depends on files outside the selected bundle
- **WHEN** 入口位于包内 `release/bin/tool`，bundle 为 `release/libexec`，另有其它普通成员
- **THEN** 完整安装布局保留全部原相对路径，入口和 bundle 锁路径指向同一完整树内容寻址目录；实际发布后用原锁核验入口和 bundle，不修改锁或声称原生可运行

#### Scenario: Content outside the bundle changes
- **WHEN** bundle 子树摘要不变，但其它成员使完整安装树与声明不同
- **THEN** 完整布局关联失败，不以 bundle 相符为依据发布剩余内容

#### Scenario: Similar sibling directories exist in a package
- **WHEN** 显式选择 `release/libexec`，包内另有 `release/libexec-other` 和外部启动器
- **THEN** 仅去除 `release/libexec/` 的精确前缀，其它成员以原路径和内容返回；投影目录摘要与对应实际目录摘要一致

#### Scenario: An invalid member lies outside the selected root
- **WHEN** 选中的子树合法，但原树其它成员含非法路径或冲突
- **THEN** 完整树核验失败，不得通过过滤该成员获得成功投影

#### Scenario: The requested root is missing or has a wrong identity
- **WHEN** 根目录不存在、指向文件、大小写不一致，或选中树与预期摘要不匹配
- **THEN** 拒绝映射，不回退整包或另一个目录，也不发布局部制品

#### Scenario: A legacy manifest declares a bundle without a root
- **WHEN** 1.0 清单可以绑定锁，但没有包内目录映射
- **THEN** 只读观察仍可读取，bundle 内容关联返回缺少映射，不猜测目录或启动安装

#### Scenario: Package identity disagrees with the bound declaration
- **WHEN** 包大小/摘要、入口或选择目录与同一绑定声明不一致
- **THEN** 不返回成功 bundle，保持来源未批准和安装未完成状态

### Requirement: Bundle directories SHALL publish without exposing partial trees or replacing existing content

完整目录发布 MUST 先验证输入树及预期 bundle 摘要，在已固定的受管缓存目录描述符下独占创建私有暂存，按规范成员构建文件/目录，拒绝链接及特殊类型并核验所有权、权限、硬链接、完整成员集合和字节内容。文件及目录 MUST 同步后才使用原生不覆盖的原子目录重命名；平台不支持该操作时 MUST 返回未完成，不得降级为可覆盖 rename。最终目录 MUST 重新核验才返回相对内容寻址收据。重复安装 MUST 重新核验后复用；已存在但内容、成员或权限不同的目录 MUST 保留且拒绝，不得替换。

取消及预算 MUST 在构建和核验期间检查；发布前失败 MUST 清理本次已创建成员，清理不得跟随链接或删除被替换的目录。进程崩溃或外部篡改导致的未清理暂存 MUST NOT 充当已安装制品。发布后同步/核验/预算失败可能留下完整目录，MUST NOT 返回安装成功，后续重试须重新核验。此收据 MUST NOT 授予来源批准、原生可运行性或其它未消费成员的安装完成状态。

#### Scenario: Two installers race to publish the same tree
- **WHEN** 两个进程同时发布同一内容寻址目录
- **THEN** 只有一个新目录发布成功，另一方完整核验后复用；最终名字不暴露半成品，也不覆盖目录

#### Scenario: Existing content is tampered or linked
- **WHEN** 已存在目录含篡改文件、额外/缺失成员、链接、FIFO、错误权限或硬链接
- **THEN** 拒绝复用并保留原目录，不覆盖为新制品

#### Scenario: Cancellation occurs after staging begins
- **WHEN** 本轮暂存目录已存在但还未原子发布时取消
- **THEN** 不返回成功，清理本次成员；最终内容寻址名字不出现

### Requirement: Plugin execution SHALL bind a verified runtime artifact

插件 MUST 绑定 CLI 版本、平台、制品摘要及协议版本；不匹配或不可用时 MUST 报未完成，不得随机使用 PATH 版本或自动回退旧 Python 产生通过。doctor MUST 明示原生扫描器的 JDK/Node/Python 等外部依赖。

#### Scenario: Runtime checksum is invalid
- **WHEN** 安装二进制摘要不符合插件锁
- **THEN** 拒绝将其作为可信检查器，交付未完成

### Requirement: Compatibility SHALL be explicit and versioned

旧 CLI/MCP/Hook 兼容 MUST 具名并按旧入口分别映射协议；禁止透传新退出码或隐式改变旧语义。新交付门禁 MUST 不接受 legacy-v1 的 fail-open 结果作为新认证。兼容移除 MUST 有发布迁移说明。

#### Scenario: Legacy caller expects findings to exit two
- **WHEN** 旧调用经 legacy-v1 接入
- **THEN** 使用该旧入口的退出约定，同时不声称已满足新门禁

### Requirement: Release claims SHALL require layered evidence

stable 发布 MUST 分别提供真实工具、平台、Git/CI、宿主安装与运行验收；不以编译、mock 测试、tag 或市场清单替代。全语言完成声明 MUST 满足语言迁移要求。回滚 MUST 不降低已确认的交付契约。

#### Scenario: Release artifact exists but host cannot run it
- **WHEN** GitHub release 有二进制但某宿主无法启动
- **THEN** 该宿主验收保持未完成，不宣称已交付

#### Scenario: Only a legacy fail-open rollback is available
- **WHEN** 新运行时故障且没有符合新契约的旧 Rust 版本
- **THEN** 交付保持未认证，不能以旧放行行为恢复绿色门禁

### Requirement: Quality claims SHALL use independently labelled stratified evidence

评测 MUST 使用有来源/摘要/工具锁的分层语料和独立holdout，由人工或已确认oracle裁定；争议单列，不用模型投票充当真值。MUST 报告每语言/类别的样本量、TP/FP/FN、precision/recall、区间、工具故障误判率、完整率、假通过数及同覆盖性能。零发现的precision MUST 不可估计，不能记100%；排除扩大或义务删除不能当作误报改善。

设计中的发布验收目标 MUST 固化到批准评测配置：确定性必备场景零假通过/零工具故障误判，预置真问题全检出，关键安全/CVE回归零漏报，有足够裁定样本的adapter/category其precision的95% Wilson下界至少0.98。证据不足不得借全局平均升级为充分验证；调整目标需独立批准。性能绝对门槛在实测基线后冻结，不凭Rust技术选择宣称已达成。

#### Scenario: Evaluation returns no findings or too few labels
- **WHEN** 某类别没有finding或统计证据不足
- **THEN** 展示不可估计/证据不足，不报告100%准确率或借其它类别平均值宣布充分验证

#### Scenario: Excluding files improves an apparent precision score
- **WHEN** 优化后排除范围扩大或必需义务减少
- **THEN** 覆盖差异可见且不能据此通过等价优化验收，原批准门槛保持
