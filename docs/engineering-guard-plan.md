# codeguard-plugin 工程守卫规划入口

日期：2026-10-09。状态：规划已写入，新增能力尚未实施。职责：**宿主事件、固定运行时与证据桥接**。

## 本仓唯一规划事实源

- [提案](../openspec/changes/integrate-engineering-guard-host/proposal.md)：目标、兼容与范围。
- [设计](../openspec/changes/integrate-engineering-guard-host/design.md)：现有实现、改动位置、协议、风险、迁移与验证。
- [实施任务](../openspec/changes/integrate-engineering-guard-host/tasks.md)：EG-H01—10，全部待实施。
- 规范要求位于同一 change 的 `specs/`，不会通过本入口另建任务或验收账本。

## 联合规划定位

完整体系由 codeguard 仓库 `docs/engineering-guard/README.md` 导航：包含六仓基线、统一内核、技术工具、协议、P0—P4、追溯和验收矩阵。共享协议的事实源是 `codeguard/openspec/changes/add-engineering-guard-core/`；本仓只定义自己拥有的集成行为。

本地按“仓库名 + 仓内路径”读取；分发时使用固定版本 release manifest 和协议摘要，不要求安装者保有兄弟仓库。任何新 CLI、适配器、schema 或 fixture 都是计划产物，实际接口以实施后的协议发布为准。

## 执行约束

沿用本仓 AGENTS、现有规格/未完成任务和已有行为，保护用户未提交修改。先完成依赖任务，再进行行为测试 RED→最小实现→GREEN→受影响回归。真实宿主、原生工具、CI、服务端保护和平台分别验收。规划完成不触发安装、分支切换、发布或默认模式变化。
