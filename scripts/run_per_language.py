"""scripts/run_per_language.py：按语言串行执行 + 结果聚合的共享入口。

暴露两个纯函数供 CLI 复用：
- `run_check(languages, project_root, *, timeout, fix, dry_run)` — 跑 lint。
- `run_fix(languages, project_root, *, timeout, dry_run)` — 跑 format。

CLI（run_check.py / fix.py）只负责 argparse + 报告格式；任何 subprocess
调用约定、退出码归一化、超时与命令缺失的处置都集中在本文件。

`run_check(fix=True)` 走「lint 失败 → 自动 fix → 复检」三段式。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from detect_lang import LANG_COMMANDS

__all__ = ["run_check", "run_fix"]


def _run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """subprocess 调用统一封装：归一化超时(124) / 命令缺失(127) / 其它返回原码。"""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", f"command not found: {e}"
    return proc.returncode, proc.stdout, proc.stderr


def run_check(languages: list[str], project_root: Path,
              *, timeout: int = 120, fix: bool = False,
              dry_run: bool = False) -> list[dict]:
    """对每个语言跑 lint；fix=True 时失败后自动跑 format 复检一次。"""
    results: list[dict] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            results.append({"language": lang, "passed": False, "error": "no command defined"})
            continue
        lint_cmd = cmd_def.get("lint")
        if dry_run or not lint_cmd:
            results.append({"language": lang, "passed": True,
                            "dry_run": True, "command": lint_cmd or []})
            continue
        rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
        passed = rc == 0
        if not passed and fix:
            fmt = cmd_def.get("format")
            if fmt:
                _run(fmt, cwd=project_root, timeout=timeout + 60)
                rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
                passed = rc == 0
        results.append({
            "language": lang,
            "passed": passed,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
            "stdout_tail": out[-1000:] if out else "",
        })
    return results


def run_fix(languages: list[str], project_root: Path,
            *, timeout: int = 120, dry_run: bool = False) -> list[dict]:
    """对每个语言跑 format；命令缺失归失败；dry_run 仅打印 would-run 行。"""
    results: list[dict] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            results.append({"language": lang, "fixed": False, "error": "no command defined"})
            continue
        fmt = cmd_def.get("format")
        if dry_run or not fmt:
            results.append({"language": lang, "fixed": True,
                            "dry_run": True, "command": fmt or []})
            continue
        rc, out, err = _run(fmt, cwd=project_root, timeout=timeout)
        results.append({
            "language": lang,
            "fixed": rc == 0,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
        })
    return results