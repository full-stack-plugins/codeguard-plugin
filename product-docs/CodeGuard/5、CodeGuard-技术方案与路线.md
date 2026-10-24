# CodeGuard 技术方案与路线

> **文档说明**：给出 CodeGuard 的实现分层和迭代路线。
>
> **版本**：V1.0.0
> **最后更新**：2026-10-24

## 1. 技术分层

~~~text
宿主 / Agent
  → Skill / Command
  → codeguard CLI
  → 领域运行时 / 外部工具
  → 证据与报告
~~~

## 2. 关键决策

- 独立 CLI，不合并为 Partme Guard 总命令。
- install 只装受管启动器，不写项目。
- init 只写项目配置，幂等。
- check 只读，必须有真实退出码。
- 没有证据时返回 UNVERIFIED 或 DESIGN_ONLY。

## 3. 路线

| 阶段 | 内容 | 状态 |
| :--- | :--- | :--- |
| P0 | 生命周期 CLI、JSON、退出码 | ✅ |
| P1 | 领域 check 与证据 | 生产可用 |
| P2 | Hook 与 CI 集成 | 部分 |
| P3 | 跨 Guard 证据协同 | 规划 |

---

**文档状态**：✅ 待评审
