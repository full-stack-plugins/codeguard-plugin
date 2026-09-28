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

from codeguard.engine import (
    ENGINES,
    INVENTORY_REPORT_TYPE,
    _iter_cells,
    resolve_authoritative,
)

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


def probe_capability_inventory(path: str) -> dict:
    """读取内核自报的能力清单。

    权威性由此决定：插件不写死内核是否可用，而是读它自己声明的
    implemented / gap。读不到就按 gap 处理（fail closed）。
    """
    try:
        proc = subprocess.run(
            [path, "capabilities", "all", "--format", "json"],
            capture_output=True, text=True, timeout=PROBE_TIMEOUT, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"readable": False, "reason": f"能力清单读取失败：{exc}"}
    if proc.returncode != 0:
        return {"readable": False, "reason": f"能力清单命令退出 {proc.returncode}"}
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        return {"readable": False, "reason": "能力清单不是 JSON"}
    if not isinstance(payload, dict) or payload.get("report_type") != INVENTORY_REPORT_TYPE:
        return {"readable": False, "reason": "缺少 capability_inventory 标记"}
    return summarize_inventory(payload)


def summarize_inventory(payload: dict) -> dict:
    """把能力清单汇总成 implemented / gap 计数。"""
    counts: dict[str, int] = {}
    for cell in _iter_cells(payload):
        status = cell.get("status")
        key = status if status in ("implemented", "gap", "not_applicable") else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return {
        "readable": True,
        "release_version": payload.get("release_version"),
        "counts": counts,
        "implemented": counts.get("implemented", 0),
        "gap": counts.get("gap", 0),
        "not_applicable": counts.get("not_applicable", 0),
        "unknown": counts.get("unknown", 0),
    }


def build_report() -> dict:
    rust = probe_rust()
    inventory = (
        probe_capability_inventory(rust["path"]) if rust["available"]
        else {"readable": False, "reason": "Rust 组件缺席"}
    )
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
        "rust_capability_inventory": inventory,
    }


def render_human(report: dict) -> str:
    lines = ["Codeguard 引擎边界", ""]
    lines.append(f"质量结论签发方：{report['authoritative_label']}（{report['authoritative_engine']}）")
    for entry in report["engines"]:
        mark = "签发方" if entry["authoritative"] else "非签发方"
        lines.append(f"  - {entry['label']}：{mark}")
        lines.append(f"      {entry['note']}")
    rust = report["rust_component"]
    inv = report["rust_capability_inventory"]
    lines.append("")
    if rust["available"]:
        lines.append(
            f"检测到 Rust 组件：{rust['path']}（cli_version={rust['cli_version']}，"
            f"target={rust['target']}，build_identity={rust['build_identity']}，"
            f"rulepack_compatibility={rust['rulepack_compatibility']}）"
        )
    else:
        lines.append(f"未检测到 Rust 组件：{rust['reason']}")
    lines.append("")
    if inv.get("readable"):
        lines.append(
            f"内核自报能力（release={inv.get('release_version')}）："
            f"implemented {inv['implemented']} / gap {inv['gap']} / "
            f"not_applicable {inv['not_applicable']} / unknown {inv['unknown']}"
        )
        if inv["implemented"] == 0:
            lines.append("  尚无任何类别自报已实现 → 全局签发方保持 Legacy。")
        else:
            lines.append("  已有类别自报已实现 → 该类别可由 Rust 签发，"
                         "逐类别结论见 category_authority。")
    else:
        lines.append(f"内核能力清单不可读（{inv.get('reason')}）→ 按未证明处理，签发方保持 Legacy。")
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
