"""Dockerfile 检查应用：范围发现、逐文件执行、保留全部工具证据。"""
from __future__ import annotations

from pathlib import Path

from .dockerfile_reports import aggregate_status, parse_report
from .execution import execute

DOCKERFILE_NAMES = {"Dockerfile"}
DOCKERFILE_EXTS = {".dockerfile"}


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str, str]:
    """兼容旧 tuple 导入，子进程不得消费宿主协议输入。"""
    return execute(cmd, cwd, timeout, stdin_null=True).as_tuple()


def find_root(path: str) -> Path:
    target = Path(path).resolve()
    return target if target.is_dir() else target.parent


def find_dockerfiles(root: Path) -> list[Path]:
    """保留原文件名集合，无隐含数量截断；显式文件范围由 scan_path 处理。"""
    found = {path for path in root.iterdir() if path.is_file() and (
        path.name in DOCKERFILE_NAMES or path.suffix.lower() in DOCKERFILE_EXTS)}
    for pattern in ("**/Dockerfile", "**/*.dockerfile"):
        found.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(found)


def _scan(files: list[Path], root: Path, tool: str, prefix: list[str], timeout: int) -> dict:
    findings, attempts, statuses = [], [], []
    for file in files:
        argv = [*prefix, str(file)]
        rc, out, err = run(argv, cwd=root, timeout=timeout)
        evidence = parse_report(tool, rc, out)
        findings.extend(evidence.findings)
        statuses.append(evidence.status)
        attempts.append({"file": str(file), "argv": argv, "cwd": str(root), "exit": rc,
                         "stdout": out, "stderr": err, "status": evidence.status, "reason": evidence.reason})
    status = aggregate_status(statuses)
    exit_code = 127 if any(attempt["exit"] == 127 for attempt in attempts) else {
        "PASS": 0, "FAIL": 2, "UNVERIFIED": 1}[status]
    return {"tool": tool, "status": status, "exit": exit_code, "scanned": len(attempts),
            "tool_ok": status != "UNVERIFIED", "findings": findings, "attempts": attempts,
            "summary_tail": "\n".join(attempt["reason"] + ": " + attempt["stderr"]
                                      for attempt in attempts if attempt["status"] == "UNVERIFIED")[-2500:]}


def hadolint_scan(files: list[Path], root: Path) -> dict:
    result = _scan(files, root, "hadolint", ["hadolint", "--format", "json"], 300)
    result["records"] = result["findings"]
    result["findings"] = [f"{item['file']}:{item['line']} {item['code']} {item['level']} {item['message']}"
                          for item in result["records"]]
    result["fix_hint"] = "确认 hadolint 已安装（brew install hadolint），按规则修复 Dockerfile"
    return result


def trivy_scan(files: list[Path], root: Path) -> dict:
    result = _scan(files, root, "trivy config",
                   ["trivy", "config", "--format", "json", "--quiet", "--exit-code", "2"], 600)
    result["records"] = result["findings"]
    result["findings"] = [{"id": item["ID"], "title": item.get("Title"), "severity": item.get("Severity"),
                           "message": str(item.get("Message") or "")[:200],
                           "resolution": str(item.get("Resolution") or "")[:200]} for item in result["records"]]
    result["fix_hint"] = "确认 trivy 已安装（brew install trivy），按 resolution 修复后重扫"
    return result


def scan_path(path: str | Path) -> dict:
    """返回独立于 stdout 的报告，兼容 hadolint/trivy 字段并补充总判定。"""
    target = Path(path).resolve()
    try:
        if not target.exists():
            raise FileNotFoundError(f"输入不存在: {target}")
        root = find_root(str(target))
        files = [target] if target.is_file() else find_dockerfiles(root)
        if not files:
            raise ValueError(f"未找到 Dockerfile: {root}")
    except (OSError, ValueError) as exc:
        return {"status": "UNVERIFIED", "exit_code": 1, "files": [], "reason": str(exc)}
    hadolint, trivy = hadolint_scan(files, root), trivy_scan(files, root)
    status = aggregate_status([hadolint["status"], trivy["status"]])
    return {"status": status, "exit_code": {"PASS": 0, "FAIL": 2, "UNVERIFIED": 1}[status],
            "files": [str(file) for file in files], "root": str(root), "hadolint": hadolint, "trivy": trivy}
