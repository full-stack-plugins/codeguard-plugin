## Why

`scripts/detect_lang.py`（401 行）当前承担三职责合一：① 进程 PATH 补齐（`ensure_user_path` + 内部 helper）、② 用户/项目级配置加载（`load_user_config` / `load_project_overrides` / `get_overrides`）、③ 语言注册表与命令表（其余）。code-review-graph 已记录 hooks↔scripts 高耦合告警（19 条 CALLS 边集中指向 `detect_lang.py`），三职责合一让新增/修改任意一条职责都会触发全部 hooks 的回归面。

## What Changes

- 新增 `scripts/paths.py`：仅含 `ensure_user_path(from_login_shell=False) -> None` 及其内部 helper；零业务依赖。
- 新增 `scripts/user_config.py`：仅含 `load_user_config` / `load_project_overrides` / `get_overrides`；与 hooks/commands 共享。
- `scripts/detect_lang.py` 改为 re-export 上述符号以保持外部 API 不变（`from detect_lang import ensure_user_path, load_user_config` 仍工作），同时删除实现正文。
- 所有 hooks（`env_check.py` / `pre_tool_git_guard.py` / `post_tool_lint.py` / `user_prompt_validator.py` / `stop_summary.py`）继续走 `detect_lang` re-export；显式注释每个 import 来自哪个新文件，便于后续单独演进。

## Capabilities

### New Capabilities

- `language-gate-commands`: Defines the responsibility split between PATH handling, user configuration loading, and language detection command tables.

### Modified Capabilities

None.

## Impact

新增 2 个脚本文件（`scripts/paths.py` / `scripts/user_config.py`，预计合计 ~150 行）；修改 `scripts/detect_lang.py`（约 400 行缩到 ~250 行，但保持 API）；hooks 无外部行为变化，仅加注释。`scripts/languages.json` 与 OpenSpec 现有 `language-gate-commands` / `language-registry-doc-sync` 两个 spec 不变。code-review-graph 的 hooks↔scripts 跨社区边应从 19 降至 ≤4。