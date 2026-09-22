# 判定可信度收敛与 Java 项目感知

## Why

v0.11.1 的代码审计复现了逐文件漏检、UNVERIFIED 假通过、暂存区与工作树错配、项目级命令约束丢失和 CVE 环境故障误报。扩大覆盖面之前，必须使检查结论与被检查内容一致，再让 Java 检查理解构建系统和模块依赖。

## What Changes

- 统一显式结果状态；**BREAKING**：CLI 无法验证退出 1，不再打印 all passed；MCP 保留兼容字段并增加 status/reason。
- 逐文件结果完整聚合；检查命令透传作用域约束；工具异常不触发自动修复。
- Git 硬门禁检查暂存/推送内容快照，预测 git add 的安全检查范围；不因报错落在未修改文件而擅自认定为历史问题。
- CVE 扫描只在有漏洞证据时报告 FAIL，保留执行失败和无法验证状态。
- 新增 Java 只读检查计划：Maven/Gradle、wrapper、多模块依赖、反向影响闭包；接入 CLI/MCP 与 Java 门禁。
- 同步宿主协议、架构与 README；保持外部 skills 快照不变。

## Capabilities

### New Capabilities

- `verdict-integrity`: 代码快照、逐文件聚合和无法验证状态的一致性。
- `java-project-impact`: Java 构建感知、模块级影响分析及检查计划。

### Modified Capabilities

- `language-gate-commands`: Git 内容范围与错误归因、项目级命令的作用域。
- `mcp-tool-server`: 显式结果状态和 Java 分析工具。
- `cve-dependency-scan`: 基于扫描证据区分漏洞与执行故障。

## Impact

修改插件 hooks/scripts/tests/docs 与版本元数据；不增加依赖、不安装工具、不初始化用户项目 CodeGraph，不修改受管技能或已有 OpenSpec change。不把模块图当作完整符号/业务语义分析，不自动提交、推送或改变用户宿主配置。
