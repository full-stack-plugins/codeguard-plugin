"""按语言检查与修复的应用服务；CLI、MCP、门禁共用此实现。

暴露两个应用服务函数供 CLI / MCP / Java 门禁复用：
- `run_check(languages, project_root, *, timeout, fix, dry_run)` — 跑 lint。
- `run_fix(languages, project_root, *, timeout, dry_run)` — 跑 format。

CLI（run_check.py / fix.py）负责 argparse + 报告格式；本层选择检查策略。
范围物化、进程执行和判定分别由 codeguard.planning / execution / verdict 负责。

`run_check(fix=True)` 走「lint 失败 → 自动 fix → 复检」三段式。
"""
from __future__ import annotations

from pathlib import Path

from .config import ConfigurationError, get_overrides
from .discovery import detect_language, project_uses_linter
from .execution import execute, execute_plan
from .models import CheckPlan, Command, PlanExecution
from .planning import scoped_plan
from .registry import LANG_COMMANDS

__all__ = ["run_check", "run_fix"]


def _run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """兼容入口；进程执行与故障证据由统一内核负责。"""
    return execute(cmd, cwd, timeout).as_tuple()


def _execution_trace(execution: PlanExecution, phase: str) -> list[dict]:
    """将实际运行的命令转成应用层有界证据；宿主适配再收敛公开字段。"""
    return [{"phase": phase, "command": list(item.argv), "cwd": str(item.cwd),
             "exit_code": item.returncode, "failure": item.failure,
             "stdout_chars": len(item.stdout), "stderr_chars": len(item.stderr),
             "stdout_tail": item.stdout[-1000:], "stderr_tail": item.stderr[-2000:]}
            for item in execution.attempts]


def _execution_output(executions: list[tuple[str, PlanExecution]]) -> str:
    """失败日志保留所有已执行检查的完整输出，不写计划中未运行的命令。"""
    blocks = []
    for phase, execution in executions:
        for number, item in enumerate(execution.attempts, start=1):
            output = item.stdout
            if item.stderr:
                output += ("\n" if output and not output.endswith("\n") else "") + item.stderr
            if output:
                blocks.append(f"[{phase} #{number} exit={item.returncode}]\n{output}")
    return "\n".join(blocks)


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
    from .verdict import FAIL, PASS, PLANNED, SKIPPED, UNVERIFIED, lint_verdict, result

    try:
        get_overrides(project_root)
    except ConfigurationError as exc:
        return [result(lang, UNVERIFIED, str(exc), exit_code=1) for lang in languages]
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
            from .java_analysis import analyze
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
            plan = CheckPlan(project_root, "repo" if files is None else "delta", tuple(
                Command(tuple(c["argv"]), tuple(c.get("env", {}).items()))
                for c in java_plan["commands"]))
        else:
            if "{file}" in " ".join(lint_cmd) and lang_files is None:
                results.append(result(lang, UNVERIFIED, "只有单文件命令，未配置项目 gate"))
                continue
            plan = scoped_plan(lint_cmd, project_root, scope="repo" if lang_files is None else "delta",
                               files=lang_files, append_files=cmd_def.get("append_files", True))
        execution = execute_plan(plan, timeout)
        check_executions = [("check", execution)]
        trace = _execution_trace(execution, "check")
        outcome = execution.terminal
        rc, out, err = outcome.as_tuple()
        lint_cmd = list(outcome.argv)
        status, reason = lint_verdict(rc, lint_cmd, out + err)
        if status == FAIL and fix:
            repairs = run_fix([lang], project_root, timeout=timeout + 60, files=files)
            for repair in repairs:
                trace.extend(repair.get("execution_trace", []))
            if any(r.get("fixed") and not r.get("dry_run") for r in repairs):
                execution = execute_plan(plan, timeout)
                check_executions.append(("recheck", execution))
                trace.extend(_execution_trace(execution, "recheck"))
                outcome = execution.terminal
                rc, out, err = outcome.as_tuple()
                lint_cmd = list(outcome.argv)
                status, reason = lint_verdict(rc, lint_cmd, out + err)
        results.append(result(lang, status, reason, exit_code=rc,
                              unverified=reason if status == UNVERIFIED else "",
                              command=lint_cmd, java_plan=java_plan,
                              stderr_tail=err[-2000:], stdout_tail=out[-1000:],
                              execution_trace=trace))
        if status != PASS:
            combined = _execution_output(check_executions)
            if combined:
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
    try:
        get_overrides(project_root)
    except ConfigurationError as exc:
        return [{"language": lang, "fixed": False, "status": "UNVERIFIED", "exit_code": 1,
                 "note": str(exc), "reason": str(exc)} for lang in languages]
    results: list[dict] = []
    for lang in languages:
        cmd_def = LANG_COMMANDS.get(lang)
        if not cmd_def:
            results.append({"language": lang, "fixed": False, "error": "no command defined"})
            continue
        lang_files: list[str] | None = None
        if files is not None:
            lang_files = [f for f in files if detect_language(f, project_root) == lang]
            # .zsh 剥离（与门禁同一份认知）：shfmt 只支持 POSIX shell/bash，
            # 对 zsh 文件 -w 会重排方言语法造成损坏；跳过并明示修复指令。
            zsh_files = [f for f in lang_files if f.endswith(".zsh")]
            if zsh_files:
                lang_files = [f for f in lang_files if not f.endswith(".zsh")]
                results.append({"language": lang, "fixed": False, "skipped": True,
                                "status": "SKIPPED", "exit_code": 0,
                                "note": (f"{len(zsh_files)} 个 zsh 文件跳过 formatter"
                                         "（shfmt 不支持 zsh；文件头添加"
                                         " `# shellcheck shell=bash` 注释后"
                                         " shellcheck 门禁即可正常送检）")})
            if not lang_files:
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
        if "{file}" in " ".join(fmt) and lang_files is None:
            results.append({"language": lang, "fixed": False, "status": "UNVERIFIED",
                            "note": "formatter 需要明确文件列表", "exit_code": 1})
            continue
        plan = scoped_plan(fmt, project_root, scope="repo" if lang_files is None else "delta",
                           files=lang_files, append_files=cmd_def.get("append_files", True))
        execution = execute_plan(plan, timeout)
        rc, _out, err = execution.terminal.as_tuple()
        results.append({
            "language": lang,
            "fixed": rc == 0,
            "exit_code": rc,
            "stderr_tail": err[-2000:] if err else "",
            "execution_trace": _execution_trace(execution, "fix"),
        })
    return results
