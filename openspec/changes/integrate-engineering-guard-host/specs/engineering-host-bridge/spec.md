## Purpose

定义 codeguard-plugin 在七产品工程守卫体系中的证据和集成契约；沿用现有插件边界，不以报告、模型或本地 Hook 自称交付授权。

来源：2026-10-17 按既有总体规划重建；原引用路径在当前检出及本地可用历史中未找到。本变更是新重建的任务定义，不声称恢复了历史原文，也不声明实现或用户验收已完成。依据为 [traceability](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/traceability.md)、[acceptance](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/acceptance.md)、[protocol](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/protocol.md) 与本仓现有维护约束。

## ADDED Requirements

### Requirement: EG-CGH-001 Pinned bridge

系统 SHALL 宿主桥必须调用固定版本及摘要的 CodeGuard/公共执行入口，保留当前 CLI 与旧 Hook 行为；缺核心、策略或平台资格时不得回退为工程通过。

#### Scenario: EG-CGH-001 reject unsupported or unsafe input

- **WHEN** 固定运行时损坏或不支持当前平台
- **THEN** 返回准备阻塞，不选择 PATH 上另一工具

#### Scenario: EG-CGH-001 preserve supported behavior

- **WHEN** 已验证组合处理同一请求
- **THEN** 跨入口产生同一领域结果并保留运行身份

### Requirement: EG-CGH-002 Correct event subject

系统 SHALL 每类事件必须绑定实际 session/worktree/task、动作和候选类型；保存、暂存、提交、合入报告不得互用，真正执行前重新核对目标身份。

#### Scenario: EG-CGH-002 reject unsupported or unsafe input

- **WHEN** index 报告用于不同 HEAD 或合入候选
- **THEN** 拒绝复用并要求验证实际候选

#### Scenario: EG-CGH-002 preserve supported behavior

- **WHEN** 事件与绑定候选完全相符
- **THEN** 仅使用该候选的有效结果

### Requirement: EG-CGH-003 Singleflight interaction

系统 SHALL 相同身份和输入的并发事件可单飞；不同内容、会话、工作树不可误去重。最新失败/取消不能被迟到旧 PASS 覆盖。

#### Scenario: EG-CGH-003 reject unsupported or unsafe input

- **WHEN** 两个会话并发且一个新运行失败
- **THEN** 分别保留归属，新失败不被旧 PASS 清除

#### Scenario: EG-CGH-003 preserve supported behavior

- **WHEN** 完全相同的重复事件到达
- **THEN** 复用同一次受管运行，不重复申请相同范围授权

### Requirement: EG-CGH-004 Nonmisleading feedback

系统 SHALL 反馈必须区分执行、规则结论、覆盖和信任；保存后反馈不声称 Git 放行；报告内容只作为数据，公开摘要脱敏，违规与 incomplete 同时保留。

#### Scenario: EG-CGH-004 reject unsupported or unsafe input

- **WHEN** 报告含指令、秘密或超时前违规
- **THEN** 不执行报告内容，保留违规与限制，公开内容脱敏

#### Scenario: EG-CGH-004 preserve supported behavior

- **WHEN** 有效检查无违规但范围局部
- **THEN** 仅报告局部结果，不称全面通过

### Requirement: EG-CGH-005 Host and distribution gates

系统 SHALL 安装、事件适配、取消、重入、卸载和升级回滚须按宿主/平台逐格验收；候选桥与正式启用必须区分，缺格明确 unverified。

#### Scenario: EG-CGH-005 reject unsupported or unsafe input

- **WHEN** 只有离线 Hook 重放通过
- **THEN** 不声明真实宿主验收完成

#### Scenario: EG-CGH-005 preserve supported behavior

- **WHEN** 某宿主真实安装及允许/拒绝/取消/回滚均完成
- **THEN** 只登记该宿主版本和平台的证据
