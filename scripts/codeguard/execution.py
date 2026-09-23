"""外部工具的唯一通用执行边界，不解释 lint/CVE 业务结论。"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from .models import CheckPlan, PlanExecution, ProcessResult


def _text(value: str | bytes | None) -> str:
    # TimeoutExpired 的输出即使 text=True 也可能是 bytes。
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def execute(argv: Sequence[str], cwd: Path, timeout: float, *,
            env: Mapping[str, str] | None = None, stdin_null: bool = False) -> ProcessResult:
    """按 argv 在指定目录执行，不启 shell、不更改全局 cwd/环境。

    归一化可预期的 OS 启动错误与超时；程序错误和用户取消仍向上传播。
    普通工具的退出码（包括工具自己返回的 124/127）原样保留，由领域
    判定解释；failure 只描述执行器实际观察到的启动/超时故障。
    """
    command = tuple(argv)
    root = Path(cwd)
    try:
        proc = subprocess.run(
            list(command), cwd=root, capture_output=True, check=False,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            env={**os.environ, **env} if env is not None else None,
            stdin=subprocess.DEVNULL if stdin_null else None,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = _text(exc.stderr)
        if stderr and not stderr.endswith("\n"):
            stderr += "\n"
        return ProcessResult(command, root, 124, _text(exc.stdout),
                             stderr + f"timeout after {timeout}s", "timeout")
    except FileNotFoundError as exc:
        return ProcessResult(command, root, 127, stderr=f"command not found: {exc}",
                             failure="not_found")
    except OSError as exc:
        return ProcessResult(command, root, 126, stderr=f"cannot start command: {exc}",
                             failure="os_error")
    return ProcessResult(command, root, proc.returncode, _text(proc.stdout), _text(proc.stderr))


def execute_plan(plan: CheckPlan, timeout: float) -> PlanExecution:
    """顺序执行到首个非零结果；保存全部已执行证据，不解释业务豁免。"""
    attempts = []
    for command in plan.commands:
        outcome = execute(command.argv, plan.cwd, timeout, env=dict(command.env) or None)
        attempts.append(outcome)
        if outcome.returncode:
            break
    return PlanExecution(tuple(attempts))
