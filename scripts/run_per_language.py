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

from detect_lang import LANG_COMMANDS, detect_language
from scope import scope_cmd

__all__ = ["run_check", "run_fix"]


def _run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """subprocess 调用统一封装：归一化超时(124) / 命令缺失(127) / 其它返回原码。"""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", f"command not found: {e}"
    return proc.returncode, proc.stdout, proc.stderr


def run_check(languages: list[str], project_root: Path,
              *, timeout: int = 120, fix: bool = False,
              dry_run: bool = False, log_dir: Path | None = None) -> list[dict]:
    """对每个语言跑 lint；fix=True 时失败后自动跑 format 复检一次。

    `log_dir` 非空且有语言失败时，完整输出（stdout+stderr 合并——ruff 等
    linter 把诊断打到 stdout）落盘到 `<log_dir>/.codeguard-last.log`
    （组头含语言与退出码），失败条目附带 `log_path`；
    全部通过则不产生日志文件。
    """
    results: list[dict] = []
    log_entries: list[tuple[str, int, str]] = []
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
        # CLI/MCP 是仓健康检查（全量）：注入默认 ruff 配置 + 剔除 vendor 快照，
        # 否则规则集随机器漂移、供应链快照给出不可修的永久红。
        lint_cmd = scope_cmd(lint_cmd, project_root, full_excludes=True)
        rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
        if rc == 2:
            # exit 2 = 用法/依赖/配置崩溃，与仓库内容无关 → unverified
            # （不计失败、不触发 fix、不写失败日志）。
            # exit 127（命令不存在）**故意保持失败**：check CLI 是 CI/健康面，
            # "工具没装"在那里就该红——test_mcp_server 的失败日志与安静模式用例
            # 依赖这条环境无关性（CI 无 ruff，靠 127=失败才进得了失败路径）。
            # 交互钩子路径对 127 归 skipped（不挡人工作）：按场景的有意分歧，
            # 不是口径 bug（v0.8.1 曾误统一过一次，本提交修正）。
            results.append({
                "language": lang,
                "passed": True,
                "exit_code": 2,
                "unverified": "exit 2（工具链异常，非 lint 结论）",
                "stderr_tail": err[-2000:] if err else "",
                "stdout_tail": out[-1000:] if out else "",
            })
            continue
        passed = rc == 0
        if not passed and fix:
            fmt = cmd_def.get("format")
            if fmt:
                _run(scope_cmd(fmt, project_root, full_excludes=True),
                     cwd=project_root, timeout=timeout + 60)
                rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
                passed = rc == 0
        results.append({
            "language": lang,
            "passed": passed,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
            "stdout_tail": out[-1000:] if out else "",
        })
        if not passed and (err or out):
            combined = ""
            if out:
                combined += out
            if err:
                if combined and not combined.endswith("\n"):
                    combined += "\n"
                combined += err
            log_entries.append((lang, rc, combined))
    if log_dir is not None and log_entries:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / ".codeguard-last.log"
        chunks = []
        for lang, rc, content in log_entries:
            block = f"===== {lang} (exit={rc}) =====\n{content}"
            if not block.endswith("\n"):
                block += "\n"
            chunks.append(block)
        try:
            log_path.write_text("\n".join(chunks), encoding="utf-8")
        except OSError:
            log_path = None
        if log_path is not None:
            for r in results:
                if not r["passed"]:
                    r["log_path"] = str(log_path.resolve())
    return results


def run_fix(languages: list[str], project_root: Path,
            *, timeout: int = 120, dry_run: bool = False,
            files: list[str] | None = None) -> list[dict]:
    """对每个语言跑 format；命令缺失归失败；dry_run 仅打印 would-run 行。

    `files` 非空 = 仅修复这些文件（fix.py 缺省 delta 模式）；某语言在改动
    里没有文件 → 该语言整行跳过（skipped 标记），绝不动仓里其它存量文件。
    """
    results: list[dict] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            results.append({"language": lang, "fixed": False, "error": "no command defined"})
            continue
        lang_files: list[str] | None = None
        if files is not None:
            lang_files = [f for f in files if detect_language(f, project_root) == lang]
            if not lang_files:
                results.append({"language": lang, "fixed": True, "skipped": True,
                                "note": "本次改动未涉及该语言"})
                continue
        fmt = cmd_def.get("format")
        if dry_run or not fmt:
            results.append({"language": lang, "fixed": True,
                            "dry_run": True, "command": fmt or []})
            continue
        cmd = scope_cmd(fmt, project_root, files=lang_files,
                        full_excludes=(lang_files is None))
        rc, _out, err = _run(cmd, cwd=project_root, timeout=timeout)
        results.append({
            "language": lang,
            "fixed": rc == 0,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
        })
    return results
