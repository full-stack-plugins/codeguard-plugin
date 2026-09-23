## Why

会话实测两处门禁缺陷：（1）`skipGate` 系豁免（仓库级 `git config codeguard.skipGate`、内联 `-c`、链式赋值）把**入库内容安全扫描**（密钥/凭据/依赖产物模式）连同语言门禁一并跳过——AI 提交 `id_rsa` / `.env` 类文件时密钥检查被静默关闭；（2）工具链发现把 `sys.executable` 的**符号链接目录**（如 `/usr/local/bin`）当脚本目录补入 PATH，真实脚本目录（Framework bin / `sysconfig.get_path("scripts")`）缺失，导致已安装工具被误报「工具不存在 (exit 127)」，全套件出现 6 项假失败。

## What Changes

- **豁免范围收窄**：`skipGate` 系豁免只覆盖语言/lint 门禁；入库内容安全扫描在这些豁免下照常执行，违规仍硬拦截（PreToolUse）或注入上下文（UserPromptSubmit）。进程环境变量 `CODEGUARD_SKIP_GATE`（宿主命令内联赋值无法传入钩子进程，仅用户可设）保留为唯一覆盖二者的完整逃生门。
- **工具链 PATH 根因修复**：`ensure_user_path` 改为补入 `Path(sys.executable).resolve().parent` 与 `sysconfig.get_path("scripts")`；`ToolchainProbe.probe` 与 `run_gate` 入口调用 `ensure_user_path`，使直调 `run_gate`（无钩子上下文）也能解析裸命令。
- **探测诊断区分**：探活 not_found 时以 `python3 -m <tool> --version` 试判，把「未安装」与「模块已安装但脚本入口不在 PATH」区分开。
- 文档与指令文案同步（`hooks/__protocol__.md`、README×2、`docs/current-architecture.md`、`gate_directive` 豁免段）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `hook-protocol`: 豁免语义收窄——skipGate 系豁免仅覆盖语言门禁；入库安全扫描不可被智能体可控的豁免关闭；进程环境变量保留为唯一完整逃生门。

## Impact

- 代码：`scripts/paths.py`、`scripts/codeguard/toolchain.py`、`scripts/codeguard/gate.py`、`scripts/codeguard/git_guard_application.py`、`scripts/codeguard/prompt_application.py`、`scripts/codeguard/reporting.py`。
- 文档：`hooks/__protocol__.md`、`README.md`、`README.zh-CN.md`、`docs/current-architecture.md`。
- 测试：新增 `tests/test_skip_gate_safety_scope.py`；既有豁免测试（空暂存面静默放行、内联豁免公告、env 逃生门）语义不变、保持绿色。
- 兼容性：行为变更点仅在「豁免 + 暂存面含敏感文件」场景；正常提交路径与 UNVERIFIED 语义不变。
