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

from detect_lang import LANG_COMMANDS, detect_language, project_uses_linter
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
              dry_run: bool = False, log_dir: Path | None = None,
              files: list[str] | None = None) -> list[dict]:
    """对每个语言跑 lint；fix=True 时失败后自动跑 format 复检一次。

    `log_dir` 非空且有语言失败时，完整输出（stdout+stderr 合并——ruff 等
    linter 把诊断打到 stdout）落盘到 `<log_dir>/.codeguard-last.log`
    （组头含语言与退出码），失败条目附带 `log_path`；
    全部通过则不产生日志文件。
    """
    from verdict import FAIL, PASS, PLANNED, SKIPPED, UNVERIFIED, lint_verdict, result

    results: list[dict] = []
    log_entries: list[tuple[str, int, str]] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            results.append(result(lang, PLANNED, "没有可执行检查命令"))
            continue
        lang_files = None if files is None else [f for f in files
                    if detect_language(f, project_root) == lang and (project_root / f).is_file()]
        if lang != "java" and lang_files == []:
            results.append(result(lang, SKIPPED, "本次改动未涉及该语言的现存文件"))
            continue
        if not project_uses_linter(cmd_def, project_root):
            results.append(result(lang, UNVERIFIED, "项目缺少已声明的检查配置，未执行"))
            continue
        lint_cmd = (cmd_def.get("gate") or cmd_def.get("lint")) if files is None else cmd_def.get("lint")
        java_plan = None
        if lang == "java":
            from java_project import analyze
            java_plan = analyze(project_root, files)
            if not java_plan["commands"]:
                results.append(result(lang, java_plan["status"], "；".join(java_plan["reasons"]),
                                      java_plan=java_plan))
                continue
            lint_cmd = java_plan["commands"][0]["argv"]
        if dry_run or not lint_cmd:
            results.append(result(lang, PLANNED, "计划检查，尚未执行",
                                  dry_run=True, command=lint_cmd or []))
            continue
        # CLI/MCP 是仓健康检查（全量）：注入默认 ruff 配置 + 剔除 vendor 快照，
        # 否则规则集随机器漂移、供应链快照给出不可修的永久红。
        if java_plan:
            commands = [c["argv"] for c in java_plan["commands"]]
        elif "{file}" in " ".join(lint_cmd):
            if lang_files is None:
                results.append(result(lang, UNVERIFIED, "只有单文件命令，未配置项目 gate"))
                continue
            commands = [scope_cmd(lint_cmd, project_root, single_file=f) for f in lang_files]
        else:
            commands = [scope_cmd(lint_cmd, project_root, files=lang_files,
                                  full_excludes=lang_files is None,
                                  append_files=cmd_def.get("append_files", True))]
        for lint_cmd in commands:
            rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
            if rc != 0:
                break
        status, reason = lint_verdict(rc, lint_cmd, out + err)
        if status == FAIL and fix:
            fixed = run_fix([lang], project_root, timeout=timeout + 60, files=files)[0]
            if fixed.get("fixed") and not fixed.get("dry_run"):
                for lint_cmd in commands:
                    rc, out, err = _run(lint_cmd, cwd=project_root, timeout=timeout)
                    if rc:
                        break
                status, reason = lint_verdict(rc, lint_cmd, out + err)
        results.append(result(lang, status, reason, exit_code=rc,
                              unverified=reason if status == UNVERIFIED else "",
                              command=lint_cmd, java_plan=java_plan,
                              stderr_tail=err[-2000:], stdout_tail=out[-1000:]))
        if status != PASS and (err or out):
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
    if files is not None and any(
            (project_root / f).is_symlink() or not (project_root / f).resolve().is_relative_to(project_root.resolve())
            for f in files):
        return [{"language": lang, "fixed": False, "status": "UNVERIFIED", "exit_code": 1,
                 "note": "修复范围含符号链接或仓外路径，未执行 formatter"} for lang in languages]
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
                results.append({"language": lang, "fixed": False, "skipped": True, "status": "SKIPPED",
                                "note": "本次改动未涉及该语言"})
                continue
        fmt = cmd_def.get("format")
        if files is not None and not cmd_def.get("append_files", True):
            results.append({"language": lang, "fixed": False, "status": "UNVERIFIED",
                            "note": "项目级 formatter 无法限制到改动文件；需显式 --all", "exit_code": 1})
            continue
        if not fmt or dry_run:
            results.append({"language": lang, "fixed": False, "status": "PLANNED",
                            "dry_run": dry_run, "command": fmt or [], "exit_code": 1,
                            "note": "尚未执行修复" if dry_run else "未配置 formatter"})
            continue
        if "{file}" in " ".join(fmt):
            if lang_files is None:
                results.append({"language": lang, "fixed": False, "status": "UNVERIFIED",
                                "note": "formatter 需要明确文件列表", "exit_code": 1})
                continue
            commands = [scope_cmd(fmt, project_root, single_file=f) for f in lang_files]
        else:
            commands = [scope_cmd(fmt, project_root, files=lang_files,
                                  full_excludes=(lang_files is None),
                                  append_files=cmd_def.get("append_files", True))]
        for cmd in commands:
            rc, _out, err = _run(cmd, cwd=project_root, timeout=timeout)
            if rc:
                break
        results.append({
            "language": lang,
            "fixed": rc == 0,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
        })
    return results
