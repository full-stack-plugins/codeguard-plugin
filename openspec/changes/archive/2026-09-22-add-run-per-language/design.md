## Context

代码图谱与全文阅读确认：
- `scripts/run_check.py` 内含 `run()`（subprocess 封装）/ `check_one()`（lint 调用）/ `fix_one()`（format 调用）/ `cli_main()`（CLI 编排 + 报告）。
- `scripts/fix.py` 内含 `main()`（detect_languages 解析 + LANG_COMMANDS 解包 + subprocess.run 串行 + 失败聚合）。
- 两脚本对「失败 = exit code != 0」与「command not found」的处置逻辑基本相同但**分散**：run_check 用 `run()` 集中捕获 `FileNotFoundError → return 127`，fix.py 用 try/except 捕获 `FileNotFoundError → continue + failed.append(lang)`。

重复的代价：
- 同一 lint/format 调用约定的所有演化（subprocess timeout、retry、probe、dry-run、节流）必须双改。
- MCP 模式占位（`run_check.py::mcp_main`）与 `fix.py` 互相不可见但语义重叠。
- 未来要支持 `--json` 输出格式、并发执行、retries 时三处同步。

## Decisions

### 共享边界 = 「per-language 串行执行 + 结果聚合」

`scripts/run_per_language.py` 暴露两个对外函数：

```python
def run_check(languages: list[str], project_root: Path,
              *, timeout: int = 120, fix: bool = False,
              dry_run: bool = False) -> list[dict]: ...
def run_fix(languages: list[str], project_root: Path,
            *, timeout: int = 120, dry_run: bool = False) -> list[dict]: ...
```

返回 dict 与现有 `check_one` / `fix_one` 形态兼容（`passed` / `fixed` / `exit_code` / `stderr_tail` / `stdout_tail`），CLI 层零报告格式改动。

### `dry_run` 显式契约

`run_check(dry_run=True)` / `run_fix(dry_run=True)` 仅打印 `would run: <cmd>`，不真跑。`fix.py` 当前就是这种行为（`print(f"  {lang:12s} would run: ...")`），`run_check.py` 无该选项但 change 不引入新 CLI flag；新增的 dry_run 行为仅作为 run_per_language 内部契约。

### fix=True 走 run_check 内部的 retry

`run_check.py` 当前的「lint fail → 自动 fix → 复检」三段式保留在 `run_per_language.run_check` 内部，作为其 fix 参数的实现细节；`run_fix` 不再做这件事——它本身就是 fix。

### subprocess 错误码统一

- 成功：`exit_code == 0`
- 超时：`exit_code == 124`，`stderr_tail == "timeout after {timeout}s"`
- 命令缺失：`exit_code == 127`，`stderr_tail == "command not found: ..."`

`run_fix` 在命令缺失时仍把 lang 加入失败列表（与现有 fix.py 行为一致）。

### CLI 文件极简化

`run_check.py` 与 `fix.py` 各自只留：argparse 解析、读调用 `run_per_language` 函数、格式化输出（含人类可读状态行 + 汇总）、设置 sys.exit 码。两份文件均 < 100 行。

### 不引入并发 / 不改调用约定

`run_per_language` 保持串行——并发是 MCP/批量场景的未来 change，不在本 change 范围内。`LANG_COMMANDS` 解包与 `subprocess.run` 调用细节都封装在 runner 内，CLI 只见 dict 结果。

## Risks / Trade-offs

- **fix.py 现有 `--dry-run` 行为**：CLI 层接受 `--dry-run` 时透传给 runner，runner 据此切换打印路径。`fix.py` 当前无 `--dry-run`（注释「只看，不真改」与 argparse `--dry-run` 是同一选项），保持兼容。
- **新模块导入路径**：`run_check.py` 与 `fix.py` 现都 `sys.path.insert(0, scripts/)`；新模块位于同目录，零额外配置。`run_per_language` 也走相同 import 路径。
- **MCP 入口**：`run_check.py::mcp_main` 仍是占位，change 不动它；未来 MCP 落地直接调 `run_per_language` 即可。