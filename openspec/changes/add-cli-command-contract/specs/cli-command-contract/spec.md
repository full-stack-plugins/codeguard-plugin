# CLI 命令契约规格

## Purpose

定义命令语义、输出、退出码和 Hook 边界，供各 Guard 独立实现。

## ADDED Requirements

### Requirement: CLI-001 Install and project initialization
命令 SHALL 区分 install、init 和 hooks install；install 不写项目文件，init 不写宿主配置。

#### Scenario: install on clean host
- **WHEN** 用户运行 install
- **THEN** 只写宿主集成，不修改项目，不执行代码检查

### Requirement: CLI-002 Discovery
discover SHALL 只读输出项目、语言、构建系统和可用工具。

### Requirement: CLI-003 Idempotent init
init SHALL 幂等，不覆盖已有配置；--dry-run 不写文件。

### Requirement: CLI-004 Diagnosis
doctor SHALL 检查运行时、依赖、配置和 Hook，不执行代码检查；status SHALL 读取状态，不重新执行。

### Requirement: CLI-005 Read-only check
check SHALL 只读，不修改文件；输出 allow、deny、unverified 或 error。

### Requirement: CLI-006 Evidence report
report SHALL 读取已有证据，不重新执行命令。

### Requirement: CLI-007 Domain commands
领域命令 SHALL 使用固定动词和明确边界，不得用同一命令混合检查与修复。

### Requirement: CLI-008 Honest capability
未实现或未执行的能力 SHALL 输出 DESIGN_ONLY 或 UNVERIFIED，不得输出 PASS。

### Requirement: CLI-009 Repository hooks
hooks install SHALL 只写当前仓库 Git Hook，并在 status 中报告真实路径和状态。

### Requirement: CLI-010 Hook ownership
每个 Hook 事件 SHALL 有唯一所有者，禁止多个 Guard 在同一事件上重复阻断。

### Requirement: CLI-011 Compatibility
旧命令 SHALL 保留别名，并输出弃用提示；不得静默改变语义。

### Requirement: CLI-012 Output contract
所有支持 --json 的命令 SHALL 输出统一信封，并保留 rawExitCode。
