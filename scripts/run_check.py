"""run_check.py：统一调度 linter，支持 CLI 和 MCP 两种入口。

CLI 模式：
    python3 run_check.py                  # 检测当前项目语言并全跑
    python3 run_check.py --lang java       # 只跑 java
    python3 run_check.py --fix             # 失败时自动修复
    python3 run_check.py --mcp             # MCP server 模式

按语言执行细节（subprocess 调用、退出码归一化、fix 复检）全部委托给
`scripts/run_per_language.py`；本文件仅负责 argparse + 报告输出。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_per_language
from detect_lang import (
    detect_languages,
    find_project_root,
    load_user_config,
)


def cli_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="只跑指定语言（逗号分隔）")
    parser.add_argument("--fix", action="store_true", help="失败时尝试自动修复")
    parser.add_argument("--mcp", action="store_true", help="启动 MCP server（stdio）")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("path", nargs="?", default=".", help="项目根")
    args = parser.parse_args()

    project_root = find_project_root(args.path) or Path(args.path).resolve()

    if args.mcp:
        return mcp_main(project_root)

    cfg = load_user_config()
    enabled = cfg.get("enabled_languages", [])
    languages = detect_languages(project_root)
    if enabled and enabled != ["auto"]:
        languages = [lang for lang in languages if lang in enabled]
    if args.lang:
        languages = [lang for lang in languages if lang in args.lang.split(",")]

    if not languages:
        print("[codeguard] 未识别到语言", file=sys.stderr)
        return 1

    print(f"[codeguard] project: {project_root}")
    print(f"[codeguard] languages: {languages}")
    print()

    results = run_per_language.run_check(
        languages, project_root,
        timeout=args.timeout, fix=args.fix,
    )
    for r, lang in zip(results, languages):
        if r.get("dry_run"):
            continue
        if not r["passed"] and args.fix:
            print(f"[codeguard] \u26a0\ufe0f  {lang} lint failed, attempting auto-fix...")
        status = "\u2705 passed" if r["passed"] else f"\u274c FAILED (exit={r.get('exit_code')})"
        print(f"  {lang:12s} {status}")
        if not r["passed"] and r.get("stderr_tail"):
            print(f"     \u2514\u2500 {r['stderr_tail'].splitlines()[-3:][0][:120]}")

    print()
    if all(r["passed"] for r in results):
        print("[codeguard] \u2705 all passed")
        return 0
    print("[codeguard] \u274c some lints failed")
    return 2


def mcp_main(project_root: Path):
    """极简 MCP server：暴露 check_code_style 工具。

    协议参考：https://modelcontextprotocol.io
    这里用 stdio JSON-RPC 风格——真实工程里应换成官方 SDK。
    """
    # 占位实现：调用方传 {"method": "tools/call", "params": {"name": "check_code_style"}}
    # 真实落地时建议用 mcp Python SDK：https://github.com/modelcontextprotocol/python-sdk
    print("[codeguard] MCP server mode not yet wired with official SDK.", file=sys.stderr)
    print("[codeguard] Use CLI mode for now: python3 run_check.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
