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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect_lang import detect_languages, find_project_root

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

# CVSS v3 档位下界（LOW 0.1–3.9 / MEDIUM 4.0–6.9 / HIGH 7.0–8.9 / CRITICAL 9.0–10）。
# maven 的 failBuildOnCVSS 是数值语义，与其余扫描器的「级别集合」必须表达同一 intent：
# --severity HIGH ⇒ 恰好在 CVSS>=7 失败，而不是旧映射 SEVERITY_ORDER+1 产生的 >=3
# （那会把全部 MEDIUM 也算进 HIGH，比其他扫描器激进一整档）。
CVSS_BAND_FLOOR = {"LOW": 0, "MEDIUM": 4, "HIGH": 7, "CRITICAL": 9}


def severities_at_and_above(threshold: str) -> list[str]:
    """「阈值及以上」的级别集合，标签序从低到高（trivy 的 --severity 逗号列表用）"""
    floor = SEVERITY_ORDER[threshold.upper()]
    return [s for s in ("LOW", "MEDIUM", "HIGH", "CRITICAL") if SEVERITY_ORDER[s] >= floor]

# 退出码：0 通过 / 1 无法验证 / 2 存在漏洞 / 3 参数错误。
# 3 必须独立：CI 常用 -eq 2 判定安全告警，而 argparse 默认的参数错误退出码正是 2，
# 复用会把一次拼写错误读成漏洞告警；复用 1 又会把「用错了参数」掩盖成「环境缺工具」。
EXIT_PASS = 0
EXIT_UNVERIFIED = 1
EXIT_FINDINGS = 2
EXIT_USAGE = 3


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False, text=True, timeout=timeout)
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
         "--severity", ",".join(severities_at_and_above(threshold)),
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


# 各扫描器的调用约定不同（阈值形式、是否支持自动修复），适配成统一入口：
# (root, severity, allow_fix) -> result。差异与生态标识放在一起，不再散落在派发分支里。
def _scan_maven_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    # failBuildOnCVSS 按数值档位（HIGH⇒7），与其余扫描器的「阈值及以上」同一 intent
    return scan_maven(root, CVSS_BAND_FLOOR[severity])


def _scan_node_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    result = scan_node(root, severity, allow_fix)
    if allow_fix and result.get("failed"):
        print("[codeguard-cve] npm audit fix ...")
        run(["npm", "audit", "fix"], cwd=root, timeout=900)
        result["after_fix"] = scan_node(root, severity, False)
    return result


def _scan_pip_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_pip(root)


def _scan_cargo_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_cargo(root)


def _scan_trivy_ecosystem(root: Path, severity: str, allow_fix: bool) -> dict:
    return scan_trivy(root, severity)


# 唯一权威映射：规范标识 → 别名 / 映射语言 / 前置条件标志文件 / 扫描入口。
# 命令行入参、语言检测映射、前置条件判定与结果报告全部从这里派生，
# 标识不一致在该文件内不再可表达。
# languages 为空的生态（universal）只能显式选择，不会被语言检测自动选中。
ECOSYSTEM_SCANNERS = {
    "maven": {
        "aliases": ("java",),
        "languages": ("java",),
        "markers": ("pom.xml",),
        "scan": _scan_maven_ecosystem,
    },
    "node": {
        "aliases": (),
        "languages": ("typescript",),
        "markers": ("package.json", "package-lock.json", "npm-shrinkwrap.json"),
        "scan": _scan_node_ecosystem,
    },
    "python": {
        "aliases": (),
        "languages": ("python",),
        "markers": ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile.lock"),
        "scan": _scan_pip_ecosystem,
    },
    "rust": {
        "aliases": (),
        "languages": ("rust",),
        "markers": ("Cargo.lock",),
        "scan": _scan_cargo_ecosystem,
    },
    "universal": {
        "aliases": ("trivy",),
        "languages": (),
        "markers": (),
        "scan": _scan_trivy_ecosystem,
    },
}


def canonical_ecosystem(value: str) -> str | None:
    """生态标识归一化：接受规范标识与其别名；未声明返回 None"""
    key = value.strip().lower()
    if key in ECOSYSTEM_SCANNERS:
        return key
    for canonical, spec in ECOSYSTEM_SCANNERS.items():
        if key in spec["aliases"]:
            return canonical
    return None


def ecosystem_choices() -> str:
    """全部可接受标识（含别名），供错误信息与 --help 共用"""
    parts = []
    for canonical, spec in ECOSYSTEM_SCANNERS.items():
        aliases = spec["aliases"]
        parts.append(f"{canonical}（别名 {'/'.join(aliases)}）" if aliases else canonical)
    return "、".join(parts)


def language_ecosystem_map() -> dict[str, str]:
    """语言 id → 规范生态标识，从权威映射派生"""
    return {lang: canonical
            for canonical, spec in ECOSYSTEM_SCANNERS.items()
            for lang in spec["languages"]}


def precheck(root: Path, eco: str) -> tuple[bool, str]:
    """返回 (可扫描, 说明)。缺少标志文件说明项目不属于该生态（或依赖未锁定），
    运行扫描器只会得到环境错误——归类为「无法验证」而非「有漏洞」。"""
    markers = ECOSYSTEM_SCANNERS.get(eco, {}).get("markers", ())
    if not markers:
        return True, ""
    if any((root / m).exists() for m in markers):
        return True, ""
    return False, f"缺少 {' / '.join(markers)}（可能不是{eco}项目或依赖未锁定）"


def main() -> int:
    ap = argparse.ArgumentParser(prog="codeguard cve")
    ap.add_argument("--ecosystem", help=f"只扫指定生态（{ecosystem_choices()}）")
    ap.add_argument("--fix", action="store_true", help="允许自动修复（当前 npm audit fix）")
    ap.add_argument("--severity", default="HIGH", choices=list(SEVERITY_ORDER))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("path", nargs="?", default=".")
    args = ap.parse_args()

    root = find_project_root(args.path) or Path(args.path).resolve()

    # 参数错误必须先于任何扫描器启动被拒绝：否则会先花掉一次真实扫描再报错。
    # 退出码用独立的 EXIT_USAGE，避免被调用方读成「存在漏洞」或「无法验证」。
    if args.ecosystem:
        # 显式指定优先：不依赖语言检测结果
        canonical = canonical_ecosystem(args.ecosystem)
        if canonical is None:
            print(f"[codeguard-cve] 未知生态 {args.ecosystem!r}；可接受：{ecosystem_choices()}",
                  file=sys.stderr)
            return EXIT_USAGE
        ecosystems = [canonical]
    else:
        langs = detect_languages(root)
        eco_map = language_ecosystem_map()
        ecosystems = sorted({eco_map[l] for l in langs if l in eco_map})
        if langs and not ecosystems:
            # 识别到了语言但都不属于原生生态（go/php/ruby…）→ 通用兜底给出结论，
            # 而不是报「无可扫描生态」。原生生态存在时不并行兜底（替换而非追加）；
            # 一个语言都没识别到的目录不算「无原生扫描器的语言」，仍报无可扫描。
            ecosystems = ["universal"]

    print(f"[codeguard-cve] project: {root}")
    print(f"[codeguard-cve] ecosystems: {ecosystems or '(none detected)'}")

    results = []
    for eco in ecosystems:
        spec = ECOSYSTEM_SCANNERS[eco]
        scannable, why = precheck(root, eco)
        if not scannable:
            results.append({"ecosystem": eco, "tool": eco, "exit": 127,
                            "summary_tail": f"无法验证: {why}", "fix_hint": "确认项目类型后重试"})
            print(f"  {eco:8s} SKIP（{why}）")
            continue
        r = spec["scan"](root, args.severity, args.fix)
        results.append(r)
        status = "PASS" if r["exit"] == 0 else f"FAILED(exit={r['exit']})"
        print(f"  {eco:8s} {r['tool']:28s} {status}")

    if not results:
        print("[codeguard-cve] 无可扫描生态（或对应工具未安装）")
        return EXIT_UNVERIFIED

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
        return EXIT_FINDINGS
    if unverifiable:
        print("\n[codeguard-cve] ⚠️ 存在无法验证的生态（工具缺失）——不能视为通过")
        return EXIT_UNVERIFIED
    print("[codeguard-cve] ✅ 所有生态 CVE 检查通过")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
