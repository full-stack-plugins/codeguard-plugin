## MODIFIED Requirements

### Requirement: Gates in git repositories SHALL default to changed-file scope

git 仓库内的门禁 MUST 缺省只检查**本次操作面**涉及的文件，并按语言归属过滤；存量问题 MUST NOT 阻塞无关的新提交。操作面 MUST 由操作类型决定：**commit 面**（`git commit` 前）= staged + 未暂存 + 未跟踪；**push 面**（`git push` 前）= 提交面并集**未推送提交**（`up...HEAD` 三点差；无 upstream 时按 `origin/<当前分支>`→`origin/main`→`origin/master` 逐个尝试，均不可解析则不猜测、不崩溃）。面的判定 MUST 单源：命中判定与选面共用同一套扫描，直接命令与一层解释器间接不得分叉；同时命中 commit 与 push 时 MUST 取 push 面。提示词触发的软门禁 MUST 以同一套面语义选择（推送意图选 push 面）。项目可用 `codeguard.json` 的 `gate_scope`（`delta`/`repo`）显式覆盖；非 git 目录缺省为全量。全量模式 MUST 从 ruff 扫描中剔除依赖快照与构建产物目录（vendor/build/dist 等）。门禁结果缓存 MUST 按面隔离（mode 进缓存键），同一 HEAD 下两面不得互相污染。

#### Scenario: A committed legacy issue is untouched by a clean change

- **WHEN** 仓内 HEAD 已含存量 lint 问题，本次提交只涉及无问题的文档文件
- **THEN** commit 面判定通过，存量问题不拦截本次提交

#### Scenario: A new staged file introduces a problem

- **WHEN** 新增或修改的文件被暂存且含 lint 问题
- **THEN** commit 面按改动集检出该问题并正常拦截

#### Scenario: A bad commit made outside the gate must not slip through the push

- **WHEN** 工作树干净、提交已完成（绕过或早于门禁的坏提交），上游可解析
- **THEN** push 面检出未推送提交中的问题文件并拦截 `git push`

#### Scenario: Push with no resolvable upstream does not crash

- **WHEN** 仓库无 upstream 且 `origin/main`/`origin/master` 均不存在
- **THEN** 提交面照常计算、push 面保持空集，门禁不报错、按提交面结论决定

#### Scenario: A chained commit-and-push takes the wider face

- **WHEN** 单条命令链同时包含 `git commit` 与 `git push`（或间接脚本体内两者并存）
- **THEN** 生效面为 push 面（提交面的超集），两面的文件并集被检查
