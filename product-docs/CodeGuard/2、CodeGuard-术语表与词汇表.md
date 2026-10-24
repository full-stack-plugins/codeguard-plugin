# CodeGuard 术语表与词汇表

> **文档说明**：统一 CodeGuard 的术语，避免实现、文档和宿主提示使用不同口径。
>
> **版本**：V1.0.0
> **最后更新**：2026-10-24

## 1. 核心术语

| 术语 | 定义 |
| :--- | :--- |
| Guard | 一个独立研发防护插件及其 CLI/Hook |
| decision | allow、deny、unverified、error 四类结论 |
| UNVERIFIED | 证据不足或运行时缺失，不能视为通过 |
| DESIGN_ONLY | 只有设计，没有可执行领域运行时 |
| PARTIAL | 只完成了部分链路或部分输入 |
| evidence | 可回读的运行结果、报告或状态快照 |
| Hook | 宿主生命周期或 Git 事件上的检查入口 |

## 2. 命令术语

| 术语 | 含义 |
| :--- | :--- |
| install | 安装受管启动器，不写项目 |
| init | 初始化项目配置，幂等 |
| discover | 只读识别项目事实 |
| check | 只读门禁，不自动修复 |
| report | 读取已有证据，不重新执行 |
| explain | 解释规则、语言或上次日志 |

## 3. 状态口径

19 条 CLI 已实现；check/fix/cve/dockerfile/impact 有真实执行入口

---

**文档状态**：✅ 待评审
