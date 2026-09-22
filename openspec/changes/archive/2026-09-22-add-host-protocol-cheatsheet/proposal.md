## Why

codeguard-plugin 的 hook 与宿主（Codex CLI / ZCode / Kimi Code）之间存在三套交互协议：SessionStart 静默启动 + 信息附加到上下文；UserPromptSubmit 软引导（exit 0 + stdout JSON additionalContext）；PreToolUse 硬拦截（exit 2 + stderr 指令）；PostToolUse 反馈（exit 0 + stdout JSON）；Stop 静默总结。

这些契约目前分散在每个 hook 脚本 docstring（`post_tool_lint.py:3-7`、`pre_tool_git_guard.py:4-9`、`user_prompt_validator.py:4-5`、`gate_lib.py:4-5`）以及 `docs/partme-codeguard-plugin-Architecture.zh_CN.md` 与 `docs/5、partme-codeguard-plugin-技术方案与路线.md`。MEDIUM #7 评审已指出：未来加新 hook 时，契约无单源——容易在退出码语义（exit 0 vs 2 vs fail-open）与 JSON 协议（stdout / additionalContext / stderr 反馈）上走偏。

## What Changes

- 新增 `hooks/__protocol__.md`：单源契约文档，覆盖 exit 码、JSON 输出格式、三端兼容矩阵、fail-open 约定、stale hook timeout 设定与新增 hook checklist。
- `tests/run_all.py` 顶部 docstring 增加「host protocol cheat-sheet」引用，明确 `__protocol__.md` 为子集契约源。
- 不修改任何 hook 脚本的实现（输出格式与退出码与 v0.6.2 完全一致）；不修改 `hooks/hooks.json`。
- 仅文档 + 引用；归档后 bump patch。

## Capabilities

### New Capabilities

- `hook-protocol`: Defines the canonical contract between codeguard-plugin hooks and host CLIs (Codex CLI / ZCode / Kimi Code).

### Modified Capabilities

None.

## Impact

新增 1 份 Markdown 文档（预计 ~120 行）；修改 1 处 docstring 引用。无脚本/测试/manifest 行为变化。