## Purpose

定义统一 Rust 二进制与宿主插件的制品绑定、兼容入口、迁移和发布证据，使源码、发布版本、实际安装和运行能力能够分别验证，避免未验证回退产生假通过。

## ADDED Requirements

### Requirement: Plugin execution SHALL bind a verified runtime artifact

插件 MUST 绑定 CLI 版本、平台、制品摘要及协议版本；不匹配或不可用时 MUST 报未完成，不得随机使用 PATH 版本或自动回退旧 Python 产生通过。doctor MUST 明示原生扫描器的 JDK/Node/Python 等外部依赖。

#### Scenario: Runtime checksum is invalid
- **WHEN** 安装二进制摘要不符合插件锁
- **THEN** 拒绝将其作为可信检查器，交付未完成

### Requirement: Compatibility SHALL be explicit and versioned

旧 CLI/MCP/Hook 兼容 MUST 具名并按旧入口分别映射协议；禁止透传新退出码或隐式改变旧语义。新交付门禁 MUST 不接受 legacy-v1 的 fail-open 结果作为新认证。兼容移除 MUST 有发布迁移说明。

#### Scenario: Legacy caller expects findings to exit two
- **WHEN** 旧调用经 legacy-v1 接入
- **THEN** 使用该旧入口的退出约定，同时不声称已满足新门禁

### Requirement: Release claims SHALL require layered evidence

stable 发布 MUST 分别提供真实工具、平台、Git/CI、宿主安装与运行验收；不以编译、mock 测试、tag 或市场清单替代。全语言完成声明 MUST 满足语言迁移要求。回滚 MUST 不降低已确认的交付契约。

#### Scenario: Release artifact exists but host cannot run it
- **WHEN** GitHub release 有二进制但某宿主无法启动
- **THEN** 该宿主验收保持未完成，不宣称已交付

#### Scenario: Only a legacy fail-open rollback is available
- **WHEN** 新运行时故障且没有符合新契约的旧 Rust 版本
- **THEN** 交付保持未认证，不能以旧放行行为恢复绿色门禁
