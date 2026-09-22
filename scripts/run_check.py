"""run_check.py：统一调度 linter，支持 CLI 和 MCP 两种入口。

CLI 模式：
    python3 run_check.py                  # 检测当前项目语言并全跑
    python3 run_check.py --lang java       # 只跑 java
    python3 run_check.py --fix             # 失败时自动修复
    python3 run_check.py --log-dir out     # 失败时完整输出落盘（默认 <path>/out）
    python3 run_check.py --quiet           # 不写日志、不打摘要行（CI 用）
    python3 run_check.py --mcp             # MCP server 模式（官方 SDK stdio）

MCP 模式（OpenSpec 2026-09-22-fix-gate-trigger-and-mcp）：
    暴露 check_code_style / auto_fix / list_languages 三个工具；
    依赖 `mcp>=1.0`（见根 requirements.txt）。按语言执行细节全部委托给
    `scripts/run_per_language.py`；本文件负责 argparse、报告输出与 MCP 接线。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_per_language
from detect_lang import (
    REGISTRY_PATH,
    detect_languages,
    find_project_root,
    load_user_config,
)

LOG_NAME = ".codeguard-last.log"


def _filter_languages(project_root: Path, lang_arg: str | None) -> list[str]:
    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    languages = detect_languages(project_root)
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]
    if lang_arg:
        languages = [lang for lang in languages if lang in lang_arg.split(",")]
    return languages


def cli_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="只跑指定语言（逗号分隔）")
    parser.add_argument("--fix", action="store_true", help="失败时尝试自动修复")
    parser.add_argument("--mcp", action="store_true", help="启动 MCP server（stdio）")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--log-dir", default=None,
                        help="失败时完整输出落盘目录（默认 <path>/out；--quiet 时不写）")
    parser.add_argument("--quiet", action="store_true",
                        help="不写日志、不打印完整日志摘要行（CI 用）")
    parser.add_argument("path", nargs="?", default=".", help="项目根")
    args = parser.parse_args()

    project_root = find_project_root(args.path) or Path(args.path).resolve()

    if args.mcp:
        return mcp_main(project_root)

    log_dir: Path | None
    if args.quiet:
        log_dir = None
    else:
        log_dir = Path(args.log_dir) if args.log_dir else project_root / "out"

    languages = _filter_languages(project_root, args.lang)
    if not languages:
        print("[codeguard] 未识别到语言", file=sys.stderr)
        return 1

    print(f"[codeguard] project: {project_root}")
    print(f"[codeguard] languages: {languages}")
    print()

    results = run_per_language.run_check(
        languages, project_root,
        timeout=args.timeout, fix=args.fix, log_dir=log_dir,
    )
    for r, lang in zip(results, languages):
        if r.get("dry_run"):
            continue
        if not r["passed"] and args.fix:
            print(f"[codeguard] ⚠️  {lang} lint failed, attempting auto-fix...")
        status = "✅ passed" if r["passed"] else f"❌ FAILED (exit={r.get('exit_code')})"
        print(f"  {lang:12s} {status}")
        if not r["passed"] and r.get("log_path") and not args.quiet:
            print(f"     └─ 完整日志: {r['log_path']}")

    print()
    if all(r["passed"] for r in results):
        print("[codeguard] ✅ all passed")
        return 0
    print("[codeguard] ❌ some lints failed")
    return 2


# ══════════════════════════ MCP server（官方 SDK） ══════════════════════════

def _mcp_envelope(results: list[dict]) -> list[dict]:
    """把 run_per_language 结果收成 MCP 契约信封：
    {language, passed, exit_code, stderr_path, log_path}。
    stderr_path 与 log_path 指向同一完整输出文件；通过的语言为空串。
    """
    envelope = []
    for r in results:
        log_path = r.get("log_path", "")
        envelope.append({
            "language": r.get("language", ""),
            "passed": bool(r.get("passed")),
            "exit_code": int(r.get("exit_code", 0)),
            "stderr_path": log_path,
            "log_path": log_path,
        })
    return envelope


def _load_registry_entries() -> list[dict]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [
        {"id": entry["id"], "name": entry.get("name", entry["id"])}
        for entry in data.get("languages", [])
    ]


def mcp_main(project_root: Path) -> int:
    """官方 mcp SDK stdio server：check_code_style / auto_fix / list_languages。"""
    try:
        import mcp.types as mcp_types
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
    except ModuleNotFoundError:
        print("[codeguard] mcp SDK 未安装：pip install -r requirements.txt", file=sys.stderr)
        return 1

    server = Server("codeguard")
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "项目根；缺省用 --mcp 启动时给的 path"},
            "languages": {"type": "array", "items": {"type": "string"},
                          "description": "只跑这些语言 id；缺省按项目自动探测"},
        },
    }

    def text_block(payload) -> mcp_types.TextContent:
        return mcp_types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))

    @server.list_tools()
    async def list_tools() -> list:
        return [
            mcp_types.Tool(
                name="check_code_style",
                description="对项目跑 lint，返回逐语言结果信封与完整输出日志路径",
                inputSchema=input_schema,
            ),
            mcp_types.Tool(
                name="auto_fix",
                description="先跑 formatter 链，再复检 lint（嵌入 check 信封）",
                inputSchema=input_schema,
            ),
            mcp_types.Tool(
                name="list_languages",
                description="列出支持的语言 id 与显示名（不含内部 lint/format 命令）",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        if name == "list_languages":
            return [text_block(_load_registry_entries())]
        if name not in ("check_code_style", "auto_fix"):
            return [text_block({"error": f"unknown tool: {name}"})]
        args = arguments or {}
        raw = args.get("path") or str(project_root)
        root = find_project_root(raw) or Path(raw).resolve()
        requested = args.get("languages")
        langs = list(requested) if requested else _filter_languages(root, None)
        if not langs:
            return [text_block({"error": "未识别到语言", "path": str(root)})]
        if name == "auto_fix":
            fix_results = run_per_language.run_fix(langs, root)
            results = run_per_language.run_check(langs, root, log_dir=root / "out")
            any_fixed = any(
                r.get("fixed") for r in fix_results if not r.get("dry_run")
            )
            payload = {
                "fixed": bool(any_fixed),
                "check": _mcp_envelope(results),
            }
        else:
            results = run_per_language.run_check(langs, root, log_dir=root / "out")
            payload = _mcp_envelope(results)
        return [text_block(payload)]

    async def _serve() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
