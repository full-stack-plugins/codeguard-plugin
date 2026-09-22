# hook-protocol Specification

## Purpose
TBD - created by archiving change add-host-protocol-cheatsheet. Update Purpose after archive.
## Requirements
### Requirement: Hook-host contract SHALL live in hooks/__protocol__.md

The canonical description of how codeguard-plugin hooks communicate with Codex CLI, ZCode, and Kimi Code (exit codes, JSON output formats, fail-open convention, three-host compatibility) SHALL live in `hooks/__protocol__.md`. No hook script or docstring SHALL contradict it; any change to exit codes or JSON schema SHALL update the document in the same commit.

#### Scenario: A future hook author consults the single source

- **WHEN** an agent (human or AI) adds a new hook to `hooks/`
- **THEN** the README and `hooks/__protocol__.md` together are sufficient to design exit codes and JSON shape without further questions

#### Scenario: A hook script's docstring contradicts the cheat-sheet

- **WHEN** a reviewer or `git diff` notices a contradiction between a hook's docstring and `hooks/__protocol__.md`
- **THEN** the implementer updates whichever side is out of date so the document and implementation match in the merged commit

### Requirement: tests/run_all.py SHALL reference the cheat-sheet

The top-of-file docstring of `tests/run_all.py` SHALL contain a one-line reference to `hooks/__protocol__.md` describing its role as the canonical contract source for the host-protocol e2e suite.

#### Scenario: A new contributor opens run_all.py to add a hook subset

- **WHEN** the contributor reads the docstring
- **THEN** the reference to `hooks/__protocol__.md` is visible and points them at the single source for protocol questions

### Requirement: The cheat-sheet SHALL document fail-open for uncaught exceptions

`hooks/__protocol__.md` SHALL include a section explaining the fail-open convention: any uncaught exception inside a hook logs to stderr and exits 0, so a hook bug never blocks the host CLI workflow. This documents the existing behavior in `env_check.py`, `post_tool_lint.py`, `pre_tool_git_guard.py`, `user_prompt_validator.py`, and `stop_summary.py`.

#### Scenario: A hook hits an unexpected exception

- **WHEN** an uncaught `Exception` propagates to the top of a hook
- **THEN** the hook prints the traceback tail to stderr and exits 0; the host CLI receives no block signal and continues its workflow

### Requirement: Hard-block feedback SHALL declare whole-call rejection

PreToolUse 硬拦截（exit 2）的 stderr 报告 MUST 包含一条整调用声明：本次被拒绝的是一次完整的 Bash 工具调用，其中非 git 的前序步骤（写文件、执行脚本）也全部未执行，指令 MUST 要求调用方把修复与提交拆成两次独立调用。该声明 MUST NOT 改变首行综述契约（首行仍为 `codeguard ❌ 提交门禁未通过：`）。该声明 MUST 紧跟首行综述（指令前置）：宿主会把超长 stderr 从尾部截断，指令位于末段时长报告下会整体丢失（实测），「怎么修」等行动指引 MUST 先于 linter 原始输出出现。整个报告 MUST 受总长硬上限（`REPORT_MAX_CHARS`）约束，超限时 MUST 保尾截断细节——尾部的完整日志路径不得截掉。

#### Scenario: AI retries a combined write-and-commit call

- **WHEN** 一次同时包含写文件与 `git commit` 的调用被门禁拦截
- **THEN** 报告在首行综述**紧后**包含"整个工具调用没有执行/拆成两次独立调用"的指令，且首行仍是综述

#### Scenario: A very long multi-language report is truncated by the host

- **WHEN** 多语言失败详情使报告超过 `REPORT_MAX_CHARS`
- **THEN** 报告总长受控、指令段完整保留，被压缩的细节块仍保留其尾部完整日志路径

### Requirement: The guard SHALL treat one-level interpreter indirection as guarded

`is_guarded()` MUST 覆盖直接命令与一层解释器间接：解释器（bash/sh/zsh/python/node）执行的脚本文件文本、或 `-c` 内联代码，按与直接命令相同的分隔符切段规则扫描到 `git commit|push` 段首命令词时 MUST 判为拦截。切段扫描前 MUST 先展开 `$(...)` 与反引号内层文本（shell 语义下它们会被真实执行；`ro=$(git push …)` 曾静默放行），段首归一化 MUST 覆盖 shell 控制引导词（`if`/`then`/`else`/`elif`/`while`/`until`/`do`/`!`——`if git push; then`、`for x; do git push; done` 曾静默放行）。`resolve_project_roots()` MUST 用同一套归一化判定收集仓库边界（含 `git -C <path>` 显式仓边界）——判定不同源时会出现"命中拦截但 roots=[] → 静默放行"的击穿（0.8.2 实测）。更深的动态构造（如 subprocess 参数拼接）MUST 在文档中声明为能力边界而非承诺。

#### Scenario: A wrapper script performs the commit

- **WHEN** 调用形如 `bash runner.sh` 且脚本体内含 `git commit` 或 `git push`
- **THEN** 钥入判定命中，硬门禁按正常流程跑 linter 并可能 exit 2

#### Scenario: Command substitution or shell control structure hides the git call

- **WHEN** 调用形如 `ro=$(git push origin b 2>&1)`、`` x=`git commit` ``、`for x; do git push; done` 或 `if git push; then …; fi`
- **THEN** 展开/归一化后命中拦截，且 `resolve_project_roots` 解析出正确仓库边界（不为 []）

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

### Requirement: The commit face SHALL match the actual staging surface

PreToolUse 的 commit 面 MUST 按命令链预测**实际会提交**的文件集（`staging_intent`）：纯 `git commit` 只取暂存区；`git add -A/-a/-u`、`commit -a` 相应扩展到未暂存/未跟踪；`git add <paths>` MUST 并入这些路径（触发拦截时 add 尚未执行、暂存区仍是旧的）。工作树里**未被该命令链触及**的改动（如并行会话的未暂存 WIP）MUST NOT 触发硬拦。预测面（lanes/extra）MUST 进入门禁缓存键。delta 作用域下，项目级 linter 报错所提及的文件 MUST 全部位于本次改动集之外时归为 skipped（存量归因）而非 failure；无法归因或存在交集时维持 failure（宁可多拦不漏拦）。

#### Scenario: Plain commit with unrelated unstaged WIP in the worktree

- **WHEN** 暂存区干净可提交，工作树存在与本命令无关的未暂存/未跟踪改动，执行 `git commit -m t`
- **THEN** 门禁只检查暂存区文件，无关 WIP 不产生 failure，提交放行

#### Scenario: Chained add widens the face before commit runs

- **WHEN** 执行 `git add -A && git commit -m t` 或 `git add path/to/file && git commit -m t`
- **THEN** 门禁按执行后的暂存区预测检查（含未暂存/未跟踪或显式路径），"即将暂存"的文件不漏检

#### Scenario: Project-level linter fails only on files outside the changeset

- **WHEN** delta 面内 mvn/cargo 等项目级命令失败，但输出提及的文件全部不在本次改动集
- **THEN** 归为 skipped（存量归因 + 完整日志路径），不拦截本次提交

