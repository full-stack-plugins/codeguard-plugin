## Context

实测证据（code-review-graph 2026-09-22 build，HEAD `5591125`）：
- 社区数 3：scripts-scan(42 节点) / hooks-gate(39 节点) / tests-skill(36 节点)。
- 跨社区边 25，其中 19 条 CALLS 全部指向 `scripts/detect_lang.py` 的同一组函数：
  - `ensure_user_path`（4 处，env_check / post_tool_lint / pre_tool_git_guard / user_prompt_validator）
  - `detect_languages` / `detect_language`（5 处）
  - `find_project_root`（3 处）
  - `probe_toolchain`（5 处）
  - `project_uses_linter`（5 处）
  - `load_user_config`（4 处，含 user_prompt_validator / pre_tool_git_guard / post_tool_lint / env_check）

耦合来源是三职责合一：所有 hook 既要 PATH 补齐（属于进程环境），又要项目配置（属于用户态），又要语言识别（属于注册表）。后续若新增 hook / 修改 PATH 策略 / 改配置 schema 都会让 hooks 全军覆没。

## Decisions

### 三个文件按职责一刀切

- `scripts/paths.py`：仅 `ensure_user_path` + 内部静态目录与 fallback。依赖：std + `Path`。无项目根、无 JSON 解析。
- `scripts/user_config.py`：`load_user_config` / `load_project_overrides` / `get_overrides`。依赖：std + JSON + `Path`。无 subprocess。
- `scripts/detect_lang.py`：保留 `detect_languages` / `detect_language` / `find_project_root` / `probe_toolchain` / `project_uses_linter` / `extract_tool_binaries` / `LANG_COMMANDS` / `_load_registry`。依赖注册表 + subprocess。

### 外部 API 不变

`detect_lang.py` 顶部 `from paths import ensure_user_path` 与 `from user_config import load_user_config, load_project_overrides, get_overrides`，并 `__all__` 暴露全部历史符号。已有 6 处 hooks + 1 处 `fix.py` + 1 处 `run_check.py` + `tests/run_all.py` 全部无需改动。

### 调用方注释化

每个 hook 的 `from detect_lang import ...` 行末尾加注释 `# 实际定义见 scripts/paths.py / user_config.py`，便于未来定位到正确文件。

### 不动锁与注册表

`scripts/languages.json` 与 `skills.lock.json` 不变；拆分是纯结构调整，不影响任何语言识别结果。

### 不下沉到插件本地技能

PATH / 用户配置是 Hook 必需的运行时环境，与「面向用户的技能」无关——下沉到 `skills/` 会让 import 路径变得奇怪且增加发现成本。

## Risks / Trade-offs

- **首次 import 多一层**：`ensure_user_path` 调用点不变，但 Python 解释器多解析一个小文件（<10ms），可忽略。
- **`detect_lang.py` 顶端 re-export 列表易过期**：新增函数时若忘记在 `detect_lang.py` 加 re-export，hook 会立刻 ImportError——这是设计意图（fail-fast），但需在 PR review 时人工检查。
- **测试夹具路径**：`tests/run_all.py` 用 `sys.path.insert(0, str(PLUGIN / "scripts"))`，新文件位置在同一目录，零改动。