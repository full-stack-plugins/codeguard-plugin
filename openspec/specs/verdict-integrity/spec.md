# verdict-integrity Specification

## Purpose
保证检查结论绑定明确的代码内容和执行证据，防止逐文件结果、工具错误、暂存区差异或报告转换制造假通过，并保持用户工作树、暂存区和外部技能内容不变。

## Requirements

### Requirement: Verdicts SHALL preserve uncertainty across interfaces

CLI、MCP 和 hooks MUST 区分 PASS、FAIL、UNVERIFIED、SKIPPED、PLANNED。仅真实执行且成功的检查允许 passed=true；无法验证 MUST NOT 触发自动修复或 all passed。CLI 聚合退出码 MUST 为 FAIL=2、无 FAIL 但存在未验证/计划项=1、全部已验证或无须检查=0。

#### Scenario: Configuration error survives MCP serialization
- **WHEN** 检查器因配置错误退出且没有有效违规结论
- **THEN** CLI 退出 1，MCP 返回 passed=false、status=UNVERIFIED 和原因

### Requirement: Every executed file SHALL contribute to the verdict

逐文件检查 MUST 纳入全部已执行文件结果，不得只保留第一个结果。

#### Scenario: The second file fails
- **WHEN** 同语言第一个文件通过、第二个文件违规
- **THEN** 聚合包含第二个文件失败并拒绝 Git 操作

### Requirement: Git gates SHALL verify the proposed content without modifying it

Git 硬门禁 MUST 在隔离内容快照上检查：纯 commit 取 index，预测暂存包含相应工作树文件，纯 push 取 HEAD。安全检查 MUST 采用同一预测范围。快照失败、无法可靠预测或无法运行工具 MUST 明示 UNVERIFIED，不得宣称通过；不得更改真实 index/工作树。已删除文件不得作为新入库敏感文件拦截。

#### Scenario: A dirty index is hidden by a clean worktree
- **WHEN** index 内容有违规而未暂存工作树内容已修好
- **THEN** 检查 index 快照检出违规，工作树和 index 保持原样

#### Scenario: A sensitive file is about to be staged
- **WHEN** 命令是 git add .env 后 commit，文件尚未暂存
- **THEN** 安全门禁仍检出 .env

#### Scenario: A push contains a bad committed file
- **WHEN** HEAD 的文件违规但工作树已修好
- **THEN** push 检查 HEAD 内容而非修好的工作树
