# hooks/ 与宿主 CLI 之间的契约（canonical cheat-sheet）

> 这份文档是 codeguard-plugin 与 Codex CLI / ZCode / Kimi Code 三端宿主
> 交互契约的**单源事实**。所有 hook 脚本（`hooks/*.py`）的实现都必须与本文件
> 一致；若未来调整任何退出码或 JSON schema，**同一 commit 内**必须更新本文件。
>
> 对应的 OpenSpec 规范是 `hook-protocol`（见 `openspec/specs/hook-protocol/spec.md`）。

---

## 1. 协议总表

| 事件 | Hook 脚本 | stdout | stderr | exit | 阻断? |
|---|---|---|---|---|---|
| SessionStart | `env_check.py` | 人类可读一行摘要 `codeguard 插件环境：...` | 仅内部错误时 | 0 | 否 |
| UserPromptSubmit | `user_prompt_validator.py` | JSON `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}` | 仅内部错误时 | 0 | 否 |
| PreToolUse `Bash` | `pre_tool_git_guard.py` | 通过：空；未验证：JSON additionalContext | 通过：空；失败：完整修复指令 | 0（通过/放行）/ 2（拦截） | 放行：否；确定违规：是 |
| PostToolUse `Write\|Edit\|MultiEdit` | `post_tool_lint.py` | JSON `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"..."}, "systemMessage":"..."}` | 仅内部错误时 | 0 | 否 |
| Stop | `stop_summary.py` | 人类可读会话摘要 | 仅内部错误时 | 0 | 否 |

实现定位（**符号而非行号**——行号随每次重构腐烂，符号不腐；v0.8.0 起弃用行号指针）：
- SessionStart 摘要：`hooks/env_check.py::main`（含双副本告警段）。
- UserPromptSubmit JSON：`hooks/user_prompt_validator.py::main`（非 git 目录跳过说明 `_non_git_note`）与 `::is_trigger`。
- PreToolUse stderr：`hooks/pre_tool_git_guard.py::main`；静态语法在 `scripts/codeguard/git_syntax.py`，仓库观察与 `is_guarded/_guarded_mode` 在 `scripts/codeguard/git_context.py`；旧 Hook helper 导入继续兼容。一层脚本观察共用 `_indirect_bodies`。
- PostToolUse JSON：`hooks/post_tool_lint.py::main`（通过/自动修复后通过/失败 additionalContext 三处 print）。
- Stop 摘要：`hooks/stop_summary.py::main`（含绕过计数 `summarize` 与 skipGate 遗留告警）。

门禁内部边界：`hooks/gate_lib.py` 只保留兼容导出；`scripts/codeguard/gate.py` 选择内容面与保序汇总，
`gate_checks.py` 返回各语言独立 `GateOutcome`；`repository_policy.py` 检查路径安全和显式豁免，
`baseline.py` 核验存量证据，`spec_validation.py` 适配可选 OpenSpec 校验，`reporting.py` 保留反馈格式。
应用服务无需 hooks 路径或宿主 SDK 即可运行；兼容面不承担第二份业务实现。

语言服务边界：`registry_schema` 的纯校验同时服务注册表 CLI 与运行时加载，`registry` 派生
识别/命令表；`config` 读取配置，`discovery` 只做项目发现，`toolchain` 负责探活。
SessionStart 与每轮门禁各持有独立 `ToolchainProbe`，在目标目录执行且 stdin=DEVNULL；
同批同命令成功探活去重，不同命令仍并行，失败与下一批检查都重新探测。
探活成功不代表 lint 通过。`detect_lang`、`user_config` 的原公开导入继续兼容。

`codeguard.json` 缺失时保留默认值；存在但 JSON/字段类型/扩展语言 ID/排除正则无效时，
CLI/MCP 明确返回 UNVERIFIED，自动修复不执行。门禁以未验证说明放行而非报告通过；
其它 Hook 的配置异常仍遵循既有 fail-open 和 stderr 告警，不把它变成代码违规。

---

## 2. 三端兼容矩阵

| 宿主 | SessionStart | UserPromptSubmit | PreToolUse Bash | PostToolUse Write\|Edit\|MultiEdit | Stop |
|---|---|---|---|---|---|
| Codex CLI | stdout 注入 developer context | stdout JSON 注入 additionalContext | exit 2 走工具结果回给 AI；exit 0 静默 | stdout JSON 注入 additionalContext + systemMessage | stdout 摘要 |
| ZCode | 同 Codex | 同 Codex，additionalContext 进 systemMessage | 同 Codex | 同 Codex | 同 Codex |
| Kimi Code CLI | stdout 摘要注入会话上下文 | stdout JSON 注入上下文（观察型，**不阻断用户消息**） | exit 2 拦截 + stderr 指令；exit 0 静默 | stdout JSON 注入上下文 | stdout 摘要 |

所有三端在所有事件上，**内部错误都走 fail-open**（见 §3），hook bug 永远不阻断工作流。

---

## 3. Fail-open 约定（强制）

任何 hook 脚本在 `__main__` 处必须有：

```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[codeguard] 内部错误已忽略（fail-open）: {exc!r}", file=sys.stderr)
        sys.exit(0)
```

含义：
- 钩子内部任何未捕获异常 → stderr 打印 traceback 摘要 → **exit 0**。
- AI 与用户上下文永远收到「钩子无意见」的语义。
- 同一约定适用于全部 5 个钩子的 `__main__` 尾部：`env_check.py`、`post_tool_lint.py`、`pre_tool_git_guard.py`、`user_prompt_validator.py`、`stop_summary.py`（符号级约束，见 §6）。

**禁止**把 fail-open 改为 exit 2——会破坏宿主工作流。

---

## 4. PreToolUse 硬拦截（exit 2）的语义边界

`pre_tool_git_guard.py` 是**唯一**会 exit 2 的 hook——且仅当：
1. 入参命令命中 `is_guarded()`：**直接**（先展开 `$(...)`/反引号内层文本到待扫面，
   再分隔符切段、剥除段首 shell 控制引导词（`if`/`then`/`do`/`while`/`!`…）与
   `NAME=VAL`/`env`/常见裸 wrapper 前缀并跳过 git 全局选项（`-C`/`-c`/…）后
   子命令为 `git commit|push`；子串匹配会误伤 payload/echo 文本）**或一层解释器
   间接**（`bash|sh|python… <脚本>` 的脚本文本、`-c` 内联代码按同规则扫描——
   `bash runner.sh` 式绕过曾连推 4 次漏网；`ro=$(git push …)`、`if git push; then`
   曾静默放行（实测）；拼接式 subprocess 不在静态扫描承诺内）；并且
   `resolve_project_roots()` 用**同一套归一化判定**收集仓库边界（含 `git -C <path>`
   的显式仓边界）——两处必须同源，否则 is_guarded 命中而 roots=[] → main 静默
   放行，归一化修复被 roots 层击穿（0.8.2 实测：`git -C`/`FOO=1 git push`/
   `sudo git push` 三种形态全部穿透）；并且
2. 仓库级 `git config codeguard.skipGate true` 未设置（命中豁免时记账一次，
   `gate_lib.record_skip_event`，Stop 汇总可见）；并且
3. 实际跑 linter 后存在非 skipped 的 failures。

出口内容（`gate_lib.gate_directive` 生成）：
- **首行必须是 `codeguard ❌ 提交门禁未通过：` 综述**（tests/run_all 守护）；
- 整调用声明——"整个工具调用没有执行（含非 git 前序步骤），请把修复与提交拆成
  两次独立调用"——**必须紧跟首行综述（指令前置）**，其后才是每语言细节、
  「怎么修」先于 linter 原始输出。**报告总长受 `REPORT_MAX_CHARS`（3000）硬上限**：
  宿主把超长 stderr 从尾部截断，指令在末段时长报告下会整体丢失（实测 AI 只见到
  首段 linter 报错，逃生门与拆调用指引全没读到）；超限按"保头保尾"截细节，
  尾部的「完整输出: /tmp/…」日志路径不得截掉。PreToolUse 的 exit 2 拒绝的是
  **整个 Bash 工具调用**，此前未声明这一点，AI 反复把写文件与提交塞进同一调用
  并误判"编辑被吞"。

**禁止**因工具未装、项目未接入、检查超时等 UNVERIFIED 状态 exit 2；保留 fail-open，
但 MUST 明确未验证，不能输出“全部通过”。没有适用改动是 SKIPPED，不等于工具故障。
退出码按工具解释，不能全局把 2 当崩溃（例如 pylint 的 2 是违规）。
**取消无基线存量归因**：报错在未修改文件上也可能是本次 API 变化造成的，不能凭路径放行。

**一致性约束**：`UserPromptSubmit` 软门禁与本硬门禁共用同一条 skipGate 豁免，
且**都不得在非 git 目录回退成"扫描 cwd"**——UPS 对非 git 目录输出一行
`_non_git_note` 说明并 exit 0（工作区根被回退扫描 = 上百无关仓的存量 lint
变成永久红，实测）。双副本事件去重键：PreToolUse 用 `tool_use_id + 命令`、
UserPromptSubmit 用 `session_id + 完整文本 + 检查输入身份`、SessionStart/Stop 用 `session_id`；
这些键同时绑定当前会话/worktree。payload 不带对应字段时不做事件去重。
去重仅记录**已经完成**的结果：SessionStart/Stop 异常后可重试；软门禁有跳过或未验证项
时不记录完成。硬门禁只短时重放已完成的拒绝（保留 exit 2 与诊断），绝不缓存放行；
第一份仍在执行时第二份可以重复检查，不可因“事件见过”直接返回 0。
这不是 exactly-once 执行保证，也不能代替当前代码快照。
推送语义：门禁面由 `_guarded_mode` 统一判定——直接命令与一层间接共用同一套
扫描；**commit 面 = 按命令链预测的实际提交面**（`pre_tool_git_guard.staging_intent`：
纯 `git commit` → 仅暂存区；`git add -A` → 含未跟踪；`git add -u` 或 `commit -a` → 仅已跟踪改动；
`git add <paths>` → 并入这些路径——add 在 PreToolUse 时**尚未执行**，
不并入会漏检"即将暂存"的文件；并行会话留在工作树的未暂存 WIP 不属于本次提交，
曾因此被误拦）；纯 push 在 HEAD 快照中检查未推送差异（`up...HEAD`），无上游时检查 HEAD 树。
commit+push 使用预测提交快照并合并未推送范围。删除文件进入影响分析，不作为新增敏感文件。
`git_staging` 将每段 cd/-C、pathspec 与其 worktree 根绑定；硬门禁逐仓传入目标身份，
另一仓的 add -A 不得扩张本仓的纯 commit。Git ls-files 成组解析 glob/目录/literal/exclude；
`-u` 不包含未跟踪文件，`-f` 可包含指定忽略文件，解析后的名字在快照中按字面处理。
子目录 add . 不扩到兄弟目录；路径含空格与连续相对 cd/-C 保留上下文。
动态路径、交互暂存和 pathspec-from-file 等未支持形态返回 JSON additionalContext 的
git UNVERIFIED，保持 exit 0 兼容放行；不能被描述为已准确验证，也不冒充程序内部异常。
硬门禁从 Git blobs 物化一次性目录，不借真实 .git，不修改原 index/工作树，也不复用软门禁缓存。
符号链接/子模块/冲突、超限、依赖不可用都明确 UNVERIFIED。快照是内容隔离，不是执行沙箱；
复杂命令链、非 HEAD refspec、并发修改仍需独立 CI 验证。
UserPromptSubmit 按提示词里的 `push/推送` 选 commit/push 面，但**不传 lanes =
三路宽口径**——软门禁没有待执行命令可预测，按"工作树有待提交改动就提醒"注入
（注入非阻断，多提醒不算错；硬门禁少拦才是底线），软硬两门只在 skipGate 豁免
上严格一致。

PostToolUse 只运行可限定到单文件的检查和 formatter。append_files=false 的项目命令推迟到
显式 check/Git 门禁；保存不能触发整项目 formatter。工具异常不能自动修复。
CLI/MCP 共用 PASS/FAIL/UNVERIFIED/SKIPPED/PLANNED，只有 PASS 的 passed=true。
CLI 的 0/1/2 与 hook 的 fail-open 退出码是不同协议，不能混用。

Java 计划由 `java_analysis` 装配：`java_build` 读描述，`java_impact` 计算模块反向闭包，
`java_planning` 选择命令，`java_environment` 选择 wrapper/JDK，`java_changes` 观察版本差异。
`java_project.py` 保留原 CLI/导入面。默认 skipTests/check -x test 不变，权威命令不加默认参数；
纯版本降级必须由正确 Git 基线与当前描述证明，依赖版本和编译配置变化不得降为 validate/help。
根与变更路径先规范化；分析仍是模块级，不等于完整符号或任意构建脚本语义验证。

### 状态归属与持久化

`scripts/codeguard/hook_state.py` 负责会话归属、统计、冷却、审计和已完成结果；
`scripts/codeguard/storage.py` 负责跨进程锁与原子文件替换。锁覆盖整个读改写，
使用独立且不随数据替换的 `.lock` 文件，不能只有原子写而没有读改写互斥。

- 宿主提供 `session_id` 时，统计保存在 `CODEGUARD_HOME/sessions/<会话与worktree哈希>.json`；
  同一 session 在不同 Git worktree 也分开。Stop 只原子消费当前作用域，后续并发写入保留。
- 无 `session_id` 时沿用 `session_state.json` 与旧插件内状态的兼容读取；此模式**没有跨会话隔离保证**。
  旧全局记录不分配给任意一个带 ID 的新会话，不能把兼容读取称为可信归属迁移。
- 门禁审计由调用线程汇总后写入，`worktree` 是原仓根，`execution_root` 是实际检查目录
  （可能为临时快照），`session_scope` 保留会话归属；`cmd` 为已物化的执行 argv，不再写未展开模板。
  存量豁免记录为 SKIPPED 而非检查通过；当前或基线为 UNVERIFIED 时均不得授予豁免。
- 保存检查只在获得 PASS/FAIL 后登记去重，UNVERIFIED 后允许立即重试。
  去重同时校验文件内容和配置/命令身份；检查前后身份不一致不登记，不把执行中产生的新内容当作已检查。
- 本批真实并发与 worktree 验证在 macOS 完成；Windows 锁实现尚未在 Windows 实机验证。

### 缓存身份与失效

`scripts/codeguard/fingerprint.py` 采集输入身份，`scripts/codeguard/cache.py` 只读写和校验完整软结果。
缓存保存在 `CODEGUARD_HOME/gate-cache/<worktree哈希>.json`；旧 `/tmp` 条目不读取、不自动删除。

- 身份包含真实 worktree 路径、HEAD、Git index 的内容条目、upstream、受版本控制及非忽略工作树文件的内容、
  常见根 linter 配置/注册表声明的配置、用户配置、命令定义和本地工具身份；不再用 mtime/size 代替源码内容。
- Git 文件名按 NUL 分隔，linked worktree 不假设 `.git` 是目录。项目 `codeguard.json` 不保留永不过期的进程副本。
- 预算为 10,000 个文件名、64 MiB 内容；符号链接/特殊文件、预算超限、读取失败或非 Git 目录时禁用该身份缓存，
  仍实际检查。预算不截断成一个看似完整的键；非 Git 保存也仍检查，但不采用仓库身份去重。
- 只保存检查前后身份一致且 `skipped` 为空的软结果；损坏格式、未来时间戳和未知结果均重跑。
  硬门禁不读取软缓存，事件去重亦不缓存放行。
- 这是有明确输入范围的软观察优化，不是原子安全快照或可移植验收凭据；任意外部动态配置、远程依赖和未声明环境变化
  不在完整性证明范围内。准确提交验证和 CI 仍独立运行，不得以软缓存证明整个项目已通过。

---

## 5. 新增 hook checklist

新加一个 hook 时，按顺序自检：

1. **读本 cheat-sheet** + `openspec/specs/hook-protocol/spec.md`。
2. 在 `hooks/hooks.json` 注册（事件 / matcher / command / timeout）。
3. 脚本实现遵守 §1 协议总表的 exit 码与 stdout 形态。
4. 脚本 `__main__` 加 §3 的 fail-open 套子。
5. 在 `tests/run_all.py` 加子集触发：stdin 喂真实宿主协议 JSON，断言 exit 码与 stdout 形状。
6. 在本文件 §1 协议总表加一行，标注实现位置（`hooks/<new>.py:line`）。
7. OpenSpec change：proposal / design / `hook-protocol/spec.md` 加 Scenario / tasks 勾选后 archive。

---

## 6. 协议变更策略

任何对 §1 协议总表字段的修改：

- 同步改本文件 + 对应 `hooks/*.py` + 对应测试。
- 走 OpenSpec change（`hook-protocol` spec 下新增 MODIFIED Requirements + Scenarios）。
- 不允许「先改代码后补文档」的拆分 commit——契约一致是同一变更的原子单位。

---

## 7. 与 OpenSpec 的对应

| Cheat-sheet 节 | OpenSpec spec / Scenario |
|---|---|
| §1 协议总表 | `hook-protocol::Requirement: Hook-host contract SHALL live in hooks/__protocol__.md` |
| §3 Fail-open | `hook-protocol::Requirement: The cheat-sheet SHALL document fail-open` |
| §5 新增 hook checklist | `hook-protocol::Requirement: tests/run_all.py SHALL reference the cheat-sheet` |

变更通过 `openspec archive add-host-protocol-cheatsheet` 入库；spec 在 `openspec/specs/hook-protocol/spec.md`。
