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
| PreToolUse `Bash` | `pre_tool_git_guard.py` | 通过：空 | 通过：空；失败：完整修复指令 | 0（通过）/ 2（拦截） | 通过：否；失败：是 |
| PostToolUse `Write\|Edit\|MultiEdit` | `post_tool_lint.py` | JSON `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"..."}, "systemMessage":"..."}` | 仅内部错误时 | 0 | 否 |
| Stop | `stop_summary.py` | 人类可读会话摘要 | 仅内部错误时 | 0 | 否 |

实现定位（**符号而非行号**——行号随每次重构腐烂，符号不腐；v0.8.0 起弃用行号指针）：
- SessionStart 摘要：`hooks/env_check.py::main`（含双副本告警段）。
- UserPromptSubmit JSON：`hooks/user_prompt_validator.py::main`（非 git 目录跳过说明 `_non_git_note`）与 `::is_trigger`。
- PreToolUse stderr：`hooks/pre_tool_git_guard.py::main`；拦截判定 `::is_guarded`（直接 + `_command_indirect` 一层间接）。
- PostToolUse JSON：`hooks/post_tool_lint.py::main`（通过/自动修复后通过/失败 additionalContext 三处 print）。
- Stop 摘要：`hooks/stop_summary.py::main`（含绕过计数 `summarize` 与 skipGate 遗留告警）。

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
1. 入参命令命中 `is_guarded()`：**直接**（分隔符切段后段首为 `git commit|push`；
   子串匹配会误伤 payload/echo 文本）**或一层解释器间接**（`bash|sh|python… <脚本>`
   的脚本文本、`-c` 内联代码按同规则扫描——`bash runner.sh` 式绕过曾连推 4 次漏网；
   拼接式 subprocess 不在静态扫描承诺内）；并且
2. 仓库级 `git config codeguard.skipGate true` 未设置（命中豁免时记账一次，
   `gate_lib.record_skip_event`，Stop 汇总可见）；并且
3. 实际跑 linter 后存在非 skipped 的 failures。

出口内容（`gate_lib.gate_directive` 生成）：
- **首行必须是 `codeguard ❌ 提交门禁未通过：` 综述**（tests/run_all 守护）；
- 报告块**末段必须包含整调用声明**——"整个工具调用没有执行（含非 git 前序步骤），
  请把修复与提交拆成两次独立调用"。PreToolUse 的 exit 2 拒绝的是**整个 Bash 工具
  调用**，此前未声明这一点，AI 反复把写文件与提交塞进同一调用并误判"编辑被吞"。

**禁止**在 lint skipped（工具未装/项目未接入/本次改动未涉及/exit 2 工具链异常）
时 exit 2——这是「无法验证」而非「验证失败」。

**一致性约束**：`UserPromptSubmit` 软门禁与本硬门禁共用同一条 skipGate 豁免，
且**都不得在非 git 目录回退成"扫描 cwd"**——UPS 对非 git 目录输出一行
`_non_git_note` 说明并 exit 0（工作区根被回退扫描 = 上百无关仓的存量 lint
变成永久红，实测）。双副本事件去重键（四个钩子同一规则）：PreToolUse 用 `tool_use_id`、
UserPromptSubmit 用 `session_id + 文本前缀`、SessionStart/Stop 用 `session_id`；
payload 不带这些字段（测试协议/其它宿主）时不去重，保持旧行为。
推送语义：门禁面由 `_guarded_mode` 统一判定——直接命令与一层间接共用同一套
扫描；commit 面=暂存+未暂存+未跟踪，push 面=并集未推送提交（`up...HEAD`）；
UserPromptSubmit 按提示词里的 `push/推送` 选同一套面，软硬两门永远看同一组文件。

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