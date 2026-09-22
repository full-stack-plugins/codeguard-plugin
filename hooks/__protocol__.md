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

实现定位（行号随 v0.6.2 锁定，下一次重构时核对）：
- SessionStart 摘要：`hooks/env_check.py:34`。
- UserPromptSubmit JSON：`hooks/user_prompt_validator.py:104-109` 与 `:117-125`。
- PreToolUse stderr：`hooks/pre_tool_git_guard.py:159`。
- PostToolUse JSON：`hooks/post_tool_lint.py:226-232`（通过）、`:253-259`（自动修复后通过）、`:275-281`（失败 additionalContext）。
- Stop 摘要：`hooks/stop_summary.py:46`。

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
- 同一约定适用于：`env_check.py:127-131`、`post_tool_lint.py:293-298`、`pre_tool_git_guard.py:166-170`、`user_prompt_validator.py:137-141`、`stop_summary.py:55-62`。

**禁止**把 fail-open 改为 exit 2——会破坏宿主工作流。

---

## 4. PreToolUse 硬拦截（exit 2）的语义边界

`pre_tool_git_guard.py` 是**唯一**会 exit 2 的 hook——且仅当：
1. 入参命令包含 `git commit` 或 `git push`（`is_guarded()` 命中）；并且
2. 仓库级 `git config codeguard.skipGate true` 未设置；并且
3. 实际跑 linter 后存在非 skipped 的 failures。

出口内容（`pre_tool_git_guard.py:158-163`）：stderr 报告块**首行必须是 `codeguard ❌ 提交门禁未通过：` 综述**，其后跟具体问题列表；这是 `tests/run_all.py:142-144` 守护的契约。

**禁止**在 lint skipped（工具未装/项目未接入）时 exit 2——这是「无法验证」而非「验证失败」。

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