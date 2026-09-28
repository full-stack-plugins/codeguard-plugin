# Codeguard Rust CLI 设计文档

状态：设计基线已完成，工程基线部分实施；原生检查、修复闭环和宿主验收尚未完成。日期：2026-09-24。原设计源码基线为 `03ebb24`，当前 HEAD `9e4adb1` 的增量见下表；后续实现仍须核对工作树和已合并规格。

| 文档 | 回答的问题 |
|---|---|
| [架构文档](architecture.zh-CN.md) | 产品目标、模块边界、检查流程、低误报机制、权威边界 |
| [技术方案](technical-design.zh-CN.md) | 命令、数据协议、适配器、执行器、配置、缓存、分发与兼容实现 |
| [逐指令架构设计](command-architecture.zh-CN.md) | 36 项命令入口的作用、价值、输入输出、副作用、退出语义、协作流程与验收 |
| [静态检测目录](static-check-catalog.zh-CN.md) | Javadoc、依赖治理、CVE 和其他 28 个检测族的义务与证据边界 |
| [语言迁移与验收](coverage-and-acceptance.zh-CN.md) | 57 个条目的迁移、类别覆盖、评测方法、验收证据 |
| [最新旧实现增量核对](legacy-delta-20260924.zh-CN.md) | 原设计基线到当前 HEAD 的源码差异、兼容/纠偏归类与回归样本 |
| [持久问题与修复工作流](remediation-workflow.zh-CN.md) | 项目内 codeguard 目录、问题记录、待办任务、智能体修复与复检闭环 |
| [项目初始化与 AGENTS.md 接入](project-initialization.zh-CN.md) | 项目画像、版本/构建器/架构/模块图、受管摘要与检查准备 |
| [误报白名单设计](false-positive-allowlist.zh-CN.md) | 精确匹配、可信审批、过期重审、任务流与带例外交付语义 |
| [OpenSpec proposal](../../openspec/changes/introduce-rust-codeguard-cli/proposal.md) | 为什么变更及变更范围 |
| [OpenSpec design](../../openspec/changes/introduce-rust-codeguard-cli/design.md) | 架构决策、兼容性、实施顺序和待验证事项 |
| [OpenSpec tasks](../../openspec/changes/introduce-rust-codeguard-cli/tasks.md) | 可执行任务、依赖和完成证据 |
| [实施覆盖索引](../../openspec/changes/introduce-rust-codeguard-cli/implementation-coverage.md) | 设计、逐条规格、36项命令、57个语言、平台/宿主到实施任务的双向追踪 |

本次需求的唯一规范性事实源为 `openspec/changes/introduce-rust-codeguard-cli/specs/`。这些说明文档展开设计，不创建第二套任务状态。仓库 `openspec/specs/` 与 [当前架构](../current-architecture.md) 仍描述已落地的旧运行时；新 Rust 工程基线不能被宣称为扫描器或宿主行为已经生效。

本次验收记录见 [verification.md](../../openspec/changes/introduce-rust-codeguard-cli/verification.md)。文档校验成功不代表二进制、扫描器或宿主运行验收成功。
