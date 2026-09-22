## Context

`grep -rn '协议\|protocol\|exit code\|JSON-RPC' hooks/*.py docs/*.md` 显示协议信息散布在 8 处（5 个 hook docstring + 2 份 docs/*.md + 1 处 `gate_lib.py:4-5` 钩子间互引）。无任何一处给「新增 hook 时」做端到端的清单。

实际行为契约（v0.6.2）：
- SessionStart 钩子（`env_check.py`）：stdout 人类可读一行摘要；exit 0；不阻断。
- UserPromptSubmit 钩子（`user_prompt_validator.py`）：stdout JSON `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}`；exit 0（不阻断用户消息）；失败时人工写明修复指令进 `additionalContext`。
- PreToolUse Bash 钩子（`pre_tool_git_guard.py`）：成功静默（exit 0、零输出）；失败 exit 2 + stderr 反馈指令回给 AI。
- PostToolUse Write|Edit|MultiEdit 钩子（`post_tool_lint.py`）：stdout JSON `{"decision":"block","reason":"..."}` 或 `{"hookSpecificOutput":{...}}`；exit 0（注入上下文）；失败 stderr + JSON 反馈。
- Stop 钩子（`stop_summary.py`）：stdout 人类可读；exit 0。
- 全部 hook 内部错误 fail-open：`except Exception: print(... file=sys.stderr); sys.exit(0)`。

三端兼容矩阵（实测）：
- Codex CLI：JSON stdout 注入 developer context；exit 2 阻断 + stderr 走工具结果回给 AI。
- ZCode：同 Codex；`additionalContext` 进 systemMessage。
- Kimi Code CLI：SessionStart/UserPromptSubmit 静默观察型，PostToolUse exit 0 时 stdout 注入上下文；Stop 静默。

## Decisions

### 单源契约 = `hooks/__protocol__.md`

文档分六节：协议总表（事件 × 端 × exit × 输出）/ 三端兼容矩阵 / fail-open 约定 / 新增 hook checklist / 协议变更策略 / 与 OpenSpec spec 的对应。

### 行为零变更

本文档仅复刻 v0.6.2 实际行为，不引入新行为；任何与现实现矛盾的描述都按现状修正，不重设契约。

### `run_all.py` 顶部 docstring 加引用

让 host-protocol 的发现面只有一个：从 README 到 hooks/ 时自然能看到。子集测试逻辑不变。

### 不锁实现细节

exit 码与 JSON schema 用「事实陈述」措辞（"scripts/post_tool_lint.py:226 emits JSON with decision/reason fields"），便于读者回溯到代码；不抽象成「必须如何」。

## Risks / Trade-offs

- **文档与实现漂移**：当前契约由 8 处分散文档描述，本身就有潜在不一致。**新文档是综合而非规范**——未来协议演化需要**先改代码 + 同步本 markdown + 提交**。在 OpenSpec spec `hook-protocol` 中作为 Requirement 加 Scenario 守卫。
- **未来新增 hook 时漏读**：用 checklist 强制后续开发者先读本文件。