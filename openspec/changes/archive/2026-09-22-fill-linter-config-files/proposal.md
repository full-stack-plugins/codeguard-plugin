## Why

M8（v0.6.5）把 `hooks/env_check.py` 的 linter 配置盘点改为从 `scripts/languages.json` 的 `linter_config_files` 字段读取，但当时只迁移了 java/rust/typescript/python 四条历史记录——54 条 stable/beta 语言中仍有约 30 条填着默认空数组，SessionStart 钩子对它们的项目依旧报告「未配置任何 linter」，即使项目里躺着 `.golangci.yml`、`.rubocop.yml`、`.shellcheckrc` 等真实配置。这就是评审遗留的「detect_linter_config 推全局」。

## What Changes

- `scripts/languages.json`：为约 30 条 stable/beta 语言填充 `linter_config_files`（**保守清单**：只填确定存在的业界标准配置文件名，如 `.golangci.yml` / `.shellcheckrc` / `.rubocop.yml` / `.swiftlint.yml` / `analysis_options.yaml` / `.credo.exs` / `.clang-tidy` / `.stylelintrc*` / `.shellcheckrc` 等）。填错无副作用——`detect_linter_config` 只报告**实际存在**的文件，永不误报；填漏只影响盘点广度，不影响正确性。
- `tests/test_validate_languages_json.py` 新增 1 条守护：stable/beta 语言中非空 `linter_config_files` 的数量 ≥ 25（防止未来重构把填充结果清空）。
- 不改 `hooks/env_check.py`（M8 已 registry 驱动）；不改 `scripts/languages.json` 其他字段；不改 `docs/LANGUAGES.md` 生成逻辑（生成器不读该字段，已实测）。

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `registry-driven-config`: 新增 Requirement——已知配置文件名的 stable/beta 语言 SHALL 填充该字段，SessionStart 盘点覆盖面由数据而非代码决定。

## Impact

约 30 条语言 JSON 条目各加 1-4 个字符串；1 条测试；spec delta 1 条 Requirement + 2 Scenario。零运行时行为变化（除 SessionStart 报告更全）。