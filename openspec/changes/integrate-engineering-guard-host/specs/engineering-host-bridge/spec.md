## Purpose

为 Partme Guard 提供 engineering-host-bridge 的可观察行为契约，统一已批准约束、当前候选和独立验证证据的关联，并明确未知、失败、兼容模式与越权情况下不得伪造工程通过的边界。

## ADDED Requirements

### Requirement: EG-CGH-001 Pinned bridge

插件 SHALL 经固定摘要运行时和协议能力协商桥接工程守卫；未启用项目保留现有行为，缺运行时不静默下载、安装或使用 PATH 同名程序替代。

#### Scenario: EG-CGH-001 contract behavior
- **WHEN** 受控模式锁定制品缺失或摘要不符
- **THEN** 报告准备阻塞；不签发通过，不回退较弱 Python 结论

### Requirement: EG-CGH-002 Correct event subject

插件 SHALL 为宿主事件绑定真实 cwd、仓库、任务、操作、候选和事件 ID，区分局部反馈、提交、推送和 CI 范围。

#### Scenario: EG-CGH-002 contract behavior
- **WHEN** 从集合目录通过 git -C 操作另一个仓库
- **THEN** 使用真实目标身份，不借用插件仓或调用者的证据

### Requirement: EG-CGH-003 Singleflight interaction

插件 SHALL 通过统一 operationId 与任务/内容去重检查和提示，保留不同内容的独立运行；不直接修改兄弟插件状态。

#### Scenario: EG-CGH-003 contract behavior
- **WHEN** 多个 Hook 重入同一事件或取消后旧结果迟到
- **THEN** 不重复运行/请求同一授权，旧结果不能覆盖新状态

### Requirement: EG-CGH-004 Nonmisleading feedback

插件 MUST 保留旧退出语义及原始结果，结构化投影缺工具、部分覆盖、风险和失败；无有效报告不能依据退出码显示工程通过。

#### Scenario: EG-CGH-004 contract behavior
- **WHEN** 本地局部检查 exit 0 但 delivery_decision=not_evaluated
- **THEN** 显示局部状态与缺口，不放行受控交付

### Requirement: EG-CGH-005 Host and distribution gates

插件 SHALL 逐宿主、平台、制品及兼容模式验证；受管技能从来源仓更新，真实安装/触发/取消/阻断不能被 manifest 或重放代替。

#### Scenario: EG-CGH-005 contract behavior
- **WHEN** CLI fixture 通过但 Codex 实际 Hook 未验收
- **THEN** 该宿主保持未验证，不能宣称全部宿主上线
