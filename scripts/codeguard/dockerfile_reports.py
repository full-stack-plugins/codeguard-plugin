"""Dockerfile 扫描的纯协议解析；不从文本噪声或空 stdout 推断安全。"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityEvidence:
    """一次文件检查的判定与结构化发现，进程故障不抹去已解析的发现。"""

    status: str
    reason: str
    findings: tuple[dict, ...] = ()


def _object(value):
    if not isinstance(value, dict):
        raise TypeError("报告记录必须是对象")
    return value


def _list(value):
    if not isinstance(value, list):
        raise TypeError("报告发现必须是列表")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("报告缺少必要字符串字段")
    return value


def _hadolint(data):
    records = _list(data)
    for record in records:
        record = _object(record)
        for field in ("file", "code", "message"):
            _text(record.get(field))
        if type(record.get("line")) is not int or record["line"] < 1:
            raise ValueError("hadolint 行号无效")
        if record.get("level") not in ("error", "warning", "info", "style", "ignore"):
            raise ValueError("hadolint 严重度无效")
    return records


def _trivy(data):
    report = _object(data)
    if report.get("error") or report.get("errors"):
        raise ValueError("Trivy 报告包含扫描错误")
    results = _list(report.get("Results"))
    if not results:
        raise ValueError("Trivy 未返回目标 Dockerfile 的扫描证据")
    findings = []
    for result in results:
        result = _object(result)
        _text(result.get("Target"))
        if result.get("Class") != "config" or result.get("Type") != "dockerfile":
            raise ValueError("Trivy 未提供 Dockerfile 配置检查结果")
        records = result.get("Misconfigurations")
        failures = 0
        for record in _list(records if records is not None else []):
            record = _object(record)
            _text(record.get("ID"))
            if record.get("Status") not in ("FAIL", "PASS", "EXCEPTION"):
                raise ValueError("Trivy 规则状态无效")
            if record["Status"] == "FAIL":
                failures += 1
                findings.append(record)
        if "MisconfSummary" in result:
            summary = _object(result["MisconfSummary"])
            if any(type(summary.get(key)) is not int or summary[key] < 0
                   for key in ("Successes", "Failures", "Exceptions")):
                raise ValueError("Trivy 汇总缺失或计数无效")
            if summary["Failures"] != failures:
                raise ValueError("Trivy 失败统计与规则发现不一致")
        elif records is None:
            raise ValueError("Trivy 缺少检查统计与规则结果")
    return findings


def parse_report(tool: str, rc: int, source: str) -> SecurityEvidence:
    """报告与返回码同时可信才下结论，解析异常只归一化为未验证。"""
    parser, accepted = {"hadolint": (_hadolint, (0, 1)), "trivy config": (_trivy, (0, 2))}[tool]
    try:
        findings = tuple(parser(json.loads(source)))
    except (ValueError, TypeError) as exc:
        return SecurityEvidence("UNVERIFIED", f"无有效扫描报告：{exc}")
    if rc not in accepted:
        return SecurityEvidence("UNVERIFIED", f"扫描进程未完成（exit={rc}）", findings)
    if findings:
        return SecurityEvidence("FAIL", "有效报告发现 Dockerfile 风险", findings)
    if rc:
        return SecurityEvidence("UNVERIFIED", "非零退出但没有有效风险证据")
    return SecurityEvidence("PASS", "有效报告未发现风险")


def aggregate_status(statuses: list[str]) -> str:
    """沿用双工具完整性要求，未知优先，但调用方必须保留已知风险。"""
    if not statuses or any(status not in ("PASS", "FAIL") for status in statuses):
        return "UNVERIFIED"
    return "FAIL" if "FAIL" in statuses else "PASS"
