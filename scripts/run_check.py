"""run_check.py：统一调度 linter，支持 CLI 和 MCP 两种入口。

CLI 模式：
    python3 run_check.py                  # 检测当前项目语言并全跑
    python3 run_check.py --lang java       # 只跑 java
    python3 run_check.py --fix             # 失败时自动修复
    python3 run_check.py --log-dir out     # 失败时完整输出落盘（默认 <path>/out）
    python3 run_check.py --quiet           # 不写日志、不打摘要行（CI 用）
    python3 run_check.py --mcp             # MCP server 模式（官方 SDK stdio）

MCP 模式（OpenSpec 2026-09-22-fix-gate-trigger-and-mcp）：
    暴露 check_code_style / auto_fix / list_languages / analyze_java_impact 四个工具；
    依赖 `mcp>=1.0`（见根 requirements.txt）。按语言执行细节全部委托给
    `codeguard.language_check`；本文件负责 argparse、报告输出与 MCP 接线。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeguard import check_application
from codeguard import language_check as run_per_language
from codeguard.config import ConfigurationError
from detect_lang import find_project_root

LOG_NAME = ".codeguard-last.log"
_auto_fix = check_application.auto_fix
_filter_languages = check_application.filter_languages
_load_registry_entries = check_application.registry_entries
_mcp_envelope = check_application.result_envelope


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

    log_dir: Path | None = (
        None if args.quiet
        else (Path(args.log_dir) if args.log_dir else project_root / "out")
    )

    try:
        languages = _filter_languages(project_root, args.lang)
    except ConfigurationError as exc:
        print(f"[codeguard] UNVERIFIED: {exc}", file=sys.stderr)
        return 1
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
    for r, lang in zip(results, languages, strict=False):
        if r.get("status") == "FAIL" and args.fix:
            print(f"[codeguard] ⚠️  {lang} lint failed, attempting auto-fix...")
        if r.get("status") in ("UNVERIFIED", "PLANNED", "SKIPPED"):
            status = f"⚠️ {r['status']} ({r.get('reason', '')})"
        else:
            status = "✅ passed" if r["passed"] else f"❌ FAILED (exit={r.get('exit_code')})"
        print(f"  {lang:12s} {status}")
        if not r["passed"] and r.get("log_path") and not args.quiet:
            print(f"     └─ 完整日志: {r['log_path']}")

    print()
    from verdict import exit_status
    verdict_code = exit_status(results)
    if verdict_code == 0:
        print("[codeguard] ✅ all passed" if all(r["passed"] for r in results)
              else "[codeguard] 无须检查的项已跳过；其余检查通过")
        return 0
    print("[codeguard] ❌ some lints failed" if verdict_code == 2
          else "[codeguard] ⚠️ UNVERIFIED：检查未完成，不能视为通过")
    return verdict_code


# MCP server（官方 SDK）；兼容导出供旧调用方使用。
__all__ = ["LOG_NAME", "_auto_fix", "_filter_languages", "_load_registry_entries",
           "_mcp_envelope", "cli_main", "mcp_main"]


def mcp_main(project_root: Path) -> int:
    """官方 mcp SDK stdio server，含只读 Java 影响分析。"""
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
                description="仅对 Git 改动文件跑 formatter 并按相同范围复检；项目级 formatter 不自动扩展范围",
                inputSchema=input_schema,
            ),
            mcp_types.Tool(
                name="list_languages",
                description="列出支持的语言 id 与显示名（不含内部 lint/format 命令）",
                inputSchema={"type": "object", "properties": {}},
            ),
            mcp_types.Tool(
                name="analyze_java_impact", description="只读分析 Java 构建系统、模块依赖和受影响检查计划；不执行构建",
                inputSchema={"type": "object", "properties": {
                    "path": {"type": "string"}, "changed": {"type": "array", "items": {"type": "string"}},
                }},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        return [text_block(check_application.mcp_tool_payload(name, arguments, project_root))]

    async def _serve() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_serve())
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
