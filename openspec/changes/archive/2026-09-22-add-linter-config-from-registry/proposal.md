## Why

`hooks/env_check.py:23-30` 内置的 `LINTER_CONFIG_FILES` 是硬编码 dict，仅覆盖 java/rust/typescript/python 四种语言。MEDIUM #8 评审指出：新增语言时既要改 `languages.json`，又要同步改 `env_check.py`，否则钩子盘点会漏报已配置 linter。新增 53 种 stable/beta 语言中只有 4 种受益于此机制——其余新增语言都会撞这个对齐陷阱。

## What Changes

- `scripts/languages.json` 每条语言加新字段 `linter_config_files: list[str]`（glob 模式允许，与 `requiresConfig` 同语义），默认 `[]`。
- `hooks/env_check.py`：
  - 删除 `LINTER_CONFIG_FILES` 硬编码常量；
  - `detect_linter_config(project_root)` 从 `LANG_COMMANDS` 派生的元数据查询对应的 `linter_config_files`（实际通过 `REGISTRY` 直接读）；
  - 新增语言自动被盘点——只要它的 `linter_config_files` 非空。
- `scripts/validate_languages_json.py` 加 1 条规则：languages.json 中 `linter_config_files` 必须是 list[str]（可空）。
- 不修改 `docs/LANGUAGES.md` 自动生成逻辑（`scripts/gen_language_docs.py` 仅显示 status/lint/format）。
- `tests/test_validate_languages_json.py` 加 2 条反例（类型错误、非字符串）。

## Capabilities

### New Capabilities

- `registry-driven-config`: Defines the rule that `linter_config_files` for a language is read from `scripts/languages.json` rather than hardcoded.

### Modified Capabilities

None.

## Impact

修改 1 个文件（env_check.py ~10 行）；`scripts/languages.json` 加 4 个现有条目（java/rust/typescript/python）的 `linter_config_files` 值，迁移既有 `LINTER_CONFIG_FILES` 内容；新增 ~10 行校验规则与测试；spec: `registry-driven-config` (2 Requirements) 合入。