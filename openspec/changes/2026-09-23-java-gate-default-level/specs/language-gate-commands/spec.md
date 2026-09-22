# language-gate-commands（增量）：默认检查等级不含测试执行

## ADDED Requirements

### Requirement: Default build-check level SHALL exclude test execution

java 门禁的默认检查命令 MUST 跳过测试**执行**（Maven 追加 `-DskipTests`、
Gradle 追加 `-x test`）——测试代码仍参与编译，编译错误照常拦截。门禁职责
是提交面的编译/打包/静态正确性；测试执行由 CI 或项目显式声明承担。项目
MUST 能通过 `codeguard.json` 的 `java.commands` 权威覆盖声明含测试执行的
完整 verify。

#### Scenario: Maven default skips test execution
- **WHEN** 项目有 pom.xml 且无 `codeguard.json` `java.commands`
- **THEN** 生成的命令含 `-DskipTests` 且目标为 `verify`（测试编译仍执行）

#### Scenario: Gradle default excludes the test task
- **WHEN** 项目有 Gradle 构建描述且无 `codeguard.json` `java.commands`
- **THEN** 生成的命令含 `-x test`

#### Scenario: Project can opt into full verification
- **WHEN** `codeguard.json` 声明 `java.commands: [["./mvnw", "-B", "verify"]]`
- **THEN** 门禁按声明执行完整 verify（含测试执行），默认等级不再适用

#### Scenario: Test code still must compile
- **WHEN** 本次改动使测试源码编译失败
- **THEN** 默认等级的 `verify` 生命周期编译测试代码，门禁照常 FAIL
