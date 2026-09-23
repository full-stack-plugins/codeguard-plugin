# Codeguard Rust CLI 设计文档

状态：设计基线，尚未实现。日期：2026-09-24。源码核对基线：`03ebb24`；后续实现必须重新核对工作树和已合并规格。

| 文档 | 回答的问题 |
|---|---|
| [架构文档](architecture.zh-CN.md) | 产品目标、模块边界、检查流程、低误报机制、权威边界 |
| [技术方案](technical-design.zh-CN.md) | 命令、数据协议、适配器、执行器、配置、缓存、分发与兼容实现 |
| [语言迁移与验收](coverage-and-acceptance.zh-CN.md) | 57 个条目的迁移、类别覆盖、评测方法、验收证据 |
| [持久问题与修复工作流](remediation-workflow.zh-CN.md) | 项目内 codeguard 目录、问题记录、待办任务、智能体修复与复检闭环 |
| [OpenSpec proposal](../../openspec/changes/introduce-rust-codeguard-cli/proposal.md) | 为什么变更及变更范围 |
| [OpenSpec design](../../openspec/changes/introduce-rust-codeguard-cli/design.md) | 架构决策、兼容性、实施顺序和待验证事项 |
| [OpenSpec tasks](../../openspec/changes/introduce-rust-codeguard-cli/tasks.md) | 可执行任务、依赖和完成证据 |

本次需求的唯一规范性事实源为 `openspec/changes/introduce-rust-codeguard-cli/specs/`。这些说明文档展开设计，不创建第二套任务状态。仓库 `openspec/specs/` 与 [当前架构](../current-architecture.md) 仍描述已落地的旧运行时；本 change 未实施前不得宣称 Rust 行为已经生效。

本次验收记录见 [verification.md](../../openspec/changes/introduce-rust-codeguard-cli/verification.md)。文档校验成功不代表二进制、扫描器或宿主运行验收成功。
