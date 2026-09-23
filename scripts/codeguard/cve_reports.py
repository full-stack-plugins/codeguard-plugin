"""五种扫描报告的纯适配器；不读文件、不启动工具、不写 stdout。"""
from __future__ import annotations

import json
import math

from .cve_policy import ReportEvidence, severities_at_and_above


def _object(value, label):
    if not isinstance(value, dict):
        raise TypeError(f"{label} 必须是对象")
    return value


def _list(value, label):
    if not isinstance(value, list):
        raise TypeError(f"{label} 必须是列表")
    return value


def _identity(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} 缺少有效标识")
    return value


def _integer(value):
    return type(value) is int and value >= 0


def _maven(report, threshold):
    scan_info = _object(report.get("scanInfo", {}), "scanInfo")
    if scan_info.get("analysisExceptions"):
        raise ValueError("dependency-check 报告含分析错误")
    findings = []
    exceeded = unknown = False
    for dependency in _list(report.get("dependencies"), "dependencies"):
        for finding in _list(_object(dependency, "dependency").get("vulnerabilities", []), "vulnerabilities"):
            finding = _object(finding, "vulnerability")
            identifier = _identity(finding.get("name"), "vulnerability.name")
            score = None
            for version in ("cvssv4", "cvssv3", "cvssv2"):
                if version not in finding or finding[version] is None:
                    continue
                cvss = _object(finding[version], version)
                candidate = cvss.get("baseScore", cvss.get("score"))
                if candidate is None:
                    continue
                if type(candidate) not in (int, float) or not math.isfinite(candidate) or not 0 <= candidate <= 10:
                    raise ValueError(f"{version} 分数必须是 0—10 的有限数值")
                score = candidate
                break
            findings.append({**finding, "id": identifier, "score": score})
            unknown |= score is None
            exceeded |= threshold == 0 or (score is not None and score >= threshold)
    return ReportEvidence(tuple(findings), len(findings), exceeded, unknown)


def _node(report, threshold):
    meta = _object(_object(report.get("metadata"), "metadata").get("vulnerabilities"), "漏洞统计")
    required = {"low", "moderate", "high", "critical"}
    if not required.issubset(meta) or set(meta) - required - {"info", "total"}:
        raise ValueError("漏洞统计缺少严重度档位或包含未知档位")
    if any(not _integer(count) for count in meta.values()):
        raise ValueError("漏洞统计必须是非负整数")
    total = sum(meta.get(key, 0) for key in (*required, "info"))
    if "total" in meta and meta["total"] != total:
        raise ValueError("漏洞总数与严重度统计不一致")
    findings = []
    if "vulnerabilities" in report:
        details = _object(report["vulnerabilities"], "vulnerabilities")
        detail_counts = dict.fromkeys((*required, "info"), 0)
        for name, finding in details.items():
            _identity(name, "vulnerabilities.name")
            severity = _object(finding, "vulnerability").get("severity")
            if not isinstance(severity, str) or severity not in detail_counts:
                raise ValueError("漏洞明细缺少可识别严重度")
            detail_counts[severity] += 1
            findings.append(finding)
        if any(detail_counts[key] != meta.get(key, 0) for key in detail_counts):
            raise ValueError("漏洞明细与严重度统计不一致")
    counts = {**meta, "medium": meta["moderate"]}
    del counts["moderate"]
    over = tuple(severity for severity in severities_at_and_above(threshold) if counts[severity.lower()])
    return ReportEvidence(findings=tuple(findings), observed=total, exceeded=bool(over),
                          counts=tuple(counts.items()), over_threshold=over)


def _pip(report, threshold):
    findings = []
    skipped = False
    for dependency in _list(report.get("dependencies"), "dependencies"):
        dependency = _object(dependency, "dependency")
        if "skip_reason" in dependency:
            skipped = True
            continue
        for finding in _list(dependency.get("vulns"), "vulns"):
            _identity(_object(finding, "vulnerability").get("id"), "vulnerability.id")
            findings.append(finding)
    return ReportEvidence(tuple(findings), len(findings), bool(findings) and threshold.upper() == "LOW",
                          bool(findings), problem="pip-audit 存在未完成审计的依赖" if skipped else "")


def _cargo(report, threshold):
    summary = _object(report.get("vulnerabilities"), "vulnerabilities")
    findings = _list(summary.get("list"), "vulnerabilities.list")
    if (type(summary.get("found")) is not bool or not _integer(summary.get("count"))
            or summary["found"] != bool(findings) or summary["count"] != len(findings)):
        raise ValueError("cargo 漏洞 found/count/list 不一致")
    for finding in findings:
        advisory = _object(_object(finding, "vulnerability").get("advisory"), "advisory")
        _identity(advisory.get("id"), "advisory.id")
    # RustSec 的 CVSS 向量尚未实现计算，不能把字符串当可比较分数。
    return ReportEvidence(tuple(findings), len(findings), bool(findings) and threshold.upper() == "LOW",
                          bool(findings))


def _trivy(report, threshold):
    findings = []
    exceeded = unknown = False
    allowed = severities_at_and_above(threshold)
    for result in _list(report.get("Results"), "Results"):
        result = _object(result, "Result")
        _identity(result.get("Target"), "Result.Target")
        # Trivy 在无漏洞时省略字段；null 切片同样代表无记录，但根 Results 必须可确认。
        vulnerabilities = result.get("Vulnerabilities")
        if vulnerabilities is None:
            continue
        for finding in _list(vulnerabilities, "Vulnerabilities"):
            _identity(_object(finding, "Vulnerability").get("VulnerabilityID"), "VulnerabilityID")
            severity = finding.get("Severity")
            if severity is not None and not isinstance(severity, str):
                raise ValueError("Severity 必须是字符串")
            severity = (severity or "UNKNOWN").upper()
            if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN"):
                raise ValueError("未知严重度标签")
            findings.append(finding)
            unknown |= severity == "UNKNOWN"
            exceeded |= severity in allowed or (threshold.upper() == "LOW" and severity == "UNKNOWN")
    return ReportEvidence(tuple(findings), len(findings), exceeded, unknown)


# "go" 与 "universal" 同为 trivy JSON 报告格式——解析器按格式复用，
# 生态身份仍由 _result 的 eco 字段按规范映射报告。
_PARSERS = {"maven": _maven, "node": _node, "python": _pip, "rust": _cargo,
            "universal": _trivy, "go": _trivy}


def parse_report(ecosystem: str, source: str, threshold: str | int) -> ReportEvidence:
    """仅捕获输入协议错误；未知适配器或程序错误仍暴露给开发者。"""
    parser = _PARSERS[ecosystem]
    try:
        report = _object(json.loads(source), "报告")
        if report.get("error") or report.get("errors"):
            raise ValueError("扫描报告包含错误")
        return parser(report, threshold)
    except (ValueError, TypeError) as exc:
        return ReportEvidence(problem=f"扫描未返回有效漏洞报告：{exc}")
