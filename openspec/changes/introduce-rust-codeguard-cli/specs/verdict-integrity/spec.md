## MODIFIED Requirements

### Requirement: Verdicts SHALL preserve uncertainty across interfaces

显式 legacy-v1 入口 MUST 保持 PASS、FAIL、UNVERIFIED、SKIPPED、PLANNED 及原聚合退出约定：通常 FAIL=2、无 FAIL 但有未验证/计划项=1、已验证或无须检查=0；各旧子命令的已记录差异由兼容层保持。仅真实成功检查允许 passed=true，无法验证不得触发自动修复或 all passed。

Rust 新入口 MUST 使用 unified-cli-contract 的版本化协议，MUST 将执行完整性与 findings 分离；混合未完成和违规保留两者并退出 3。CLI/MCP/Hook 转换 MUST 根据协议和结构化语义，不能根据同一个数字猜测通过。此版本边界同样约束旧 CVE、Dockerfile 等结果在新入口的映射。

#### Scenario: Configuration error survives MCP serialization
- **WHEN** 旧入口检查器因配置错误退出且没有有效违规结论
- **THEN** 旧 CLI 退出 1，旧 MCP 返回 passed=false、UNVERIFIED 和原因

#### Scenario: Configuration error survives Rust MCP serialization
- **WHEN** 新入口同一检查因配置错误未完成
- **THEN** Rust CLI 退出 3，MCP 保留 incomplete，不能通过协议转换生成 PASS

## ADDED Requirements

### Requirement: Required completeness SHALL gate Rust delivery

Rust 交付 allow MUST 同时满足全部适用必需义务完成、覆盖匹配、内容与批准策略身份有效、无阻断违规。缺工具、无实现、坏报告、超时、缓存身份失败或输入变化 MUST NOT 成为 allow。未选择的类别与有理由不适用的类别 MUST 明确区分。

#### Scenario: No findings but a required tool is missing
- **WHEN** 已运行检查无违规但另一必需工具缺失
- **THEN** 交付 incomplete，不制造代码违规，也不允许交付

#### Scenario: Finding remains in a historical file
- **WHEN** 必需规则检出历史文件中的违规
- **THEN** 保留 finding 并按同一策略阻断，基线分类不能改变结果

### Requirement: Coverage SHALL not change with scheduling strategy

Rust MUST 在调度前建立完整义务；分批、并发、缓存和增量 MUST 保持等价覆盖与判定，未执行义务必须具有有效复用证明，否则未完成。文件数量阈值 MUST NOT 改变历史问题是否阻断。

#### Scenario: A clean extra file crosses a batching boundary
- **WHEN** 目标从 50 个增加至 51 个文件但已有违规未变
- **THEN** 原违规的门禁影响不变，不能因切换扫描方式而豁免或新增归因
