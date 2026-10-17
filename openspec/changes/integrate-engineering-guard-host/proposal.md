# 工程守卫集成：codeguard-plugin

来源：2026-10-17 按既有总体规划重建；原引用路径在当前检出及本地可用历史中未找到。本变更是新重建的任务定义，不声称恢复了历史原文，也不声明实现或用户验收已完成。依据为 [traceability](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/traceability.md)、[acceptance](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/acceptance.md)、[protocol](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/protocol.md) 与本仓现有维护约束。

## Why

总体规划引用的 H 系列任务缺少原生定义，无法校验依赖与验收归属。需要补齐本插件的唯一实施账本，并把已有插件能力接到七产品的版本化证据协议；不得把规划补齐等同于产品交付。

## What Changes

- 在本仓保留 EG-CGH-001、EG-CGH-002、EG-CGH-003、EG-CGH-004、EG-CGH-005 的职责及可观察行为。
- 定义 EG-H01、EG-H02、EG-H03、EG-H04、EG-H05、EG-H06、EG-H07、EG-H08、EG-H09、EG-H10，全部待实施；保留总体规划的稳定引用。
- provider 兼容证明先于消费方最终发布；最终迁移验收仍要求实际产品、宿主、版本与保护证据，不减少验收范围。
- 不初始化新规格体系，不改变既有运行时、技能来源锁、Hook 语义、批准策略或发布流程。

## Capabilities

### New Capabilities

- `engineering-host-bridge`：本插件面向公共工程协议的来源、范围、覆盖、权限与生命周期边界。

### Modified Capabilities

无；既有规格继续适用，不通过本变更改写已确认行为。

## Impact

计划影响本插件的适配入口、证据投影、测试与未来发布。实施时遵守 AGENTS.md；受管技能不在插件内手改，真实宿主和托管保护不得由离线模拟替代。普通验证不顺带安装、初始化、索引、外发或 Git 写动作。
