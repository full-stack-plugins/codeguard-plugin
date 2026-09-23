"""CVE 的纯证据与判定契约；进程成功本身不是安全通过。"""
from __future__ import annotations

from dataclasses import dataclass

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
CVSS_BAND_FLOOR = {"LOW": 0, "MEDIUM": 4, "HIGH": 7, "CRITICAL": 9}
EXIT_PASS, EXIT_UNVERIFIED, EXIT_FINDINGS, EXIT_USAGE = 0, 1, 2, 3


def severities_at_and_above(threshold: str) -> list[str]:
    """阈值及以上；UNKNOWN 不属于任意已知严重度档位。"""
    floor = SEVERITY_ORDER[threshold.upper()]
    return [severity for severity, rank in SEVERITY_ORDER.items() if rank >= floor]


@dataclass(frozen=True)
class ReportEvidence:
    """解析后的报告事实；findings 保留工具字段，不是宿主状态或执行结果。"""

    findings: tuple[dict, ...] = ()
    observed: int = 0
    exceeded: bool = False
    unknown: bool = False
    problem: str = ""
    counts: tuple[tuple[str, int], ...] = ()
    over_threshold: tuple[str, ...] = ()


def classify(report: ReportEvidence, rc: int, accepted_codes=(0, 1), *,
             allow_below_threshold_exit: bool = False) -> tuple[str, str]:
    """先验证扫描与报告，再解释阈值；已知发现不掩盖扫描故障。"""
    if rc not in accepted_codes:
        return "UNVERIFIED", f"扫描进程未正常完成（exit={rc}）"
    if report.problem:
        return "UNVERIFIED", report.problem
    if report.exceeded:
        return "FAIL", "有效报告包含阈值及以上漏洞"
    if report.unknown:
        return "UNVERIFIED", "报告含未解析依赖或缺少可比较严重度；保留发现，请复核"
    if rc and not (allow_below_threshold_exit and report.observed):
        return "UNVERIFIED", "非零退出但无匹配的阈值漏洞证据"
    return "PASS", "有效报告中无阈值及以上漏洞"


def aggregate_exit(results: list[dict]) -> int:
    """混合生态以发现优先；空批次或缺失/未知判定不得通过。"""
    if any(result.get("status") == "FAIL" for result in results):
        return EXIT_FINDINGS
    if not results or any(result.get("status") != "PASS" for result in results):
        return EXIT_UNVERIFIED
    return EXIT_PASS
