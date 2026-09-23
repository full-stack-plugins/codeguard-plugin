"""Java 项目规划兼容入口；应用、构建解析、影响策略、环境观察各有单一实现。"""
from __future__ import annotations

import argparse
import json

from codeguard.java_analysis import analyze
from codeguard.java_changes import is_version_bump_only as _is_version_bump_only
from codeguard.java_environment import resolve_java_home as _resolve_java_home

__all__ = ["_is_version_bump_only", "_resolve_java_home", "analyze"]


def main() -> int:
    parser = argparse.ArgumentParser(description="只读 Java 项目与影响分析；不会执行构建或安装工具")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--changed", nargs="*", default=None, help="仓根相对路径；缺省全量")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()
    plan = analyze(args.path, args.changed)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(f"Java {plan['status']} | {plan['build_system']} | 模块级分析（未执行）")
        print("影响模块: " + ", ".join(plan["affected_modules"]))
        for command in plan["commands"]:
            import shlex
            print("计划命令: " + shlex.join(command["argv"]))
        print("说明: " + "；".join(plan["reasons"] + plan["gaps"]))
    return 1 if plan["status"] == "UNVERIFIED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
