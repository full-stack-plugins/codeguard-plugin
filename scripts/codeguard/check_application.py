"""CLI/MCP 共用的项目检查请求；不依赖宿主协议或输出流。"""
from __future__ import annotations

from pathlib import Path

from scope import changed_files

from .config import ConfigurationError, get_overrides, load_user_config
from .discovery import detect_languages, find_project_root
from .java_analysis import analyze
from .language_check import run_check, run_fix
from .registry import REGISTRY


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


def result_envelope(results: list[dict]) -> list[dict]:
    """保留 MCP 历史字段；完整日志路径只来自实际检查。"""
    envelope = []
    for result in results:
        log_path = result.get("log_path", "")
        envelope.append({
            "language": result.get("language", ""),
            "passed": bool(result.get("passed")),
            "status": result.get("status", "PASS" if result.get("passed") else "FAIL"),
            "reason": result.get("reason") or result.get("unverified", ""),
            "exit_code": int(result.get("exit_code", 0)),
            "stderr_path": log_path,
            "log_path": log_path,
        })
    return envelope


def auto_fix(root: Path, languages: list[str]) -> dict:
    """仅修复当前 Git 改动；无法确定范围时不扩大写入面。"""
    files = changed_files(root)
    if files is None:
        return {"fixed": False, "status": "UNVERIFIED", "reason": "无法确定 Git 改动范围；请显式使用 CLI fix --all",
                "check": []}
    targets = [root / file for file in files if (root / file).is_file() and not (root / file).is_symlink()]
    before = {path: path.read_bytes() for path in targets}
    fix_results = run_fix(languages, root, files=files)
    results = run_check(languages, root, files=files, log_dir=root / "out")
    changed = any(not path.is_file() or path.read_bytes() != body for path, body in before.items())
    return {"fixed": changed, "fix_results": fix_results, "check": result_envelope(results)}


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
