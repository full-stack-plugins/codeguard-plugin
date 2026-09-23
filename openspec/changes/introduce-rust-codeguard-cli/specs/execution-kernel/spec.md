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

### Requirement: Rust execution SHALL bound and close process lifecycles

执行 MUST 使用字面 argv、明确 cwd/env/stdin、总预算及有界输出，记录真实终止原因。超时/取消/超限 MUST 停止并回收受控进程树，保留部分证据；同一构建目录的冲突任务 MUST 互斥。工具规则解释 MUST 不属于通用进程执行层。

#### Scenario: Child process outlives its parent
- **WHEN** 工具创建子孙进程后发生取消
- **THEN** 在声明的平台保证内终止并回收整棵受控进程树，不能仅丢弃句柄

### Requirement: Rust snapshots SHALL bind the actual delivery input

真实 pre-commit MUST 尊重 GIT_INDEX_FILE；pre-push MUST 读取每条 ref/OID 元组，不能假定 HEAD；CI MUST 绑定明确不可变内容。字节完整性、类型、哈希、路径和执行前后身份 MUST 校验。快照失败或源内容被检查器修改 MUST 未完成，不改真实 index；宿主预测 MUST 不冒充完整 Shell 语义。

#### Scenario: Push targets a non HEAD ref
- **WHEN** 用户推送的 local OID 与当前 HEAD 不同
- **THEN** 检查实际 local OID 及指定推送范围，不能用 HEAD 通过替代

#### Scenario: Partial commit uses an alternate index
- **WHEN** Git hook 环境含 GIT_INDEX_FILE
- **THEN** 检查该 index，保留真实工作树及 index 内容

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
