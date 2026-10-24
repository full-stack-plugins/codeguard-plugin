## Why

现有 Rust 生命周期、Python Git 兼容门禁和 MCP 入口具有不同的信任与退出语义。工程守卫接入必须保证它们传递同一受检对象及证据，而不能把局部检查、安装成功或宿主放行解释为统一工程验收。

## What Changes

- 增加显式启用的工程守卫宿主桥接、固定制品与协议版本协商。
- 区分 soft feedback、local cooperative gate、trusted delivery gate；旧兼容入口不被默认为可信门禁。
- 统一事件/请求身份、并发去重、取消、原始报告引用与安全反馈；避免重复检查和跨插件重复询问。
- 保留受管技能来源、五类生命周期语义、点前缀范围约定及旧 CLI/MCP 协议；rmcp 新入口在独立命名空间渐进接入。
- 规划实际宿主、平台制品、市场、回滚与兼容矩阵。

## Capabilities

### New Capabilities

- `engineering-host-bridge`: 宿主桥接、制品信任、事件协调及受控模式映射。

### Modified Capabilities

无。新增 opt-in 模式；既有 Rust 生命周期 change 的未完成宿主/发行任务继续有效，不在本 change 重复勾选。

## Impact

未来涉及 hooks/rust_runtime_dispatch.cjs、固定运行时安装器、CLI/MCP 适配、manifest/协议文档及 tests。检查算法继续在独立 codeguard 仓库；禁止把共享策略复制进各 Hook。

本轮只写规格、设计、任务和导航，不升级版本或发布。
