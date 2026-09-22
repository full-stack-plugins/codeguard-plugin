## Purpose

让 Java 守卫依据真实构建描述和模块依赖制定可解释的检查计划，识别 wrapper 与多模块影响范围，并在动态构建配置无法静态确定时保守扩大范围而不是伪造完整语义分析。

## ADDED Requirements

### Requirement: Java planning SHALL be read only and project aware

系统 MUST 提供 CLI java-plan 和 MCP analyze_java_impact，识别 Maven/Gradle 与 wrapper，返回构建系统、模块、依赖边、受影响模块、检查命令、依据和未验证边界。规划 MUST NOT 执行构建、安装工具、下载依赖或初始化 CodeGraph。

#### Scenario: Maven wrapper multi-module project
- **WHEN** 仓库存在 mvnw、父 pom 和 api/service 模块，service 依赖 api
- **THEN** 修改 api 的计划包含 api 和 service，并优先使用 ./mvnw

### Requirement: Impact SHALL include reverse dependency closure

受影响范围 MUST 包含修改模块及其直接/间接依赖方；构建配置变化、无法解析的依赖表达式或 Gradle 动态配置 MUST 保守退回全模块，并给出原因。删除文件、无改动、仓外路径和缺失构建描述 MUST 被明确处理。

#### Scenario: A shared module changes
- **WHEN** app 依赖 service、service 依赖 api，仅 api 源码变化
- **THEN** 计划覆盖 api、service、app，且不把未修改调用方错误归为历史问题

#### Scenario: Dynamic Gradle project configuration
- **WHEN** settings 或项目依赖使用无法可靠解析的动态表达式
- **THEN** 计划使用根项目 check 并标明全量保守回退

### Requirement: Java execution SHALL follow the plan without claiming unrun checks

Java 仓库级检查 MUST 使用计划的 Maven verify 或 Gradle check（显式项目命令可覆盖），分别记录命令与覆盖边界。PostToolUse MUST NOT 静默进行项目级格式化；无静态规则配置时 MUST NOT 宣称已执行 Checkstyle/PMD 等规则。

#### Scenario: Gradle-only repository
- **WHEN** Java 仓库使用 Gradle 而无 pom.xml
- **THEN** 检查调用 Gradle check，不调用 Maven
