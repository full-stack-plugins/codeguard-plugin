## Context

本变更的判定来自 2026-09-22 codeguard-plugin 实测排错：同一 session 里 codeguard-plugin 0.6.5 已发布，被消费的 plugin（stitch-design-plugin、codeguard-skills 等）作为基础设施出错时的第一道防线。

- **触发启发式现状**（2026-09-22 实测复核）：`is_trigger()` 用**子串**匹配触发词；`QUESTION_MARKERS` 已同时覆盖 `？` 与 `?`。因此纯英文问句 `Should I commit this?` 本来就被排除。**真实漏洞是子串匹配**：`pushed` 命中 `push`、`deployment` 命中 `deploy`——不含行动意图的动词变体照样跑全仓 lint。修复方向是词边界 + 行动意图组合，而非再扩问号表。
- **MCP 现状**：`scripts/run_check.py:115-123` 写 "MCP server mode not yet wired with official SDK."。`commands/check.json` 和 `commands/fix.json` 提示词里只指引 `python3 scripts/run_check.py`，没有提 MCP。意味着 MCP 入口是"摆设"，agent 唯一可用路径仍是 shell 子进程。
- **失败输出现状**：`scripts/run_check.py:96` 取 stderr 最后 3 行的第 1 行再截 120 字符。实测 ruff 对单条违规的描述就超过 120 字符（路径 + 行号 + 错误码 + 描述），截断后用户得重跑或加 `--output-format=concise` 才能定位。

## Goals / Non-Goals

**Goals:**

- 让"使用过程中的情况"这种含"发布"二字但意图为询问的句子不再误触发全仓 lint。
- 让英文问句（带 `?`）同样被识别为非提交意图。
- 触发后只跑用户消息中实际提到的语言（提速 + 减少噪声）。
- `--mcp` 走官方 `mcp` Python SDK，暴露三个工具；agent 不再被强制 spawn 子进程。
- 失败时 stderr 完整写入磁盘，终端只给摘要。

**Non-Goals:**

- 不修改 `commands/check.json` / `commands/fix.json` 的提示词结构（已存在的命令可继续工作；仅在 README 里增加 MCP 用法说明）。
- 不修改 vendored 技能（codeguard-* 走 vendor 流程；本变更涉及的语言与脚本都是仓内自有代码）。
- 不重写 `commands/init.json` / `assets/templates/pre-commit-config.yaml`（与本变更无直接关系，且已在前置审计中标记为独立改进项）。
- 不引入自动 commit / 自动 push——`/check` 与 `/fix` 仍只读 + 只修，提交门禁仍由 PreToolUse 钩子把守。

## Decisions

1. **触发判定改为词边界 + 行动意图双条件**：先 `re.search(r"\b(commit|push|deploy)\b|提交|发布|部署", text, re.I)`（中文词无边界问题，按原样保留子串；英文词加 `\b`）。再要求同时命中行动意图：`re.search(r"(请帮我|帮我|请|马上|立刻|现在|下一步|继续|please|now|next|proceed|go ahead|commit this|push this|deploy this)", text, re.I)` **或** 触发词位于句首（祈使语气，如 `commit this now`）。两者其一即进入 lint 路径；否则静默退出 0。`QUESTION_MARKERS` 仅加回归用例，不改内容。
2. **英文 `?` 加入 `QUESTION_MARKERS`**：把 `?` 加入列表，并把"问句句尾 `?` 紧跟在触发词后"做特例豁免（提问「要不要 commit 这个？」即使包含 commit 也不进入门禁）。
3. **trigger 后只跑检测到的语言**：从用户消息中正则提取候选语言 token（与 `languages.json` 的 `id` 字段做大小写无关匹配），命中的子集运行；没有命中则 fallback 到 `detect_languages()` 全量（保持原有探测能力）。
4. **`--mcp` 走官方 SDK**：使用 `mcp.server.Server` + `stdio_server()` 注册三个工具：
   - `check_code_style(path, languages?)`：跑 lint，返回 `{language, passed, exit_code, stderr_path}` 结构。
   - `auto_fix(path, languages?)`：调 formatter，再跑 lint 验证。
   - `list_languages()`：返回 `languages.json` 的 `id` 与 `name`，便于 agent 端校验输入。
   删掉占位 `mcp_main` 分支；新增 `requirements-test.txt` 引入 `mcp>=1.0`。
5. **失败信息落盘**：`scripts/run_check.py` 增加一个可选 `--log-dir` 参数（默认 `out/`），将完整 stderr 写到 `out/.codeguard-last.log`；终端输出改为"完整日志：<abs path>"。保留 `--quiet` 反向开关用于 CI。

## Risks / Trade-offs

- **触发判定变严后真触发是否会漏判？**：在排错里手工构造 12 条真实用户消息（"请帮我 commit"、"commit this" 等）逐条验证。漏判成本 = 用户主动提交时不被门禁拦下，违反 #1 优先级（保安全）。需要红蓝两套回归。
- **MCP 引入新依赖**：`mcp` SDK 是 1.0+ 包，依赖较重。在 vendored 技能外，仓内 `requirements-test.txt` 增加一行 `mcp>=1.0`；CI 安装会自动取到。
- **log 文件泄漏**：写到 `out/.codeguard-last.log` 默认随仓库 `.gitignore`（`out/` 已忽略），不污染版本库；若仓库没忽略 `out/`，本变更需在 `design.md` Migration Plan 加一行 `.gitignore` 检查。

## Migration Plan

1. 修改 `hooks/user_prompt_validator.py`：扩展 `TRIGGER_PATTERNS` / `QUESTION_MARKERS`，新增 `_detect_languages_in_text` 辅助函数，在 `main()` 中按子集运行门禁。
2. 重写 `scripts/run_check.py` 的失败输出逻辑与 `mcp_main()` 实现。
3. 在 `requirements-test.txt` 增加 `mcp>=1.0`。
4. 在 README.md 与 README.zh-CN.md 补 MCP 用法一段（不修改 commands/check.json 本身）。
5. 跑 `python3 tests/run_all.py`（141 项）+ `python3 -m unittest discover -s tests -p 'test_*.py'` 全绿。
6. `openspec validate --strict` 通过后按 `AGENTS.md` 强制发版规则 bump minor 版本（MCP 服务器属新功能：0.6.6 → 0.7.0），归档本变更。
