# hook-protocol（增量）：非 Shell 间接正文按调用形态归因

## MODIFIED Requirements

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
