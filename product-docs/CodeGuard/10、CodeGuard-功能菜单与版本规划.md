# CodeGuard 功能菜单与版本规划

> **文档说明**：列出 CodeGuard 的命令菜单和版本归属。
>
> **版本**：V1.0.0
> **最后更新**：2026-10-24

## 1. 命令菜单

| 命令 | 类型 |
| :--- | :--- |
| install | 独立 CLI |
| uninstall | 独立 CLI |
| upgrade | 独立 CLI |
| version | 独立 CLI |
| doctor | 独立 CLI |
| status | 独立 CLI |
| discover | 独立 CLI |
| init | 独立 CLI |
| check | 独立 CLI |
| fix | 独立 CLI |
| cve | 独立 CLI |
| dockerfile | 独立 CLI |
| impact | 独立 CLI |
| explain | 独立 CLI |
| report | 独立 CLI |
| hooks install | 独立 CLI |
| hooks status | 独立 CLI |
| engine | 独立 CLI |
| completion | 独立 CLI |

## 2. 版本归属

| 命令组 | 版本 | 状态 |
| :--- | :--- | :--- |
| 生命周期 | 0.1.x | 已实现 |
| 项目事实 | 0.1.x | 部分/已实现 |
| 领域检查 | 当前版本 | 生产可用 |

## 3. 未实现项

- 未完成的领域运行时。
- 未验证的宿主 Hook 接线。
- 未同步的市场 catalog 版本。

## 4. 验收

- 命令有真实退出码。
- JSON 通过 schema 校验。
- 没有证据时不返回 PASS。

---

**文档状态**：✅ 待评审
