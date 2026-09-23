# hook-protocol（增量）：save 范围锁定与豁免值语义

## ADDED Requirements

### Requirement: Save-face auto-fix SHALL stay scoped to the edited file

PostToolUse 保存面的自动修复 MUST 只作用于被编辑的单文件：带 scan token 的 format 命令 MUST
收束到该文件；`{file}` 形态 MUST 替换为该文件；裸命令形态只追加该文件参数。formatter 仍改动
到其它文件时，反馈 MUST 显式列出被改动的文件并要求重新读取，MUST NOT 静默携带副作用。该行为
MUST 有回归测试锁定（收束/替换/追加三态 + 越界告警）。

#### Scenario: Repo-wide format command collapses to the edited file

- **WHEN** format 命令含全仓 scan token（如 `ruff check . --fix` 形态）且保存 `src/a.py`
- **THEN** 实际执行的命令只针对 `src/a.py`，项目内其它文件不被改动

#### Scenario: Formatter touches files beyond the edited one

- **WHEN** formatter 实际改动了被编辑文件之外的文件
- **THEN** 反馈显式列出这些文件并声明内存版本已过期需重新读取

### Requirement: Skip-gate bypass values SHALL be parsed strictly

环境变量 `CODEGUARD_SKIP_GATE` 的豁免判定 MUST 只认 `1`/`true`/`yes`（大小写不敏感，与
`git config codeguard.skipGate` 的值词表一致）；`0`/`false`/空串等 MUST NOT 豁免——存在性判断
会让设 `=0` 意图保持门禁的用户**静默关闭门禁**。指令文案 MUST 与实际判定语义一致
（说明宿主命令内联赋值不会传入钩子进程，并给出准确的值词表）。

#### Scenario: Zero and false values do not bypass

- **WHEN** 环境变量值为 `0` 或 `false` 且命令含 git commit/git push
- **THEN** 门禁照常评估，不豁免

#### Scenario: Accepted values bypass consistently

- **WHEN** 环境变量值为 `1`、`true` 或 `yes`（任意大小写）
- **THEN** 豁免生效并记入审计，与 git config 豁免的值词表一致
