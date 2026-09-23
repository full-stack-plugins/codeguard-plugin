## ADDED Requirements

### Requirement: The commit-content safety scan SHALL NOT be covered by any agent-controllable escape

入库内容安全扫描（密钥/凭据/依赖产物模式）MUST NOT 被智能体可控的豁免（仓库级 `codeguard.skipGate`、内联 `-c codeguard.skipGate=true`、链式赋值）关闭。命中该类豁免时语言门禁跳过并记账，但安全扫描 MUST 照常执行；违规 MUST 以 exit 2 硬拦（PreToolUse）或注入安全报告（UserPromptSubmit）。唯一可同时豁免二者的逃生门是进程环境变量 `CODEGUARD_SKIP_GATE`（宿主命令内联赋值不传入钩子进程，仅用户可设），且 MUST 记账。

#### Scenario: Repository escape set and a credential file is staged

- **WHEN** 仓库已设 `codeguard.skipGate` 为真值且暂存面含 id_rsa 类文件并执行 `git commit`
- **THEN** PreToolUse 仍 exit 2 输出入库安全报告；语言 lint 问题不再拦截

#### Scenario: Inline bypass with a secret staged

- **WHEN** 以 `-c codeguard.skipGate=true` 形态执行提交且暂存面含 .env 类文件
- **THEN** 安全扫描仍拦截；放行仅发生在无违规时，内联豁免公告照常注入

#### Scenario: Process-environment escape covers both gates

- **WHEN** 钩子进程环境存在 `CODEGUARD_SKIP_GATE=1` 并执行含敏感文件的提交
- **THEN** 语言门禁与安全扫描均跳过，记账一次（该逃生门仅用户可设）

## MODIFIED Requirements

### Requirement: Soft and hard gates SHALL share the skipGate escape and neither may fall back to scanning outside a git repository

UserPromptSubmit 与 PreToolUse MUST 共用同一条仓库级豁免（`codeguard.skipGate`）；该豁免及其内联/链式形态的覆盖范围 MUST 限定为语言门禁（见「commit-content safety scan 不被智能体可控豁免关闭」）。两门在命中豁免时 MUST 记账一次供 Stop 汇总。UserPromptSubmit 在当前目录不属于任何 git 仓库时 MUST 输出一行跳过说明并 exit 0，MUST NOT 把非 git 目录（尤其是多仓工作区根）回退为扫描对象。

#### Scenario: SkipGate set, user asks to commit

- **WHEN** 仓库已设 skipGate 且用户消息触发提交意图，且待提交面无敏感模式文件
- **THEN** 软门禁静默退出（与硬门禁一致），绕过计数 +1

#### Scenario: SkipGate set with a secret on the commit face

- **WHEN** 仓库已设 skipGate 且用户消息触发提交意图，待提交面含敏感模式文件
- **THEN** 软门禁注入入库安全报告（非阻断）；硬门禁在同一提交面 exit 2

#### Scenario: Prompt fires outside any git repository

- **WHEN** cwd 不在 git 仓库内且消息触发提交意图
- **THEN** 输出“不是 git 仓库，提交门禁已跳过”的说明，不运行任何 linter、不扫描 cwd
