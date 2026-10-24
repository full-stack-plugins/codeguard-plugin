## Why

CodeGuard 需要一套可预测、可诊断、可自动化的命令契约，避免安装、初始化、检查、修复和 Hook 语义互相混淆。当前状态：已实现 check/fix/cve/dockerfile/detect/engine/init(引导)。

## What Changes

- 统一生命周期命令：install、uninstall、upgrade、version、doctor、status、completion。
- 统一项目事实命令：discover、init、check、report。
- 按能力增加 impact、explain、hooks、plan/apply 等领域命令。
- 统一 JSON 信封、退出码、--dry-run/--yes、Hook 事件责任。
- CodeReview 只使用阿里云 OCR 的真实命令，不新增自有 CLI。

## Capabilities

### New Capabilities
- cli-command-contract: 命令语义、输出、退出码和 Hook 边界。

### Modified Capabilities
无。

## Impact

涉及 CLI 入口、插件 Hook、技能路由和文档；不改变 CodeGuard 的专业判定边界。未实现能力必须报告 DESIGN_ONLY 或 UNVERIFIED。
