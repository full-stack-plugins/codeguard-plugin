# Rust 文档已迁移

Rust CLI 的设计文档、进行中的 OpenSpec change、任务与验收记录已整体迁至独立 [codeguard 仓库](https://github.com/full-stack-plugins/codeguard)。本页仅作导航，不维护第二份 Rust 规范或任务。

- [中英文架构与技术方案](https://github.com/full-stack-plugins/codeguard/tree/main/docs)
- [逐指令、初始化、修复闭环、白名单与迁移设计](https://github.com/full-stack-plugins/codeguard/blob/main/docs/README.zh_CN.md)
- [唯一 OpenSpec change 与任务](https://github.com/full-stack-plugins/codeguard/tree/main/openspec/changes/introduce-rust-codeguard-cli)

本插件的旧运行时及宿主规范仍在本仓 `openspec/specs/`；Rust 集成接口在新仓维护，宿主实际接线仍由本插件实现和验收。迁移于 2026-09-28 在本地完成；远程链接须随两仓后续提交推送生效。
