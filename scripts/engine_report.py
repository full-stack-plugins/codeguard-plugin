#!/usr/bin/env python3
"""engine —— 报告当前由哪个引擎签发质量结论，以及是否检测到 Rust 组件。

这是插件侧唯一需要回答"结论是谁给的"的地方。只读，不执行任何检查：
本命令既不扫描代码，也不安装工具，更不会因为发现 Rust 内核就切换签发方。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codeguard.engine import ENGINES, resolve_authoritative

PROBE_TIMEOUT = 10


def probe_rust() -> dict:
    """探测 PATH 上的 codeguard 是否为 Rust 组件。

    Legacy CLI 没有 --version（会落入未知子命令并以 1 退出），Rust 组件则以
    report_type=version 的 JSON 应答。两者因此可以无歧义区分。
    """
    candidate = shutil.which("codeguard")
    if not candidate:
        return {"available": False, "reason": "PATH 上没有 codeguard"}
    try:
        proc = subprocess.run(
            [candidate, "--version", "--format", "json"],
            capture_output=True, text=True, timeout=PROBE_TIMEOUT, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "reason": f"探测失败：{exc}"}
    if proc.returncode != 0:
        return {"available": False,
                "reason": f"不是 Rust 协议（exit {proc.returncode}）"}
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        return {"available": False, "reason": "版本输出不是 JSON"}
    if not isinstance(payload, dict) or payload.get("report_type") != "version":
        return {"available": False, "reason": "缺少 report_type=version 标记"}
    return {
        "available": True,
        "path": candidate,
        "cli_version": payload.get("cli_version"),
        "target": payload.get("target"),
        "build_identity": payload.get("build_identity"),
        "rulepack_compatibility": payload.get("rulepack_compatibility"),
    }


def build_report() -> dict:
    rust = probe_rust()
    authoritative = resolve_authoritative(rust_available=rust["available"])
    return {
        "report_type": "engine",
        "authoritative_engine": authoritative.id,
        "authoritative_label": authoritative.label,
        "engines": [
            {
                "id": spec.id,
                "label": spec.label,
                "authoritative": spec.authoritative,
                "note": spec.note,
            }
            for spec in (ENGINES["legacy"], ENGINES["rust"])
        ],
        "rust_component": rust,
    }


def render_human(report: dict) -> str:
    lines = ["Codeguard 引擎边界", ""]
    lines.append(f"质量结论签发方：{report['authoritative_label']}（{report['authoritative_engine']}）")
    for entry in report["engines"]:
        mark = "签发方" if entry["authoritative"] else "非签发方"
        lines.append(f"  - {entry['label']}：{mark}")
        lines.append(f"      {entry['note']}")
    rust = report["rust_component"]
    lines.append("")
    if rust["available"]:
        lines.append(
            f"检测到 Rust 组件：{rust['path']}（cli_version={rust['cli_version']}，"
            f"target={rust['target']}，build_identity={rust['build_identity']}，"
            f"rulepack_compatibility={rust['rulepack_compatibility']}）"
        )
        lines.append("  它当前不签发质量结论：检测到 ≠ 可用于门禁。")
    else:
        lines.append(f"未检测到 Rust 组件：{rust['reason']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeguard engine",
        description="报告由哪个引擎签发质量结论（只读，不执行检查）",
    )
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    report = build_report()
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
