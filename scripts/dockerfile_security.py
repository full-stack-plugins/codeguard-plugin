"""`codeguard dockerfile` 协议入口；扫描范围与判定由应用服务负责。"""
from __future__ import annotations

import argparse
import json
import sys

from codeguard.dockerfile import (
    DOCKERFILE_EXTS,
    DOCKERFILE_NAMES,
    find_dockerfiles,
    find_root,
    hadolint_scan,
    run,
    scan_path,
    trivy_scan,
)

__all__ = ["DOCKERFILE_EXTS", "DOCKERFILE_NAMES", "find_dockerfiles", "find_root",
           "hadolint_scan", "main", "run", "scan_path", "trivy_scan"]


def _print_text(report: dict) -> None:
    if not report.get("files"):
        print(f"[codeguard-dockerfile] {report['reason']}", file=sys.stderr)
        return
    print(f"[codeguard-dockerfile] 扫描 {len(report['files'])} 个 Dockerfile @ {report['root']}")
    for key, title in (("hadolint", "hadolint（lint + 安全规则）"),
                       ("trivy", "trivy config（misconfig 安全规则）")):
        result = report[key]
        findings = result["findings"]
        print(f"\n== {title} == {len(findings)} 条发现")
        for finding in findings:
            if isinstance(finding, str):
                print("  " + finding[:180])
            else:
                print(f"  [{finding.get('severity')}] {finding.get('id')}: {finding.get('title')}")
                if finding.get("resolution"):
                    print(f"      ➜ {finding['resolution']}")
        if result["status"] == "UNVERIFIED":
            print(f"  ⚠️ 未验证：{result['summary_tail'] or '没有有效扫描报告'}")
    if report["status"] == "PASS":
        print("[codeguard-dockerfile] ✅ Dockerfile 安全检查通过")
    elif report["status"] == "FAIL":
        print("[codeguard-dockerfile] ❌ Dockerfile 存在安全风险——修复后重扫", file=sys.stderr)
    else:
        print("[codeguard-dockerfile] ⚠️ 检查未完整验证——修复工具或报告问题后重扫", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="codeguard dockerfile")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("path", nargs="?", default=".")
    args = parser.parse_args()

    report = scan_path(args.path)
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
