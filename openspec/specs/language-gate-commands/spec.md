# language-gate-commands Specification

## Purpose
定义语言注册表中每个条目所声明命令的可执行性要求：`lint` / `format` / `probe` 必须能以声明的方式真正运行，需要路径或文件参数时必须以显式占位符或 glob 表达；并定义语言声明配置前置条件的能力，使「项目未接入」与「检查失败」不再混为一谈。
## Requirements
### Requirement: Declared commands must be runnable as written

注册表声明的 `lint` / `format` / `probe` 命令 SHALL 能按声明形式直接执行；需要文件或路径参数的 SHALL 以 `{file}` 占位符或显式 glob 表达，不得依赖调用方补全。

#### Scenario: 缺少必需参数

- **WHEN** 某语言的 `lint` 命令在无参数调用下返回工具用法错误（而非 lint 结论）
- **THEN** 门禁不得把它作为「lint 失败」上报，因为该结果与仓库内容无关

#### Scenario: markdown 的 lint 命令

- **WHEN** 门禁在已接入 markdown 的项目上运行
- **THEN** markdownlint 实际检查文件并以 lint 结论作为退出码，而不是返回用法错误

### Requirement: Probe must not confirm availability through a misinterpreted argument

`probe` 命令 SHALL 使用目标工具真实支持的可用性查询方式。当命令中的 flag 不被工具识别、因而被解释为路径或 glob 参数时，SHALL NOT 据此判定工具可用。

#### Scenario: 无效 flag 被当成路径

- **WHEN** probe 命令包含该工具不认识的 flag，导致其被当作文件或 glob 处理并仍然成功退出
- **THEN** 该探测结果不得被用作「工具已安装且可用」的证据

### Requirement: Auto-fix command must be executable and scoped

`format` 命令 SHALL 可通过注册表声明的入口直接执行，包括在工具未全局安装时经包管理器解析；且 SHALL 明确其作用范围是单文件还是整个项目，不得使调用方无从判断影响面。

#### Scenario: 工具未全局安装

- **WHEN** `format` 命令引用一个未全局安装的工具
- **THEN** 自动修复 SHALL 经包管理器解析执行，而不是以 command not found 失败

### Requirement: Languages may declare a configuration prerequisite

注册表 SHALL 允许为语言声明 `requiresConfig`。对以风格偏好为主、其默认规则会大面积误报的工具（如 markdown、yaml），SHALL 声明该前置条件。

#### Scenario: 已声明前置条件且项目未接入

- **WHEN** 项目缺少该语言声明的配置文件
- **THEN** 该语言判定为未接入 / 未验证，安全跳过且不阻塞提交，并在结果中说明未验证的原因

#### Scenario: 已声明前置条件且项目已接入

- **WHEN** 项目存在该语言声明的配置文件
- **THEN** 门禁按该配置正常检查，结论作为 lint 结果上报

#### Scenario: 未声明前置条件的语言不受影响

- **WHEN** 某语言未声明 `requiresConfig`
- **THEN** 其行为与现状一致，不被本要求改变

