"""CLI/MCP 共用的项目检查请求；不依赖宿主协议或输出流。"""
from __future__ import annotations

from pathlib import Path

from scope import changed_files

from .config import ConfigurationError, get_overrides, load_user_config
from .discovery import detect_languages, find_project_root
from .fingerprint import MAX_BYTES, MAX_FILES, file_content
from .java_analysis import analyze
from .language_check import run_check, run_fix
from .registry import REGISTRY
from .storage import write_private_text


def filter_languages(project_root: Path, lang_arg: str | None) -> list[str]:
    config = load_user_config()
    enabled = config.get("enabled_languages", [])
    languages = detect_languages(project_root)
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]
    if lang_arg:
        languages = [lang for lang in languages if lang in lang_arg.split(",")]
    return languages


def registry_entries() -> list[dict]:
    return [{"id": entry["id"], "name": entry.get("name", entry["id"])}
            for entry in REGISTRY.values()]


def _public_trace(trace: list[dict]) -> list[dict]:
    """MCP 只暴露逐命令状态；原始 argv/输出仍留在进程结果与本地日志。"""
    phases: dict[str, int] = {}
    output = []
    for attempt in trace:
        phase = attempt["phase"]
        number = phases.get(phase, 0) + 1
        phases[phase] = number
        output.append({
            "phase": phase, "number": number,
            "program": Path(attempt["command"][0]).name,
            "exit_code": attempt["exit_code"], "failure": attempt["failure"],
            "stdout_chars": attempt["stdout_chars"],
            "stderr_chars": attempt["stderr_chars"],
        })
    return output


def result_envelope(results: list[dict]) -> list[dict]:
    """保留 MCP 历史字段；完整日志路径只来自实际检查。"""
    envelope = []
    for result in results:
        log_path = result.get("log_path", "")
        item = {
            "language": result.get("language", ""),
            "passed": bool(result.get("passed")),
            "status": result.get("status", "PASS" if result.get("passed") else "FAIL"),
            "reason": result.get("reason") or result.get("unverified", ""),
            "exit_code": int(result.get("exit_code", 0)),
            "stderr_path": log_path,
            "log_path": log_path,
        }
        if "execution_trace" in result:
            item["execution_trace"] = _public_trace(result["execution_trace"])
        envelope.append(item)
    return envelope


def _formatter_attempts(results: list[dict]) -> list[int]:
    """辨认实际执行的 formatter，跳过计划/豁免/范围拒绝结果。"""
    return [index for index, item in enumerate(results)
            if ("exit_code" in item or item.get("fixed") is True)
            and not item.get("skipped") and not item.get("dry_run")
            and item.get("status") not in ("PLANNED", "SKIPPED", "UNVERIFIED")]


def _public_fix_results(root: Path, results: list[dict],
                        *, confirmed_change: bool | None = None) -> list[dict]:
    """命令成功与已证实修复分列；原始 formatter 诊断进入私有日志。"""
    public = []
    diagnostics = []
    attempts = _formatter_attempts(results)
    attributable = attempts[0] if len(attempts) == 1 and results[attempts[0]].get("fixed") else None
    for index, item in enumerate(results):
        safe = {key: item[key] for key in (
            "language", "status", "exit_code", "note", "reason", "error", "skipped", "dry_run",
        ) if key in item}
        if "fixed" in item:
            safe["formatter_succeeded"] = bool(item["fixed"])
            safe["change_verified"] = confirmed_change is not None and index == attributable
            safe["fixed"] = bool(safe["change_verified"] and confirmed_change)
        if "execution_trace" in item:
            safe["execution_trace"] = _public_trace(item["execution_trace"])
        tail = item.get("stderr_tail")
        if isinstance(tail, str) and tail:
            safe["stderr_chars"] = len(tail)
            diagnostics.append((len(public), f"===== {item.get('language', '')} fix #{index + 1} =====\n{tail}"))
        public.append(safe)
    if diagnostics:
        path = root / "out" / ".codeguard-fix.log"
        try:
            write_private_text(path, "\n".join(block for _, block in diagnostics))
        except OSError:
            return public
        for index, _ in diagnostics:
            public[index]["stderr_path"] = str(path.resolve())
    return public


def _repair_identity(root: Path, files: list[str]) -> dict[Path, str]:
    """对拟修复文件采集有预算的内容身份，不读取仓外路径或整份大文件。"""
    root = root.resolve()
    if len(files) > MAX_FILES:
        raise ValueError("改动文件数超过身份预算")
    identities = {}
    remaining = MAX_BYTES
    for name in files:
        if not isinstance(name, str):
            raise TypeError("改动路径不是字符串")
        path = root / name
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            raise ValueError("改动路径无法解析") from exc
        if not resolved.is_relative_to(root) or path.is_symlink():
            raise ValueError("改动路径越界或包含符号链接")
        try:
            path.lstat()
        except FileNotFoundError:
            # Git 已删除的文件不需要修复；读取期间消失的文件仍由 file_content 拒绝。
            continue
        identity, used = file_content(path, remaining)
        identities[path] = identity
        remaining -= used
    return identities


def auto_fix(root: Path, languages: list[str]) -> dict:
    """仅修复当前 Git 改动；无法确定范围时不扩大写入面。"""
    files = changed_files(root)
    if files is None:
        return {"fixed": False, "status": "UNVERIFIED", "reason": "无法确定 Git 改动范围；请显式使用 CLI fix --all",
                "check": []}
    try:
        before = _repair_identity(root, files)
    except (OSError, TypeError, ValueError):
        return {"fixed": False, "status": "UNVERIFIED",
                "reason": "改动文件路径或内容身份不可验证（链接、读取故障或超预算）；未执行自动修复",
                "check": []}
    fix_results = run_fix(languages, root, files=files)
    try:
        after_fix = _repair_identity(root, files)
    except (OSError, TypeError, ValueError):
        after_fix = None
    results = run_check(languages, root, files=files, log_dir=root / "out")
    checks = result_envelope(results)
    if after_fix is None:
        return {"fixed": False, "status": "UNVERIFIED",
                "reason": "修复后的文件身份不可验证，不能确认内容变化",
                "fix_results": _public_fix_results(root, fix_results), "check": checks}
    try:
        after_check = _repair_identity(root, files)
    except (OSError, TypeError, ValueError):
        return {"fixed": False, "status": "UNVERIFIED",
                "reason": "复检后的文件身份不可验证，不能确认修复结果",
                "fix_results": _public_fix_results(root, fix_results), "check": checks}
    if after_fix != after_check:
        return {"fixed": False, "status": "UNVERIFIED",
                "reason": "复检期间目标文件发生变化，检查结论无法绑定最终内容",
                "fix_results": _public_fix_results(root, fix_results), "check": checks}
    changed = before != after_fix
    attempts = _formatter_attempts(fix_results)
    if changed and (not attempts or not all(fix_results[index].get("fixed") for index in attempts)):
        return {"fixed": False, "status": "UNVERIFIED",
                "reason": "formatter 未全部成功，目标文件虽变化但不能确认为修复完成",
                "fix_results": _public_fix_results(root, fix_results), "check": checks}
    return {"fixed": changed,
            "fix_results": _public_fix_results(root, fix_results, confirmed_change=changed), "check": checks}


def mcp_tool_payload(name: str, arguments: dict | None, project_root: Path):
    """按已公开的四个工具返回 JSON 可序列化结果；不包含 SDK 类型。"""
    if name == "analyze_java_impact":
        args = arguments or {}
        return analyze(args.get("path") or project_root, args.get("changed"))
    if name == "list_languages":
        return registry_entries()
    if name not in ("check_code_style", "auto_fix"):
        return {"error": f"unknown tool: {name}"}
    args = arguments or {}
    raw = args.get("path") or str(project_root)
    root = find_project_root(raw) or Path(raw).resolve()
    requested = args.get("languages")
    try:
        get_overrides(root)
        languages = list(requested) if requested else filter_languages(root, None)
    except ConfigurationError as exc:
        return {"status": "UNVERIFIED", "passed": False, "exit_code": 1,
                "error": str(exc), "path": str(root)}
    if not languages:
        return {"error": "未识别到语言", "path": str(root)}
    if name == "auto_fix":
        return auto_fix(root, languages)
    return result_envelope(run_check(languages, root, log_dir=root / "out"))
