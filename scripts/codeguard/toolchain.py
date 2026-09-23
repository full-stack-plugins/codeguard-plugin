"""工具探活：显式目标目录、统一执行边界、仅单轮检查内成功去重。"""
from __future__ import annotations

import sys
from pathlib import Path
from threading import Lock

from paths import ensure_user_path

from .execution import execute

BINARY_DEPENDENCIES = {"npx": ["node"]}
_PIPE_GLUE = {"find", "xargs", "grep", "sort", "sh", "bash", "echo"}


def extract_tool_binaries(cmd_def: dict) -> list[str]:
    """提取既有注册表静态命令的工具名；不是通用 Shell 解释器。"""
    binaries: set[str] = set()
    for field in ("lint", "gate"):
        command = cmd_def.get(field)
        if not command:
            continue
        if command[0] in ("bash", "sh") and len(command) >= 3 and command[1] == "-c":
            for segment in command[2].split("|"):
                tokens = segment.strip().split()
                if tokens and tokens[0] not in _PIPE_GLUE:
                    binaries.add(tokens[0])
        else:
            binaries.add(command[0])
    for binary in tuple(binaries):
        binaries.update(BINARY_DEPENDENCIES.get(binary, []))
    return sorted(binary for binary in binaries if binary)


class ToolchainProbe:
    """一轮检查持有一个实例；只记成功，下一轮必须新建。

    相同工具可能被并行语言 worker 共享；按命令加锁，避免重复启动 npx，
    不同工具仍可并行。探活不是 lint 通过证据，随后异常仍由真实检查报告。
    不设置全局缓存，也不跨项目复用实例。
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self._successful: set[tuple[tuple[str, ...], float]] = set()
        self._commands: dict[tuple[tuple[str, ...], float], Lock] = {}
        self._lock = Lock()

    def probe(self, cmd_def: dict, timeout: float = 10) -> tuple[bool, str]:
        """显式 probe 优先，否则逐一验证工具 --version；绝不读取宿主 stdin。"""
        ensure_user_path()  # 直调 run_gate 的路径（测试、run_check）没有钩子代补 PATH
        commands = ([cmd_def["probe"]] if cmd_def.get("probe") else
                    [[binary, "--version"] for binary in extract_tool_binaries(cmd_def)])
        for command in commands:
            key = (tuple(command), timeout)
            with self._lock:
                command_lock = self._commands.setdefault(key, Lock())
            with command_lock:
                with self._lock:
                    if key in self._successful:
                        continue
                result = execute(command, self.project_root, timeout, stdin_null=True)
                if result.failure == "timeout":
                    return False, f"探活超时: {' '.join(command)}"
                if result.failure:
                    hint = _module_entry_hint(command) if result.failure == "not_found" else ""
                    return False, f"探活无法执行: {result.stderr}{hint}"
                if result.returncode:
                    first = next((line for line in (result.stderr or result.stdout).splitlines()
                                  if line.strip()), "")
                    return False, f"探活退出 {result.returncode}: {first[:100]}"
                with self._lock:
                    self._successful.add(key)
        return True, ""


def probe_toolchain(cmd_def: dict, timeout: int = 10, *,
                    project_root: str | Path | None = None) -> tuple[bool, str]:
    """兼容单次调用；批次调用方显式持有 ToolchainProbe 以共享成功探活。"""
    return ToolchainProbe(Path(project_root) if project_root is not None else Path.cwd()).probe(cmd_def, timeout)


def _module_entry_hint(command: list[str]) -> str:
    """裸命令缺失时试 `python3 -m <tool> --version`，区分「未安装」与「入口缺失」。

    仅作诊断提示，不改写执行命令——探活若以 `-m` 形式通过而后续命令仍按裸名
    执行会自相矛盾；入口缺失的根因修复在 ensure_user_path 的 PATH 补齐。
    """
    if len(command) != 2 or "/" in command[0] or command[1] != "--version":
        return ""
    result = execute([sys.executable, "-m", command[0], "--version"], Path.cwd(), 10, stdin_null=True)
    if not result.failure and result.returncode == 0:
        return f"（检测到 Python 模块 `{command[0]}`：已安装但脚本入口不在 PATH）"
    return "（也未检测到同名 Python 模块：可能确实未安装）"
