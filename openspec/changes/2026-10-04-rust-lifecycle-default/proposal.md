# Why

已发布 CLI 0.1.4 含编辑检查、稳定任务和原生复检，但插件默认生命周期仍调用 Python，用户无法自动得到该修复指引。

# What Changes

- 将 canonical Claude 形状 SessionStart、UserPromptSubmit、PostToolUse、PostToolUseFailure、Stop 接到受固定摘要保护的 Rust 0.1.4；保留真实 Git PreToolUse 兼容门禁。
- 显式安装，普通 Hook 不下载、不安装、不自动改源码或关闭任务；缺运行时给可执行准备指引。
- 安装器公开 init、next、task show/verify 的受限命令转发，使对话指引可通过同一固定程序执行。
- 同步协议、双语文档、制品证据和插件/市场版本；已安装宿主与全部语言精度独立验收。

# Capabilities

## Modified Capabilities
- `hook-protocol`: Rust 非阻断生命周期默认入口和修复指引。

# Impact

仅插件宿主绑定与固定制品锁改变；检查逻辑仍由 Rust 与生态原生工具承担。Copilot/OpenHands 分发镜像保持字节一致，Python Git 门禁、MCP 兼容服务保留独立边界，不冒充 Rust 完整迁移。原生未接线、未初始化与运行时未安装均明确未完成。
