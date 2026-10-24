# CodeGuard CLI 架构设计

> **文档说明**：描述 CodeGuard 的命令分层、运行时和证据边界。
>
> **版本**：V1.0.0
> **最后更新**：2026-10-24

## 1. 组件

~~~text
bin/codeguard
  → 命令路由
  → 生命周期 / 只读检查 / 领域运行时
  → 证据与报告
~~~

## 2. 命令分层

- 生命周期：install、uninstall、upgrade、version、doctor、status、completion。
- 项目事实：discover、init、check、report。
- 领域命令：install、uninstall、upgrade、version、doctor、status、discover、init、check、fix、cve、dockerfile、impact、explain、report、hooks install、hooks status、engine、completion。

## 3. 输出与退出码

统一信封：schemaVersion、tool、command、decision、exitCode、findings、evidence、nextActions。

退出码：0 PASS，1 BLOCK，2 用法/配置错误，3 UNVERIFIED/DESIGN_ONLY，4 内部错误。

## 4. 安全边界

- install 不写项目。
- init 幂等，不覆盖用户配置。
- check 只读。
- 外部 CLI 缺失时返回 PARTIAL，不伪造通过。

## 5. 当前成熟度

生产可用

---

**文档状态**：✅ 待评审
