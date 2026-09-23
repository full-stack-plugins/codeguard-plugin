"""扫描器 IO 适配：显式项目输入、独立报告目录、统一进程边界。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .cve_policy import ReportEvidence, classify, severities_at_and_above
from .cve_reports import parse_report
from .execution import execute


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> tuple[int, str, str]:
    """保留旧 tuple 导入面；扫描器不消费宿主标准输入。"""
    return execute(cmd, cwd, timeout, stdin_null=True).as_tuple()


def _result(ecosystem, tool, root, argv, outcome, report, fix_hint, accepted_codes=(0, 1), *,
            allow_below_threshold_exit=False):
    rc, out, err = outcome
    status, reason = classify(report, rc, accepted_codes, allow_below_threshold_exit=allow_below_threshold_exit)
    return {"ecosystem": ecosystem, "tool": tool, "exit": rc, "status": status, "reason": reason,
            "findings": list(report.findings), "summary_tail": (out + err)[-2500:], "fix_hint": fix_hint,
            "execution": {"argv": argv, "cwd": str(root), "exit": rc, "stdout": out, "stderr": err}}


def scan_maven(root: Path, threshold: int) -> dict:
    """只读本次独立目录的报告；项目中的旧报告永远不是证据。"""
    with tempfile.TemporaryDirectory(prefix="codeguard-cve-") as output_dir:
        argv = ["./mvnw" if (root / "mvnw").exists() else "mvn", "-q",
                "org.owasp:dependency-check-maven:aggregate", f"-DfailBuildOnCVSS={threshold}",
                "-Dformat=JSON", f"-Dodc.outputDirectory={output_dir}"]
        outcome = run(argv, cwd=root, timeout=1800)
        try:
            source = (Path(output_dir) / "dependency-check-report.json").read_text(encoding="utf-8")
            report = parse_report("maven", source, threshold)
        except (OSError, UnicodeError) as exc:
            report = ReportEvidence(problem=f"无法读取本次 dependency-check 报告：{exc}")
    return _result("maven", "owasp dependency-check", root, argv, outcome, report,
                   "mvn versions:display-dependency-updates；升级受影响组件，或登记确认的误报")


def scan_node(root: Path, threshold: str, allow_fix: bool = False) -> dict:
    """只执行审计；allow_fix 为旧签名兼容，修复由应用层显式编排。"""
    argv = ["npm", "audit", "--json"]
    outcome = run(argv, cwd=root, timeout=600)
    report = parse_report("node", outcome[1], threshold)
    result = _result("node", "npm audit", root, argv, outcome, report, "npm audit fix；确认 Node.js 与 registry 可用",
                     allow_below_threshold_exit=True)
    result.update(counts=dict(report.counts), over_threshold=list(report.over_threshold), failed=result["status"] == "FAIL")
    return result


def scan_pip(root: Path, threshold: str = "LOW") -> dict:
    requirements = next((name for name in ("requirements.txt", "requirements-dev.txt")
                         if (root / name).is_file()), None)
    if requirements:
        target = ["--requirement", requirements]
    elif (root / "pyproject.toml").is_file():
        target = ["."]
    else:
        return {"ecosystem": "python", "tool": "pip-audit", "exit": 1, "status": "UNVERIFIED",
                "reason": "没有支持的 requirements/pyproject 项目输入", "findings": []}
    argv = ["pip-audit", "--strict", "--format", "json", *target]
    outcome = run(argv, cwd=root, timeout=900)
    return _result("python", "pip-audit", root, argv, outcome, parse_report("python", outcome[1], threshold),
                   "确认 pip-audit 可用；按报告升级 requirements/pyproject 中受影响包，不自动修改依赖")


def scan_cargo(root: Path, threshold: str = "LOW") -> dict:
    probe_argv = ["cargo", "audit", "--version"]
    probe = run(probe_argv, cwd=root, timeout=60)
    if probe[0]:
        return _result("rust", "cargo audit", root, probe_argv, probe,
                       ReportEvidence(problem="cargo-audit 探活失败"), "确认 cargo-audit 已安装且可执行")
    argv = ["cargo", "audit", "--json"]
    outcome = run(argv, cwd=root, timeout=900)
    return _result("rust", "cargo audit", root, argv, outcome, parse_report("rust", outcome[1], threshold),
                   "按报告升级 Cargo.toml 中的受影响 crate（cargo update 可试）")


def scan_go(root: Path, threshold: str) -> dict:
    """go 生态扫描：trivy 原生解析 gomod/go.sum，报告格式与 universal 同族。

    保留 UNKNOWN 进入过滤（同 scan_trivy 注释）：若先滤掉缺严重度的发现，
    解析器会把它们当不存在——假 PASS。标识为 "go"（规范映射单独成条），
    解析复用 trivy 格式解析器——格式是格式，身份是身份。
    """
    selected = severities_at_and_above(threshold) + ["UNKNOWN"]
    argv = ["trivy", "fs", "--scanners", "vuln", "--format", "json", "--exit-code", "2",
            "--severity", ",".join(selected), "."]
    outcome = run(argv, cwd=root, timeout=1800)
    return _result("go", "trivy", root, argv, outcome, parse_report("go", outcome[1], threshold),
                   "确认 trivy 与漏洞库可用；按报告升级 go.mod 受影响依赖（go get 对应模块）", (0, 2))


def scan_trivy(root: Path, threshold: str) -> dict:
    # 若先过滤 UNKNOWN，解析器看不到缺严重度的发现，会产生假 PASS。
    selected = severities_at_and_above(threshold) + ["UNKNOWN"]
    argv = ["trivy", "fs", "--scanners", "vuln", "--format", "json", "--exit-code", "2",
            "--severity", ",".join(selected), "."]
    outcome = run(argv, cwd=root, timeout=1800)
    return _result("universal", "trivy", root, argv, outcome, parse_report("universal", outcome[1], threshold),
                   "确认 trivy 与漏洞库可用；按报告升级受影响依赖版本", (0, 2))
