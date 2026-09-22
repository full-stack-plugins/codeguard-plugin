## Why

本变更解决三个在真实使用中持续踩中的痛点：

1. **提交门禁触发过于敏感（子串匹配）**：`hooks/user_prompt_validator.py` 的 `is_trigger()` 对 `TRIGGER_PATTERNS = ["commit", "push", "deploy", "提交", "发布", "部署"]` 做**子串**匹配。实测（2026-09-22）真实误触发样例：`我刚才 pushed 了`（命中 `push`）、`关于 deployment 策略的讨论`（命中 `deploy`）——历史行为记录在该文件 `QUESTION_MARKERS` 的注释里（`「git 提交和推送，是不能把 .venv 排除掉么」被当成提交意图`）。纯词边界匹配可消除这类误触发；同时 `?` 已在 `QUESTION_MARKERS` 中，但**触发词与行动意图的组合判定**缺失，导致"非提交语境里的动词"照样进全仓门禁。
2. **`--mcp` 是占位**：`scripts/run_check.py:115-123` 的 `mcp_main()` 明文写"MCP server mode not yet wired with official SDK"。文档承诺的 MCP server 入口实际不可用，AI agent 想在不改 shell spawn 的前提下复用 codeguard 失败，只能重新发明。
3. **失败输出截断**：`scripts/run_check.py:96` 失败时仅 `stderr.splitlines()[-3:][0][:120]`，路径 + 错误码 + 长描述常超过 120 字符，截断后用户得自己翻完整日志。

## What Changes

- 触发启发式改为词边界匹配 + 行动意图组合判定（触发词必须出现在祈使/请求语境，而非任意子串），trigger 后只跑"当前消息提到的语言"而非 `detect_languages()` 的全量。`QUESTION_MARKERS` 保留现有中英双标点并加回归用例锁定。
- `--mcp` 走官方 `mcp` Python SDK：注册 `check_code_style` / `auto_fix` / `list_languages` 三个 stdio JSON-RPC 工具，删除占位分支。
- linter 失败：完整 stderr 写入 `out/.codeguard-last.log`，终端只显示问题摘要与日志路径。

## Capabilities

### New Capabilities

- `gate-trigger-policy`: Defines when the UserPromptSubmit hook runs the lint gate and which languages it checks; explicitly documents when it stays silent.
- `mcp-tool-server`: Defines the stdio JSON-RPC surface exposed by `scripts/run_check.py --mcp`, the three tools, their inputs and outputs, and the failure envelope.

### Modified Capabilities

None.

## Impact

- `hooks/user_prompt_validator.py`：触发判定与语言选择逻辑改动；外部行为变化仅在误触发场景（更少误触发为正向变化）。
- `scripts/run_check.py`：新增官方 SDK 依赖（`mcp` 包需写入 `requirements.txt` 或类似清单），新增 `out/.codeguard-last.log` 落盘逻辑，删除占位 `mcp_main` 分支。
- 新建根 `requirements.txt` 声明 `mcp>=1.0,<2`（2.x 更改了装饰器 API；本仓此前无 requirements 文件，CI 显式安装）。
- 不修改 vendored 技能（codeguard-* 走 vendor 流程）；不修改 marketplace 清单。
