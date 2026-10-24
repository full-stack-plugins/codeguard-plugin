> ⏸️ **已冻结（2026-10-09 用户决定）**：engineering-guard 系列整体冻结，暂停实施。保留任务与文档，不开始新任务、不新增计划、不并行推进实现；解冻需用户明确批准。

# 工程守卫实施任务

状态：全部待实施。本轮仅完成规划；下面的 fixture/测试模块为拟新增，不声称已经存在或执行。只在实现、目标 RED→GREEN、受影响回归及所需真实环境证据齐备后勾选。

依赖前缀：K=codeguard 内核，F=codegraph-plugin，H=codeguard-plugin，R=codereview-plugin，G=gitflow-plugin，W=flowguard-plugin。跨仓依赖通过任务 ID 引用，完成状态只在所属仓账本维护。所有实现先复核当前 HEAD 与用户修改；目标路径见 [design](design.md)。

## 1. P0 运行时与事件桥接

- [ ] 1.1 **EG-H01** 在现有 runtime lock 上定义独立工程制品能力和协议协商，错摘要/未知版本 RED；安装只走已有显式授权。 依赖：EG-K01。规格：EG-CGH-001。
- [ ] 1.2 **EG-H02** 新增只读 event-to-request 与证据投影；实际 cwd/index/HEAD/候选差异验证，不升级 not_evaluated。 依赖：EG-H01, EG-K11。规格：EG-CGH-002, EG-CGH-004。
- [ ] 1.3 **EG-H03** 实现 operationId 单飞、取消与交互 owner；多 Hook 乱序、迟到结果、不同内容不误去重。 依赖：EG-H02。规格：EG-CGH-003。
- [ ] 1.4 **EG-H04** 实现显式 cooperative/enforced 入口映射；缺 controller 不放行硬动作，旧 standalone 兼容和安全反馈回归。 依赖：EG-H03, EG-W04。规格：EG-CGH-001, EG-CGH-004。

## 2. P1/P2 架构反馈与 MCP

- [ ] 2.1 **EG-H05** 将架构/领域/代码/准备 blocker 投影为有界对话反馈；日志脱敏，诊断不作为指令。 依赖：EG-H04, EG-K13。规格：EG-CGH-004。
- [ ] 2.2 **EG-H06** 接 rmcp 新命名空间与旧 MCP 兼容映射，stdio 日志不污染协议；验证参数、取消及版本不匹配。 依赖：EG-H04, EG-K18。规格：EG-CGH-001, EG-CGH-002。
- [ ] 2.3 **EG-H07** 按实际 Codex/ZCode/Kimi/Claude 声明宿主分别安装验证生命周期、Git 拦截、取消和恢复；缺能力保持 unverified。 依赖：EG-H05, EG-H06。规格：EG-CGH-005。
- [ ] 2.4 **EG-H08** 完成原有未完成宿主/发行任务依赖核对、vendor 离线在线、回归与市场制品身份；同一证据可引用但不重复计完成。 依赖：EG-H07。规格：EG-CGH-005。

## 3. P3/P4 扩展与回滚

- [ ] 3.1 **EG-H09** 消费语义冲突和历史差异的新协议，验证 N/N-1、上下文切换及不同任务并发隔离。 依赖：EG-H08, EG-K23。规格：EG-CGH-003, EG-CGH-004。
- [ ] 3.2 **EG-H10** 执行多平台升级/回滚/缺策略演练及实际宿主复验；不得为回滚关闭服务端保护。 依赖：EG-H09。规格：EG-CGH-001, EG-CGH-005。
