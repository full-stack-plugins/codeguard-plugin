## ADDED Requirements

### Requirement: Hard-block feedback SHALL declare whole-call rejection

PreToolUse 硬拦截（exit 2）的 stderr 报告 MUST 包含一条整调用声明：本次被拒绝的是一次完整的 Bash 工具调用，其中非 git 的前序步骤（写文件、执行脚本）也全部未执行，指令 MUST 要求调用方把修复与提交拆成两次独立调用。该声明 MUST NOT 改变首行综述契约（首行仍为 `codeguard ❌ 提交门禁未通过：`）。

#### Scenario: AI retries a combined write-and-commit call

- **WHEN** 一次同时包含写文件与 `git commit` 的调用被门禁拦截
- **THEN** 报告在首行综述之后包含"整个工具调用没有执行/拆成两次独立调用"的指令，且首行仍是综述

### Requirement: The guard SHALL treat one-level interpreter indirection as guarded

`is_guarded()` MUST 覆盖直接命令与一层解释器间接：解释器（bash/sh/zsh/python/node）执行的脚本文件文本、或 `-c` 内联代码，按与直接命令相同的分隔符切段规则扫描到 `git commit|push` 段首命令词时 MUST 判为拦截。更深的动态构造（如 subprocess 参数拼接）MUST 在文档中声明为能力边界而非承诺。

#### Scenario: A wrapper script performs the commit

- **WHEN** 调用形如 `bash runner.sh` 且脚本体内含 `git commit` 或 `git push`
- **THEN** 钥入判定命中，硬门禁按正常流程跑 linter 并可能 exit 2

#### Scenario: Text mentioning git push in an echo is not guarded

- **WHEN** 调用为 `echo "git push 是危险命令"` 或脚本内容仅为 `echo hi`
- **THEN** 判定不命中，钩子静默放行

### Requirement: Soft and hard gates SHALL share the skipGate escape and neither may fall back to scanning outside a git repository

UserPromptSubmit 与 PreToolUse MUST 共用同一条仓库级豁免（`git config codeguard.skipGate`）；两门在命中豁免时 MUST 记账一次供 Stop 汇总。UserPromptSubmit 在当前目录不属于任何 git 仓库时 MUST 输出一行跳过说明并 exit 0，MUST NOT 把非 git 目录（尤其是多仓工作区根）回退为扫描对象。

#### Scenario: SkipGate set, user asks to commit

- **WHEN** 仓库已设 skipGate 且用户消息触发提交意图
- **THEN** 软门禁静默退出（与硬门禁一致），绕过计数 +1

#### Scenario: Prompt fires outside any git repository

- **WHEN** cwd 不在 git 仓库内且消息触发提交意图
- **THEN** 输出"不是 git 仓库，提交门禁已跳过"的说明，不运行任何 linter、不扫描 cwd
