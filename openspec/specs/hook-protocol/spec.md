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

`is_guarded()` MUST 覆盖直接命令与一层解释器间接。**Shell 解释器（bash/sh/zsh）**：脚本文件文本或 `-c` 内联代码按与直接命令相同的分隔符切段规则扫描到 `git commit|git push` 段首命令词时 MUST 判为拦截；切段扫描前 MUST 先展开 `$(...)` 与反引号内层文本（shell 语义下它们会被真实执行；`ro=$(git push …)` 曾静默放行），段首归一化 MUST 覆盖 shell 控制引导词（`if`/`then`/`else`/`elif`/`while`/`until`/`do`/`!`——`if git push; then`、`for x; do git push; done` 曾静默放行）。**非 Shell 解释器（python/node 等）**：正文 MUST NOT 按 shell 切段归因——模板字符串/帮助文本里的 git 命令字面量样例不是调用（bump-plugin.mjs:164-165 帮助文本实测误报、发版工具被不可绕过地锁死）；归因 MUST 只认 subprocess/exec 调用形态（`execFileSync("git", …)`、`subprocess.run(["git", …])`、`os.system("…")` 等调用点的 git 参数位），命中调用形态时 MUST 判为拦截并在 resolve 阶段按「不可建模」UNVERIFIED 阻断。`resolve_project_roots()` MUST 用同一套归一化判定收集仓库边界（含 `git -C <path>` 显式仓边界）——判定不同源时会出现"命中拦截但 roots=[] → 静默放行"的击穿（0.8.2 实测）。更深的动态构造（如 subprocess 参数拼接）MUST 在文档中声明为能力边界而非承诺。

#### Scenario: A wrapper script performs the commit

- **WHEN** 调用形如 `bash runner.sh` 且脚本体内含 `git commit` 或 `git push`
- **THEN** 判定命中，硬门禁按正常流程跑 linter 并可能 exit 2

#### Scenario: Command substitution or shell control structure hides the git call

- **WHEN** 调用形如 `ro=$(git push origin b 2>&1)`、`` x=`git commit` ``、`for x; do git push; done` 或 `if git push; then …; fi`
- **THEN** 展开/归一化后命中拦截，且 `resolve_project_roots` 解析出正确仓库边界（不为 []）

#### Scenario: Text mentioning git push in an echo is not guarded

- **WHEN** 调用为 `echo "git push 是危险命令"` 或脚本内容仅为 `echo hi`
- **THEN** 判定不命中，钩子静默放行

#### Scenario: Help text samples in a non-shell script are not guarded

- **WHEN** `node scripts/tool.mjs` 的正文含模板字符串帮助文本 `cd <root> && git add -A && git commit -m "x" && git push`
- **THEN** 判定不命中（字面量样例不是调用），钩子放行

#### Scenario: A non-shell script really invokes git via subprocess

- **WHEN** `python3 work.py` 的正文含 `subprocess.run(["git", "push"])` 或 `node run.mjs` 的正文含 `execFileSync("git", ["git commit" …])` 形态的调用
- **THEN** 判定命中，且 resolve 阶段按「间接 Git 操作不能可靠建模」UNVERIFIED 阻断（不静默放行）

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

### Requirement: Heredoc bodies SHALL be attributed by owner semantics

命令文本中 heredoc 正文的 git 归因 MUST 按归属语义区分：数据程序 + 引号定界符的正文是全字面量
（文档样例/模板字符串），MUST NOT 视为 shell 语法切段出 git 副作用；数据程序 + 无引号的正文会做
命令替换展开，`$(...)` 与反引号跨度的内层文本 MUST 保留扫描（其会被外层真实执行）；Shell 解释器
（bash/sh/zsh）接收的正文是内层 shell 代码，MUST 按既有切段规则建模；python/node 等非 Shell 解释器
接收的正文不是 shell 语法，MUST NOT 按切段归因。遮蔽处理 MUST 先于命令替换展开执行，
否则引号定界正文的字面 `$(...)` 会被误判为可执行替换。

#### Scenario: Sample text in a python heredoc is not guarded

- **WHEN** `python3 - <<'PY'` 的正文含三引号字符串 `'''cd a && git add && git commit && git push'''`（文档样例）
- **THEN** 判定不命中，钩子放行（此前整调用被拦且写入步骤不执行）

#### Scenario: Command substitution in an unquoted data heredoc is guarded

- **WHEN** `cat <<EOF` 的正文含 `$(git push origin b)` 或反引号包裹的 `git commit`
- **THEN** 展开后命中拦截（外层会真实执行，既有实测向量保持）

#### Scenario: Literal substitution text in a quoted data heredoc is not guarded

- **WHEN** `cat <<'EOF'` 的正文含字面 `$(git push origin b)`
- **THEN** 判定不命中（引号定界正文全字面量，不发生替换）

#### Scenario: Shell interpreter heredoc keeps modeled semantics

- **WHEN** `bash <<'SH'` 的正文含 `git commit -m t`
- **THEN** 判定命中且按一层间接建模（行为与既有切段语义一致）

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
