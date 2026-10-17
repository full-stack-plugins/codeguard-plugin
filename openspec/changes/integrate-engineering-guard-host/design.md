# 集成设计与验收边界

来源：2026-10-17 按既有总体规划重建；原引用路径在当前检出及本地可用历史中未找到。本变更是新重建的任务定义，不声称恢复了历史原文，也不声明实现或用户验收已完成。依据为 [traceability](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/traceability.md)、[acceptance](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/acceptance.md)、[protocol](https://github.com/full-stack-plugins/codeguard/blob/8d7c0e997bf21b3306573b3be89ff8c312c9de38/docs/engineering-guard/protocol.md) 与本仓现有维护约束。

## Context

本仓已有实现、公共接口和兼容义务，属于 Brownfield。当前变更沿用既有 OpenSpec，只定义总体规划已要求的增量，不建立第二套领域规则或宿主 Runtime。

## Goals / Non-Goals

目标：维持现有行为，以版本化输入、来源身份与明确覆盖向专业守卫提供可核验事实；在原生账本保留稳定任务及真实验收证据。

非目标：在插件内复制公共内核、持久数据库、专业规则判定或授权签发；仅凭模型结论、Hook 或本地文件声明对抗性强制。

## Decisions

1. 本仓 specs/tasks 是 H 系列定义及状态的唯一事实源，总体追溯表只引用。现有原生规格继续适用。
2. 适配器固定 producer/adapter/protocol/制品身份，保留原始报告。解析不赋予可信身份；确定性结果、建议、覆盖与执行状态分离。
3. 跨仓依赖只使用任务 ID 与发布接口，不在已安装插件中要求相邻源码目录。当前临时账本仍在 CodeGuard，公共内核实际实现仓库为 guardengine（逻辑 GuardCore）。
4. provider 兼容任务可在最终产品发布前独立验收，但不能以离线协议样本替代任务明确要求的真实工具、宿主或服务端验收。最终迁移/发布任务保留全部组合验收责任。
5. 授权只接受独立受信来源；已有同范围授权复用，扩大权限另核验。输入报告视为数据，不执行建议文本。

## Risks / Trade-offs

旧引用只说明规划意图，不能证明旧任务实现。缺工具、宿主、身份或权限时保持 pending/blocked 证据，不编造完成节点。安装与发布时按本仓版本、技能来源和市场规则执行，规划文件存在不构成安装或发布。

## Migration Plan

先固定现有 provider 行为与黄金反例，再接入公共协议和消费者，最后完成真实宿主/平台/升级回滚与规则单一 owner 交接。迁移前旧实现继续唯一拥有既有语义，迁移后不保留第二判定核；历史证据保留原身份，不自动升权。

## Validation

每个任务先使目标反例失败，再实现并执行目标测试与受影响回归。证据记录输入/候选/契约/工具/平台/宿主/命令/原始输出及摘要。全部 required 场景满足后才能勾选、同步和归档。
