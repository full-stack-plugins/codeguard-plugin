"""外部工具的唯一通用执行边界，不解释 lint/CVE 业务结论。"""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from .models import CheckPlan, PlanExecution, ProcessResult

DEFAULT_MAX_OUTPUT_BYTES = 16 * 1024 * 1024
_READ_SIZE = 64 * 1024


def _text(value: bytes) -> str:
    """只在有界捕获完成后解码，保留非法 UTF-8 的可读上下文。"""
    return value.decode("utf-8", errors="replace")


def execute(argv: Sequence[str], cwd: Path, timeout: float, *,
            env: Mapping[str, str] | None = None, stdin_null: bool = False,
            max_output_bytes: int | None = None) -> ProcessResult:
    """按 argv 在指定目录执行，不启 shell、不更改全局 cwd/环境。

    归一化可预期的 OS 启动错误、超时与输出超限；程序错误和用户取消仍向上传播。
    普通工具的退出码（包括工具自己返回的 124/127）原样保留，由领域
    判定解释；failure 只描述执行器实际观察到的故障。
    """
    if max_output_bytes is None:
        max_output_bytes = DEFAULT_MAX_OUTPUT_BYTES
    if max_output_bytes < 1:
        raise ValueError("输出捕获预算必须为正数")
    command = tuple(argv)
    root = Path(cwd)
    try:
        proc = subprocess.Popen(
            list(command), cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, **env} if env is not None else None,
            stdin=subprocess.DEVNULL if stdin_null else None,
            start_new_session=os.name == "posix",
        )
    except FileNotFoundError as exc:
        return ProcessResult(command, root, 127, stderr=f"command not found: {exc}",
                             failure="not_found")
    except OSError as exc:
        return ProcessResult(command, root, 126, stderr=f"cannot start command: {exc}",
                             failure="os_error")

    captured = (bytearray(), bytearray())
    guard = threading.Lock()
    overflow = threading.Event()
    reader_error = threading.Event()
    total = 0

    def drain(stream, output: bytearray) -> None:
        nonlocal total
        try:
            with stream:
                while chunk := stream.read1(_READ_SIZE):
                    with guard:
                        keep = min(len(chunk), max_output_bytes - total)
                        output.extend(chunk[:keep])
                        total += keep
                        if keep < len(chunk):
                            overflow.set()
        except OSError:
            reader_error.set()

    readers = [threading.Thread(target=drain, args=(stream, output), daemon=True)
               for stream, output in zip((proc.stdout, proc.stderr), captured, strict=True)]
    for reader in readers:
        reader.start()

    def stop_process() -> None:
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif proc.poll() is None:
            proc.kill()

    fault = None
    try:
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if reader_error.is_set():
                fault = "os_error"
                break
            if overflow.is_set():
                fault = "output_limit"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                fault = "timeout"
                break
            overflow.wait(min(0.02, remaining))
        if fault is not None:
            stop_process()
        proc.wait()
        for reader in readers:
            reader.join(timeout=1)
        if any(reader.is_alive() for reader in readers):
            stop_process()
            for reader in readers:
                reader.join(timeout=1)
            fault = fault or "os_error"
        if overflow.is_set() and fault is None:
            fault = "output_limit"
        if reader_error.is_set() and fault is None:
            fault = "os_error"
    except BaseException:
        stop_process()
        proc.wait()
        raise

    stdout, stderr = (_text(bytes(stream)) for stream in captured)
    if fault is not None:
        message = {"timeout": f"timeout after {timeout}s",
                   "output_limit": f"output limit exceeded ({max_output_bytes} bytes)",
                   "os_error": "cannot finish reading command output"}[fault]
        stderr += ("\n" if stderr and not stderr.endswith("\n") else "") + message
    return ProcessResult(command, root, {"timeout": 124, "output_limit": 125,
                                         "os_error": 126}.get(fault, proc.returncode),
                         stdout, stderr, fault)


def execute_plan(plan: CheckPlan, timeout: float) -> PlanExecution:
    """顺序执行到首个非零结果；保存全部已执行证据，不解释业务豁免。"""
    attempts = []
    for command in plan.commands:
        outcome = execute(command.argv, plan.cwd, timeout, env=dict(command.env) or None)
        attempts.append(outcome)
        if outcome.returncode:
            break
    return PlanExecution(tuple(attempts))
