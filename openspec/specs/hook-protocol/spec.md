# hook-protocol Specification

## Purpose
定义 CodeGuard 与宿主的事件、输出和退出码契约：区分观察性反馈与 Git 硬门禁，保留 fail-open 的同时明确未验证状态，并将检查绑定到拟提交或推送的内容。

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

PreToolUse MUST 按可识别命令预测提交内容：纯 commit 使用 index，git add -A 使用工作树覆盖，git add -u / commit -a 不得纳入未跟踪文件，带路径 add 不得扩张到全仓。精确快照不得复用软门禁缓存。无独立基线时，项目命令在未修改文件上的失败 MUST 保留，不得按路径猜测历史债。无法完整建模的命令必须声明能力边界，不能作为全面验收证据。

#### Scenario: Plain commit with unrelated unstaged WIP in the worktree
- **WHEN** index 可提交且工作树存在无关 WIP
- **THEN** 在 index 快照检查，不检查 WIP 内容

#### Scenario: Chained add widens the face before commit runs
- **WHEN** git add 后接 commit
- **THEN** 按 add 的范围叠加工作树文件并保留删除影响

#### Scenario: Project-level linter fails only on files outside the changeset
- **WHEN** 项目级检查在未修改文件发现违规且没有独立基线证据
- **THEN** 保留失败，不归类为已知存量

### Requirement: Fail-open uncertainty SHALL be visible

PreToolUse 放行工具故障或无法物化快照时 MUST 使用 JSON additionalContext 说明未验证；UserPromptSubmit MUST NOT 对含未验证项的检查输出全部通过。PostToolUse 只提供反馈，strict_mode 不得被文档描述为已生效的阻断开关。

#### Scenario: A tool cannot run at the Git gate
- **WHEN** 工具缺失或配置导致无法获得检查结论
- **THEN** 保留 exit 0 的兼容放行，并明确未验证而不是 PASS
