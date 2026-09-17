"""cve_check.py：多生态 CVE 依赖漏洞扫描编排器（codeguard cve）。

生态 → 工具映射：
  Maven(Java)   → mvn org.owasp:dependency-check-maven:check（NVD 数据库，检查出即报告修复）
  Node(前端)    → npm audit --json（可 npm audit fix 自动修复）
  Python        → pip-audit（未装则提示安装）
  Rust          → cargo audit（未装则提示安装）
  通用兜底      → trivy fs --scanners vuln（装了 trivy 就能扫一切锁文件）

用法：
  python3 cve_check.py                     # 自动检测项目类型并扫描
  python3 cve_check.py --ecosystem node    # 只扫 node
  python3 cve_check.py --fix               # 允许自动修复（当前仅 npm audit fix）
  python3 cve_check.py --severity HIGH     # 失败阈值（LOW/MEDIUM/HIGH/CRITICAL）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect_lang import detect_languages, find_project_root  # noqa: E402

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, "", "command not found"


def scan_maven(root: Path, threshold: int) -> dict:
    """OWASP dependency-check-maven：failBuildOnCVSS 按阈值，报告落 target/dependency-check-report.html"""
    rc, out, err = run(
        ["mvn", "-q", "org.owasp:dependency-check-maven:check",
         f"-DfailBuildOnCVSS={threshold}"],
        cwd=root, timeout=1800,
    )
    fix_hint = (
        "修复路径: mvn versions:display-dependency-updates 查看可升级依赖；"
        "升级受影响组件版本，或在 dependency-check-suppressions.xml 登记误报"
    )
    return {"ecosystem": "maven", "tool": "owasp dependency-check", "exit": rc,
            "summary_tail": (out + err)[-2500:], "fix_hint": fix_hint}


def scan_node(root: Path, threshold: str, allow_fix: bool) -> dict:
    rc, out, err = run(["npm", "audit", "--json"], cwd=root, timeout=600)
    if rc == 127:
        return {"ecosystem": "node", "tool": "npm audit", "exit": 127,
                "summary_tail": "npm not found", "fix_hint": "安装 Node.js"}
    counts = {}
    fixed_hint = "npm audit fix"
    try:
        meta = json.loads(out).get("metadata", {}).get("vulnerabilities", {})
        counts = {k.lower(): v for k, v in meta.items()}
    except json.JSONDecodeError:
        pass
    over = [s for s in SEVERITY_ORDER
            if SEVERITY_ORDER[s] >= SEVERITY_ORDER.get(threshold.upper(), 2)
            and counts.get(s.lower(), 0) > 0]
    failed = bool(over)
    fix_hint = fixed_hint if failed else ""
    return {"ecosystem": "node", "tool": "npm audit", "exit": rc,
            "counts": counts, "over_threshold": over, "failed": failed,
            "summary_tail": err[-1000:], "fix_hint": fix_hint}


def scan_pip(root: Path) -> dict:
    rc, out, err = run(["pip-audit", "--strict"], cwd=root, timeout=900)
    if rc == 127:
        return {"ecosystem": "python", "tool": "pip-audit", "exit": 127,
                "summary_tail": "pip-audit not installed (pip install pip-audit)",
                "fix_hint": "pip install pip-audit"}
    fix_hint = "pip-audit 无内置修复；按报告升级 requirements/pyproject 中的受影响包"
    return {"ecosystem": "python", "tool": "pip-audit", "exit": rc,
            "summary_tail": (out + err)[-2500:], "fix_hint": fix_hint}


def scan_cargo(root: Path) -> dict:
    # cargo 本体存在但 audit 是外部子命令——先探测，未安装返回 127（无法验证）
    rc_v, _, err_v = run(["cargo", "audit", "--version"], cwd=root, timeout=60)
    if rc_v == 127 or "no such command" in (err_v or "").lower() or "unrecognized" in (err_v or "").lower():
        return {"ecosystem": "rust", "tool": "cargo audit", "exit": 127,
                "summary_tail": "cargo-audit not installed (cargo install cargo-audit)",
                "fix_hint": "cargo install cargo-audit"}
    rc, out, err = run(["cargo", "audit"], cwd=root, timeout=900)
    fix_hint = "按报告升级 Cargo.toml 中的受影响 crate（cargo update 可试）"
    return {"ecosystem": "rust", "tool": "cargo audit", "exit": rc,
            "summary_tail": (out + err)[-2500:], "fix_hint": fix_hint}


def scan_trivy(root: Path, threshold: str) -> dict:
    rc, out, err = run(
        ["trivy", "fs", "--scanners", "vuln",
         "--severity", f"{threshold},CRITICAL" if threshold != "CRITICAL" else "CRITICAL",
         "."],
        cwd=root, timeout=1800,
    )
    if rc == 127:
        return {"ecosystem": "universal", "tool": "trivy", "exit": 127,
                "summary_tail": "trivy not installed (brew install trivy)",
                "fix_hint": "brew install trivy"}
    return {"ecosystem": "universal", "tool": "trivy", "exit": rc,
            "summary_tail": (out + err)[-2500:],
            "fix_hint": "按报告升级受影响依赖版本"}


ECOSYSTEM_SCANNERS = {
    "java": scan_maven,
    "node": scan_node,
    "python": scan_pip,
    "rust": scan_cargo,
}

# 扫描前置条件：缺少标志文件说明项目不属于该生态（或依赖未锁定），
# 运行扫描器只会得到环境错误——归类为「无法验证」而非「有漏洞」。
ECOSYSTEM_PRECHECK = {
    "maven": ["pom.xml"],
    "node": ["package.json", "package-lock.json", "npm-shrinkwrap.json"],
    "python": ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile.lock"],
    "rust": ["Cargo.lock"],
}


def precheck(root: Path, eco: str) -> tuple[bool, str]:
    """返回 (可扫描, 说明)"""
    markers = ECOSYSTEM_PRECHECK.get(eco, [])
    if not markers:
        return True, ""
    if any((root / m).exists() for m in markers):
        return True, ""
    return False, f"缺少 {' / '.join(markers)}（可能不是{eco}项目或依赖未锁定）"


def main() -> int:
    ap = argparse.ArgumentParser(prog="codeguard cve")
    ap.add_argument("--ecosystem", help="只扫指定生态（java/node/python/rust）")
    ap.add_argument("--fix", action="store_true", help="允许自动修复（当前 npm audit fix）")
    ap.add_argument("--severity", default="HIGH", choices=list(SEVERITY_ORDER))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("path", nargs="?", default=".")
    args = ap.parse_args()

    root = find_project_root(args.path) or Path(args.path).resolve()
    langs = detect_languages(root)
    eco_map = {"java": "maven", "typescript": "node", "python": "python", "rust": "rust"}
    ecosystems = sorted({eco_map[l] for l in langs if l in eco_map})
    if args.ecosystem:
        # 显式指定优先：不依赖语言检测结果
        ecosystems = [args.ecosystem]

    print(f"[codeguard-cve] project: {root}")
    print(f"[codeguard-cve] ecosystems: {ecosystems or '(none detected)'}")

    results = []
    for eco in ecosystems:
        ok, why = precheck(root, eco)
        if not ok:
            results.append({"ecosystem": eco, "tool": eco, "exit": 127,
                            "summary_tail": f"无法验证: {why}", "fix_hint": "确认项目类型后重试"})
            print(f"  {eco:8s} SKIP（{why}）")
            continue
        if eco == "maven":
            r = scan_maven(root, SEVERITY_ORDER[args.severity] + 1)  # fail on >= threshold
        elif eco == "node":
            r = scan_node(root, args.severity, args.fix)
            if args.fix and r.get("failed"):
                print("[codeguard-cve] npm audit fix ...")
                frc, _, _ = run(["npm", "audit", "fix"], cwd=root, timeout=900)
                r2 = scan_node(root, args.severity, False)
                r["after_fix"] = r2
        elif eco == "python":
            r = scan_pip(root)
        elif eco == "rust":
            r = scan_cargo(root)
        else:
            continue
        results.append(r)
        status = "PASS" if r["exit"] == 0 else f"FAILED(exit={r['exit']})"
        print(f"  {eco:8s} {r['tool']:28s} {status}")

    if not results:
        print("[codeguard-cve] 无可扫描生态（或对应工具未安装）")
        return 1

    failed = [r for r in results if r["exit"] not in (0, 127) or r.get("failed")]
    unverifiable = [r for r in results if r["exit"] == 127]
    print()
    for r in failed:
        print(f"[codeguard-cve] ❌ {r['ecosystem']} 有漏洞需修复:")
        if r.get("summary_tail"):
            print("  " + r["summary_tail"].replace("\n", "\n  ")[:2000])
        print(f"  ➜ {r.get('fix_hint', '')}")
    for r in unverifiable:
        print(f"[codeguard-cve] ⚠️  {r['ecosystem']} 无法验证（工具未安装）: {r.get('summary_tail', '')}")
        print(f"  ➜ 安装后重跑: {r.get('fix_hint', '')}")
    if failed:
        n = len(failed)
        print(f"\n[codeguard-cve] {n} 个生态存在漏洞——检查出来了就得修，禁止带洞提交")
        return 2
    if unverifiable:
        print("\n[codeguard-cve] ⚠️ 存在无法验证的生态（工具缺失）——不能视为通过")
        return 1
    print("[codeguard-cve] ✅ 所有生态 CVE 检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
