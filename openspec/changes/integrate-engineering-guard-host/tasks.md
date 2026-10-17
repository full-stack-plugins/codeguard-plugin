# codeguard-plugin 工程守卫集成任务

来源：2026-10-17 按既有总体规划重建；原引用路径在当前检出及本地可用历史中未找到。本变更是新重建的任务定义，不声称恢复了历史原文，也不声明实现或用户验收已完成。依据为 [traceability](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/traceability.md)、[acceptance](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/acceptance.md)、[protocol](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/protocol.md) 与本仓现有维护约束。

状态：全部待实施。完成状态只在本账本维护；实现与所需真实环境验证齐备后才能勾选。每行列出的依赖是前置验收义务，不把文档创建当成前置实现完成。

## 1. 实施与验证

- [ ] 1.1 **EG-H01** [owner=codeguard-plugin] 固定现有 Rust/Python 入口、发布制品及协议身份和候选/正式资格；缺核心不弱化回退。 依赖：EG-K01。规格：EG-CGH-001。

- [ ] 1.2 **EG-H02** [owner=codeguard-plugin] 为发现、保存、提交、推送等事件建立 session/worktree/task/action/subject 映射；真实暂存与HEAD差异反例验证。 依赖：EG-H01, EG-K04。规格：EG-CGH-002, EG-CGH-004。

- [ ] 1.3 **EG-H03** [owner=codeguard-plugin] 接公共单飞、运行序列与取消结果；双会话/双工作树/迟到PASS反例保持隔离，不扩用户授权。 依赖：EG-H02, EG-K05, EG-K06。规格：EG-CGH-003。

- [ ] 1.4 **EG-H04** [owner=codeguard-plugin] 建立可独立验收的宿主反馈与必需检查桥；缺策略/缺结果/超时不能放行，CodeGuard原始结果映射保持诚实。 依赖：EG-H01, EG-H02, EG-K07。规格：EG-CGH-001, EG-CGH-004。

- [ ] 1.5 **EG-H05** [owner=codeguard-plugin] 对诊断和恢复建议做数据化呈现、输出预算及脱敏；恶意报告不能执行，PostTool反馈不冒充操作授权。 依赖：EG-H04。规格：EG-CGH-004。

- [ ] 1.6 **EG-H06** [owner=codeguard-plugin] 接 CLI/MCP/Hook 同请求及动作候选复核，授权由控制端独立核验；重放不同候选必须拒绝。 依赖：EG-H02, EG-K10, EG-K18。规格：EG-CGH-001, EG-CGH-002。

- [ ] 1.7 **EG-H07** [owner=codeguard-plugin] 完成宿主能力和事件兼容矩阵的独立真实试验；记录支持/未知平台，不以K19整体完成作为试验前置。 依赖：EG-H04, EG-K18。规格：EG-CGH-005。

- [ ] 1.8 **EG-H08** [owner=codeguard-plugin] 完成宿主桥与CLI/MCP N/N-1兼容和未知major负例，形成固定制品组合，供总体发布使用。 依赖：EG-H07。规格：EG-CGH-001, EG-CGH-005。

- [ ] 1.9 **EG-H09** [owner=codeguard-plugin] 验证会话授权复用、取消/重入/恢复与损坏回执；既有授权范围不变不重复问，最新失败不能恢复旧通过。 依赖：EG-H03, EG-H05, EG-K09。规格：EG-CGH-003, EG-CGH-004。

- [ ] 1.10 **EG-H10** [owner=codeguard-plugin] 执行真实宿主全链路及升级/卸载/回滚、受管技能来源验证与市场版本同步；只有证据齐备才启用候选桥。 依赖：EG-H06, EG-H08, EG-H09, EG-K20。规格：EG-CGH-001, EG-CGH-005。
