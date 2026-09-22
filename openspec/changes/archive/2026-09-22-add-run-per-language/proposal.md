## Why

`scripts/run_check.py` 与 `scripts/fix.py` 重复编排同一逻辑：枚举 `detect_languages` → 取 `LANG_COMMANDS[lang].lint/format` → `subprocess.run` → 收集结果。两份脚本共 ~198 行，编排代码占约 80%，只有 argparse 与报告格式不同。任何 lint/format 调用约定变更都要两处同步改；任何新加 per-language 行为（pre-flight probe、retries、dry-run）也要改两处。

## What Changes

- 新增 `scripts/run_per_language.py`：暴露 `run_check(languages, project_root, *, timeout, fix=False, dry_run=False) -> list[dict]` 与 `run_fix(languages, project_root, *, timeout, dry_run=False) -> list[dict]` 两个纯函数，封装「per-language 串行执行 + 结果聚合」逻辑。
- `scripts/run_check.py` 仅保留 CLI 入口（argparse + 报告输出），调用 `run_per_language.run_check`；删除 `check_one` / `fix_one` / `run` 局部实现。
- `scripts/fix.py` 仅保留 CLI 入口，调用 `run_per_language.run_fix`；删除内联 subprocess 与 LANG_COMMANDS 解包。
- 不引入新依赖；不改变 CLI 行为（输出格式、`--fix` 语义、退出码 0/2）。

## Capabilities

### New Capabilities

- `idiomatic-runner`: Defines the per-language execution runner shared between `run_check.py` and `fix.py`.

### Modified Capabilities

None.

## Impact

新增 1 个 Python 文件 `scripts/run_per_language.py`（预计 ~120 行）；修改 `scripts/run_check.py`（128 → ~80 行）与 `scripts/fix.py`（70 → ~40 行）；合计 ~110 行净增（注释与日志占大头）。`commands/`、`hooks/`、`tests/`、`skills/`、`openspec/specs/` 全部不变；`scripts/languages.json` 与 `skills.lock.json` 不变。