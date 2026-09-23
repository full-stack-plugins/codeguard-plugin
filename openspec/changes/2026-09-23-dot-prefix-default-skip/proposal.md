# 2026-09-23-dot-prefix-default-skip

## Why

用户指令（2026-09-23）：codeguard 要默认忽略 `.` 开头的目录和文件，且这套硬性约束必须**既在代码中也在提示词中**。

实测背景：插件仓发版时 `.agents/plugins/marketplace.json` 与 `.codex-plugin/plugin.json` 被提交安全检查判成「不应入库」阻断发版（入库面已由 `0f284ee` 修复）；但**检查/保存/发现/全量扫描**四类面仍会把点前缀路径当检查对象——宿主工具目录（`.cursor/`、`.claude/`、`.mimosa/` 快照等新点目录不在 `FULL_SCAN_EXCLUDES` 枚举内）、点前缀配置文件（`.eslintrc.js`）会被 lint 报与仓库内容无关的问题，且枚举永远追不上新宿主目录。

## What Changes

- 单一谓词 `path_policy.is_dot_prefixed(path, root)`：相对项目根任一路径段 `.` 开头（`.`/`..` 段除外）即点前缀。
- 检查面四通道接入默认忽略：PostToolUse 保存面、提交门禁 delta 面（`changed_files`）、全量扫描的 ruff 与 `find` 型 gate 注入。
- 语言发现面（`detect_languages`）不再计入点前缀文件。
- **两个例外面不受影响**：入库安全检查照拦密钥模式（`.env`/`*.pem`/`.DS_Store`），linter 配置发现（`requiresConfig`/`linter_config_files`）照常匹配点文件。
- 提示词面声明约束：SessionStart「codeguard 项目记忆」上下文与 `AGENTS.md` 硬性禁令写明该规则，并以测试锚定。

## Capabilities

### New Capabilities

- `scan-scope-policy`：检查作用域的点前缀默认忽略规则、例外面边界与提示词声明要求。

### Modified Capabilities

无。既有 `gate-trigger-policy`、`verdict-integrity` 等行为契约不变。

## Impact

- `scripts/codeguard/path_policy.py`（新谓词）、`scripts/scope.py`（delta 过滤 + ruff/find 注入）、`scripts/codeguard/save_application.py`、`scripts/codeguard/discovery.py`、`scripts/codeguard/startup_application.py`（提示词）。
- `AGENTS.md`、`docs/current-architecture.md`（提示词/文档面）。
- 行为变更：检查面默认忽略点前缀路径——此前会被检查的 `.eslintrc.js`、`.github/` 下文件等不再进入检查面；入库安全与配置发现行为不变。`0f284ee` 的入库面行为一并纳入规格固化。
- 不改动受管技能内容、不改 `FULL_SCAN_EXCLUDES` 枚举本体。
