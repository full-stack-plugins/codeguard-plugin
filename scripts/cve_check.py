"""codeguard cve：旧导入兼容与 CLI 呈现；业务实现位于 codeguard.cve。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeguard.cve import (  # noqa: F401 — 旧导入兼容
    ECOSYSTEM_SCANNERS,
    _scan_cargo_ecosystem,
    _scan_maven_ecosystem,
    _scan_node_ecosystem,
    _scan_pip_ecosystem,
    _scan_trivy_ecosystem,
    canonical_ecosystem,
    ecosystem_choices,
    language_ecosystem_map,
    precheck,
    scan_project,
)
from codeguard.cve_policy import (  # noqa: F401 — 旧导入兼容
    CVSS_BAND_FLOOR,
    EXIT_FINDINGS,
    EXIT_PASS,
    EXIT_UNVERIFIED,
    EXIT_USAGE,
    SEVERITY_ORDER,
    severities_at_and_above,
)
from codeguard.cve_scanners import (  # noqa: F401
    run,
    scan_cargo,
    scan_maven,
    scan_node,
    scan_pip,
    scan_trivy,
)


def _print_batch(batch):
    print(f"[codeguard-cve] project: {batch.root}")
    print(f"[codeguard-cve] ecosystems: {list(batch.ecosystems) or '(none detected)'}")
    for result in batch.results:
        print(f"  {result['ecosystem']:8s} {result['tool']:28s} {result['status']}")
        if "before_fix" in result:
            print("[codeguard-cve] npm audit fix 已执行；当前结论来自复扫")
        if result["status"] == "PASS":
            continue
        label = "❌ 有漏洞需修复" if result["status"] == "FAIL" else "⚠️ 无法验证"
        print(f"[codeguard-cve] {result['ecosystem']} {label}: {result.get('reason', '')}")
        if result.get("summary_tail"):
            print("  " + result["summary_tail"].replace("\n", "\n  ")[:2000])
        print(f"  ➜ {result.get('fix_hint', '')}")
    if not batch.results:
        print("[codeguard-cve] 无可扫描生态（或对应工具未安装）")
    elif batch.exit_code == EXIT_FINDINGS:
        count = sum(result["status"] == "FAIL" for result in batch.results)
        print(f"[codeguard-cve] {count} 个生态存在漏洞——检查出来了就得修，禁止带洞提交")
    elif batch.exit_code == EXIT_UNVERIFIED:
        print("[codeguard-cve] ⚠️ 存在无法验证的生态——不能视为通过")
    else:
        print("[codeguard-cve] ✅ 所有生态 CVE 检查通过")


def main() -> int:
    ap = argparse.ArgumentParser(prog="codeguard cve")
    ap.add_argument("--ecosystem", help=f"只扫指定生态（{ecosystem_choices()}）")
    ap.add_argument("--fix", action="store_true", help="允许自动修复（当前 npm audit fix）")
    ap.add_argument("--severity", default="HIGH", choices=list(SEVERITY_ORDER))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("path", nargs="?", default=".")
    try:
        args = ap.parse_args()
    except SystemExit as exc:
        if exc.code == 2:
            return EXIT_USAGE
        raise
    batch = scan_project(args.path, args.ecosystem, args.severity, args.fix)
    if batch.error:
        print(f"[codeguard-cve] {batch.error}", file=sys.stderr)
    if args.as_json:
        print(json.dumps({"status": {0: "PASS", 1: "UNVERIFIED", 2: "FAIL", 3: "USAGE"}[batch.exit_code],
                          "exit_code": batch.exit_code, "results": list(batch.results)}, ensure_ascii=False))
    elif not batch.error:
        _print_batch(batch)
    return batch.exit_code


if __name__ == "__main__":
    sys.exit(main())
